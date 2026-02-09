"""
NetOps Toolkit TUI - 适配器模块

将核心插件系统与TUI组件连接
"""

from .plugin_adapter import PluginUIAdapter, PluginRunner

__all__ = ["PluginUIAdapter", "PluginRunner"]
