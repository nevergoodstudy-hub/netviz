"""
设备领域事件

定义设备生命周期中的业务事件，用于解耦跨模块通知。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """领域事件基类"""

    event_type: str = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加数据")


class DeviceStatusChanged(DomainEvent):
    """设备状态变更事件"""

    event_type: str = "device.status_changed"
    device_name: str = ""
    device_ip: str = ""
    old_status: str = ""
    new_status: str = ""


class DeviceDiscovered(DomainEvent):
    """设备发现事件"""

    event_type: str = "device.discovered"
    device_name: str = ""
    device_ip: str = ""
    vendor: str = ""


class DeviceCommandExecuted(DomainEvent):
    """设备命令执行事件"""

    event_type: str = "device.command_executed"
    device_name: str = ""
    command: str = ""
    success: bool = True
    duration: Optional[float] = None


class ConfigBackupCompleted(DomainEvent):
    """配置备份完成事件"""

    event_type: str = "device.config_backup"
    device_name: str = ""
    backup_path: str = ""
    success: bool = True


__all__ = [
    "DomainEvent",
    "DeviceStatusChanged",
    "DeviceDiscovered",
    "DeviceCommandExecuted",
    "ConfigBackupCompleted",
]
