"""
NetViz WebSocket 接口
提供实时通信功能，包括解析进度、实时分析等
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活动连接: {client_id: WebSocket}
        self.active_connections: dict[str, WebSocket] = {}
        # 订阅: {topic: set[client_id]}
        self.subscriptions: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket 客户端连接: {client_id}")

    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        # 从所有订阅中移除
        for topic in self.subscriptions.values():
            topic.discard(client_id)

        logger.info(f"WebSocket 客户端断开: {client_id}")

    def subscribe(self, client_id: str, topic: str):
        """订阅主题"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)
        logger.debug(f"客户端 {client_id} 订阅主题: {topic}")

    def unsubscribe(self, client_id: str, topic: str):
        """取消订阅"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

    async def send_personal(self, client_id: str, message: dict[str, Any]):
        """发送私人消息"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(client_id)

    async def broadcast(self, topic: str, message: dict[str, Any]):
        """向订阅主题的所有客户端广播消息"""
        if topic not in self.subscriptions:
            return

        disconnected = []
        for client_id in self.subscriptions[topic]:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"广播消息失败: {e}")
                    disconnected.append(client_id)

        # 清理断开的连接
        for client_id in disconnected:
            self.disconnect(client_id)

    async def broadcast_all(self, message: dict[str, Any]):
        """向所有客户端广播消息"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)


# 全局连接管理器
manager = ConnectionManager()


async def notify_parse_progress(pcap_id: int, progress: float, message: str):
    """通知解析进度"""
    await manager.broadcast(
        f"pcap:{pcap_id}",
        {
            "type": "parse_progress",
            "pcap_id": pcap_id,
            "progress": progress,
            "message": message,
        },
    )


async def notify_parse_complete(pcap_id: int, stats: dict[str, Any]):
    """通知解析完成"""
    await manager.broadcast(
        f"pcap:{pcap_id}",
        {
            "type": "parse_complete",
            "pcap_id": pcap_id,
            "stats": stats,
        },
    )


async def notify_alert(alert: dict[str, Any]):
    """通知新告警"""
    await manager.broadcast_all(
        {
            "type": "alert",
            "alert": alert,
        }
    )


@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 端点"""
    await manager.connect(websocket, client_id)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "subscribe":
                    # 订阅主题
                    topic = message.get("topic")
                    if topic:
                        manager.subscribe(client_id, topic)
                        await manager.send_personal(
                            client_id,
                            {"type": "subscribed", "topic": topic},
                        )

                elif msg_type == "unsubscribe":
                    # 取消订阅
                    topic = message.get("topic")
                    if topic:
                        manager.unsubscribe(client_id, topic)
                        await manager.send_personal(
                            client_id,
                            {"type": "unsubscribed", "topic": topic},
                        )

                elif msg_type == "ping":
                    # 心跳
                    await manager.send_personal(client_id, {"type": "pong"})

                else:
                    logger.warning(f"未知消息类型: {msg_type}")

            except json.JSONDecodeError:
                logger.error(f"无效的 JSON 消息: {data}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        manager.disconnect(client_id)


@router.get("/stats")
async def get_websocket_stats():
    """获取 WebSocket 统计信息"""
    return {
        "active_connections": len(manager.active_connections),
        "subscriptions": {topic: len(clients) for topic, clients in manager.subscriptions.items()},
    }
