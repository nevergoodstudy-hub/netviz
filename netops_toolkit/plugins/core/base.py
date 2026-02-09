"""
简化的插件基类

遵循单一职责原则:
- Plugin 只有一个抽象方法: execute()
- 输入/输出通过 Pydantic 模型自动验证
- 元数据通过 PluginMetadata 声明
- 依赖验证、生命周期由 Executor 管理
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class PluginMetadata(BaseModel):
    """插件元数据"""

    name: str = Field(..., description="插件唯一标识")
    version: str = Field(default="1.0.0", description="版本号")
    description: str = Field(default="", description="描述")
    author: str = Field(default="NetOps Team", description="作者")
    category: str = Field(default="utils", description="分类")
    dependencies: list[str] = Field(default_factory=list, description="外部依赖")


TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class Plugin(ABC, Generic[TInput, TOutput]):
    """
    简化的插件基类

    泛型参数:
        TInput: 输入模型 (Pydantic BaseModel 子类)
        TOutput: 输出模型 (Pydantic BaseModel 子类)

    子类只需实现 execute() 方法和定义 metadata 属性。

    示例::

        class PingInput(BaseModel):
            targets: list[str]
            count: int = 4

        class PingOutput(BaseModel):
            results: list[PingResult]

        class PingPlugin(Plugin[PingInput, PingOutput]):
            metadata = PluginMetadata(name="ping", category="diagnostics")

            async def execute(self, input: PingInput) -> PingOutput:
                ...
    """

    metadata: PluginMetadata

    @abstractmethod
    async def execute(self, input: TInput) -> TOutput:
        """
        执行插件逻辑

        这是唯一需要实现的抽象方法。

        Args:
            input: 经过 Pydantic 验证的输入数据

        Returns:
            插件执行结果
        """
        ...

    def validate_input(self, input: TInput) -> None:
        """
        输入验证钩子

        默认依赖 Pydantic 自动验证，子类可覆盖以添加自定义验证。
        """
        pass

    async def on_before_execute(self, input: TInput) -> None:
        """执行前钩子 (可选)"""
        pass

    async def on_after_execute(self, input: TInput, output: TOutput) -> None:
        """执行后钩子 (可选)"""
        pass

    def __repr__(self) -> str:
        return f"<Plugin: {self.metadata.name} v{self.metadata.version}>"


__all__ = ["Plugin", "PluginMetadata", "TInput", "TOutput"]
