"""
领域事件
"""

from netops_toolkit.domain.events.device_events import (
    ConfigBackupCompleted,
    DeviceCommandExecuted,
    DeviceDiscovered,
    DeviceStatusChanged,
    DomainEvent,
)

__all__ = [
    "DomainEvent",
    "DeviceStatusChanged",
    "DeviceDiscovered",
    "DeviceCommandExecuted",
    "ConfigBackupCompleted",
]
