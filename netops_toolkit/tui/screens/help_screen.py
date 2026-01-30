"""
NetOps Toolkit TUI 帮助屏幕

显示快捷键和使用帮助。
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Static, Button, DataTable

from netops_toolkit import __version__


class HelpScreen(ModalScreen):
    """帮助屏幕 - 显示快捷键和使用说明"""
    
    BINDINGS = [
        ("escape", "close_help", "关闭"),
        ("f1", "close_help", "关闭"),
        ("q", "close_help", "关闭"),
    ]
    
    def compose(self) -> ComposeResult:
        """组合界面组件"""
        with Container(id="help-container"):
            yield Static(
                f"[bold cyan]📖 NetOps Toolkit v{__version__} 帮助[/bold cyan]",
                id="help-title"
            )
            
            with ScrollableContainer(id="help-content"):
                # 快捷键列表
                yield Static(
                    "[bold yellow]⌨️ 全局快捷键[/bold yellow]",
                    classes="help-section-title"
                )
                yield Static("""
  [green]Q[/green]          退出应用
  [green]Escape[/green]     返回上一屏幕
  [green]F1[/green]         显示此帮助
  [green]Ctrl+R[/green]     刷新当前界面
  [green]Ctrl+P[/green]     打开命令面板
  [green]Tab[/green]        切换到下一个组件
  [green]Shift+Tab[/green]  切换到上一个组件
  [green]Enter/空格[/green] 激活当前按钮
  [green]方向键[/green]     在选项间移动
""", classes="help-content")
                
                # 主屏幕快捷键
                yield Static(
                    "[bold yellow]🏠 主屏幕[/bold yellow]",
                    classes="help-section-title"
                )
                yield Static("""
  [green]S[/green]          打开系统设置
  [green]A[/green]          显示关于信息
  [green]1-6[/green]        快速选择功能分类
""", classes="help-content")
                
                # 设置屏幕快捷键
                yield Static(
                    "[bold yellow]⚙️ 系统设置[/bold yellow]",
                    classes="help-section-title"
                )
                yield Static("""
  [green]R[/green]          刷新系统信息
  [green]Ctrl+S[/green]     保存配置更改
""", classes="help-content")
                
                # 功能说明
                yield Static(
                    "[bold yellow]📋 功能分类说明[/bold yellow]",
                    classes="help-section-title"
                )
                yield Static("""
  [cyan]🔍 诊断工具[/cyan]    Ping/Traceroute/DNS等网络诊断
  [cyan]📡 网络扫描[/cyan]    端口扫描/主机发现
  [cyan]🖥️ 设备管理[/cyan]    SSH批量执行/配置备份
  [cyan]⚡ 性能测试[/cyan]    网络质量/带宽测速
  [cyan]🛠️ 实用工具[/cyan]    子网计算/IP转换/MAC查询
""", classes="help-content")
                
                # 使用技巧
                yield Static(
                    "[bold yellow]💡 使用技巧[/bold yellow]",
                    classes="help-section-title"
                )
                yield Static("""
  • 使用 [green]Tab[/green] 键在按钮间移动，[green]Enter[/green] 键确认
  • 鼠标点击可直接选择功能
  • 插件执行后结果会显示在日志区域
  • 部分功能需要安装额外依赖
""", classes="help-content")
            
            yield Button("关闭帮助 (Esc/F1)", id="close-help-btn", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "close-help-btn":
            self.action_close_help()
    
    def action_close_help(self) -> None:
        """关闭帮助屏幕"""
        self.app.pop_screen()


__all__ = ["HelpScreen"]
