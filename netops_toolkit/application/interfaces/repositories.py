"""
仓储接口 (Ports)

定义领域对象的持久化抽象。基础设施层提供具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from netops_toolkit.domain.entities.credential import Credential
from netops_toolkit.domain.entities.device import Device, DeviceGroup


class DeviceRepository(ABC):
    """
    设备仓储接口

    定义设备数据的 CRUD 操作抽象，不关心底层存储方式
    (YAML、数据库、API 等)。
    """

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Device]:
        """按名称获取设备"""
        ...

    @abstractmethod
    def get_by_ip(self, ip: str) -> Optional[Device]:
        """按 IP 获取设备"""
        ...

    @abstractmethod
    def get_all(self) -> list[Device]:
        """获取所有设备"""
        ...

    @abstractmethod
    def get_by_group(self, group_name: str) -> list[Device]:
        """按组名获取设备列表"""
        ...

    @abstractmethod
    def get_by_tag(self, tag: str) -> list[Device]:
        """按标签筛选设备"""
        ...

    @abstractmethod
    def get_by_vendor(self, vendor: str) -> list[Device]:
        """按厂商类型筛选设备"""
        ...

    @abstractmethod
    def get_group(self, name: str) -> Optional[DeviceGroup]:
        """获取设备组"""
        ...

    @abstractmethod
    def list_groups(self) -> list[str]:
        """列出所有设备组名称"""
        ...

    @abstractmethod
    def list_ips(self) -> list[str]:
        """列出所有设备 IP"""
        ...

    @abstractmethod
    def count(self) -> int:
        """设备总数"""
        ...


class CredentialRepository(ABC):
    """
    凭证仓储接口

    定义凭证数据的 CRUD 操作抽象。
    """

    @abstractmethod
    def get(self, name: str) -> Optional[Credential]:
        """按名称获取凭证"""
        ...

    @abstractmethod
    def get_all(self) -> list[Credential]:
        """获取所有凭证"""
        ...

    @abstractmethod
    def save(self, credential: Credential) -> None:
        """保存/更新凭证"""
        ...

    @abstractmethod
    def delete(self, name: str) -> bool:
        """删除凭证, 返回是否成功"""
        ...

    @abstractmethod
    def exists(self, name: str) -> bool:
        """检查凭证是否存在"""
        ...


__all__ = ["DeviceRepository", "CredentialRepository"]
