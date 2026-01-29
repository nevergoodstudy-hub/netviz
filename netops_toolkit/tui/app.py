"""
NetOps Toolkit TUI 主应用

基于 Textual 框架构建的现代化 TUI 界面。
"""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from netops_toolkit import __version__
from netops_toolkit.config.config_manager import get_config
from netops_toolkit.core.logger import setup_logging, get_logger

from .screens.main_screen import MainScreen

logger = get_logger(__name__)


class NetOpsApp(App):
    """NetOps Toolkit TUI 主应用类"""
    
    # 应用标题
    TITLE = "NetOps Toolkit"
    SUB_TITLE = f"网络工程实施及测试工具集 v{__version__}"
    
    # CSS 样式文件路径
    CSS_PATH = Path(__file__).parent / "styles" / "netops.tcss"
    
    # 全局快捷键绑定
    BINDINGS = [
        Binding("q", "quit", "退出", show=True, priority=True),
        Binding("escape", "go_back", "返回", show=True),
        Binding("f1", "show_help", "帮助", show=True),
        Binding("ctrl+r", "refresh", "刷新", show=True),
        Binding("ctrl+l", "toggle_log", "日志", show=False),
    ]
    
    # 启用命令面板
    ENABLE_COMMAND_PALETTE = True
    
    def __init__(self):
        """初始化应用"""
        super().__init__()
        self._init_config()
    
    def _init_config(self) -> None:
        """初始化配置"""
        config = get_config()
        
        # 设置日志
        log_level = config.get("app.log_level", "INFO")
        log_dir = config.get("output.log_dir", "./logs")
        
        setup_logging(
            log_dir=log_dir,
            log_level=log_level,
            enable_console=False,  # TUI 模式禁用控制台日志
            enable_file=True,
        )
        
        logger.info("NetOps Toolkit TUI 应用已初始化")
    
    def compose(self) -> ComposeResult:
        """组合根界面组件"""
        yield Header(show_clock=True)
        yield Footer()
    
    def on_mount(self) -> None:
        """应用挂载时的回调"""
        # 推送主屏幕
        self.push_screen(MainScreen())
        logger.info("TUI 主界面已加载")
    
    def action_quit(self) -> None:
        """退出应用"""
        logger.info("用户退出 TUI 应用")
        self.exit()
    
    def action_go_back(self) -> None:
        """返回上一屏幕"""
        if len(self.screen_stack) > 1:
            self.pop_screen()
    
    def action_show_help(self) -> None:
        """显示帮助信息"""
        # TODO: 实现帮助屏幕
        self.notify("帮助功能开发中...", title="提示")
    
    def action_refresh(self) -> None:
        """刷新当前界面"""
        self.refresh()
        self.notify("界面已刷新", title="刷新")
    
    def action_toggle_log(self) -> None:
        """切换日志面板"""
        # TODO: 实现日志面板切换
        pass


def run_tui() -> None:
    """运行 TUI 应用的便捷函数"""
    app = NetOpsApp()
    app.run()


if __name__ == "__main__":
    run_tui()
