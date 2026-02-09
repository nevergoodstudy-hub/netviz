"""审计日志增强器 + 敏感数据脱敏 单元测试"""

import re

import pytest

from netops_toolkit.infrastructure.security.audit_log_enhancer import (
    AuditLogEnhancer,
    MaskRule,
    MaskStrategy,
    SensitiveDataMasker,
    create_loguru_filter,
)


class TestSensitiveDataMasker:
    """SensitiveDataMasker 单元测试"""

    def setup_method(self):
        self.masker = SensitiveDataMasker()

    # ── 文本脱敏 ──

    def test_mask_password_assignment(self):
        text = "password=admin123"
        result = self.masker.mask_text(text)
        assert "admin123" not in result
        assert "******" in result

    def test_mask_password_colon(self):
        text = "password: my_secret_pass"
        result = self.masker.mask_text(text)
        assert "my_secret_pass" not in result

    def test_mask_bearer_token(self):
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature"
        result = self.masker.mask_text(text)
        assert "eyJhbG" not in result
        assert "[REDACTED]" in result

    def test_mask_api_key(self):
        text = "api_key=sk-1234567890abcdef"
        result = self.masker.mask_text(text)
        assert "sk-1234567890" not in result
        assert "[REDACTED]" in result

    def test_mask_connection_string(self):
        text = "postgres://user:s3cretP@ss@db.example.com:5432/mydb"
        result = self.masker.mask_text(text)
        assert "s3cretP@ss" not in result
        assert "******" in result

    def test_mask_ssh_password_arg(self):
        text = "ssh -p mysecret admin@host"
        result = self.masker.mask_text(text)
        assert "mysecret" not in result

    def test_mask_private_key_block(self):
        text = (
            "key is:\n"
            "-----BEGIN PRIVATE KEY-----\n"
            "MIIEvQIBADANBgkqhki...\n"
            "-----END PRIVATE KEY-----\n"
            "done"
        )
        result = self.masker.mask_text(text)
        assert "MIIEvQ" not in result
        assert "[REDACTED PRIVATE KEY]" in result

    def test_safe_text_unchanged(self):
        text = "Device 192.168.1.1 is online, latency 5ms"
        result = self.masker.mask_text(text)
        assert result == text

    def test_empty_text(self):
        assert self.masker.mask_text("") == ""

    # ── 字典脱敏 ──

    def test_mask_dict_password_key(self):
        data = {"host": "10.0.0.1", "password": "admin123"}
        result = self.masker.mask_dict(data)
        assert result["host"] == "10.0.0.1"
        assert "admin123" not in result["password"]
        assert "REDACTED" in result["password"]

    def test_mask_dict_multiple_sensitive_keys(self):
        data = {
            "username": "admin",
            "password": "secret",
            "token": "abc123",
            "api_key": "key-456",
        }
        result = self.masker.mask_dict(data)
        assert result["username"] == "admin"
        assert "secret" not in result["password"]
        assert "abc123" not in result["token"]
        assert "key-456" not in result["api_key"]

    def test_mask_dict_recursive(self):
        data = {
            "device": "router",
            "credentials": {
                "password": "supersecret",
                "username": "admin",
            },
        }
        result = self.masker.mask_dict(data, recursive=True)
        assert "supersecret" not in str(result)
        assert result["credentials"]["username"] == "admin"

    def test_mask_dict_non_recursive(self):
        data = {
            "nested": {
                "password": "inner_secret",
            },
        }
        result = self.masker.mask_dict(data, recursive=False)
        # 非递归: 嵌套字典不被处理
        assert result["nested"]["password"] == "inner_secret"

    def test_mask_dict_preserves_non_sensitive(self):
        data = {"hostname": "router-01", "port": 22, "enabled": True}
        result = self.masker.mask_dict(data)
        assert result == data

    def test_original_dict_not_mutated(self):
        data = {"password": "original"}
        _ = self.masker.mask_dict(data)
        assert data["password"] == "original"

    # ── 自定义规则 ──

    def test_add_custom_rule(self):
        rule = MaskRule(
            name="custom_id",
            pattern=re.compile(r"DEVICE-\d{6}"),
            replacement="DEVICE-[REDACTED]",
        )
        self.masker.add_rule(rule)
        result = self.masker.mask_text("Found DEVICE-123456 in scan")
        assert "DEVICE-123456" not in result
        assert "DEVICE-[REDACTED]" in result

    def test_add_custom_sensitive_key(self):
        self.masker.add_sensitive_key("snmp_community")
        data = {"snmp_community": "public123"}
        result = self.masker.mask_dict(data)
        assert "public123" not in result["snmp_community"]

    def test_extra_rules_at_init(self):
        rule = MaskRule(
            name="mac_addr",
            pattern=re.compile(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"),
            replacement="[REDACTED MAC]",
        )
        masker = SensitiveDataMasker(extra_rules=[rule])
        result = masker.mask_text("MAC: AA:BB:CC:DD:EE:FF")
        assert "[REDACTED MAC]" in result

    def test_extra_sensitive_keys_at_init(self):
        masker = SensitiveDataMasker(
            extra_sensitive_keys={"snmp_community", "enable_password"}
        )
        data = {"snmp_community": "public", "host": "10.0.0.1"}
        result = masker.mask_dict(data)
        assert "public" not in result["snmp_community"]


class TestAuditLogEnhancer:
    """AuditLogEnhancer 单元测试"""

    def setup_method(self):
        self.enhancer = AuditLogEnhancer()

    def test_enhance_masks_description(self):
        record = {
            "description": "Login with password=admin123 to device",
            "old_value": "",
            "new_value": "",
        }
        result = self.enhancer.enhance(record)
        assert "admin123" not in result["description"]

    def test_enhance_masks_old_new_values(self):
        record = {
            "description": "Config change",
            "old_value": "secret_key=abc12345678",
            "new_value": "secret_key=xyz98765432",
        }
        result = self.enhancer.enhance(record)
        assert "abc12345678" not in result["old_value"]
        assert "xyz98765432" not in result["new_value"]

    def test_enhance_masks_metadata(self):
        record = {
            "description": "SSH session",
            "metadata": {
                "host": "10.0.0.1",
                "password": "ssh_secret",
            },
        }
        result = self.enhancer.enhance(record)
        assert "ssh_secret" not in str(result["metadata"])
        assert result["metadata"]["host"] == "10.0.0.1"

    def test_enhance_preserves_non_text_fields(self):
        record = {
            "id": 42,
            "event_type": "config_backup",
            "duration_ms": 150,
            "description": "safe text",
        }
        result = self.enhancer.enhance(record)
        assert result["id"] == 42
        assert result["event_type"] == "config_backup"
        assert result["duration_ms"] == 150

    def test_enhance_handles_missing_fields(self):
        record = {"id": 1}
        result = self.enhancer.enhance(record)
        assert result == {"id": 1}


class TestLoguruFilter:
    """loguru 过滤器单元测试"""

    def test_filter_masks_message(self):
        log_filter = create_loguru_filter()
        record = {"message": "Connecting with password=admin123"}
        result = log_filter(record)
        assert result is True
        assert "admin123" not in record["message"]

    def test_filter_passes_safe_message(self):
        log_filter = create_loguru_filter()
        record = {"message": "Device 10.0.0.1 is online"}
        log_filter(record)
        assert record["message"] == "Device 10.0.0.1 is online"

    def test_filter_handles_non_string_message(self):
        log_filter = create_loguru_filter()
        record = {"message": None}
        result = log_filter(record)
        assert result is True
