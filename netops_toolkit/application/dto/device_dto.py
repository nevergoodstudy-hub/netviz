"""
设备相关 DTO

用于应用层/表示层之间的数据传输，与领域实体解耦。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from netops_toolkit.domain.entities.device import DeviceStatus


class DeviceDTO(BaseModel):
    """设备摘要 DTO (不含敏感信息)"""

    name: str
    ip: str
    port: int = 22
    vendor: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    group: str = ""
    status: DeviceStatus = DeviceStatus.UNKNOWN


class DeviceDetailDTO(DeviceDTO):
    """设备详情 DTO"""

    extra: Dict[str, Any] = Field(default_factory=dict)
    credential_name: str = ""


class DeviceGroupDTO(BaseModel):
    """设备组 DTO"""

    name: str
    vendor: str = ""
    description: str = ""
    device_count: int = 0
    device_ips: list[str] = Field(default_factory=list)


class DeviceFilterDTO(BaseModel):
    """设备过滤条件 DTO"""

    group: Optional[str] = None
    tag: Optional[str] = None
    vendor: Optional[str] = None
    status: Optional[DeviceStatus] = None
    name_pattern: Optional[str] = None
    ip_prefix: Optional[str] = None


__all__ = [
    "DeviceDTO",
    "DeviceDetailDTO",
    "DeviceGroupDTO",
    "DeviceFilterDTO",
]
