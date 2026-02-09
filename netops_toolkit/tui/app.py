"""
NetOps Toolkit TUI主应用

基于Textual框架的现代终端用户界面应用。
支持:
- 键盘快捷键和鼠标/触控双模式交互
- 响应式CSS样式
- 异步任务执行
- 实时数据更新
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

# 导入命令面板Provider
from .commands.plugin_provider import PluginProvider

if TYPE_CHECKING:
    from textual.screen import Screen

# CSS文件路径（相对于此文件）
STYLES_DIR = Path(__file__).parent / "styles"


class NetOpsApp(App):
    """NetOps Toolkit TUI主应用类
    
    Attributes:
        TITLE: 应用标题
        SUB_TITLE: 应用副标题
        CSS_PATH: CSS样式文件路径列表
        BINDINGS: 全局快捷键绑定
        SCREENS: 已注册的屏幕字典
    """
    
    TITLE = "NetOps Toolkit"
    SUB_TITLE = "网络工程实施及测试工具集"
    
    # 加载基础样式（主题通过dark_mode属性切换）
    CSS_PATH = [
        "styles/base.tcss",
    ]
    
    # 全局快捷键绑定
    BINDINGS = [
        Binding("q", "quit", "退出", show=True, priority=True),
        Binding("ctrl+q", "quit", "退出", show=False),
        Binding("?", "show_help", "帮助", show=True),
        Binding("f1", "show_help", "帮助", show=False),
        Binding("escape", "go_back", "返回", show=True),
        Binding("ctrl+c", "quit", "强制退出", show=False, priority=True),
        # 导航快捷键
        Binding("h", "go_home", "主页", show=True),
        Binding("d", "show_devices", "设备管理", show=True),
        Binding("c", "show_config", "配置中心", show=True),
        Binding("x", "show_diagnostics", "诊断工具", show=True),
        Binding("m", "show_monitoring", "监控仪表板", show=True),
        Binding("r", "show_reports", "报表中心", show=True),
        Binding("o", "show_topology", "网络拓扑", show=True),
        Binding("p", "show_compliance", "合规检查", show=True),
        Binding("a", "show_audit", "变更审计", show=True),
        Binding("s", "show_settings", "设置", show=True),
        # 主题切换
        Binding("t", "toggle_theme", "切换主题", show=True),
    ]
    
    # 启用命令面板
    ENABLE_COMMAND_PALETTE = True
    
    # 注册自定义命令面板Provider（合并默认Provider）
    COMMANDS = App.COMMANDS | {PluginProvider}
    
    def __init__(self, *args, **kwargs):
        """初始化应用"""
        super().__init__(*args, **kwargs)
        self._plugin_registry = None
        # 使用Textual的theme属性进行主题切换
        # 默认主textual-dark
    
    def compose(self) -> ComposeResult:
        """构建应用界面
        
        初始界面包含:
        - Header: 顶部标题栏
        - MainScreen内容（通过push_screen加载）
        - Footer: 底部快捷键提示栏
        """
        yield Header(show_clock=True)
        yield Footer()
    
    def on_mount(self) -> None:
        """应用挂载后的初始化
        
        - 加载插件注册表
        - 推送主界面
        """
        # 延迟导入避免循环引用
        from .screens.main_screen import MainScreen
        
        # 安装并推送主界面
        self.install_screen(MainScreen(), name="main")
        self.push_screen("main")
    
    # ========== Action方法 ==========
    
    def action_quit(self) -> None:
        """退出应用"""
        self.exit()
    
    def action_go_back(self) -> None:
        """返回上一界面"""
        if len(self.screen_stack) > 1:
            self.pop_screen()
    
    def action_go_home(self) -> None:
        """返回主界面"""
        # 弹出所有屏幕直到主界面
        while len(self.screen_stack) > 1:
            self.pop_screen()
    
    def action_show_help(self) -> None:
        """显示帮助界面"""
        # TODO: 实现帮助界面
        self.notify("帮助功能开发中...", title="提示")
    
    def action_show_settings(self) -> None:
        """显示设置界面"""
        # TODO: 实现设置界面
        self.notify("设置功能开发中...", title="提示")
    
    def action_show_devices(self) -> None:
        """显示设备管理界面"""
        from .screens.device_screen import DeviceScreen
        self.push_screen(DeviceScreen())
    
    def action_show_config(self) -> None:
        """显示配置中心界面"""
        from .screens.config_screen import ConfigScreen
        self.push_screen(ConfigScreen())
    
    def action_show_diagnostics(self) -> None:
        """显示诊断工具界面"""
        from .screens.diagnostics_screen import DiagnosticsScreen
        self.push_screen(DiagnosticsScreen())
    
    def action_show_monitoring(self) -> None:
        """显示监控仪表板界面"""
        from .screens.monitoring_screen import MonitoringScreen
        self.push_screen(MonitoringScreen())
    
    def action_show_reports(self) -> None:
        """显示报表中心界面"""
        from .screens.reports_screen import ReportsScreen
        self.push_screen(ReportsScreen())
    
    def action_show_topology(self) -> None:
        """显示网络拓扑界面"""
        from .screens.topology_screen import TopologyScreen
        self.push_screen(TopologyScreen())
    
    def action_show_compliance(self) -> None:
        """显示合规检查界面"""
        from .screens.compliance_screen import ComplianceScreen
        self.push_screen(ComplianceScreen())
    
    def action_show_audit(self) -> None:
        """显示变更审计界面"""
        from .screens.audit_screen import AuditScreen
        self.push_screen(AuditScreen())
    
    def action_toggle_theme(self) -> None:
        """切换明暗主题
        
        使用Textual的theme属性在textual-dark和textual-light之间切换
        """
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )
        theme_name = "暗色" if self.theme == "textual-dark" else "亮色"
        self.notify(f"已切换到{theme_name}主题", title="主题")
    
    # ========== 插件集成方法 ==========
    
    def get_plugin_registry(self):
        """获取插件注册表
        
        延迟加载以避免启动时的依赖问题
        """
        if self._plugin_registry is None:
            try:
                from ..plugins import registry
                self._plugin_registry = registry
            except ImportError:
                self._plugin_registry = {}
        return self._plugin_registry
    
    def run_plugin(self, plugin_name: str, params: dict) -> None:
        """运行指定插件
        
        Args:
            plugin_name: 插件名称
            params: 插件参数字典
        """
        # TODO: 实现插件执行逻辑
        # 将使用Worker进行后台执行
        self.notify(f"准备执行插件: {plugin_name}", title="插件")


def run_tui():
    """启动TUI应用的便捷函数"""
    app = NetOpsApp()
    app.run()


if __name__ == "__main__":
    run_tui()
