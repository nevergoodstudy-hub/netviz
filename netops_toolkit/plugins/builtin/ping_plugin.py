"""
Ping 内置插件

使用新版 Plugin[TInput, TOutput] 泛型基类实现。
通过 @register 装饰器自动注册到 PluginRegistry。
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from pydantic import BaseModel, Field

from netops_toolkit.plugins.core.base import Plugin, PluginMetadata
from netops_toolkit.plugins.core.registry import register


class PingInput(BaseModel):
    """Ping 插件输入"""

    targets: List[str] = Field(..., min_length=1, description="目标主机列表")
    count: int = Field(default=4, ge=1, le=100, description="Ping 次数")
    timeout: float = Field(default=2.0, gt=0, description="超时 (秒)")
    concurrency: int = Field(default=50, ge=1, le=500, description="并发数")


class PingResultItem(BaseModel):
    """单个 Ping 结果"""

    host: str
    is_alive: bool = False
    avg_latency: Optional[float] = None
    packet_loss: float = 100.0


class PingOutput(BaseModel):
    """Ping 插件输出"""

    results: List[PingResultItem] = Field(default_factory=list)
    total: int = 0
    alive_count: int = 0
    dead_count: int = 0
    duration: Optional[float] = None


@register
class PingPlugin(Plugin[PingInput, PingOutput]):
    """
    Ping 连通性测试插件

    使用 AsyncPingService 执行异步批量 Ping。
    """

    metadata = PluginMetadata(
        name="ping",
        version="2.0.0",
        description="ICMP Ping 连通性测试",
        author="NetOps Team",
        category="diagnostics",
    )

    async def execute(self, input: PingInput) -> PingOutput:
        from datetime import datetime

        from netops_toolkit.infrastructure.network.async_ping import AsyncPingService

        service = AsyncPingService()
        start = datetime.now()

        results = await service.ping_batch(
            hosts=input.targets,
            count=input.count,
            timeout=input.timeout,
            concurrency=input.concurrency,
        )

        end = datetime.now()
        duration = (end - start).total_seconds()

        items = [
            PingResultItem(
                host=r.host,
                is_alive=r.is_alive,
                avg_latency=r.avg_latency,
                packet_loss=r.packet_loss,
            )
            for r in results
        ]

        alive = sum(1 for r in results if r.is_alive)

        return PingOutput(
            results=items,
            total=len(results),
            alive_count=alive,
            dead_count=len(results) - alive,
            duration=duration,
        )


__all__ = ["PingPlugin", "PingInput", "PingOutput"]
