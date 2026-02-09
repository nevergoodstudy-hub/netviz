"""
插件注册表

支持:
- 装饰器注册: @register
- 自动发现: discover(package_name)
- 按名称/分类查询
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Dict, Optional, Type

from netops_toolkit.domain.exceptions import PluginNotFoundError
from netops_toolkit.plugins.core.base import Plugin, PluginMetadata


class PluginRegistry:
    """
    插件注册表

    集中管理所有已注册的插件类。
    """

    _plugins: Dict[str, Type[Plugin]] = {}

    @classmethod
    def register(cls, plugin_class: Type[Plugin]) -> Type[Plugin]:
        """
        装饰器: 注册插件

        Usage::

            @PluginRegistry.register
            class MyPlugin(Plugin[...]):
                metadata = PluginMetadata(name="my_plugin")
                ...
        """
        name = plugin_class.metadata.name
        cls._plugins[name] = plugin_class
        return plugin_class

    @classmethod
    def unregister(cls, name: str) -> None:
        """取消注册插件"""
        cls._plugins.pop(name, None)

    @classmethod
    def get(cls, name: str) -> Type[Plugin]:
        """
        获取插件类

        Args:
            name: 插件名称

        Returns:
            插件类

        Raises:
            PluginNotFoundError: 插件未找到
        """
        if name not in cls._plugins:
            raise PluginNotFoundError(name)
        return cls._plugins[name]

    @classmethod
    def get_optional(cls, name: str) -> Optional[Type[Plugin]]:
        """获取插件类，不存在返回 None"""
        return cls._plugins.get(name)

    @classmethod
    def has(cls, name: str) -> bool:
        """检查插件是否已注册"""
        return name in cls._plugins

    @classmethod
    def list_all(cls) -> Dict[str, PluginMetadata]:
        """列出所有已注册插件的元数据"""
        return {
            name: plugin.metadata
            for name, plugin in cls._plugins.items()
        }

    @classmethod
    def list_by_category(cls, category: str) -> Dict[str, Type[Plugin]]:
        """按分类列出插件"""
        return {
            name: plugin
            for name, plugin in cls._plugins.items()
            if plugin.metadata.category == category
        }

    @classmethod
    def discover(cls, package_name: str) -> int:
        """
        自动发现并加载包内的插件模块

        扫描指定包下的所有模块，触发其中 @register 装饰器执行。

        Args:
            package_name: 包名 (e.g., "netops_toolkit.plugins.builtin")

        Returns:
            新发现的插件数量
        """
        count_before = len(cls._plugins)

        try:
            package = importlib.import_module(package_name)
        except ImportError:
            return 0

        if not hasattr(package, "__path__"):
            return 0

        for _, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, prefix=f"{package_name}."
        ):
            try:
                importlib.import_module(module_name)
            except ImportError:
                continue

        return len(cls._plugins) - count_before

    @classmethod
    def clear(cls) -> None:
        """清空注册表 (用于测试)"""
        cls._plugins.clear()

    @classmethod
    def count(cls) -> int:
        """已注册插件数量"""
        return len(cls._plugins)


# 便捷别名
register = PluginRegistry.register


__all__ = ["PluginRegistry", "register"]
