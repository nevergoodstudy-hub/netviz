"""领域事件总线

激活已定义但未使用的 DomainEvent 系统:
- 异步 publish / subscribe
- 处理器错误隔离 (不影响其他订阅者)
- 全局单例 event_bus
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from loguru import logger

from netops_toolkit.domain.events.device_events import DomainEvent

# Handler types
SyncHandler = Callable[[DomainEvent], None]
AsyncHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]
Handler = SyncHandler | AsyncHandler


class EventBus:
    """领域事件总线

    支持同步和异步处理器:
    - subscribe(event_type, handler)
    - subscribe_async(event_type, handler)
    - publish(event)  — async, 通知所有注册的处理器
    """

    def __init__(self) -> None:
        self._sync_handlers: dict[str, list[SyncHandler]] = defaultdict(list)
        self._async_handlers: dict[str, list[AsyncHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: SyncHandler) -> None:
        """注册同步事件处理器"""
        key = event_type.__name__
        self._sync_handlers[key].append(handler)
        logger.debug(f"EventBus: 订阅 {key} → {handler.__name__}")

    def subscribe_async(
        self, event_type: type[DomainEvent], handler: AsyncHandler
    ) -> None:
        """注册异步事件处理器"""
        key = event_type.__name__
        self._async_handlers[key].append(handler)
        logger.debug(f"EventBus: 异步订阅 {key} → {handler.__name__}")

    async def publish(self, event: DomainEvent) -> None:
        """发布事件 (异步)

        所有处理器的异常会被捕获并记录，不会影响其他订阅者。
        """
        key = type(event).__name__
        logger.debug(f"EventBus: 发布 {key}")

        # 调用同步处理器
        for handler in self._sync_handlers.get(key, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"EventBus: 同步处理器 {handler.__name__} 异常: {e}")

        # 调用异步处理器
        tasks = []
        for handler in self._async_handlers.get(key, []):
            tasks.append(self._safe_call_async(handler, event))
        if tasks:
            await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_call_async(handler: AsyncHandler, event: DomainEvent) -> None:
        """安全调用异步处理器"""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"EventBus: 异步处理器 {handler.__name__} 异常: {e}")

    def clear(self) -> None:
        """清除所有订阅 (用于测试)"""
        self._sync_handlers.clear()
        self._async_handlers.clear()


# 全局事件总线
event_bus = EventBus()


__all__ = ["EventBus", "event_bus"]
