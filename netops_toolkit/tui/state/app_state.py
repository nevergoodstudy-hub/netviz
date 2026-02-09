"""
应用状态管理

集中式状态管理系统，支持:
- 状态订阅和通知
- 状态持久化
- 状态历史记录
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from weakref import WeakSet


T = TypeVar("T")


class StateChangeType(Enum):
    """状态变更类型"""
    SET = "set"
    UPDATE = "update"
    DELETE = "delete"
    RESET = "reset"


@dataclass
class StateChange:
    """状态变更记录"""
    change_type: StateChangeType
    key: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class Observable(Generic[T]):
    """可观察的值容器
    
    当值变化时自动通知订阅者
    """
    
    def __init__(self, initial_value: T) -> None:
        self._value = initial_value
        self._subscribers: list[Callable[[T, T], None]] = []
    
    @property
    def value(self) -> T:
        """获取当前值"""
        return self._value
    
    @value.setter
    def value(self, new_value: T) -> None:
        """设置新值"""
        if new_value != self._value:
            old_value = self._value
            self._value = new_value
            self._notify(old_value, new_value)
    
    def subscribe(self, callback: Callable[[T, T], None]) -> Callable[[], None]:
        """订阅值变化
        
        Args:
            callback: 回调函数，接收(old_value, new_value)
        
        Returns:
            取消订阅的函数
        """
        self._subscribers.append(callback)
        return lambda: self._subscribers.remove(callback)
    
    def _notify(self, old_value: T, new_value: T) -> None:
        """通知所有订阅者"""
        for callback in self._subscribers:
            try:
                callback(old_value, new_value)
            except Exception:
                pass


@dataclass
class AppState:
    """应用状态容器
    
    存储应用级别的状态数据
    """
    # 当前选中的插件
    current_plugin: Optional[str] = None
    current_plugin_info: Optional[dict] = None
    
    # 插件参数
    plugin_params: dict = field(default_factory=dict)
    
    # 执行状态
    is_executing: bool = False
    current_task_id: Optional[str] = None
    
    # 结果数据
    last_result: Optional[dict] = None
    result_history: list = field(default_factory=list)
    
    # 用户偏好
    theme: str = "dark"
    language: str = "zh"
    show_tips: bool = True
    
    # 连接状态
    connections: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "current_plugin": self.current_plugin,
            "plugin_params": self.plugin_params,
            "is_executing": self.is_executing,
            "theme": self.theme,
            "language": self.language,
            "show_tips": self.show_tips,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AppState":
        """从字典创建"""
        return cls(
            current_plugin=data.get("current_plugin"),
            plugin_params=data.get("plugin_params", {}),
            is_executing=data.get("is_executing", False),
            theme=data.get("theme", "dark"),
            language=data.get("language", "zh"),
            show_tips=data.get("show_tips", True),
        )


class StateManager:
    """状态管理器
    
    提供:
    - 集中式状态存储
    - 状态变更通知
    - 状态持久化
    """
    
    _instance: Optional["StateManager"] = None
    
    def __new__(cls) -> "StateManager":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._state = AppState()
        self._subscribers: dict[str, list[Callable]] = {}
        self._change_history: list[StateChange] = []
        self._max_history = 100
        self._initialized = True
    
    @property
    def state(self) -> AppState:
        """获取当前状态"""
        return self._state
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取状态值
        
        Args:
            key: 状态键名（支持点号分隔的嵌套路径）
            default: 默认值
        """
        try:
            value = self._state
            for part in key.split("."):
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict):
                    value = value.get(part, default)
                else:
                    return default
            return value
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """设置状态值
        
        Args:
            key: 状态键名
            value: 新值
        """
        old_value = self.get(key)
        
        # 设置值
        parts = key.split(".")
        if len(parts) == 1:
            if hasattr(self._state, key):
                setattr(self._state, key, value)
        else:
            # 处理嵌套路径
            obj = self._state
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict):
                    obj = obj.setdefault(part, {})
            
            final_key = parts[-1]
            if hasattr(obj, final_key):
                setattr(obj, final_key, value)
            elif isinstance(obj, dict):
                obj[final_key] = value
        
        # 记录变更
        self._record_change(StateChangeType.SET, key, old_value, value)
        
        # 通知订阅者
        self._notify(key, old_value, value)
    
    def update(self, key: str, updates: dict) -> None:
        """更新状态（合并字典）
        
        Args:
            key: 状态键名
            updates: 要合并的字典
        """
        current = self.get(key, {})
        if isinstance(current, dict):
            old_value = current.copy()
            current.update(updates)
            self._record_change(StateChangeType.UPDATE, key, old_value, current)
            self._notify(key, old_value, current)
    
    def delete(self, key: str) -> None:
        """删除状态值"""
        old_value = self.get(key)
        
        parts = key.split(".")
        if len(parts) == 1:
            if hasattr(self._state, key):
                setattr(self._state, key, None)
        else:
            obj = self._state
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict):
                    obj = obj.get(part, {})
            
            final_key = parts[-1]
            if isinstance(obj, dict) and final_key in obj:
                del obj[final_key]
        
        self._record_change(StateChangeType.DELETE, key, old_value, None)
        self._notify(key, old_value, None)
    
    def subscribe(
        self,
        key: str,
        callback: Callable[[Any, Any], None],
    ) -> Callable[[], None]:
        """订阅状态变化
        
        Args:
            key: 状态键名（可以是"*"表示订阅所有变化）
            callback: 回调函数(old_value, new_value)
        
        Returns:
            取消订阅的函数
        """
        if key not in self._subscribers:
            self._subscribers[key] = []
        
        self._subscribers[key].append(callback)
        
        def unsubscribe():
            if key in self._subscribers and callback in self._subscribers[key]:
                self._subscribers[key].remove(callback)
        
        return unsubscribe
    
    def _notify(self, key: str, old_value: Any, new_value: Any) -> None:
        """通知订阅者"""
        # 通知特定键的订阅者
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    callback(old_value, new_value)
                except Exception:
                    pass
        
        # 通知全局订阅者
        if "*" in self._subscribers:
            for callback in self._subscribers["*"]:
                try:
                    callback(old_value, new_value)
                except Exception:
                    pass
    
    def _record_change(
        self,
        change_type: StateChangeType,
        key: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """记录状态变更"""
        change = StateChange(
            change_type=change_type,
            key=key,
            old_value=old_value,
            new_value=new_value,
        )
        self._change_history.append(change)
        
        # 限制历史记录数量
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history:]
    
    def get_history(self, key: Optional[str] = None) -> list[StateChange]:
        """获取状态变更历史
        
        Args:
            key: 可选，筛选特定键的历史
        """
        if key:
            return [c for c in self._change_history if c.key == key]
        return self._change_history.copy()
    
    def reset(self) -> None:
        """重置状态"""
        old_state = self._state
        self._state = AppState()
        self._record_change(StateChangeType.RESET, "*", old_state, self._state)
        self._notify("*", old_state, self._state)
    
    def save_to_dict(self) -> dict:
        """保存状态到字典"""
        return self._state.to_dict()
    
    def load_from_dict(self, data: dict) -> None:
        """从字典加载状态"""
        self._state = AppState.from_dict(data)


# 便捷访问函数
def get_state_manager() -> StateManager:
    """获取状态管理器实例"""
    return StateManager()


def get_state(key: str, default: Any = None) -> Any:
    """获取状态值"""
    return get_state_manager().get(key, default)


def set_state(key: str, value: Any) -> None:
    """设置状态值"""
    get_state_manager().set(key, value)


def subscribe_state(key: str, callback: Callable[[Any, Any], None]) -> Callable[[], None]:
    """订阅状态变化"""
    return get_state_manager().subscribe(key, callback)
