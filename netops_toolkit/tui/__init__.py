"""
NetOps Toolkit TUI模块

基于Textual框架的现代终端用户界面。
支持鼠标/键盘双模式交互、响应式布局和实时数据更新。

使用方法:
    from netops_toolkit.tui import run_tui
    run_tui()  # 启动TUI应用
"""

from .app import NetOpsApp, run_tui

__all__ = ["NetOpsApp", "run_tui"]
