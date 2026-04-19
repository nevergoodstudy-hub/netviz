import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.core.secret_store as secret_store_module
from app.core.config import settings
from app.core.provider_urls import normalize_ai_base_url
from app.core.database import get_db
from app.main import app
from app.models.analysis import Settings as DbSettings


@pytest_asyncio.fixture
async def remote_client(test_db):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app, client=("203.0.113.10", 12345))
    async with AsyncClient(transport=transport, base_url="http://remote.test") as ac:
        yield ac

    app.dependency_overrides.clear()


class TestSettingsSecurity:
    @pytest.mark.asyncio
    async def test_remote_settings_routes_are_forbidden_without_admin_access(
        self, remote_client
    ):
        response = await remote_client.get("/api/settings/")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remote_settings_routes_allow_valid_admin_token(
        self, remote_client, monkeypatch
    ):
        monkeypatch.setattr(settings, "admin_access_token", "netviz-admin-token")

        response = await remote_client.get(
            "/api/settings/",
            headers={"X-NetViz-Admin-Token": "netviz-admin-token"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_remote_system_info_requires_admin_access(self, remote_client):
        response = await remote_client.get("/api/settings/system-info")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_remote_data_plane_routes_require_admin_access(self, remote_client):
        for path in (
            "/api/pcap/list",
            "/api/analysis/alerts",
            "/api/capture/interfaces",
            "/api/ai/providers",
        ):
            response = await remote_client.get(path)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_rejects_private_cloud_ai_base_url_without_unsafe_opt_in(self, client):
        response = await client.post(
            "/api/settings/ai-providers",
            json={
                "provider": "openai",
                "api_key": "sk-secret-1234567890",
                "base_url": "http://127.0.0.1:8765/v1",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_sensitive_settings_are_encrypted_at_rest(self, client, test_db):
        plaintext = "sk-secret-1234567890"

        response = await client.put(
            "/api/settings/",
            json={"key": "openai_api_key", "value": plaintext},
        )

        assert response.status_code == 200

        result = await test_db.execute(
            select(DbSettings).where(DbSettings.key == "openai_api_key")
        )
        record = result.scalar_one()

        assert record.is_encrypted is True
        assert record.value != plaintext

        settings_response = await client.get("/api/settings/")
        assert settings_response.status_code == 200
        assert settings_response.json()["openai_api_key"].endswith("...")

        providers_response = await client.get("/api/settings/ai-providers")
        assert providers_response.status_code == 200
        providers = {item["provider"]: item for item in providers_response.json()}
        assert providers["openai"]["configured"] is True

    @pytest.mark.asyncio
    async def test_threat_intel_config_requires_admin_access_and_encrypts_keys(
        self, client, remote_client, test_db
    ):
        plaintext = "vt-secret-1234567890"

        remote_response = await remote_client.post(
            "/api/threat-intel/configure",
            json={"virustotal_api_key": plaintext},
        )
        assert remote_response.status_code == 403

        response = await client.post(
            "/api/threat-intel/configure",
            json={"virustotal_api_key": plaintext},
        )
        assert response.status_code == 200

        result = await test_db.execute(
            select(DbSettings).where(DbSettings.key == "virustotal_api_key")
        )
        record = result.scalar_one()

        assert record.is_encrypted is True
        assert record.value != plaintext

        status_response = await client.get("/api/threat-intel/status")
        assert status_response.status_code == 200
        assert status_response.json()["configured"] is True

    @pytest.mark.asyncio
    async def test_remote_threat_intel_query_routes_require_admin_access(self, remote_client):
        check_response = await remote_client.get("/api/threat-intel/check/1.1.1.1")
        assert check_response.status_code == 403

        batch_response = await remote_client.post(
            "/api/threat-intel/check/batch",
            json={"ips": ["1.1.1.1"]},
        )
        assert batch_response.status_code == 403

        enrich_response = await remote_client.get("/api/threat-intel/enrich/pcap/1")
        assert enrich_response.status_code == 403

    @pytest.mark.asyncio
    async def test_sensitive_settings_use_generated_install_key_when_env_key_missing(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(settings, "settings_encryption_key", None)
        monkeypatch.setattr(settings, "settings_encryption_key_file", tmp_path / "settings.key")
        secret_store_module._generated_install_key.cache_clear()

        encrypted, is_encrypted = secret_store_module.encrypt_setting_value(
            "openai_api_key",
            "sk-generated-1234567890",
        )

        assert is_encrypted is True
        assert encrypted != "sk-generated-1234567890"
        assert settings.settings_encryption_key_file.exists()
        assert (
            secret_store_module.decrypt_setting_value("openai_api_key", encrypted, True)
            == "sk-generated-1234567890"
        )

    @pytest.mark.asyncio
    async def test_legacy_default_key_records_are_rotated_to_install_key(
        self, test_db, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(settings, "settings_encryption_key", None)
        monkeypatch.setattr(settings, "settings_encryption_key_file", tmp_path / "settings.key")
        secret_store_module._generated_install_key.cache_clear()

        legacy_ciphertext = secret_store_module._build_fernet_from_material(
            "netviz-secret-key-change-in-production"
        ).encrypt(b"sk-legacy-1234567890").decode("utf-8")
        record = DbSettings(
            key="openai_api_key",
            value=legacy_ciphertext,
            is_encrypted=True,
        )
        test_db.add(record)
        await test_db.commit()

        rotated = await secret_store_module.rotate_legacy_encrypted_settings(test_db)
        await test_db.commit()
        await test_db.refresh(record)

        assert rotated == 1
        assert record.value != legacy_ciphertext
        assert (
            secret_store_module.decrypt_setting_value("openai_api_key", record.value, True)
            == "sk-legacy-1234567890"
        )

    def test_ai_base_url_helper_rejects_loopback_cloud_hosts(self):
        with pytest.raises(ValueError):
            normalize_ai_base_url("deepseek", "https://127.0.0.1:8443")

    @pytest.mark.asyncio
    async def test_loopback_requests_with_forwarded_headers_require_admin_token(
        self, client
    ):
        response = await client.get(
            "/api/settings/",
            headers={"X-Forwarded-For": "198.51.100.10"},
        )

        assert response.status_code == 403
