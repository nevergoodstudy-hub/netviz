"""
设备管理领域服务

纯业务逻辑：设备分组、筛选、状态推导等。
"""

from __future__ import annotations

from netops_toolkit.domain.entities.device import Device, DeviceStatus
from netops_toolkit.domain.entities.scan_result import PingResult


def derive_device_status(device: Device, ping: PingResult | None) -> DeviceStatus:
    """根据 Ping 结果推导设备状态"""
    if device.status == DeviceStatus.MAINTENANCE:
        return DeviceStatus.MAINTENANCE
    if ping is None:
        return DeviceStatus.UNKNOWN
    return DeviceStatus.ONLINE if ping.is_alive else DeviceStatus.OFFLINE


def filter_devices(
    devices: list[Device],
    *,
    group: str | None = None,
    tag: str | None = None,
    vendor: str | None = None,
    status: DeviceStatus | None = None,
) -> list[Device]:
    """通用设备过滤"""
    result = devices
    if group:
        result = [d for d in result if d.group == group]
    if tag:
        result = [d for d in result if tag in d.tags]
    if vendor:
        result = [d for d in result if d.vendor == vendor]
    if status:
        result = [d for d in result if d.status == status]
    return result


def group_devices_by_vendor(devices: list[Device]) -> dict[str, list[Device]]:
    """按厂商分组"""
    groups: dict[str, list[Device]] = {}
    for d in devices:
        groups.setdefault(d.vendor, []).append(d)
    return groups


__all__ = [
    "derive_device_status",
    "filter_devices",
    "group_devices_by_vendor",
]
