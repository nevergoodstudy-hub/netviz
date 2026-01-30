"""
NetOps Toolkit TUI 主屏幕

显示功能分类的网格按钮界面。
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Grid, Vertical
from textual.widgets import Static, Button, Footer

from netops_toolkit import __version__
from netops_toolkit.plugins import PluginCategory, get_registered_plugins
from netops_toolkit.tui.widgets.menu_button import CategoryButton

# 导入所有插件以确保它们被注册
from netops_toolkit.plugins.diagnostics import ping, traceroute, dns_lookup
from netops_toolkit.plugins.scanning import port_scan, arp_scan
from netops_toolkit.plugins.device_mgmt import ssh_batch, config_backup, config_diff
from netops_toolkit.plugins.performance import network_quality, bandwidth_test
from netops_toolkit.plugins.utils import (
    subnet_calc, ip_converter, mac_lookup, http_debug, whois_lookup
)


# 分类配置
CATEGORY_CONFIG = {
    PluginCategory.DIAGNOSTICS: {
        "icon": "🔍",
        "label": "诊断工具",
        "description": "Ping/Traceroute/DNS 等网络诊断",
    },
    PluginCategory.SCANNING: {
        "icon": "📡",
        "label": "网络扫描",
        "description": "端口扫描/主机发现",
    },
    PluginCategory.DEVICE_MGMT: {
        "icon": "🖥️",
        "label": "设备管理",
        "description": "SSH批量/配置备份",
    },
    PluginCategory.PERFORMANCE: {
        "icon": "⚡",
        "label": "性能测试",
        "description": "网络质量/带宽测速",
    },
    PluginCategory.UTILS: {
        "icon": "🛠️",
        "label": "实用工具",
        "description": "子网计算/IP转换/MAC查询",
    },
}


def get_plugins_by_category():
    """按分类获取已注册的插件"""
    plugins = get_registered_plugins()
    categorized = {}
    
    for name, plugin_class in plugins.items():
        cat = plugin_class.category
        # 将字符串分类转换为枚举
        if isinstance(cat, str):
            try:
                category = PluginCategory(cat)
            except ValueError:
                continue  # 跳过无效分类
        else:
            category = cat
        
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(plugin_class)
    
    return categorized


class MainScreen(Screen):
    """主屏幕 - 显示功能分类的网格按钮"""
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("a", "about", "关于"),
        ("s", "settings", "设置"),
        ("1", "select_category('diagnostics')", "诊断工具"),
        ("2", "select_category('scanning')", "网络扫描"),
        ("3", "select_category('device_mgmt')", "设备管理"),
        ("4", "select_category('performance')", "性能测试"),
        ("5", "select_category('utils')", "实用工具"),
        ("6", "settings", "系统设置"),
    ]
    
    def compose(self) -> ComposeResult:
        """组合界面组件"""
        # 欢迎面板
        yield Container(
            Static(
                f"[bold cyan]🌐 NetOps Toolkit v{__version__}[/bold cyan]",
                id="welcome-title"
            ),
            Static(
                "[dim]网络工程实施及测试工具集 - 请选择功能分类[/dim]",
                id="welcome-subtitle"
            ),
            id="welcome-panel"
        )
        
        # 菜单网格
        plugins_by_category = get_plugins_by_category()
        
        with Grid(id="menu-grid"):
            for category in PluginCategory:
                config = CATEGORY_CONFIG.get(category, {})
                plugins = plugins_by_category.get(category, [])
                
                yield CategoryButton(
                    icon=config.get("icon", "•"),
                    label=config.get("label", category.value),
                    category=category.value,
                    count=len(plugins),
                    description=config.get("description", ""),
                    id=f"btn-{category.value}",
                )
            
            # 设置按钮
            yield CategoryButton(
                icon="⚙️",
                label="系统设置",
                category="settings",
                count=4,  # 4个选项卡: 系统信息/网络接口/应用配置/关于
                description="系统信息和应用配置",
                id="btn-settings",
            )
    
    def on_category_button_selected(self, event: CategoryButton.Selected) -> None:
        """处理分类按钮点击事件"""
        if event.category == "settings":
            # 打开设置屏幕
            from .settings_screen import SettingsScreen
            self.app.push_screen(SettingsScreen())
            return
        
        # 导入并推送分类屏幕
        from .category_screen import CategoryScreen
        self.app.push_screen(CategoryScreen(event.category, event.label))
    
    def action_quit(self) -> None:
        """退出应用"""
        self.app.exit()
    
    def action_about(self) -> None:
        """显示关于信息"""
        self.app.notify(
            f"NetOps Toolkit v{__version__}\n网络工程实施及测试工具集\nMIT License",
            title="关于",
            timeout=5
        )
    
    def action_settings(self) -> None:
        """打开设置"""
        from .settings_screen import SettingsScreen
        self.app.push_screen(SettingsScreen())
    
    def action_select_category(self, category: str) -> None:
        """通过数字键快速选择分类"""
        # 获取分类标签
        category_labels = {
            "diagnostics": "诊断工具",
            "scanning": "网络扫描",
            "device_mgmt": "设备管理",
            "performance": "性能测试",
            "utils": "实用工具",
        }
        label = category_labels.get(category, category)
        
        from .category_screen import CategoryScreen
        self.app.push_screen(CategoryScreen(category, label))


__all__ = ["MainScreen"]
