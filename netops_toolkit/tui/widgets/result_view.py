"""
NetOps Toolkit TUI 结果视图组件

用于显示插件执行结果和日志。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.widgets import Static, RichLog
from textual.reactive import reactive


class ResultView(Static):
    """结果视图组件 - 用于显示插件执行结果"""
    
    result_data: reactive[Optional[Dict[str, Any]]] = reactive(None)
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("result-view")
    
    def render(self) -> RenderableType:
        """渲染结果视图"""
        if not self.result_data:
            return Panel(
                Text("等待执行...", style="dim"),
                title="执行结果",
                border_style="dim",
            )
        
        # 构建结果表格
        table = Table(show_header=True, expand=True)
        table.add_column("项目", style="cyan")
        table.add_column("结果", style="white")
        
        for key, value in self.result_data.items():
            if isinstance(value, (list, dict)):
                value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
            table.add_row(str(key), str(value))
        
        return Panel(
            table,
            title="[bold]执行结果[/bold]",
            border_style="green",
        )
    
    def set_result(self, data: Dict[str, Any]) -> None:
        """设置结果数据"""
        self.result_data = data
    
    def clear(self) -> None:
        """清空结果"""
        self.result_data = None


class LogView(RichLog):
    """日志视图组件 - 用于显示实时日志"""
    
    def __init__(self, **kwargs) -> None:
        super().__init__(highlight=True, markup=True, **kwargs)
        self.add_class("log-view")
    
    def log_info(self, message: str) -> None:
        """记录信息日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/dim] [blue]INFO[/blue]  {message}")
    
    def log_success(self, message: str) -> None:
        """记录成功日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/dim] [green]OK[/green]    {message}")
    
    def log_warning(self, message: str) -> None:
        """记录警告日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/dim] [yellow]WARN[/yellow]  {message}")
    
    def log_error(self, message: str) -> None:
        """记录错误日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write(f"[dim]{timestamp}[/dim] [red]ERROR[/red] {message}")
    
    def log_result(self, status: str, message: str) -> None:
        """根据状态记录结果日志"""
        if status == "success":
            self.log_success(message)
        elif status == "failed" or status == "error":
            self.log_error(message)
        elif status == "partial":
            self.log_warning(message)
        else:
            self.log_info(message)


class StatusBar(Static):
    """状态栏组件 - 显示当前操作状态"""
    
    status_text: reactive[str] = reactive("就绪")
    status_type: reactive[str] = reactive("info")  # info, success, warning, error
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("status-bar")
    
    def render(self) -> RenderableType:
        """渲染状态栏"""
        style_map = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        icon_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
        }
        
        style = style_map.get(self.status_type, "white")
        icon = icon_map.get(self.status_type, "•")
        
        return Text(f" {icon} {self.status_text}", style=style)
    
    def set_status(self, text: str, status_type: str = "info") -> None:
        """设置状态"""
        self.status_text = text
        self.status_type = status_type


__all__ = ["ResultView", "LogView", "StatusBar"]
