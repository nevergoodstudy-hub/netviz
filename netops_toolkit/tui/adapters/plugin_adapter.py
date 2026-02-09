"""
NetOps Toolkit TUI - 插件适配器

将插件系统与TUI组件桥接:
- PluginUIAdapter: 将Plugin类转换为TUI可用的格式
- PluginRunner: 在后台线程执行插件，支持进度回调
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union
import importlib
import pkgutil

if TYPE_CHECKING:
    from textual.app import App
    from textual.worker import Worker


class PluginExecutionStatus(str, Enum):
    """插件执行状态"""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PluginInfo:
    """TUI用的插件信息格式
    
    从Plugin类提取的信息，用于TUI显示
    """
    plugin_id: str
    display_name: str
    description: str
    category: str
    category_display: str
    icon: str
    version: str
    author: str
    parameters: List[Dict[str, Any]]
    plugin_class: Optional[Type] = None
    dependencies_ok: bool = True
    missing_deps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "version": self.version,
            "parameters": self.parameters,
        }


@dataclass
class ExecutionProgress:
    """执行进度信息"""
    current: int = 0
    total: int = 0
    message: str = ""
    percentage: float = 0.0
    
    @property
    def is_indeterminate(self) -> bool:
        """是否为不确定进度"""
        return self.total <= 0


@dataclass
class ExecutionResult:
    """执行结果"""
    status: PluginExecutionStatus
    message: str = ""
    data: Any = None
    errors: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """执行耗时(秒)"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == PluginExecutionStatus.COMPLETED


