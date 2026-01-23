"""
可复用UI组件模块

提供常用的Rich UI组件封装,简化界面开发。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from rich.align import Align
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.table import Table
from rich.text import Text

from .theme import NetOpsTheme, console


def create_header_panel(title: str, subtitle: str = "") -> Panel:
    """
    创建标题面板
    
    Args:
        title: 主标题
        subtitle: 副标题 (可选)
        
    Returns:
        Rich Panel对象
    """
    content_parts = [Text(title, style=NetOpsTheme.TITLE, justify="center")]
    
    if subtitle:
        content_parts.append(Text(subtitle, style=NetOpsTheme.SUBTITLE, justify="center"))
    
    content = Group(*content_parts)
    
    return Panel(
        content,
        box=NetOpsTheme.BOX_TITLE,
        border_style=NetOpsTheme.BORDER,
        padding=NetOpsTheme.PANEL_PADDING,
        expand=True,
    )


def create_info_panel(
    title: str,
    content: Union[str, RenderableType],
    style: str = NetOpsTheme.INFO,
    expand: bool = False,
) -> Panel:
    """
    创建信息面板
    
    Args:
        title: 面板标题
        content: 面板内容
        style: 边框样式
        expand: 是否扩展到全宽
        
    Returns:
        Rich Panel对象
    """
    return Panel(
        content,
        title=f"[{NetOpsTheme.HEADER}]{title}[/]",
        box=NetOpsTheme.BOX_DEFAULT,
        border_style=style,
        padding=NetOpsTheme.PANEL_PADDING,
        expand=expand,
    )


def create_result_table(
    title: str,
    columns: List[Dict[str, Any]],
    rows: List[List[Any]],
    show_header: bool = True,
    show_lines: bool = False,
) -> Table:
    """
    创建结果表格
    
    Args:
        title: 表格标题
        columns: 列定义列表,每个字典包含: header, style, justify, width等
        rows: 数据行列表
        show_header: 是否显示表头
        show_lines: 是否显示行分隔线
        
    Returns:
        Rich Table对象
        
    Example:
        columns = [
            {"header": "IP", "style": "cyan", "justify": "left"},
            {"header": "Status", "style": "green", "justify": "center"},
        ]
        rows = [
            ["192.168.1.1", "Online"],
            ["192.168.1.2", "Offline"],
        ]
        table = create_result_table("Ping Results", columns, rows)
    """
    table = Table(
        title=title,
        title_style=NetOpsTheme.TITLE,
        show_header=show_header,
        show_lines=show_lines,
        border_style=NetOpsTheme.BORDER,
        header_style=NetOpsTheme.HEADER,
    )
    
    # 添加列
    for col_def in columns:
        table.add_column(
            col_def.get("header", ""),
            style=col_def.get("style"),
            justify=col_def.get("justify", "left"),
            width=col_def.get("width"),
            no_wrap=col_def.get("no_wrap", False),
        )
    
    # 添加行
    for row in rows:
        table.add_row(*[str(cell) for cell in row])
    
    return table


def create_status_text(status: str, message: str = "") -> Text:
    """
    创建带状态的文本
    
    Args:
        status: 状态 (success, error, warning, info等)
        message: 消息文本
        
    Returns:
        Rich Text对象
    """
    status_icons = {
        "success": NetOpsTheme.ICON_SUCCESS,
        "error": NetOpsTheme.ICON_ERROR,
        "warning": NetOpsTheme.ICON_WARNING,
        "info": NetOpsTheme.ICON_INFO,
        "running": NetOpsTheme.ICON_RUNNING,
    }
    
    icon = status_icons.get(status.lower(), "•")
    color = NetOpsTheme.get_status_color(status)
    
    text = Text()
    text.append(f"{icon} ", style=color)
    text.append(message, style=color if not message else "")
    
    return text


def create_progress_bar(description: str = "Processing") -> Progress:
    """
    创建进度条
    
    Args:
        description: 进度描述文本
        
    Returns:
        Rich Progress对象
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        console=console,
    )


def create_summary_panel(
    title: str,
    stats: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> Panel:
    """
    创建统计摘要面板
    
    Args:
        title: 摘要标题
        stats: 统计数据字典
        timestamp: 时间戳 (可选)
        
    Returns:
        Rich Panel对象
        
    Example:
        stats = {
            "Total": 10,
            "Success": 8,
            "Failed": 2,
            "Success Rate": "80%",
        }
        panel = create_summary_panel("Test Results", stats)
    """
    lines = []
    
    for key, value in stats.items():
        # 根据键名选择样式
        if any(word in key.lower() for word in ["success", "ok", "pass"]):
            style = NetOpsTheme.SUCCESS
        elif any(word in key.lower() for word in ["fail", "error"]):
            style = NetOpsTheme.ERROR
        elif any(word in key.lower() for word in ["warn", "skip"]):
            style = NetOpsTheme.WARNING
        else:
            style = NetOpsTheme.INFO
        
        text = Text()
        text.append(f"{key}: ", style=NetOpsTheme.HEADER)
        text.append(str(value), style=style)
        lines.append(text)
    
    if timestamp:
        time_text = Text()
        time_text.append("时间: ", style=NetOpsTheme.MUTED)
        time_text.append(timestamp.strftime("%Y-%m-%d %H:%M:%S"), style=NetOpsTheme.INFO)
        lines.append(time_text)
    
    content = Group(*lines)
    
    return Panel(
        content,
        title=f"[{NetOpsTheme.TITLE}]{title}[/]",
        box=NetOpsTheme.BOX_DEFAULT,
        border_style=NetOpsTheme.BORDER,
        padding=NetOpsTheme.PANEL_PADDING,
    )


def print_banner(app_name: str, version: str, width: int = 60) -> None:
    """
    打印应用横幅
    
    Args:
        app_name: 应用名称
        version: 版本号
        width: 横幅宽度
    """
    banner = f"""
╔{'═' * (width - 2)}╗
║{app_name.center(width - 2)}║
║{f'v{version}'.center(width - 2)}║
╚{'═' * (width - 2)}╝
    """.strip()
    
    console.print(banner, style=NetOpsTheme.TITLE)


def print_separator(char: str = "─", style: str = NetOpsTheme.BORDER) -> None:
    """
    打印分隔线
    
    Args:
        char: 分隔符字符
        style: Rich样式
    """
    console.print(char * console.width, style=style)


__all__ = [
    "create_header_panel",
    "create_info_panel",
    "create_result_table",
    "create_status_text",
    "create_progress_bar",
    "create_summary_panel",
    "print_banner",
    "print_separator",
]
