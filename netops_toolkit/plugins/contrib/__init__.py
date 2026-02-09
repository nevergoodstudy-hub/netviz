"""
社区贡献插件包

社区插件由第三方开发者贡献，放置在此目录下。
通过 PluginRegistry.discover("netops_toolkit.plugins.contrib") 自动加载。

开发社区插件:
1. 在此目录下创建 Python 模块
2. 继承 Plugin[TInput, TOutput] 基类
3. 使用 @register 装饰器注册插件
4. 定义 PluginMetadata 声明插件元数据

示例::

    from pydantic import BaseModel
    from netops_toolkit.plugins.core.base import Plugin, PluginMetadata
    from netops_toolkit.plugins.core.registry import register

    class MyInput(BaseModel):
        target: str

    class MyOutput(BaseModel):
        result: str

    @register
    class MyContribPlugin(Plugin[MyInput, MyOutput]):
        metadata = PluginMetadata(
            name="my_contrib_plugin",
            version="1.0.0",
            description="示例社区插件",
            author="Your Name",
            category="utils",
        )

        async def execute(self, input: MyInput) -> MyOutput:
            return MyOutput(result=f"processed: {input.target}")
"""

from __future__ import annotations

# 社区插件包标识
CONTRIB_PACKAGE = "netops_toolkit.plugins.contrib"

__all__ = ["CONTRIB_PACKAGE"]
