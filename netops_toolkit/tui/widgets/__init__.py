"""
TUI组件模块

可复用的UI组件:
- PluginList: 插件列表（支持分类折叠、鼠标悬停）
- PluginParamForm: 参数表单（动态生成、验证）
- ResultTable: 结果表格（实时更新、可点击行）
- ProgressPanel: 进度面板（多任务进度、动画）
- StatusBar: 状态栏（连接状态、通知）
- LogViewer: 日志查看器（实时滚动、过滤）
"""

__all__ = [
    "PluginList",
    "PluginParamForm",
    "ResultTable",
    "ProgressPanel",
    "StatusBar",
    "LogViewer",
    "Breadcrumb",
    "ActionButton",
    "Tooltip",
]

def __getattr__(name):
    if name == "PluginList":
        from .plugin_list import PluginList
        return PluginList
    if name == "PluginParamForm":
        from .param_form import PluginParamForm
        return PluginParamForm
    if name == "ResultTable":
        from .result_table import ResultTable
        return ResultTable
    if name == "ProgressPanel":
        from .progress_panel import ProgressPanel
        return ProgressPanel
    if name == "StatusBar":
        from .status_bar import StatusBar
        return StatusBar
    if name == "LogViewer":
        from .log_viewer import LogViewer
        return LogViewer
    if name == "Breadcrumb":
        from .breadcrumb import Breadcrumb
        return Breadcrumb
    if name == "ActionButton":
        from .action_button import ActionButton
        return ActionButton
    if name == "Tooltip":
        from .tooltip import Tooltip
        return Tooltip
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
