"""领域异常单元测试"""

import pytest

from netops_toolkit.domain.exceptions import (
    CommandInjectionError,
    DeviceConnectionError,
    DeviceNotFoundError,
    NetOpsError,
    PluginDependencyError,
    PluginNotFoundError,
    ValidationError,
)


class TestNetOpsError:
    def test_base_error(self):
        err = NetOpsError("test error", "TEST_CODE")
        assert str(err) == "test error"
        assert err.code == "TEST_CODE"

    def test_to_dict(self):
        err = NetOpsError("msg", "CODE", {"key": "val"})
        d = err.to_dict()
        assert d["error"] == "CODE"
        assert d["message"] == "msg"
        assert d["details"]["key"] == "val"

    def test_repr(self):
        err = NetOpsError("msg", "CODE")
        assert "CODE" in repr(err)


class TestValidationError:
    def test_with_field(self):
        err = ValidationError("bad input", field="ip")
        assert err.field == "ip"
        assert err.details["field"] == "ip"

    def test_without_field(self):
        err = ValidationError("bad input")
        assert err.field is None


class TestDeviceErrors:
    def test_connection_error(self):
        err = DeviceConnectionError("router-01", "timeout")
        assert "router-01" in str(err)
        assert err.device == "router-01"

    def test_not_found_error(self):
        err = DeviceNotFoundError("unknown-device")
        assert err.code == "DEVICE_NOT_FOUND"


class TestPluginErrors:
    def test_not_found(self):
        err = PluginNotFoundError("my_plugin")
        assert "my_plugin" in str(err)

    def test_dependency_error(self):
        err = PluginDependencyError("test", ["numpy", "scipy"])
        assert "numpy" in str(err)
        assert err.details["missing_dependencies"] == ["numpy", "scipy"]


class TestSecurityErrors:
    def test_command_injection(self):
        err = CommandInjectionError("rm -rf /")
        # Should NOT expose the actual argument
        assert "rm" not in str(err)
        assert err.code == "COMMAND_INJECTION"
