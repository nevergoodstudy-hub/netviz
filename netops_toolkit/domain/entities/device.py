"""
设备领域实体

纯业务对象，不依赖任何外部框架或基础设施。
使用 Pydantic BaseModel 提供类型安全和自动验证。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DeviceVendor(str, Enum):
    """设备厂商类型"""

    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    CISCO_XR = "cisco_xr"
    HUAWEI = "huawei"
    HUAWEI_VRPV8 = "huawei_vrpv8"
    H3C = "hp_comware"
    JUNIPER = "juniper_junos"
    ARISTA = "arista_eos"
    LINUX = "linux"
    GENERIC = "autodetect"


class DeviceStatus(str, Enum):
    """设备状态"""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


class Device(BaseModel):
    """
    设备领域实体

    表示网络中的一个可管理设备。
    """

    name: str = Field(..., min_length=1, description="设备名称")
    ip: str = Field(..., min_length=1, description="设备IP地址")
    port: int = Field(default=22, ge=1, le=65535, description="管理端口")
    vendor: str = Field(default=DeviceVendor.CISCO_IOS.value, description="设备厂商类型")
    credentials: str = Field(default="", description="凭证标识")
    description: str = Field(default="", description="设备描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    group: str = Field(default="", description="所属设备组")
    status: DeviceStatus = Field(default=DeviceStatus.UNKNOWN, description="设备状态")
    extra: Dict[str, Any] = Field(default_factory=dict, description="扩展属性")

    @field_validator("ip")
    @classmethod
    def validate_ip_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("device IP cannot be empty")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("device name cannot be empty")
        return v.strip()

    def get_netmiko_params(self) -> Dict[str, Any]:
        """获取 Netmiko 连接参数"""
        return {
            "device_type": self.vendor,
            "host": self.ip,
            "port": self.port,
        }

    def __str__(self) -> str:
        return f"{self.name} ({self.ip})"

    def __hash__(self) -> int:
        return hash((self.name, self.ip))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Device):
            return NotImplemented
        return self.name == other.name and self.ip == other.ip


class DeviceGroup(BaseModel):
    """设备组领域实体"""

    name: str = Field(..., min_length=1, description="组名称")
    vendor: str = Field(default=DeviceVendor.CISCO_IOS.value, description="默认厂商类型")
    credentials: str = Field(default="", description="默认凭证标识")
    description: str = Field(default="", description="组描述")
    devices: List[Device] = Field(default_factory=list, description="组内设备列表")

    @property
    def device_count(self) -> int:
        return len(self.devices)

    @property
    def device_ips(self) -> List[str]:
        return [d.ip for d in self.devices]

    def __len__(self) -> int:
        return len(self.devices)

    def __iter__(self):
        return iter(self.devices)


__all__ = ["Device", "DeviceGroup", "DeviceVendor", "DeviceStatus"]
