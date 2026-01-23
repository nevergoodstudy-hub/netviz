"""
NetOps Toolkit 核心框架模块

包含日志系统、会话管理、菜单引擎、插件加载器等核心组件。
"""

from .logger import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging"]
