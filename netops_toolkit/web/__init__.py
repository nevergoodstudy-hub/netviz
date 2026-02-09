"""
NetOps Toolkit - Web UI 模块

基于 FastAPI + HTMX + Jinja2 的现代 Web 界面
支持:
- RESTful API
- WebSocket 实时推送
- HTMX 动态交互
- 响应式布局
"""

from .app import create_app, run_web_server

__all__ = ["create_app", "run_web_server"]
