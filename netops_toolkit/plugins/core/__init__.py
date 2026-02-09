"""
插件核心模块
"""

from netops_toolkit.plugins.core.base import Plugin, PluginMetadata
from netops_toolkit.plugins.core.executor import PluginExecutor
from netops_toolkit.plugins.core.loader import PluginLoader
from netops_toolkit.plugins.core.registry import PluginRegistry, register

__all__ = [
    "Plugin",
    "PluginMetadata",
    "PluginExecutor",
    "PluginLoader",
    "PluginRegistry",
    "register",
]
