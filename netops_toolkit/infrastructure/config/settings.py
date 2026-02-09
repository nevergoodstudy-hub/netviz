"""
Pydantic Settings v2 配置管理模块

提供类型安全、可验证的配置管理:
- 支持 .env 文件、环境变量、YAML 等多源配置
- 嵌套配置模型，使用 env_nested_delimiter='__'
- SecretStr 保护敏感信息
- lru_cache 避免重复加载
- 兼容现有 settings.yaml 配置文件
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==================== 嵌套配置模型 ====================


class NetworkSettings(BaseModel):
    """网络相关配置"""

    # SSH
    ssh_timeout: int = Field(default=30, ge=1, le=300, description="SSH连接超时(秒)")
    ssh_banner_timeout: int = Field(default=15, ge=1, description="Banner超时(秒)")
    connect_retry: int = Field(default=3, ge=1, le=10, description="连接重试次数")
    retry_delay: int = Field(default=2, ge=0, description="重试间隔(秒)")
    default_port: int = Field(default=22, ge=1, le=65535, description="默认SSH端口")

    # 并发
    max_workers: int = Field(default=10, ge=1, le=100, description="最大并发工作线程数")
    thread_pool_size: int = Field(default=20, ge=1, le=200, description="线程池大小")

    # Ping
    ping_count: int = Field(default=4, ge=1, le=100, description="默认Ping次数")
    ping_timeout: float = Field(default=2.0, ge=0.1, le=30.0, description="Ping超时(秒)")
    ping_interval: float = Field(default=0.5, ge=0.01, description="Ping间隔(秒)")

    # DNS
    dns_servers: List[str] = Field(
        default=["8.8.8.8", "114.114.114.114", "223.5.5.5"],
        description="DNS服务器列表",
    )
    dns_timeout: float = Field(default=3.0, ge=0.5, description="DNS查询超时(秒)")


class SecuritySettings(BaseModel):
    """安全相关配置"""

    encrypt_passwords: bool = Field(default=True, description="是否加密存储密码")
    use_keyring: bool = Field(default=False, description="是否使用系统凭据管理器")
    session_timeout: int = Field(default=3600, ge=0, description="会话超时(秒), 0=永不超时")
    require_auth: bool = Field(default=False, description="是否需要身份验证")
    audit_logging: bool = Field(default=True, description="是否记录审计日志")

    # 敏感信息使用 SecretStr
    encryption_key: Optional[SecretStr] = Field(
        default=None,
        description="加密密钥 (用于密码加密)",
    )


class OutputSettings(BaseModel):
    """输出相关配置"""

    reports_dir: str = Field(default="./reports", description="报告输出目录")
    log_dir: str = Field(default="./logs", description="日志目录")
    export_format: str = Field(default="json", description="默认导出格式")
    save_history: bool = Field(default=True, description="是否保存历史记录")
    history_size: int = Field(default=100, ge=0, description="历史记录数量")
    auto_export: bool = Field(default=False, description="是否自动导出结果")
    timestamp_format: str = Field(
        default="%Y%m%d_%H%M%S",
        description="时间戳格式",
    )

    @field_validator("export_format")
    @classmethod
    def validate_export_format(cls, v: str) -> str:
        allowed = {"json", "csv", "xlsx", "yaml"}
        if v.lower() not in allowed:
            raise ValueError(f"export_format must be one of {allowed}, got '{v}'")
        return v.lower()


class UISettings(BaseModel):
    """UI 相关配置"""

    theme: str = Field(default="default", description="主题")
    show_banner: bool = Field(default=True, description="是否显示欢迎横幅")
    show_tips: bool = Field(default=True, description="是否显示操作提示")
    page_size: int = Field(default=20, ge=1, description="分页大小")
    confirm_dangerous: bool = Field(default=True, description="危险操作是否需要确认")
    animation: bool = Field(default=True, description="是否启用动画效果")


class LoggingSettings(BaseModel):
    """日志配置"""

    rotation: str = Field(default="10 MB", description="日志滚动策略")
    retention: str = Field(default="30 days", description="日志保留时间")
    compression: str = Field(default="zip", description="压缩格式")
    backtrace: bool = Field(default=True, description="是否记录回溯信息")
    diagnose: bool = Field(default=True, description="是否记录诊断信息")


class PluginSettings(BaseModel):
    """插件配置"""

    auto_load: bool = Field(default=True, description="是否自动加载插件")
    enabled_plugins: List[str] = Field(default_factory=list, description="启用的插件列表")
    disabled_plugins: List[str] = Field(default_factory=list, description="禁用的插件列表")


class AdvancedSettings(BaseModel):
    """高级配置"""

    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    cache_ttl: int = Field(default=300, ge=0, description="缓存过期时间(秒)")
    performance_mode: bool = Field(default=False, description="性能模式")
    debug_mode: bool = Field(default=False, description="调试模式")
    telemetry: bool = Field(default=False, description="是否发送使用统计")


# ==================== 主配置类 ====================


class AppSettings(BaseSettings):
    """
    应用主配置

    配置优先级 (从高到低):
    1. 构造函数参数
    2. 环境变量
    3. .env 文件
    4. YAML 配置文件 (通过 load_from_yaml)
    5. 默认值
    """

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_prefix="NETOPS_",
        extra="ignore",
        case_sensitive=False,
    )

    # 应用基本信息
    app_name: str = Field(default="NetOps Toolkit", description="应用名称")
    version: str = Field(default="1.0.0", description="版本号")
    description: str = Field(default="网络工程实施及测试工具集", description="描述")
    log_level: str = Field(default="INFO", description="日志级别")
    locale: str = Field(default="zh_CN", description="语言环境")
    debug: bool = Field(default=False, description="调试模式")

    # 嵌套配置
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    output: OutputSettings = Field(default_factory=OutputSettings)
    ui: UISettings = Field(default_factory=UISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    advanced: AdvancedSettings = Field(default_factory=AdvancedSettings)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    def get(self, key: str, default: Any = None) -> Any:
        """
        兼容旧配置管理器的点号访问方式

        Args:
            key: 配置键 (e.g., "network.ssh_timeout", "app.log_level")
            default: 默认值

        Returns:
            配置值
        """
        parts = key.split(".")

        # 处理旧格式的 "app.xxx" 键
        if parts[0] == "app" and len(parts) == 2:
            attr_map = {
                "name": "app_name",
                "version": "version",
                "log_level": "log_level",
                "locale": "locale",
            }
            attr_name = attr_map.get(parts[1], parts[1])
            return getattr(self, attr_name, default)

        obj: Any = self
        for part in parts:
            if isinstance(obj, BaseModel):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return default
            elif isinstance(obj, dict):
                obj = obj.get(part, default)
                if obj is default:
                    return default
            else:
                return default
        return obj


def load_settings_from_yaml(yaml_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    从 YAML 文件加载配置并转换为 AppSettings 兼容格式

    Args:
        yaml_path: YAML 文件路径

    Returns:
        配置字典
    """
    if yaml_path is None:
        # 搜索默认路径
        candidates = [
            Path("config/settings.yaml"),
            Path.cwd() / "config" / "settings.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                yaml_path = candidate
                break

    if yaml_path is None or not yaml_path.exists():
        return {}

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    # 将 YAML 的 "app" 节点映射到顶层属性
    result: Dict[str, Any] = {}
    app_section = data.get("app", {})
    if app_section:
        result["app_name"] = app_section.get("name", "NetOps Toolkit")
        result["version"] = app_section.get("version", "1.0.0")
        result["description"] = app_section.get("description", "")
        result["log_level"] = app_section.get("log_level", "INFO")
        result["locale"] = app_section.get("locale", "zh_CN")

    # 直接传递嵌套配置
    for section in ("network", "security", "output", "ui", "logging", "plugins", "advanced"):
        if section in data:
            result[section] = data[section]

    return result


@lru_cache
def get_settings(yaml_path: Optional[str] = None) -> AppSettings:
    """
    获取全局配置实例 (带缓存)

    优先从 YAML 文件加载默认值，再叠加环境变量。

    Args:
        yaml_path: 可选的 YAML 配置文件路径

    Returns:
        AppSettings 实例
    """
    path = Path(yaml_path) if yaml_path else None
    yaml_data = load_settings_from_yaml(path)
    return AppSettings(**yaml_data)


def reset_settings() -> None:
    """重置配置缓存 (用于测试或重新加载)"""
    get_settings.cache_clear()


__all__ = [
    "AppSettings",
    "NetworkSettings",
    "SecuritySettings",
    "OutputSettings",
    "UISettings",
    "LoggingSettings",
    "PluginSettings",
    "AdvancedSettings",
    "get_settings",
    "reset_settings",
    "load_settings_from_yaml",
]
