"""
NetOps Toolkit - FastAPI Web 应用

功能:
- RESTful API 端点
- WebSocket 实时通信
- Jinja2 模板渲染
- HTMX 动态交互
- 静态文件服务
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 获取模块路径
MODULE_DIR = Path(__file__).parent
TEMPLATES_DIR = MODULE_DIR / "templates"
STATIC_DIR = MODULE_DIR / "static"


# ============================================================
# WebSocket 连接管理器
# ============================================================

class ConnectionManager:
    """WebSocket 连接管理器
    
    管理多个 WebSocket 连接，支持广播消息
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket) -> None:
        """接受新连接"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """断开连接"""
        async with self._lock:
            self.active_connections.discard(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception:
            await self.disconnect(websocket)
    
    async def send_json(self, data: dict, websocket: WebSocket) -> None:
        """发送 JSON 数据"""
        try:
            await websocket.send_json(data)
        except Exception:
            await self.disconnect(websocket)
    
    async def broadcast(self, message: str) -> None:
        """广播文本消息到所有连接"""
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.active_connections.discard(conn)
    
    async def broadcast_json(self, data: dict) -> None:
        """广播 JSON 数据到所有连接"""
        async with self._lock:
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(data)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.active_connections.discard(conn)
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self.active_connections)


# 全局连接管理器
manager = ConnectionManager()


# ============================================================
# FastAPI 应用工厂
# ============================================================

def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    
    app = FastAPI(
        title="NetOps Toolkit",
        description="网络运维工具集 Web API",
        version="1.8.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # 挂载静态文件
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    
    # 配置 Jinja2 模板
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    
    # 注入模板到应用状态
    app.state.templates = templates
    app.state.ws_manager = manager
    
    # ========== 页面路由 ==========
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """首页 - 仪表板"""
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "NetOps Toolkit",
                "page": "dashboard",
            }
        )
    
    @app.get("/devices", response_class=HTMLResponse)
    async def devices_page(request: Request):
        """设备管理页面"""
        return templates.TemplateResponse(
            "devices.html",
            {
                "request": request,
                "title": "设备管理",
                "page": "devices",
            }
        )
    
    @app.get("/monitoring", response_class=HTMLResponse)
    async def monitoring_page(request: Request):
        """监控仪表板页面"""
        return templates.TemplateResponse(
            "monitoring.html",
            {
                "request": request,
                "title": "实时监控",
                "page": "monitoring",
            }
        )
    
    @app.get("/audit", response_class=HTMLResponse)
    async def audit_page(request: Request):
        """审计日志页面"""
        return templates.TemplateResponse(
            "audit.html",
            {
                "request": request,
                "title": "变更审计",
                "page": "audit",
            }
        )
    
    @app.get("/config", response_class=HTMLResponse)
    async def config_page(request: Request):
        """配置中心页面"""
        return templates.TemplateResponse(
            "config.html",
            {
                "request": request,
                "title": "配置中心",
                "page": "config",
            }
        )
    
    # ========== API 路由 ==========
    
    @app.get("/api/devices")
    async def api_list_devices():
        """获取设备列表 API"""
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory
            
            config_paths = [
                Path("config/devices.yaml"),
                Path.cwd() / "config" / "devices.yaml",
            ]
            
            for path in config_paths:
                if path.exists():
                    inventory = DeviceInventory(path)
                    devices = [
                        {
                            "name": d.name,
                            "ip": d.ip,
                            "vendor": d.vendor,
                            "group": d.group or "-",
                            "description": d.description or "-",
                        }
                        for d in inventory
                    ]
                    return {"status": "ok", "devices": devices, "count": len(devices)}
            
            # 演示数据
            return {
                "status": "ok",
                "devices": [
                    {"name": "SW-CORE-01", "ip": "192.168.1.10", "vendor": "cisco_ios", "group": "core", "description": "核心交换机"},
                    {"name": "SW-CORE-02", "ip": "192.168.1.11", "vendor": "cisco_ios", "group": "core", "description": "核心交换机"},
                    {"name": "R-EDGE-01", "ip": "192.168.1.1", "vendor": "cisco_ios", "group": "edge", "description": "出口路由器"},
                ],
                "count": 3,
                "demo": True,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @app.get("/api/audit/logs")
    async def api_audit_logs(
        limit: int = 50,
        event_type: Optional[str] = None,
        result: Optional[str] = None,
    ):
        """获取审计日志 API"""
        try:
            from netops_toolkit.services.audit_service import (
                get_audit_service, AuditQuery, AuditEventType, AuditResult
            )
            
            service = get_audit_service()
            query = AuditQuery(limit=limit)
            
            if event_type:
                try:
                    query.event_types = [AuditEventType(event_type)]
                except ValueError:
                    pass
            
            if result:
                try:
                    query.results = [AuditResult(result)]
                except ValueError:
                    pass
            
            records = service.query(query)
            logs = [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "event_type": r.event_type.value,
                    "device_name": r.device_name or "-",
                    "device_ip": r.device_ip or "-",
                    "operator": r.operator or "-",
                    "description": r.description,
                    "result": r.result.value,
                }
                for r in records
            ]
            return {"status": "ok", "logs": logs, "count": len(logs)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @app.get("/api/audit/summary")
    async def api_audit_summary():
        """获取审计统计 API"""
        try:
            from netops_toolkit.services.audit_service import get_audit_service
            from datetime import timedelta
            
            service = get_audit_service()
            summary = service.get_summary(
                start_time=datetime.now() - timedelta(hours=24)
            )
            return {
                "status": "ok",
                "summary": {
                    "total": summary.total_records,
                    "success": summary.success_count,
                    "failure": summary.failure_count,
                    "partial": summary.partial_count,
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @app.get("/api/monitoring/status")
    async def api_monitoring_status():
        """获取监控状态 API"""
        import platform

        async def _async_ping(ip: str, timeout: float = 3.0) -> str:
            """异步执行 ping 命令，不阻塞事件循环"""
            param = "-n" if platform.system().lower() == "windows" else "-c"
            cmd = ["ping", param, "1", "-w", "1000", ip]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                try:
                    await asyncio.wait_for(proc.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return "unknown"
                return "online" if proc.returncode == 0 else "offline"
            except OSError:
                return "unknown"

        # 获取设备列表
        devices = []
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory
            config_paths = [
                Path("config/devices.yaml"),
                Path.cwd() / "config" / "devices.yaml",
            ]
            for path in config_paths:
                if path.exists():
                    inventory = DeviceInventory(path)
                    devices = [{"name": d.name, "ip": d.ip} for d in inventory]
                    break
        except Exception:
            devices = [
                {"name": "SW-CORE-01", "ip": "192.168.1.10"},
                {"name": "SW-CORE-02", "ip": "192.168.1.11"},
            ]

        # 并发异步 Ping 检测（不阻塞事件循环）
        target_devices = devices[:5]
        statuses = await asyncio.gather(
            *[_async_ping(d["ip"]) for d in target_devices]
        )

        results = [
            {
                "name": device["name"],
                "ip": device["ip"],
                "status": status,
                "latency": "-",
            }
            for device, status in zip(target_devices, statuses)
        ]

        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "devices": results,
        }
    
    # ========== HTMX 片段路由 ==========
    
    @app.get("/htmx/devices/table", response_class=HTMLResponse)
    async def htmx_devices_table(request: Request):
        """HTMX: 设备表格片段"""
        data = await api_list_devices()
        return templates.TemplateResponse(
            "partials/devices_table.html",
            {
                "request": request,
                "devices": data.get("devices", []),
            }
        )
    
    @app.get("/htmx/audit/table", response_class=HTMLResponse)
    async def htmx_audit_table(request: Request, limit: int = 50):
        """HTMX: 审计日志表格片段"""
        data = await api_audit_logs(limit=limit)
        return templates.TemplateResponse(
            "partials/audit_table.html",
            {
                "request": request,
                "logs": data.get("logs", []),
            }
        )
    
    @app.get("/htmx/monitoring/cards", response_class=HTMLResponse)
    async def htmx_monitoring_cards(request: Request):
        """HTMX: 监控状态卡片片段"""
        data = await api_monitoring_status()
        return templates.TemplateResponse(
            "partials/monitoring_cards.html",
            {
                "request": request,
                "devices": data.get("devices", []),
                "timestamp": data.get("timestamp", ""),
            }
        )
    
    # ========== WebSocket 端点 ==========
    
    @app.websocket("/ws/monitoring")
    async def websocket_monitoring(websocket: WebSocket):
        """WebSocket: 实时监控数据推送"""
        await manager.connect(websocket)
        try:
            while True:
                # 等待客户端消息或推送更新
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=5.0
                    )
                    # 处理客户端请求
                    if data == "refresh":
                        status_data = await api_monitoring_status()
                        await manager.send_json(status_data, websocket)
                except asyncio.TimeoutError:
                    # 定期推送状态更新
                    status_data = await api_monitoring_status()
                    await manager.send_json(status_data, websocket)
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
        except Exception:
            await manager.disconnect(websocket)
    
    @app.websocket("/ws/command")
    async def websocket_command(websocket: WebSocket):
        """WebSocket: 命令执行实时输出"""
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                command = data.get("command", "")
                device_ip = data.get("device_ip", "")
                
                # 模拟命令执行输出
                await websocket.send_json({
                    "type": "start",
                    "message": f"执行命令: {command} @ {device_ip}",
                })
                
                await asyncio.sleep(0.5)
                
                await websocket.send_json({
                    "type": "output",
                    "message": f"[模拟输出]\n{command}\n设备: {device_ip}\n",
                })
                
                await websocket.send_json({
                    "type": "complete",
                    "message": "命令执行完成",
                })
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
        except Exception:
            await manager.disconnect(websocket)
    
    # ========== 健康检查 ==========
    
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "websocket_connections": manager.connection_count,
        }
    
    return app


# ============================================================
# 服务器启动
# ============================================================

def run_web_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """启动 Web 服务器
    
    Args:
        host: 监听地址
        port: 监听端口
        reload: 是否启用热重载
    """
    try:
        import uvicorn
    except ImportError:
        print("错误: 请安装 uvicorn")
        print("  pip install uvicorn")
        return
    
    print(f"🚀 启动 NetOps Web UI...")
    print(f"📍 地址: http://{host}:{port}")
    print(f"📚 API 文档: http://{host}:{port}/api/docs")
    print()
    
    uvicorn.run(
        "netops_toolkit.web.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


# 直接运行支持
if __name__ == "__main__":
    run_web_server()
