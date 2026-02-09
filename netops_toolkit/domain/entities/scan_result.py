"""
扫描和诊断结果领域实体

定义各类操作结果的数据模型。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResultStatus(str, Enum):
    """结果状态"""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


class PingResult(BaseModel):
    """单个目标的 Ping 结果"""

    host: str = Field(..., description="目标主机")
    is_alive: bool = Field(default=False, description="是否可达")
    min_latency: Optional[float] = Field(default=None, description="最小延迟(ms)")
    avg_latency: Optional[float] = Field(default=None, description="平均延迟(ms)")
    max_latency: Optional[float] = Field(default=None, description="最大延迟(ms)")
    jitter: Optional[float] = Field(default=None, description="抖动(ms)")
    packet_loss: float = Field(default=100.0, ge=0, le=100, description="丢包率(%)")
    packets_sent: int = Field(default=0, ge=0, description="发送包数")
    packets_received: int = Field(default=0, ge=0, description="接收包数")

    @property
    def success(self) -> bool:
        return self.is_alive


class PortScanResult(BaseModel):
    """端口扫描结果"""

    host: str = Field(..., description="目标主机")
    port: int = Field(..., ge=1, le=65535, description="端口号")
    is_open: bool = Field(default=False, description="是否开放")
    service: str = Field(default="", description="服务名称")
    banner: str = Field(default="", description="Banner信息")
    latency: Optional[float] = Field(default=None, description="响应延迟(ms)")


class OperationResult(BaseModel):
    """
    通用操作结果

    替代旧的 PluginResult dataclass，提供 Pydantic 验证。
    """

    status: ResultStatus = Field(default=ResultStatus.SUCCESS, description="执行状态")
    message: str = Field(default="", description="结果消息")
    data: Any = Field(default=None, description="结果数据")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @property
    def duration(self) -> Optional[float]:
        """执行耗时(秒)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """兼容旧版 PluginResult.to_dict()"""
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "metadata": self.metadata,
        }


__all__ = [
    "ResultStatus",
    "PingResult",
    "PortScanResult",
    "OperationResult",
]
