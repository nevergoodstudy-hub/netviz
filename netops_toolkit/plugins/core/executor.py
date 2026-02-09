"""
插件执行器

负责插件的生命周期管理:
- 依赖检查
- 输入验证
- 执行 (同步/异步)
- 错误处理
- 审计日志
"""

from __future__ import annotations

import asyncio
import importlib
from datetime import datetime
from typing import Any, Type

from pydantic import BaseModel

from netops_toolkit.domain.exceptions import (
    PluginDependencyError,
    PluginExecutionError,
)
from netops_toolkit.plugins.core.base import Plugin


class PluginExecutor:
    """
    插件执行器

    将依赖验证、生命周期管理等横切关注点从插件基类中分离出来。
    """

    @staticmethod
    def check_dependencies(plugin: Plugin) -> list[str]:
        """
        检查插件的外部依赖

        Returns:
            缺失的依赖列表
        """
        missing: list[str] = []
        for dep in plugin.metadata.dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)
        return missing

    @staticmethod
    async def execute_async(
        plugin: Plugin,
        input_data: BaseModel,
        check_deps: bool = True,
    ) -> Any:
        """
        异步执行插件

        完整的执行流程:
        1. 检查依赖
        2. 验证输入
        3. 调用 on_before_execute
        4. 执行 execute
        5. 调用 on_after_execute
        6. 返回结果

        Args:
            plugin: 插件实例
            input_data: 输入数据
            check_deps: 是否检查依赖

        Returns:
            插件执行结果

        Raises:
            PluginDependencyError: 依赖缺失
            PluginExecutionError: 执行失败
        """
        name = plugin.metadata.name

        # 1. 依赖检查
        if check_deps:
            missing = PluginExecutor.check_dependencies(plugin)
            if missing:
                raise PluginDependencyError(name, missing)

        # 2. 输入验证
        plugin.validate_input(input_data)

        # 3-5. 执行
        try:
            await plugin.on_before_execute(input_data)
            result = await plugin.execute(input_data)
            await plugin.on_after_execute(input_data, result)
            return result
        except (PluginDependencyError, PluginExecutionError):
            raise
        except Exception as e:
            raise PluginExecutionError(name, str(e)) from e

    @staticmethod
    def execute_sync(
        plugin: Plugin,
        input_data: BaseModel,
        check_deps: bool = True,
    ) -> Any:
        """
        同步执行插件 (CLI 兼容)

        在没有事件循环时创建新的事件循环执行。

        Args:
            plugin: 插件实例
            input_data: 输入数据
            check_deps: 是否检查依赖

        Returns:
            插件执行结果
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 已在异步上下文中，创建 task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    PluginExecutor.execute_async(plugin, input_data, check_deps),
                )
                return future.result()
        else:
            return asyncio.run(
                PluginExecutor.execute_async(plugin, input_data, check_deps)
            )


__all__ = ["PluginExecutor"]
