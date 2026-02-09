"""领域事件单元测试"""

from datetime import datetime

import pytest

from netops_toolkit.domain.events.device_events import (
    ConfigBackupCompleted,
    DeviceCommandExecuted,
    DeviceDiscovered,
    DeviceStatusChanged,
    DomainEvent,
)


class TestDomainEvent:
    def test_create_event(self):
        event = DomainEvent(event_type="test")
        assert event.event_type == "test"
        assert isinstance(event.timestamp, datetime)

    def test_has_metadata(self):
        event = DomainEvent(event_type="a", metadata={"key": "val"})
        assert event.metadata == {"key": "val"}


class TestDeviceStatusChanged:
    def test_create(self):
        event = DeviceStatusChanged(
            device_name="router-01",
            device_ip="10.0.0.1",
            old_status="offline",
            new_status="online",
        )
        assert event.event_type == "device.status_changed"
        assert event.device_name == "router-01"
        assert event.old_status == "offline"
        assert event.new_status == "online"


class TestDeviceDiscovered:
    def test_create(self):
        event = DeviceDiscovered(
            device_name="switch-01",
            device_ip="10.0.0.2",
            vendor="cisco",
        )
        assert event.event_type == "device.discovered"
        assert event.vendor == "cisco"


class TestDeviceCommandExecuted:
    def test_create(self):
        event = DeviceCommandExecuted(
            device_name="router-01",
            command="show version",
            success=True,
            duration=0.15,
        )
        assert event.event_type == "device.command_executed"
        assert event.command == "show version"
        assert event.success is True
        assert event.duration == 0.15

    def test_failed_command(self):
        event = DeviceCommandExecuted(
            device_name="router-01",
            command="write mem",
            success=False,
        )
        assert event.success is False


class TestConfigBackupCompleted:
    def test_create(self):
        event = ConfigBackupCompleted(
            device_name="router-01",
            backup_path="/backups/router-01.cfg",
            success=True,
        )
        assert event.event_type == "device.config_backup"
        assert event.backup_path == "/backups/router-01.cfg"
        assert event.success is True

    def test_serialization(self):
        event = ConfigBackupCompleted(
            device_name="r1",
            backup_path="/tmp/r1.cfg",
            success=True,
        )
        data = event.model_dump()
        assert data["event_type"] == "device.config_backup"
        assert data["device_name"] == "r1"
        assert "timestamp" in data
