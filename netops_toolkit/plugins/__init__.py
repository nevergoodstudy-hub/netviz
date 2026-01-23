"""
NetOps Toolkit 插件模块

提供插件基类和插件注册机制。
"""

from .base import (
    Plugin,
    PluginCategory,
    PluginResult,
    ResultStatus,
    ParamSpec,
    register_plugin,
    get_registered_plugins,
)

__all__ = [
    "Plugin",
    "PluginCategory",
    "PluginResult",
    "ResultStatus",
    "ParamSpec",
    "register_plugin",
    "get_registered_plugins",
]
