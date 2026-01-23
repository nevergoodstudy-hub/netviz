"""
插件基类模块

定义所有插件的抽象接口和生命周期管理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type


class PluginCategory(str, Enum):
    """插件分类枚举"""
    DIAGNOSTICS = "diagnostics"      # 诊断工具
    DEVICE_MGMT = "device_mgmt"      # 设备管理
    SCANNING = "scanning"            # 网络扫描
    PERFORMANCE = "performance"      # 性能测试
    UTILS = "utils"                  # 实用工具


class ResultStatus(str, Enum):
    """结果状态枚举"""
    SUCCESS = "success"
    PARTIAL = "partial"   # 部分成功
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class PluginResult:
    """
    插件执行结果数据类
    
    Attributes:
        status: 执行状态
        message: 结果消息
        data: 结果数据 (字典或列表)
        errors: 错误列表
        start_time: 开始时间
        end_time: 结束时间
        metadata: 元数据
    """
    status: ResultStatus
    message: str = ""
    data: Any = None
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """计算执行耗时(秒)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status in (ResultStatus.SUCCESS, ResultStatus.PARTIAL)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "metadata": self.metadata,
        }


@dataclass
class ParamSpec:
    """
    参数规格说明
    
    用于定义插件所需的输入参数
    """
    name: str
    param_type: Type
    description: str = ""
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None


class Plugin(ABC):
    """
    插件抽象基类
    
    所有功能插件必须继承此类并实现抽象方法。
    """
    
    # 插件元数据 (子类必须定义)
    name: str = "BasePlugin"
    category: PluginCategory = PluginCategory.UTILS
    description: str = "Base plugin class"
    version: str = "1.0.0"
    author: str = "NetOps Team"
    
    # 插件依赖 (可选)
    dependencies: List[str] = []
    
    def __init__(self):
        """初始化插件"""
        self._initialized = False
        self._result: Optional[PluginResult] = None
    
    @abstractmethod
    def validate_dependencies(self) -> bool:
        """
        验证插件依赖
        
        检查运行此插件所需的外部依赖是否满足。
        
        Returns:
            True表示依赖满足, False表示缺少依赖
        """
        pass
    
    @abstractmethod
    def get_required_params(self) -> List[ParamSpec]:
        """
        获取插件所需参数规格
        
        Returns:
            参数规格列表
        """
        pass
    
    @abstractmethod
    def run(self, **kwargs) -> PluginResult:
        """
        执行插件主逻辑
        
        Args:
            **kwargs: 插件参数
            
        Returns:
            PluginResult执行结果
        """
        pass
    
    def initialize(self) -> bool:
        """
        初始化插件
        
        在执行run()之前调用,用于准备资源。
        
        Returns:
            True表示初始化成功
        """
        if not self.validate_dependencies():
            return False
        self._initialized = True
        return True
    
    def cleanup(self) -> None:
        """
        清理插件资源
        
        在执行完成后调用,用于释放资源。
        """
        self._initialized = False
    
    def get_menu_title(self) -> str:
        """
        获取菜单显示标题
        
        Returns:
            带图标的菜单标题
        """
        icons = {
            PluginCategory.DIAGNOSTICS: "🔍",
            PluginCategory.DEVICE_MGMT: "🖥️",
            PluginCategory.SCANNING: "📡",
            PluginCategory.PERFORMANCE: "⚡",
            PluginCategory.UTILS: "🛠️",
        }
        icon = icons.get(self.category, "•")
        return f"{icon} {self.name}"
    
    def __repr__(self) -> str:
        return f"<Plugin: {self.name} v{self.version}>"


# 插件注册表
_plugin_registry: Dict[str, Type[Plugin]] = {}


def register_plugin(plugin_class: Type[Plugin]) -> Type[Plugin]:
    """
    插件注册装饰器
    
    使用方法:
        @register_plugin
        class MyPlugin(Plugin):
            ...
    """
    _plugin_registry[plugin_class.name] = plugin_class
    return plugin_class


def get_registered_plugins() -> Dict[str, Type[Plugin]]:
    """获取所有已注册的插件"""
    return _plugin_registry.copy()


__all__ = [
    "Plugin",
    "PluginCategory",
    "PluginResult",
    "ResultStatus",
    "ParamSpec",
    "register_plugin",
    "get_registered_plugins",
]
