"""
NetViz WebSocket 接口
提供实时通信功能，包括解析进度、实时分析等
"""

import json
import logging
import uuid
from typing import Any

from fastapi import status
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.admin_access import websocket_has_admin_access

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活动连接: {connection_id: WebSocket}
        self.active_connections: dict[str, WebSocket] = {}
        # 客户端标签: {connection_id: client_label}
        self.connection_labels: dict[str, str] = {}
        # 订阅: {topic: set[connection_id]}
        self.subscriptions: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, client_label: str) -> str:
        """接受新连接"""
        await websocket.accept()
        connection_id = uuid.uuid4().hex
        self.active_connections[connection_id] = websocket
        self.connection_labels[connection_id] = client_label
        logger.info(f"WebSocket 客户端连接: {client_label} ({connection_id})")
        return connection_id

    def disconnect(self, connection_id: str):
        """断开连接"""
        client_label = self.connection_labels.pop(connection_id, connection_id)
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # 从所有订阅中移除
        for topic in self.subscriptions.values():
            topic.discard(connection_id)

        logger.info(f"WebSocket 客户端断开: {client_label} ({connection_id})")

    def subscribe(self, connection_id: str, topic: str):
        """订阅主题"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(connection_id)
        client_label = self.connection_labels.get(connection_id, connection_id)
        logger.debug(f"客户端 {client_label} ({connection_id}) 订阅主题: {topic}")

    def unsubscribe(self, connection_id: str, topic: str):
        """取消订阅"""
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(connection_id)

    async def send_personal(self, connection_id: str, message: dict[str, Any]):
        """发送私人消息"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(connection_id)

    async def broadcast(self, topic: str, message: dict[str, Any]):
        """向订阅主题的所有客户端广播消息"""
        if topic not in self.subscriptions:
            return

        disconnected = []
        for connection_id in self.subscriptions[topic]:
            if connection_id in self.active_connections:
                try:
                    await self.active_connections[connection_id].send_json(message)
                except Exception as e:
                    logger.error(f"广播消息失败: {e}")
                    disconnected.append(connection_id)

        # 清理断开的连接
        for connection_id in disconnected:
            self.disconnect(connection_id)

    async def broadcast_all(self, message: dict[str, Any]):
        """向所有客户端广播消息"""
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection_id)

        for connection_id in disconnected:
            self.disconnect(connection_id)


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
    if not websocket_has_admin_access(websocket):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Administrative access required",
        )
        return

    connection_id = await manager.connect(websocket, client_id)

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
                        manager.subscribe(connection_id, topic)
                        await manager.send_personal(
                            connection_id,
                            {"type": "subscribed", "topic": topic},
                        )

                elif msg_type == "unsubscribe":
                    # 取消订阅
                    topic = message.get("topic")
                    if topic:
                        manager.unsubscribe(connection_id, topic)
                        await manager.send_personal(
                            connection_id,
                            {"type": "unsubscribed", "topic": topic},
                        )

                elif msg_type == "ping":
                    # 心跳
                    await manager.send_personal(connection_id, {"type": "pong"})

                else:
                    logger.warning(f"未知消息类型: {msg_type}")

            except json.JSONDecodeError:
                logger.error(f"无效的 JSON 消息: {data}")

    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        manager.disconnect(connection_id)


@router.get("/stats")
async def get_websocket_stats():
    """获取 WebSocket 统计信息"""
    return {
        "active_connections": len(manager.active_connections),
        "subscriptions": {topic: len(clients) for topic, clients in manager.subscriptions.items()},
    }
