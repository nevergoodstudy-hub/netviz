"""
YAML 设备仓储适配器

将旧的 DeviceInventory YAML 加载逻辑适配到
新的 DeviceRepository 接口，实现关注点分离。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from netops_toolkit.application.interfaces.repositories import DeviceRepository
from netops_toolkit.domain.entities.device import Device, DeviceGroup


class YamlDeviceRepository(DeviceRepository):
    """
    基于 YAML 文件的设备仓储

    从 YAML 配置文件加载设备清单，实现 DeviceRepository 接口。
    使用内存缓存避免重复读取文件。
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._groups: Dict[str, DeviceGroup] = {}
        self._devices: Dict[str, Device] = {}

        if config_path:
            self.load(config_path)

    def load(self, config_path: Path) -> None:
        """从 YAML 文件加载设备清单"""
        if not config_path.exists():
            logger.warning(f"设备清单文件不存在: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载设备清单失败: {e}")
            return

        # 解析设备组
        for group_name, group_info in data.get("groups", {}).items():
            self._parse_group(group_name, group_info)

        # 解析独立设备
        for dev_info in data.get("standalone_devices", []):
            self._parse_standalone(dev_info)

        logger.info(
            f"设备清单已加载 | 组: {len(self._groups)} | "
            f"总设备: {len(self._devices)}"
        )

    # ── DeviceRepository 接口实现 ──

    def get_by_name(self, name: str) -> Optional[Device]:
        return self._devices.get(name)

    def get_by_ip(self, ip: str) -> Optional[Device]:
        for dev in self._devices.values():
            if dev.ip == ip:
                return dev
        return None

    def get_all(self) -> list[Device]:
        return list(self._devices.values())

    def get_by_group(self, group_name: str) -> list[Device]:
        group = self._groups.get(group_name)
        if group:
            return list(group.devices)
        return []

    def get_by_tag(self, tag: str) -> list[Device]:
        return [d for d in self._devices.values() if tag in d.tags]

    def get_by_vendor(self, vendor: str) -> list[Device]:
        return [d for d in self._devices.values() if d.vendor == vendor]

    def get_group(self, name: str) -> Optional[DeviceGroup]:
        return self._groups.get(name)

    def list_groups(self) -> list[str]:
        return list(self._groups.keys())

    def list_ips(self) -> list[str]:
        return [d.ip for d in self._devices.values()]

    def count(self) -> int:
        return len(self._devices)

    # ── 内部解析 ──

    def _parse_group(self, group_name: str, info: Dict[str, Any]) -> None:
        vendor = info.get("vendor", "cisco_ios")
        credentials = info.get("credentials", "")
        description = info.get("description", "")

        devices: List[Device] = []
        for dev_info in info.get("devices", []):
            dev = Device(
                name=dev_info.get("name", ""),
                ip=dev_info.get("ip", ""),
                port=dev_info.get("port", 22),
                vendor=dev_info.get("vendor", vendor),
                credentials=dev_info.get("credentials", credentials),
                description=dev_info.get("description", ""),
                tags=dev_info.get("tags", []),
                group=group_name,
                extra={
                    k: v
                    for k, v in dev_info.items()
                    if k
                    not in (
                        "name", "ip", "port", "vendor",
                        "credentials", "description", "tags",
                    )
                },
            )
            devices.append(dev)
            self._devices[dev.name] = dev

        self._groups[group_name] = DeviceGroup(
            name=group_name,
            vendor=vendor,
            credentials=credentials,
            description=description,
            devices=devices,
        )

    def _parse_standalone(self, dev_info: Dict[str, Any]) -> None:
        dev = Device(
            name=dev_info.get("name", ""),
            ip=dev_info.get("ip", ""),
            port=dev_info.get("port", 22),
            vendor=dev_info.get("vendor", "cisco_ios"),
            credentials=dev_info.get("credentials", ""),
            description=dev_info.get("description", ""),
            tags=dev_info.get("tags", []),
            group="",
        )
        self._devices[dev.name] = dev


__all__ = ["YamlDeviceRepository"]
