"""
SSH 连接池 / 资源管理器

功能:
- Semaphore 控制最大并发连接数
- 连接超时自动释放
- 资源使用统计
- 可作为 AsyncContextManager 使用
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator

from loguru import logger


@dataclass
class PoolStats:
    """连接池统计"""

    max_connections: int = 10
    active_connections: int = 0
    total_acquired: int = 0
    total_released: int = 0
    total_timeouts: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class ConnectionPool:
    """
    异步连接池

    使用 asyncio.Semaphore 控制并发连接数上限。
    适用于 SSH、SNMP 等需要限制并发的场景。

    用法::

        pool = ConnectionPool(max_connections=10)

        async with pool.acquire(timeout=5.0):
            # 在此上下文内执行需要连接的操作
            await ssh_service.execute_command(...)
        # 连接自动释放
    """

    def __init__(self, max_connections: int = 10) -> None:
        self._semaphore = asyncio.Semaphore(max_connections)
        self._stats = PoolStats(max_connections=max_connections)

    @property
    def stats(self) -> PoolStats:
        """获取连接池统计"""
        return self._stats

    @property
    def available(self) -> int:
        """当前可用连接数"""
        return self._stats.max_connections - self._stats.active_connections

    @asynccontextmanager
    async def acquire(
        self, timeout: float | None = None
    ) -> AsyncIterator[None]:
        """
        获取一个连接槽位

        Args:
            timeout: 等待超时 (秒), None 表示无限等待

        Raises:
            asyncio.TimeoutError: 等待超时
        """
        try:
            if timeout is not None:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
            else:
                await self._semaphore.acquire()
        except asyncio.TimeoutError:
            self._stats.total_timeouts += 1
            logger.warning(
                f"连接池超时: active={self._stats.active_connections}/{self._stats.max_connections}"
            )
            raise

        self._stats.active_connections += 1
        self._stats.total_acquired += 1

        try:
            yield
        finally:
            self._semaphore.release()
            self._stats.active_connections -= 1
            self._stats.total_released += 1


# 全局默认连接池实例
_default_pool: ConnectionPool | None = None


def get_connection_pool(max_connections: int = 10) -> ConnectionPool:
    """获取全局连接池 (惰性初始化)"""
    global _default_pool
    if _default_pool is None:
        _default_pool = ConnectionPool(max_connections=max_connections)
    return _default_pool


__all__ = ["ConnectionPool", "PoolStats", "get_connection_pool"]