class PluginUIAdapter:
    """插件UI适配器
    
    将插件系统的Plugin类转换为TUI可用的格式
    """
    
    # 分类图标映射
    CATEGORY_ICONS = {
        "diagnostics": "🔍",
        "device_mgmt": "🖥️",
        "scanning": "📡",
        "performance": "⚡",
        "utils": "🛠️",
    }
    
    # 分类显示名称
    CATEGORY_NAMES = {
        "diagnostics": "诊断工具",
        "device_mgmt": "设备管理",
        "scanning": "网络扫描",
        "performance": "性能测试",
        "utils": "实用工具",
    }
    
    _instance: Optional["PluginUIAdapter"] = None
    _plugins_loaded: bool = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugin_cache = {}
        return cls._instance
    
    def load_all_plugins(self) -> None:
        """加载所有已注册的插件
        
        扫描并导入plugins模块下的所有插件
        """
        if self._plugins_loaded:
            return
        
        try:
            # 导入plugins包以触发所有插件的注册
            from netops_toolkit import plugins
            
            # 扫描plugins目录下的所有子模块
            package_path = plugins.__path__
            for importer, modname, ispkg in pkgutil.walk_packages(package_path, prefix="netops_toolkit.plugins."):
                try:
                    importlib.import_module(modname)
                except ImportError as e:
                    # 跳过导入失败的模块（可能缺少依赖）
                    pass
            
            self._plugins_loaded = True
        except ImportError:
            pass
    
    def get_all_plugins(self) -> Dict[str, PluginInfo]:
        """获取所有插件的TUI格式信息
        
        Returns:
            {plugin_id: PluginInfo} 字典
        """
        # 确保插件已加载
        self.load_all_plugins()
        
        # 如果有缓存，直接返回
        if self._plugin_cache:
            return self._plugin_cache
        
        try:
            from netops_toolkit.plugins import get_registered_plugins
            registered = get_registered_plugins()
            
            for name, plugin_class in registered.items():
                info = self._convert_plugin(name, plugin_class)
                self._plugin_cache[name] = info
            
            return self._plugin_cache
        except ImportError:
            return {}
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取单个插件信息
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            PluginInfo或None
        """
        plugins = self.get_all_plugins()
        return plugins.get(plugin_id)
    
    def get_plugins_by_category(self) -> Dict[str, Dict[str, PluginInfo]]:
        """按分类获取插件
        
        Returns:
            {category: {plugin_id: PluginInfo}} 嵌套字典
        """
        plugins = self.get_all_plugins()
        categorized = {}
        
        for plugin_id, info in plugins.items():
            cat = info.category
            if cat not in categorized:
                categorized[cat] = {}
            categorized[cat][plugin_id] = info
        
        return categorized
    
    def _convert_plugin(self, name: str, plugin_class: Type) -> PluginInfo:
        """将Plugin类转换为PluginInfo
        
        Args:
            name: 插件名称
            plugin_class: 插件类
            
        Returns:
            PluginInfo实例
        """
        # 获取分类
        category = getattr(plugin_class, "category", "utils")
        if hasattr(category, "value"):
            category = category.value
        
        # 获取参数规格
        parameters = []
        try:
            instance = plugin_class()
            params = instance.get_required_params()
            
            for param in params:
                param_dict = {
                    "name": param.name,
                    "type": self._get_type_name(param.param_type),
                    "description": param.description,
                    "required": param.required,
                    "default": param.default,
                }
                if param.choices:
                    param_dict["choices"] = param.choices
                parameters.append(param_dict)
            
            # 检查依赖
            deps_ok = instance.validate_dependencies()
            missing = instance.get_missing_dependencies() if not deps_ok else []
        except Exception:
            deps_ok = True
            missing = []
        
        return PluginInfo(
            plugin_id=name,
            display_name=getattr(plugin_class, "name", name),
            description=getattr(plugin_class, "description", ""),
            category=category,
            category_display=self.CATEGORY_NAMES.get(category, category),
            icon=self.CATEGORY_ICONS.get(category, "🔧"),
            version=getattr(plugin_class, "version", "1.0.0"),
            author=getattr(plugin_class, "author", "Unknown"),
            parameters=parameters,
            plugin_class=plugin_class,
            dependencies_ok=deps_ok,
            missing_deps=missing,
        )
    
    def _get_type_name(self, param_type: Type) -> str:
        """获取类型名称
        
        Args:
            param_type: Python类型
            
        Returns:
            类型名称字符串
        """
        type_map = {
            str: "string",
            int: "integer",
            float: "float",
            bool: "boolean",
            list: "list",
            dict: "dict",
        }
        return type_map.get(param_type, "string")
    
    def convert_params_for_form(self, plugin_info: PluginInfo) -> List[Dict[str, Any]]:
        """将参数规格转换为表单字段格式
        
        Args:
            plugin_info: 插件信息
            
        Returns:
            表单字段列表
        """
        form_fields = []
        
        for param in plugin_info.parameters:
            field = {
                "name": param["name"],
                "label": param.get("description") or param["name"],
                "required": param.get("required", True),
                "default": param.get("default"),
            }
            
            # 根据类型确定表单控件
            param_type = param.get("type", "string")
            if param.get("choices"):
                field["type"] = "choice"
                field["choices"] = param["choices"]
            elif param_type == "boolean":
                field["type"] = "boolean"
            elif param_type == "integer":
                field["type"] = "integer"
            elif param_type == "float":
                field["type"] = "float"
            else:
                field["type"] = "string"
            
            form_fields.append(field)
        
        return form_fields


class PluginRunner:
    """插件执行器
    
    在后台线程执行插件，支持:
    - 进度回调
    - 取消操作
    - 线程安全的UI更新
    """
    
    def __init__(
        self,
        plugin_info: PluginInfo,
        app: "App",
        on_progress: Optional[Callable[[ExecutionProgress], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[ExecutionResult], None]] = None,
    ):
        """初始化执行器
        
        Args:
            plugin_info: 插件信息
            app: Textual应用实例（用于call_from_thread）
            on_progress: 进度回调
            on_log: 日志回调
            on_complete: 完成回调
        """
        self.plugin_info = plugin_info
        self.app = app
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_complete = on_complete
        
        self._cancelled = False
        self._plugin_instance = None
        self._start_time: Optional[datetime] = None
    
    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self._cancelled
    
    def cancel(self) -> None:
        """取消执行"""
        self._cancelled = True
        self._log("任务已取消")
    
    def execute(self, params: Dict[str, Any]) -> ExecutionResult:
        """执行插件（在线程中调用）
        
        Args:
            params: 插件参数
            
        Returns:
            执行结果
        """
        self._start_time = datetime.now()
        self._cancelled = False
        
        # 检查插件类是否存在
        if not self.plugin_info.plugin_class:
            return self._create_error_result("插件类不存在")
        
        # 检查依赖
        if not self.plugin_info.dependencies_ok:
            missing = ", ".join(self.plugin_info.missing_deps)
            return self._create_error_result(f"缺少依赖: {missing}")
        
        try:
            # 创建插件实例
            self._update_progress(0, 100, "初始化插件...")
            self._plugin_instance = self.plugin_info.plugin_class()
            
            # 初始化
            if not self._plugin_instance.initialize():
                missing = self._plugin_instance.get_missing_dependencies()
                return self._create_error_result(f"初始化失败，缺少依赖: {missing}")
            
            if self._cancelled:
                return self._create_cancelled_result()
            
            # 转换参数类型（TUI表单返回的都是字符串）
            converted_params = self._convert_params(params)
            
            # 执行插件
            self._update_progress(10, 100, "正在执行...")
            self._log(f"▶ 开始执行: {self.plugin_info.display_name}")
            self._log(f"参数: {converted_params}")
            
            # 注入进度回调（如果插件支持）
            # 目前大多数插件不支持进度回调，使用模拟进度
            result = self._plugin_instance.run(**converted_params)
            
            if self._cancelled:
                return self._create_cancelled_result()
            
            # 清理
            self._plugin_instance.cleanup()
            
            # 转换结果
            return self._convert_result(result)
            
        except Exception as e:
            self._log(f"[red]❌ 执行错误: {e}[/]")
            return self._create_error_result(str(e))
    
    def _update_progress(
        self,
        current: int,
        total: int,
        message: str = "",
    ) -> None:
        """更新进度（线程安全）"""
        if self.on_progress:
            progress = ExecutionProgress(
                current=current,
                total=total,
                message=message,
                percentage=current / total * 100 if total > 0 else 0,
            )
            # 使用call_from_thread确保线程安全
            self.app.call_from_thread(self.on_progress, progress)
    
    def _log(self, message: str) -> None:
        """记录日志（线程安全）"""
        if self.on_log:
            self.app.call_from_thread(self.on_log, message)
    
    def _convert_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """根据插件参数规格转换参数类型
        
        TUI表单返回的参数都是字符串，需要根据插件定义的类型进行转换
        
        Args:
            params: 原始参数字典（值为字符串）
            
        Returns:
            转换后的参数字典
        """
        # 构建参数名称到类型的映射
        type_map = {}
        for param in self.plugin_info.parameters:
            type_map[param.get("name")] = param.get("type", "string")
        
        converted = {}
        for name, value in params.items():
            param_type = type_map.get(name, "string")
            
            # 如果值为空或None，保持不变
            if value is None or value == "":
                converted[name] = value
                continue
            
            # 根据类型转换
            try:
                if param_type in ("int", "integer", "port"):
                    converted[name] = int(value)
                elif param_type == "float":
                    converted[name] = float(value)
                elif param_type in ("bool", "boolean"):
                    # 布尔值可能是 True/False 或字符串 "true"/"false"
                    if isinstance(value, bool):
                        converted[name] = value
                    elif isinstance(value, str):
                        converted[name] = value.lower() in ("true", "1", "yes", "on")
                    else:
                        converted[name] = bool(value)
                else:
                    # 字符串类型，保持不变
                    converted[name] = value
            except (ValueError, TypeError):
                # 转换失败，保持原值
                converted[name] = value
        
        return converted
    
    def _convert_result(self, plugin_result) -> ExecutionResult:
        """转换插件结果为TUI格式"""
        end_time = datetime.now()
        
        # 从PluginResult转换
        from netops_toolkit.plugins import ResultStatus
        
        status_map = {
            ResultStatus.SUCCESS: PluginExecutionStatus.COMPLETED,
            ResultStatus.PARTIAL: PluginExecutionStatus.COMPLETED,
            ResultStatus.FAILED: PluginExecutionStatus.FAILED,
            ResultStatus.ERROR: PluginExecutionStatus.FAILED,
            ResultStatus.CANCELLED: PluginExecutionStatus.CANCELLED,
        }
        
        status = status_map.get(plugin_result.status, PluginExecutionStatus.COMPLETED)
        
        self._update_progress(100, 100, "完成")
        self._log(f"[green]✓ 执行完成: {plugin_result.message}[/]")
        
        result = ExecutionResult(
            status=status,
            message=plugin_result.message,
            data=plugin_result.data,
            errors=plugin_result.errors,
            start_time=self._start_time,
            end_time=end_time,
            metadata=plugin_result.metadata,
        )
        
        # 通知完成
        if self.on_complete:
            self.app.call_from_thread(self.on_complete, result)
        
        return result
    
    def _create_error_result(self, error_message: str) -> ExecutionResult:
        """创建错误结果"""
        end_time = datetime.now()
        
        self._update_progress(0, 100, f"错误: {error_message}")
        
        result = ExecutionResult(
            status=PluginExecutionStatus.FAILED,
            message=error_message,
            errors=[error_message],
            start_time=self._start_time,
            end_time=end_time,
        )
        
        if self.on_complete:
            self.app.call_from_thread(self.on_complete, result)
        
        return result
    
    def _create_cancelled_result(self) -> ExecutionResult:
        """创建取消结果"""
        end_time = datetime.now()
        
        result = ExecutionResult(
            status=PluginExecutionStatus.CANCELLED,
            message="任务已取消",
            start_time=self._start_time,
            end_time=end_time,
        )
        
        if self.on_complete:
            self.app.call_from_thread(self.on_complete, result)
        
        return result


def get_adapter() -> PluginUIAdapter:
    """获取适配器单例"""
    return PluginUIAdapter()
