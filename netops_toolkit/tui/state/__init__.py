"""
TUI状态管理模块

集中式状态管理:
- AppState: 应用状态容器
- StateManager: 状态管理器（响应式更新通知）
"""

from .app_state import AppState, StateManager

__all__ = ["AppState", "StateManager"]
