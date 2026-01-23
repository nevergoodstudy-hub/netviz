"""
设备清单管理模块

负责加载、解析、查询设备清单信息。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Device:
    """设备数据类"""
    name: str
    ip: str
    port: int = 22
    vendor: str = "cisco_ios"
    credentials: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    group: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证设备数据"""
        if not self.name:
            raise ValueError("设备名称不能为空")
        if not self.ip:
            raise ValueError("设备IP不能为空")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "ip": self.ip,
            "port": self.port,
            "vendor": self.vendor,
            "credentials": self.credentials,
            "description": self.description,
            "tags": self.tags,
            "group": self.group,
            "extra": self.extra,
        }
    
    def get_netmiko_params(self) -> Dict[str, Any]:
        """
        获取Netmiko连接参数
        
        Returns:
            Netmiko ConnectHandler参数字典
        """
        return {
            "device_type": self.vendor,
            "host": self.ip,
            "port": self.port,
        }
    
    def __str__(self) -> str:
        return f"{self.name} ({self.ip})"


@dataclass
class DeviceGroup:
    """设备组数据类"""
    name: str
    vendor: str
    credentials: str
    description: str = ""
    devices: List[Device] = field(default_factory=list)
    
    def __len__(self) -> int:
        return len(self.devices)
    
    def __iter__(self):
        return iter(self.devices)


class DeviceInventory:
    """设备清单管理类"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化设备清单
        
        Args:
            config_path: 设备清单YAML文件路径
        """
        self._groups: Dict[str, DeviceGroup] = {}
        self._standalone_devices: List[Device] = []
        self._all_devices: Dict[str, Device] = {}
        
        if config_path:
            self.load(config_path)
    
    def load(self, config_path: Path) -> None:
        """
        加载设备清单文件
        
        Args:
            config_path: YAML配置文件路径
        """
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
        groups_data = data.get("groups", {})
        for group_name, group_info in groups_data.items():
            self._parse_group(group_name, group_info)
        
        # 解析独立设备
        standalone_data = data.get("standalone_devices", [])
        for device_info in standalone_data:
            self._parse_standalone_device(device_info)
        
        logger.info(
            f"设备清单已加载 | 组: {len(self._groups)} | "
            f"总设备: {len(self._all_devices)}"
        )
    
    def _parse_group(self, group_name: str, group_info: Dict[str, Any]) -> None:
        """解析设备组"""
        vendor = group_info.get("vendor", "cisco_ios")
        credentials = group_info.get("credentials", "")
        description = group_info.get("description", "")
        
        group = DeviceGroup(
            name=group_name,
            vendor=vendor,
            credentials=credentials,
            description=description,
        )
        
        devices_data = group_info.get("devices", [])
        for dev_info in devices_data:
            device = Device(
                name=dev_info.get("name", ""),
                ip=dev_info.get("ip", ""),
                port=dev_info.get("port", 22),
                vendor=dev_info.get("vendor", vendor),
                credentials=dev_info.get("credentials", credentials),
                description=dev_info.get("description", ""),
                tags=dev_info.get("tags", []),
                group=group_name,
                extra={k: v for k, v in dev_info.items() 
                       if k not in ["name", "ip", "port", "vendor", 
                                   "credentials", "description", "tags"]},
            )
            group.devices.append(device)
            self._all_devices[device.name] = device
        
        self._groups[group_name] = group
    
    def _parse_standalone_device(self, dev_info: Dict[str, Any]) -> None:
        """解析独立设备"""
        device = Device(
            name=dev_info.get("name", ""),
            ip=dev_info.get("ip", ""),
            port=dev_info.get("port", 22),
            vendor=dev_info.get("vendor", "cisco_ios"),
            credentials=dev_info.get("credentials", ""),
            description=dev_info.get("description", ""),
            tags=dev_info.get("tags", []),
            group="",
        )
        self._standalone_devices.append(device)
        self._all_devices[device.name] = device
    
    def get_device(self, name: str) -> Optional[Device]:
        """
        按名称获取设备
        
        Args:
            name: 设备名称
            
        Returns:
            Device对象或None
        """
        return self._all_devices.get(name)
    
    def get_device_by_ip(self, ip: str) -> Optional[Device]:
        """
        按IP获取设备
        
        Args:
            ip: IP地址
            
        Returns:
            Device对象或None
        """
        for device in self._all_devices.values():
            if device.ip == ip:
                return device
        return None
    
    def get_group(self, name: str) -> Optional[DeviceGroup]:
        """
        获取设备组
        
        Args:
            name: 组名称
            
        Returns:
            DeviceGroup对象或None
        """
        return self._groups.get(name)
    
    def get_devices_by_group(self, group_name: str) -> List[Device]:
        """
        获取组内所有设备
        
        Args:
            group_name: 组名称
            
        Returns:
            设备列表
        """
        group = self._groups.get(group_name)
        if group:
            return list(group.devices)
        return []
    
    def get_devices_by_tag(self, tag: str) -> List[Device]:
        """
        按标签筛选设备
        
        Args:
            tag: 标签名称
            
        Returns:
            设备列表
        """
        return [d for d in self._all_devices.values() if tag in d.tags]
    
    def get_devices_by_vendor(self, vendor: str) -> List[Device]:
        """
        按厂商类型筛选设备
        
        Args:
            vendor: 厂商类型
            
        Returns:
            设备列表
        """
        return [d for d in self._all_devices.values() if d.vendor == vendor]
    
    def get_all_devices(self) -> List[Device]:
        """获取所有设备"""
        return list(self._all_devices.values())
    
    def get_all_groups(self) -> List[str]:
        """获取所有组名称"""
        return list(self._groups.keys())
    
    def get_all_ips(self) -> List[str]:
        """获取所有设备IP"""
        return [d.ip for d in self._all_devices.values()]
    
    def __len__(self) -> int:
        return len(self._all_devices)
    
    def __iter__(self):
        return iter(self._all_devices.values())


__all__ = ["Device", "DeviceGroup", "DeviceInventory"]
