"""API 请求/响应 Schema

表示层 API Schema 复用 application/dto 定义,
并添加 HTTP 层特有的包装 (如分页、错误响应格式)。
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# 复用应用层 DTO
from netops_toolkit.application.dto.device_dto import (
    DeviceDetailDTO,
    DeviceDTO,
    DeviceFilterDTO,
    DeviceGroupDTO,
)
from netops_toolkit.application.dto.network_dto import (
    PingBatchResponseDTO,
    PingRequestDTO,
    PortScanBatchResponseDTO,
    PortScanRequestDTO,
    SSHBatchResponseDTO,
    SSHCommandRequestDTO,
)

T = TypeVar("T")


# ── 通用响应包装 ──


class ApiResponse(BaseModel, Generic[T]):
    """标准 API 响应包装"""

    status: str = "ok"
    message: str = ""
    data: T | None = None


class ApiErrorResponse(BaseModel):
    """标准 API 错误响应"""

    status: str = "error"
    message: str
    error_code: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    status: str = "ok"
    data: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False


# ── 设备 API Schema ──


class DeviceListResponse(ApiResponse[list[DeviceDTO]]):
    """设备列表响应"""

    pass


class DeviceDetailResponse(ApiResponse[DeviceDetailDTO]):
    """设备详情响应"""

    pass


class DeviceGroupListResponse(ApiResponse[list[DeviceGroupDTO]]):
    """设备组列表响应"""

    pass


# ── 网络操作 API Schema ──


class PingResponse(ApiResponse[PingBatchResponseDTO]):
    """Ping 操作响应"""

    pass


class PortScanResponse(ApiResponse[PortScanBatchResponseDTO]):
    """端口扫描响应"""

    pass


class SSHBatchResponse(ApiResponse[SSHBatchResponseDTO]):
    """SSH 批量执行响应"""

    pass


# ── 监控 API Schema ──


class MonitoringDeviceStatus(BaseModel):
    """单个设备监控状态"""

    name: str
    ip: str
    status: str = "unknown"
    latency: str = "-"


class MonitoringStatusResponse(BaseModel):
    """监控状态响应"""

    status: str = "ok"
    timestamp: str = ""
    devices: list[MonitoringDeviceStatus] = Field(default_factory=list)


# ── 审计 API Schema ──


class AuditLogEntry(BaseModel):
    """审计日志条目"""

    id: int | None = None
    timestamp: str | None = None
    event_type: str = ""
    device_name: str = "-"
    device_ip: str = "-"
    operator: str = "-"
    description: str = ""
    result: str = ""


class AuditLogResponse(BaseModel):
    """审计日志响应"""

    status: str = "ok"
    logs: list[AuditLogEntry] = Field(default_factory=list)
    count: int = 0


__all__ = [
    # 通用
    "ApiResponse",
    "ApiErrorResponse",
    "PaginatedResponse",
    # 设备
    "DeviceDTO",
    "DeviceDetailDTO",
    "DeviceFilterDTO",
    "DeviceGroupDTO",
    "DeviceListResponse",
    "DeviceDetailResponse",
    "DeviceGroupListResponse",
    # 网络
    "PingRequestDTO",
    "PingResponse",
    "PortScanRequestDTO",
    "PortScanResponse",
    "SSHCommandRequestDTO",
    "SSHBatchResponse",
    # 监控
    "MonitoringDeviceStatus",
    "MonitoringStatusResponse",
    # 审计
    "AuditLogEntry",
    "AuditLogResponse",
]
