"""
UI主题配置模块

定义统一的色彩规范、样式和Rich Console配置。
"""

from rich.console import Console
from rich.theme import Theme as RichTheme
from rich.box import Box, ROUNDED, DOUBLE, HEAVY


class NetOpsTheme:
    """NetOps Toolkit 主题配置类"""
    
    # ==================== 功能状态颜色 ====================
    SUCCESS = "bold green"
    ERROR = "bold red"
    WARNING = "bold yellow"
    INFO = "cyan"
    DEBUG = "dim white"
    
    # ==================== UI元素颜色 ====================
    TITLE = "bold magenta"
    SUBTITLE = "bold cyan"
    HEADER = "bold white"
    MENU_ITEM = "white"
    MENU_SELECTED = "bold cyan"
    MENU_DISABLED = "dim white"
    BORDER = "blue"
    HIGHLIGHT = "yellow"
    MUTED = "dim"
    
    # ==================== 数据展示颜色 ====================
    IP_ADDRESS = "cyan"
    HOSTNAME = "green"
    STATUS_ONLINE = "bold green"
    STATUS_OFFLINE = "bold red"
    STATUS_UNKNOWN = "yellow"
    LATENCY_GOOD = "green"      # < 50ms
    LATENCY_MEDIUM = "yellow"    # 50-100ms
    LATENCY_BAD = "red"          # > 100ms
    
    # ==================== 图标/表情符号 ====================
    ICON_SUCCESS = "✅"
    ICON_ERROR = "❌"
    ICON_WARNING = "⚠️"
    ICON_INFO = "ℹ️"
    ICON_RUNNING = "⏳"
    ICON_NETWORK = "🌐"
    ICON_DEVICE = "🖥️"
    ICON_TOOLS = "🛠️"
    ICON_SEARCH = "🔍"
    ICON_SETTINGS = "⚙️"
    ICON_CHART = "📊"
    ICON_LOG = "📝"
    
    # ==================== 盒子样式 ====================
    BOX_DEFAULT = ROUNDED
    BOX_TITLE = DOUBLE
    BOX_HEAVY = HEAVY
    
    # ==================== 面板配置 ====================
    PANEL_PADDING = (1, 2)  # (vertical, horizontal)
    PANEL_EXPAND = False
    
    @classmethod
    def get_rich_theme(cls) -> RichTheme:
        """
        获取Rich Theme配置
        
        Returns:
            配置好的Rich Theme对象
        """
        return RichTheme({
            "success": cls.SUCCESS,
            "error": cls.ERROR,
            "warning": cls.WARNING,
            "info": cls.INFO,
            "debug": cls.DEBUG,
            "title": cls.TITLE,
            "subtitle": cls.SUBTITLE,
            "header": cls.HEADER,
            "highlight": cls.HIGHLIGHT,
            "muted": cls.MUTED,
            "ip": cls.IP_ADDRESS,
            "hostname": cls.HOSTNAME,
            "online": cls.STATUS_ONLINE,
            "offline": cls.STATUS_OFFLINE,
        })
    
    @classmethod
    def get_status_color(cls, status: str) -> str:
        """
        根据状态字符串返回对应颜色
        
        Args:
            status: 状态文本 (online, offline, success, error等)
            
        Returns:
            Rich样式字符串
        """
        status_map = {
            "online": cls.STATUS_ONLINE,
            "up": cls.STATUS_ONLINE,
            "success": cls.SUCCESS,
            "ok": cls.SUCCESS,
            "offline": cls.STATUS_OFFLINE,
            "down": cls.STATUS_OFFLINE,
            "error": cls.ERROR,
            "failed": cls.ERROR,
            "warning": cls.WARNING,
            "unknown": cls.STATUS_UNKNOWN,
            "pending": cls.WARNING,
        }
        return status_map.get(status.lower(), cls.INFO)
    
    @classmethod
    def get_latency_color(cls, latency_ms: float) -> str:
        """
        根据延迟值返回对应颜色
        
        Args:
            latency_ms: 延迟毫秒数
            
        Returns:
            Rich样式字符串
        """
        if latency_ms < 50:
            return cls.LATENCY_GOOD
        elif latency_ms < 100:
            return cls.LATENCY_MEDIUM
        else:
            return cls.LATENCY_BAD


# 全局Console实例 (单例模式)
_console_instance = None


def get_console(width: int = None, force_terminal: bool = None) -> Console:
    """
    获取全局Console实例
    
    Args:
        width: 控制台宽度 (None表示自动检测)
        force_terminal: 强制终端模式
        
    Returns:
        配置好的Rich Console实例
    """
    global _console_instance
    
    if _console_instance is None:
        _console_instance = Console(
            theme=NetOpsTheme.get_rich_theme(),
            width=width,
            force_terminal=force_terminal,
            highlight=True,
            markup=True,
            emoji=True,
            soft_wrap=True,
        )
    
    return _console_instance


def reset_console() -> None:
    """重置控制台实例 (用于测试)"""
    global _console_instance
    _console_instance = None


# 便捷导出
console = get_console()


__all__ = [
    "NetOpsTheme",
    "get_console",
    "reset_console",
    "console",
]
