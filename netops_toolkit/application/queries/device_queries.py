"""
设备查询 (Query)

遵循 CQRS 模式: 查询只读取数据，不产生副作用。
"""

from __future__ import annotations

from typing import Optional

from netops_toolkit.application.dto.device_dto import (
    DeviceDTO,
    DeviceDetailDTO,
    DeviceFilterDTO,
    DeviceGroupDTO,
)
from netops_toolkit.application.interfaces.repositories import DeviceRepository
from netops_toolkit.domain.entities.device import Device


class DeviceQuery:
    """
    设备查询服务

    将仓储数据映射为 DTO 返回给表示层。
    """

    def __init__(self, device_repo: DeviceRepository) -> None:
        self._repo = device_repo

    def get_device(self, name: str) -> Optional[DeviceDetailDTO]:
        dev = self._repo.get_by_name(name)
        if dev is None:
            return None
        return self._to_detail_dto(dev)

    def get_device_by_ip(self, ip: str) -> Optional[DeviceDetailDTO]:
        dev = self._repo.get_by_ip(ip)
        if dev is None:
            return None
        return self._to_detail_dto(dev)

    def list_devices(
        self, filter_dto: Optional[DeviceFilterDTO] = None
    ) -> list[DeviceDTO]:
        """列出设备, 支持过滤"""
        if filter_dto is None:
            devices = self._repo.get_all()
        elif filter_dto.group:
            devices = self._repo.get_by_group(filter_dto.group)
        elif filter_dto.tag:
            devices = self._repo.get_by_tag(filter_dto.tag)
        elif filter_dto.vendor:
            devices = self._repo.get_by_vendor(filter_dto.vendor)
        else:
            devices = self._repo.get_all()

        # 额外过滤
        if filter_dto and filter_dto.name_pattern:
            pattern = filter_dto.name_pattern.lower()
            devices = [d for d in devices if pattern in d.name.lower()]
        if filter_dto and filter_dto.ip_prefix:
            prefix = filter_dto.ip_prefix
            devices = [d for d in devices if d.ip.startswith(prefix)]

        return [self._to_dto(d) for d in devices]

    def list_groups(self) -> list[DeviceGroupDTO]:
        group_names = self._repo.list_groups()
        result = []
        for name in group_names:
            group = self._repo.get_group(name)
            if group:
                result.append(
                    DeviceGroupDTO(
                        name=group.name,
                        vendor=group.vendor,
                        description=group.description,
                        device_count=group.device_count,
                        device_ips=group.device_ips,
                    )
                )
        return result

    def count(self) -> int:
        return self._repo.count()

    # ── 映射 ──

    @staticmethod
    def _to_dto(dev: Device) -> DeviceDTO:
        return DeviceDTO(
            name=dev.name,
            ip=dev.ip,
            port=dev.port,
            vendor=dev.vendor,
            description=dev.description,
            tags=dev.tags,
            group=dev.group,
            status=dev.status,
        )

    @staticmethod
    def _to_detail_dto(dev: Device) -> DeviceDetailDTO:
        return DeviceDetailDTO(
            name=dev.name,
            ip=dev.ip,
            port=dev.port,
            vendor=dev.vendor,
            description=dev.description,
            tags=dev.tags,
            group=dev.group,
            status=dev.status,
            extra=dev.extra,
            credential_name=dev.credentials,
        )


__all__ = ["DeviceQuery"]
