"""
网络操作 DTO

用于 Ping、端口扫描、SSH 批量执行等操作的请求/响应数据传输。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from netops_toolkit.domain.entities.scan_result import ResultStatus


# ── Ping ──


class PingRequestDTO(BaseModel):
    """Ping 请求"""

    targets: list[str] = Field(..., min_length=1, description="目标列表")
    count: int = Field(default=4, ge=1, le=100, description="Ping 次数")
    timeout: float = Field(default=2.0, gt=0, description="超时(秒)")
    concurrency: int = Field(default=50, ge=1, le=500, description="并发数")


class PingResultDTO(BaseModel):
    """单个 Ping 结果"""

    host: str
    is_alive: bool = False
    avg_latency: Optional[float] = None
    packet_loss: float = 100.0


class PingBatchResponseDTO(BaseModel):
    """批量 Ping 响应"""

    results: list[PingResultDTO] = Field(default_factory=list)
    total: int = 0
    alive_count: int = 0
    dead_count: int = 0
    duration: Optional[float] = None


# ── 端口扫描 ──


class PortScanRequestDTO(BaseModel):
    """端口扫描请求"""

    targets: list[str] = Field(..., min_length=1, description="目标列表")
    ports: str = Field(default="22,80,443", description="端口 (支持范围)")
    timeout: float = Field(default=2.0, gt=0, description="超时(秒)")
    concurrency: int = Field(default=100, ge=1, le=1000, description="并发数")


class PortScanResultDTO(BaseModel):
    """单个端口扫描结果"""

    host: str
    port: int
    is_open: bool = False
    service: str = ""
    banner: str = ""


class PortScanBatchResponseDTO(BaseModel):
    """批量端口扫描响应"""

    results: list[PortScanResultDTO] = Field(default_factory=list)
    total_scanned: int = 0
    open_count: int = 0
    duration: Optional[float] = None


# ── SSH 批量执行 ──


class SSHCommandRequestDTO(BaseModel):
    """SSH 命令执行请求"""

    device_names: list[str] = Field(default_factory=list, description="设备名称")
    group: Optional[str] = Field(default=None, description="设备组名")
    commands: list[str] = Field(..., min_length=1, description="命令列表")
    credential_name: str = Field(default="", description="凭证名称")
    timeout: float = Field(default=30.0, gt=0, description="超时(秒)")
    concurrency: int = Field(default=10, ge=1, le=100, description="并发数")


class SSHCommandResultDTO(BaseModel):
    """单个设备的 SSH 执行结果"""

    device_name: str
    device_ip: str
    status: ResultStatus = ResultStatus.SUCCESS
    output: str = ""
    error: str = ""
    duration: Optional[float] = None


class SSHBatchResponseDTO(BaseModel):
    """SSH 批量执行响应"""

    results: list[SSHCommandResultDTO] = Field(default_factory=list)
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    duration: Optional[float] = None


__all__ = [
    "PingRequestDTO",
    "PingResultDTO",
    "PingBatchResponseDTO",
    "PortScanRequestDTO",
    "PortScanResultDTO",
    "PortScanBatchResponseDTO",
    "SSHCommandRequestDTO",
    "SSHCommandResultDTO",
    "SSHBatchResponseDTO",
]
