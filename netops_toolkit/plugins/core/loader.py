"""
插件加载器

支持多种加载方式:
- 从 Python 包加载 (内置插件)
- 从文件路径加载 (外部插件)
- 从 entry_points 加载 (第三方插件)
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from netops_toolkit.domain.exceptions import PluginLoadError
from netops_toolkit.plugins.core.base import Plugin
from netops_toolkit.plugins.core.registry import PluginRegistry


class PluginLoader:
    """
    插件加载器

    集中管理插件的加载来源和加载逻辑。
    """

    ENTRY_POINT_GROUP = "netops_toolkit.plugins"
    BUILTIN_PACKAGE = "netops_toolkit.plugins.builtin"

    @classmethod
    def load_builtin(cls) -> int:
        """
        加载内置插件

        扫描 netops_toolkit.plugins.builtin 包。

        Returns:
            加载的插件数量
        """
        count = PluginRegistry.discover(cls.BUILTIN_PACKAGE)
        logger.debug(f"已加载 {count} 个内置插件")
        return count

    @classmethod
    def load_from_package(cls, package_name: str) -> int:
        """
        从指定包加载插件

        Args:
            package_name: 完整包路径

        Returns:
            加载的插件数量
        """
        count = PluginRegistry.discover(package_name)
        logger.debug(f"从 {package_name} 加载了 {count} 个插件")
        return count

    @classmethod
    def load_from_path(cls, path: str | Path) -> int:
        """
        从文件系统路径加载插件

        支持单个 .py 文件或目录。

        Args:
            path: 文件或目录路径

        Returns:
            加载的插件数量

        Raises:
            PluginLoadError: 加载失败
        """
        path = Path(path)
        count_before = PluginRegistry.count()

        if path.is_file() and path.suffix == ".py":
            cls._load_module_from_file(path)
        elif path.is_dir():
            for py_file in sorted(path.glob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                try:
                    cls._load_module_from_file(py_file)
                except PluginLoadError:
                    logger.warning(f"跳过无法加载的文件: {py_file}")
        else:
            raise PluginLoadError(str(path), f"路径不存在或不是有效的插件: {path}")

        loaded = PluginRegistry.count() - count_before
        logger.debug(f"从 {path} 加载了 {loaded} 个插件")
        return loaded

    @classmethod
    def load_from_entry_points(cls) -> int:
        """
        从 setuptools entry_points 加载第三方插件

        第三方包可在其 pyproject.toml 中声明::

            [project.entry-points."netops_toolkit.plugins"]
            my_plugin = "my_package.plugins:MyPlugin"

        Returns:
            加载的插件数量
        """
        count = 0
        try:
            eps = importlib.metadata.entry_points()
            # Python 3.12+ returns SelectableGroups
            if hasattr(eps, "select"):
                group = eps.select(group=cls.ENTRY_POINT_GROUP)
            else:
                group = eps.get(cls.ENTRY_POINT_GROUP, [])

            for ep in group:
                try:
                    plugin_class = ep.load()
                    if isinstance(plugin_class, type) and issubclass(
                        plugin_class, Plugin
                    ):
                        PluginRegistry.register(plugin_class)
                        count += 1
                        logger.debug(f"从 entry_point 加载插件: {ep.name}")
                except Exception as e:
                    logger.warning(f"加载 entry_point {ep.name} 失败: {e}")
        except Exception as e:
            logger.warning(f"读取 entry_points 失败: {e}")

        return count

    @classmethod
    def load_all(cls, extra_paths: Optional[list[str | Path]] = None) -> int:
        """
        加载所有可用插件

        按优先级加载:
        1. 内置插件
        2. entry_points 插件
        3. 额外路径插件

        Args:
            extra_paths: 额外的插件搜索路径

        Returns:
            加载的总插件数量
        """
        total = 0
        total += cls.load_builtin()
        total += cls.load_from_entry_points()

        if extra_paths:
            for p in extra_paths:
                try:
                    total += cls.load_from_path(p)
                except PluginLoadError as e:
                    logger.warning(f"加载路径 {p} 失败: {e}")

        logger.info(f"共加载 {total} 个插件 (注册表总数: {PluginRegistry.count()})")
        return total

    # ── 内部方法 ──

    @classmethod
    def _load_module_from_file(cls, file_path: Path) -> None:
        """从单个 .py 文件加载模块"""
        module_name = f"_netops_plugin_{file_path.stem}"

        try:
            spec = importlib.util.spec_from_file_location(
                module_name, str(file_path)
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(
                    str(file_path), "无法创建模块 spec"
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except PluginLoadError:
            raise
        except Exception as e:
            raise PluginLoadError(str(file_path), str(e)) from e


__all__ = ["PluginLoader"]
