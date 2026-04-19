"""
NetViz API 端点测试
"""

import pytest
from contextlib import asynccontextmanager
from types import SimpleNamespace

from app.core.config import settings
from app.core.config import Settings
from app.core.database import get_db
from app.models.pcap import Packet, PcapFile, ParseStatus
import app.api.pcap as pcap_api_module


class TestHealthEndpoints:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查端点"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_info_endpoint(self, client):
        """测试系统信息端点"""
        response = await client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data


class TestPcapEndpoints:
    """PCAP 文件管理端点测试"""

    @pytest.mark.asyncio
    async def test_list_pcap_files(self, client):
        """测试列出 PCAP 文件"""
        response = await client.get("/api/pcap/list")
        assert response.status_code == 200
        data = response.json()
        # 返回 PcapListResponse 格式: {items: [], total: 0}
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_upload_invalid_file(self, client):
        """测试上传无效文件"""
        files = {"file": ("test.txt", b"not a pcap file", "text/plain")}
        response = await client.post("/api/pcap/upload", files=files)
        # 应该返回 400 或验证错误
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_upload_accepts_nanosecond_pcap_and_cap_extension(
        self, client, monkeypatch, tmp_path
    ):
        """测试纳秒级 PCAP 和 .cap 扩展名可被接受"""

        async def noop_parse_task(*args, **kwargs):
            return None

        monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
        monkeypatch.setattr(pcap_api_module, "parse_pcap_task", noop_parse_task)

        files = {
            "file": (
                "capture.cap",
                b"\x4d\x3c\xb2\xa1" + (b"\x00" * 64),
                "application/octet-stream",
            )
        }
        response = await client.post("/api/pcap/upload", files=files)

        assert response.status_code == 200
        assert response.json()["original_filename"] == "capture.cap"

    @pytest.mark.asyncio
    async def test_upload_rejects_files_over_max_size(self, client, monkeypatch, tmp_path):
        async def noop_parse_task(*args, **kwargs):
            return None

        monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")
        monkeypatch.setattr(settings, "max_upload_size", 8)
        monkeypatch.setattr(pcap_api_module, "parse_pcap_task", noop_parse_task)

        files = {
            "file": (
                "oversized.pcap",
                b"\xd4\xc3\xb2\xa1" + (b"\x00" * 16),
                "application/octet-stream",
            )
        }
        response = await client.post("/api/pcap/upload", files=files)

        assert response.status_code == 400
        assert "文件过大" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_parse_failure_rolls_back_partial_packet_rows(
        self, test_db, monkeypatch, tmp_path
    ):
        import app.core.database as database_module

        pcap_file = PcapFile(
            filename="broken.pcap",
            original_filename="broken.pcap",
            file_path=str(tmp_path / "broken.pcap"),
            file_size=128,
            file_hash="a" * 64,
            status=ParseStatus.PENDING.value,
        )
        test_db.add(pcap_file)
        await test_db.commit()
        await test_db.refresh(pcap_file)

        class FakeParser:
            def __init__(self, file_path: str):
                self.file_path = file_path

            def set_progress_callback(self, callback):
                self._callback = callback

            def iter_packets(self):
                yield SimpleNamespace(
                    packet=SimpleNamespace(
                        packet_number=1,
                        timestamp=pcap_api_module.datetime.utcnow(),
                        timestamp_micro=0,
                        src_mac=None,
                        dst_mac=None,
                        eth_type=None,
                        src_ip="1.1.1.1",
                        dst_ip="2.2.2.2",
                        ip_version=4,
                        ttl=64,
                        protocol="TCP",
                        src_port=1111,
                        dst_port=80,
                        tcp_flags="SYN",
                        tcp_seq=1,
                        tcp_ack=0,
                        app_protocol=None,
                        length=60,
                        payload_length=0,
                    ),
                    dns_record=None,
                    http_transaction=None,
                )
                raise RuntimeError("broken parse")

            def build_result(self):
                raise AssertionError("build_result should not be reached")

        @asynccontextmanager
        async def fake_db_context():
            yield test_db

        monkeypatch.setattr(pcap_api_module, "PcapParser", FakeParser)
        monkeypatch.setattr(database_module, "get_db_context", fake_db_context)

        with pytest.raises(RuntimeError, match="broken parse"):
            await pcap_api_module.parse_pcap_task(pcap_file.id, pcap_file.file_path)

        await test_db.refresh(pcap_file)
        assert pcap_file.status == ParseStatus.FAILED.value

        packet_count = await test_db.scalar(
            pcap_api_module.select(pcap_api_module.func.count(Packet.id)).where(
                Packet.pcap_file_id == pcap_file.id
            )
        )
        assert packet_count == 0


class TestCaptureEndpoints:
    """网络捕获端点测试"""

    @pytest.mark.asyncio
    async def test_list_interfaces(self, client):
        """测试列出网络接口"""
        response = await client.get("/api/capture/interfaces")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAnalysisEndpoints:
    """分析端点测试"""

    @pytest.mark.asyncio
    async def test_list_alerts(self, client):
        """测试列出告警"""
        response = await client.get("/api/analysis/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_time_series_rejects_zero_interval(self, client):
        response = await client.get("/api/analysis/time-series/1", params={"interval": 0})
        assert response.status_code == 422


class TestSettingsEndpoints:
    """设置端点测试"""

    @pytest.mark.asyncio
    async def test_get_ai_providers(self, client):
        """测试获取 AI 提供商列表"""
        response = await client.get("/api/settings/ai-providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 应该有默认的提供商
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_settings(self, client):
        """测试获取设置 (端点为 /api/settings/)"""
        response = await client.get("/api/settings/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_settings_accept_comma_separated_cors_origins_and_runtime_state_dir(self, tmp_path):
        runtime_settings = Settings(
            app_data_dir=tmp_path,
            cors_origins="http://localhost:5173,http://127.0.0.1:5173",
        )

        assert runtime_settings.cors_origins == [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        assert tmp_path.as_posix() in runtime_settings.database_url
        assert runtime_settings.upload_dir == (tmp_path / "data" / "uploads").resolve()


class TestAIEndpoints:
    """AI 分析端点测试"""

    @pytest.mark.asyncio
    async def test_ai_chat_endpoint_exists(self, client):
        """测试 AI 聊天端点存在"""
        # 发送测试请求，验证端点存在
        response = await client.post(
            "/api/ai/chat",
            json={"message": "test", "pcap_id": None}
        )
        # 端点存在应返回以下码之一
        # 200: 成功, 400: 请求无效, 422: 验证错误, 500: AI 未配置
        assert response.status_code in [200, 400, 422, 500]


class TestPcapTimelineValidation:
    @pytest.mark.asyncio
    async def test_pcap_timeline_rejects_zero_interval(self, client):
        response = await client.get("/api/pcap/1/stats/timeline", params={"interval": 0})
        assert response.status_code == 422
