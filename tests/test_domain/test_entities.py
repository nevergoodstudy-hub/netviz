"""领域实体单元测试"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from netops_toolkit.domain.entities.device import (
    Device,
    DeviceGroup,
    DeviceStatus,
    DeviceVendor,
)
from netops_toolkit.domain.entities.credential import Credential, CredentialType
from netops_toolkit.domain.entities.scan_result import (
    OperationResult,
    PingResult,
    PortScanResult,
    ResultStatus,
)


class TestDevice:
    def test_create_device(self):
        dev = Device(name="router-01", ip="192.168.1.1")
        assert dev.name == "router-01"
        assert dev.ip == "192.168.1.1"
        assert dev.port == 22
        assert dev.status == DeviceStatus.UNKNOWN

    def test_device_strips_whitespace(self):
        dev = Device(name="  router-01  ", ip=" 10.0.0.1 ")
        assert dev.name == "router-01"
        assert dev.ip == "10.0.0.1"

    def test_device_empty_name_fails(self):
        with pytest.raises(PydanticValidationError):
            Device(name="", ip="10.0.0.1")

    def test_device_empty_ip_fails(self):
        with pytest.raises((PydanticValidationError, ValueError)):
            Device(name="dev", ip="  ")

    def test_device_netmiko_params(self):
        dev = Device(name="r1", ip="10.0.0.1", port=2222, vendor="huawei")
        params = dev.get_netmiko_params()
        assert params["host"] == "10.0.0.1"
        assert params["port"] == 2222
        assert params["device_type"] == "huawei"

    def test_device_equality(self):
        d1 = Device(name="r1", ip="10.0.0.1")
        d2 = Device(name="r1", ip="10.0.0.1")
        assert d1 == d2

    def test_device_hash(self):
        d1 = Device(name="r1", ip="10.0.0.1")
        d2 = Device(name="r1", ip="10.0.0.1")
        assert hash(d1) == hash(d2)


class TestDeviceGroup:
    def test_create_group(self):
        group = DeviceGroup(name="core")
        assert group.name == "core"
        assert group.device_count == 0

    def test_group_with_devices(self):
        devices = [
            Device(name="r1", ip="10.0.0.1"),
            Device(name="r2", ip="10.0.0.2"),
        ]
        group = DeviceGroup(name="core", devices=devices)
        assert group.device_count == 2
        assert group.device_ips == ["10.0.0.1", "10.0.0.2"]
        assert len(group) == 2


class TestCredential:
    def test_create_credential(self):
        cred = Credential(name="default", username="admin", password="secret")
        assert cred.name == "default"
        assert cred.username == "admin"
        # SecretStr hides value in repr
        assert "secret" not in repr(cred.password)
        assert cred.get_password_value() == "secret"

    def test_credential_no_password(self):
        cred = Credential(name="key-only", username="admin")
        assert cred.get_password_value() == ""

    def test_credential_ssh_key(self):
        cred = Credential(
            name="key",
            username="admin",
            ssh_key_path="/home/user/.ssh/id_rsa",
            credential_type=CredentialType.SSH_KEY,
        )
        assert cred.has_ssh_key() is True

    def test_credential_no_ssh_key(self):
        cred = Credential(name="pw", username="admin")
        assert cred.has_ssh_key() is False


class TestScanResult:
    def test_ping_result_alive(self):
        r = PingResult(host="10.0.0.1", is_alive=True, avg_latency=5.0)
        assert r.success is True

    def test_ping_result_dead(self):
        r = PingResult(host="10.0.0.1")
        assert r.success is False
        assert r.packet_loss == 100.0

    def test_operation_result_success(self):
        r = OperationResult(status=ResultStatus.SUCCESS, message="ok")
        assert r.is_success is True

    def test_operation_result_partial(self):
        r = OperationResult(status=ResultStatus.PARTIAL)
        assert r.is_success is True

    def test_operation_result_failed(self):
        r = OperationResult(status=ResultStatus.FAILED)
        assert r.is_success is False

    def test_operation_result_to_dict(self):
        r = OperationResult(status=ResultStatus.SUCCESS, message="done")
        d = r.to_legacy_dict()
        assert d["status"] == "success"
        assert d["message"] == "done"
