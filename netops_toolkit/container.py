"""
依赖注入容器

使用 dependency-injector 框架集中管理所有依赖的创建和生命周期。
支持:
- Configuration provider: 从 YAML/环境变量加载配置
- Singleton: 全局唯一实例 (配置、凭证存储等)
- Factory: 每次创建新实例 (SSH 客户端、用例等)
- Wiring: 自动注入到指定模块
"""

from __future__ import annotations

from dependency_injector import containers, providers

from netops_toolkit.application.commands.network_commands import (
    PingCommand,
    SSHBatchCommand,
)
from netops_toolkit.application.queries.device_queries import DeviceQuery
from netops_toolkit.infrastructure.config.settings import get_settings
from netops_toolkit.infrastructure.network.async_ping import AsyncPingService
from netops_toolkit.infrastructure.network.async_ssh import AsyncSSHService
from netops_toolkit.infrastructure.security.credential_store import (
    FernetCredentialStore,
)


class Container(containers.DeclarativeContainer):
    """
    NetOps Toolkit 依赖注入容器

    集中定义所有组件的装配方式和依赖关系。
    遵循 Clean Architecture 原则，依赖方向由外向内。
    """

    # ==================== 配置 ====================

    config = providers.Configuration()

    wiring_config = containers.WiringConfiguration(
        modules=[
            # 在需要注入的模块中添加
            # "netops_toolkit.presentation.cli.commands",
            # "netops_toolkit.presentation.api.routers",
        ],
    )

    # ==================== 基础设施层 - 配置 ====================

    app_settings = providers.Singleton(get_settings)

    # ==================== 基础设施层 - 安全 ====================

    credential_store = providers.Singleton(FernetCredentialStore)

    # ==================== 基础设施层 - 网络 ====================

    ping_service = providers.Singleton(AsyncPingService)

    ssh_service = providers.Singleton(AsyncSSHService)

    # ==================== 基础设施层 - 持久化 ====================

    # device_repository 需要在运行时根据配置文件路径构建,
    # 具体实现见 infrastructure/persistence/yaml_device_repository.py
    # device_repository = providers.Singleton(YamlDeviceRepository, ...)

    # ==================== 应用层 - 命令 ====================

    ping_command = providers.Factory(
        PingCommand,
        ping_service=ping_service,
    )

    # ssh_batch_command 需要 device_repository 和 credential_repository,
    # 在持久化层实现后启用:
    # ssh_batch_command = providers.Factory(
    #     SSHBatchCommand,
    #     ssh_service=ssh_service,
    #     device_repo=device_repository,
    #     credential_repo=credential_store,
    # )

    # ==================== 应用层 - 查询 ====================

    # device_query 同样需要 device_repository:
    # device_query = providers.Factory(
    #     DeviceQuery,
    #     device_repo=device_repository,
    # )


def create_container(config_path: str | None = None) -> Container:
    """
    创建并初始化容器

    Args:
        config_path: 可选的 YAML 配置文件路径

    Returns:
        已初始化的 Container 实例
    """
    container = Container()

    # 从 YAML 加载配置
    if config_path:
        container.config.from_yaml(config_path)
    else:
        # 尝试加载默认配置
        import os
        from pathlib import Path

        default_paths = [
            Path("config/settings.yaml"),
            Path.cwd() / "config" / "settings.yaml",
        ]
        for path in default_paths:
            if path.exists():
                container.config.from_yaml(str(path))
                break

    return container


# 全局容器实例 (延迟初始化)
_container: Container | None = None


def get_container() -> Container:
    """获取全局容器实例"""
    global _container
    if _container is None:
        _container = create_container()
    return _container


def reset_container() -> None:
    """重置全局容器 (用于测试)"""
    global _container
    _container = None


__all__ = [
    "Container",
    "create_container",
    "get_container",
    "reset_container",
]
