"""
配置管理器模块

负责加载、解析、验证YAML配置文件。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器类"""
    
    DEFAULT_CONFIG_DIR = Path("config")
    DEFAULT_SETTINGS_FILE = "settings.yaml"
    DEFAULT_DEVICES_FILE = "devices.yaml"
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录路径 (None表示使用默认路径)
        """
        self.config_dir = Path(config_dir) if config_dir else self.DEFAULT_CONFIG_DIR
        self._settings: Optional[Dict[str, Any]] = None
        self._devices: Optional[Dict[str, Any]] = None
        
        logger.info(f"配置管理器已初始化 | 配置目录: {self.config_dir}")
    
    def load_settings(self, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        加载全局配置
        
        Args:
            file_name: 配置文件名 (None表示使用默认)
            
        Returns:
            配置字典
        """
        if file_name is None:
            file_name = self.DEFAULT_SETTINGS_FILE
        
        config_path = self.config_dir / file_name
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}, 使用默认配置")
            return self._get_default_settings()
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._settings = yaml.safe_load(f) or {}
            logger.info(f"配置文件已加载: {config_path}")
            return self._settings
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self._get_default_settings()
    
    def load_devices(self, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        加载设备清单配置
        
        Args:
            file_name: 设备清单文件名 (None表示使用默认)
            
        Returns:
            设备清单字典
        """
        if file_name is None:
            file_name = self.DEFAULT_DEVICES_FILE
        
        config_path = self.config_dir / file_name
        
        if not config_path.exists():
            logger.warning(f"设备清单文件不存在: {config_path}")
            return {"groups": {}, "standalone_devices": []}
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._devices = yaml.safe_load(f) or {}
            logger.info(f"设备清单已加载: {config_path}")
            return self._devices
        except Exception as e:
            logger.error(f"加载设备清单失败: {e}")
            return {"groups": {}, "standalone_devices": []}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值 (支持点号分隔的嵌套键)
        
        Args:
            key: 配置键 (e.g., "network.ssh_timeout")
            default: 默认值
            
        Returns:
            配置值
        """
        if self._settings is None:
            self.load_settings()
        
        keys = key.split(".")
        value = self._settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "app": {
                "name": "NetOps Toolkit",
                "version": "1.0.0",
                "log_level": "INFO",
            },
            "network": {
                "ssh_timeout": 30,
                "connect_retry": 3,
                "default_port": 22,
                "max_workers": 10,
                "ping_count": 4,
                "ping_timeout": 2.0,
            },
            "security": {
                "encrypt_passwords": True,
                "session_timeout": 3600,
                "audit_logging": True,
            },
            "output": {
                "reports_dir": "./reports",
                "log_dir": "./logs",
                "export_format": "json",
            },
            "ui": {
                "theme": "default",
                "show_banner": True,
                "confirm_dangerous": True,
            },
            "logging": {
                "rotation": "10 MB",
                "retention": "30 days",
                "compression": "zip",
            },
        }


# 全局配置实例 (单例)
_config_instance: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Returns:
        ConfigManager实例
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = ConfigManager()
        _config_instance.load_settings()
        _config_instance.load_devices()
    
    return _config_instance


__all__ = ["ConfigManager", "get_config"]
