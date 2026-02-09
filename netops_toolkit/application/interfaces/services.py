"""
服务接口 (Ports)

定义网络操作的抽象服务接口。基础设施层提供具体实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from netops_toolkit.domain.entities.credential import Credential
from netops_toolkit.domain.entities.device import Device
from netops_toolkit.domain.entities.scan_result import (
    OperationResult,
    PingResult,
    PortScanResult,
)


class PingService(ABC):
    """Ping 服务接口"""

    @abstractmethod
    async def ping(
        self,
        host: str,
        count: int = 4,
        timeout: float = 2.0,
    ) -> PingResult:
        """对单个主机执行 Ping"""
        ...

    @abstractmethod
    async def ping_batch(
        self,
        hosts: list[str],
        count: int = 4,
        timeout: float = 2.0,
        concurrency: int = 50,
    ) -> list[PingResult]:
        """批量 Ping"""
        ...


class PortScanService(ABC):
    """端口扫描服务接口"""

    @abstractmethod
    async def scan_port(
        self,
        host: str,
        port: int,
        timeout: float = 2.0,
    ) -> PortScanResult:
        """扫描单个端口"""
        ...

    @abstractmethod
    async def scan_ports(
        self,
        host: str,
        ports: list[int],
        timeout: float = 2.0,
        concurrency: int = 100,
    ) -> list[PortScanResult]:
        """扫描多个端口"""
        ...


class SSHService(ABC):
    """SSH 执行服务接口"""

    @abstractmethod
    async def execute_command(
        self,
        device: Device,
        credential: Credential,
        command: str,
        timeout: float = 30.0,
    ) -> OperationResult:
        """在设备上执行命令"""
        ...

    @abstractmethod
    async def execute_batch(
        self,
        devices: list[Device],
        credential: Credential,
        commands: list[str],
        timeout: float = 30.0,
        concurrency: int = 10,
    ) -> list[OperationResult]:
        """批量执行命令"""
        ...


class DNSService(ABC):
    """DNS 服务接口"""

    @abstractmethod
    async def resolve(
        self,
        hostname: str,
        record_type: str = "A",
    ) -> list[str]:
        """DNS 解析"""
        ...

    @abstractmethod
    async def reverse_lookup(self, ip: str) -> Optional[str]:
        """反向 DNS 查询"""
        ...


class CredentialStore(ABC):
    """
    凭证存储服务接口

    比 CredentialRepository 更高层的抽象，
    包含加密/解密逻辑。
    """

    @abstractmethod
    def store(self, credential: Credential) -> None:
        """安全存储凭证"""
        ...

    @abstractmethod
    def retrieve(self, name: str) -> Optional[Credential]:
        """检索凭证"""
        ...

    @abstractmethod
    def remove(self, name: str) -> bool:
        """删除凭证"""
        ...

    @abstractmethod
    def list_names(self) -> list[str]:
        """列出所有凭证名称"""
        ...


__all__ = [
    "PingService",
    "PortScanService",
    "SSHService",
    "DNSService",
    "CredentialStore",
]
