"""
NetViz 核心配置模块
使用 pydantic-settings 管理应用配置
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基础配置
    app_name: str = "NetViz"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "production", "testing"] = "development"

    # 服务器配置
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True

    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./data/netviz.db"

    # 文件存储配置
    upload_dir: Path = Path("./data/uploads")
    max_upload_size: int = Field(default=500 * 1024 * 1024, description="最大上传文件大小(字节)")

    # GeoIP 配置
    geoip_db_path: Path = Path("./data/geoip/GeoLite2-City.mmdb")
    geoip_asn_db_path: Path = Path("./data/geoip/GeoLite2-ASN.mmdb")

    # AI 配置 - 用户自行提供密钥
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # DeepSeek
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 默认 AI 提供商
    default_ai_provider: Literal["openai", "anthropic", "ollama", "deepseek", "none"] = "none"

    # 威胁情报 API 配置
    virustotal_api_key: str | None = None
    abuseipdb_api_key: str | None = None

    # 安全配置
    secret_key: str = "netviz-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24小时

    # CORS 配置
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # 日志配置
    log_dir: Path = Path("./logs")
    log_level: str = "INFO"
    log_max_bytes: int = Field(default=10 * 1024 * 1024, description="单个日志文件最大大小(字节)")
    log_backup_count: int = Field(default=5, description="保留的历史日志文件数量")

    @computed_field
    @property
    def base_dir(self) -> Path:
        """项目根目录"""
        return Path(__file__).parent.parent.parent

    def ensure_directories(self) -> None:
        """确保必要的目录存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.geoip_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_ai_config(self, provider: str | None = None) -> dict:
        """获取指定 AI 提供商的配置"""
        provider = provider or self.default_ai_provider

        if provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.openai_model,
            }
        elif provider == "anthropic":
            return {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
            }
        elif provider == "ollama":
            return {
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
            }
        elif provider == "deepseek":
            return {
                "api_key": self.deepseek_api_key,
                "base_url": self.deepseek_base_url,
                "model": self.deepseek_model,
            }
        return {}


# 全局配置实例
settings = Settings()
