"""
NetOps Toolkit TUI 分类屏幕

显示特定分类下的所有插件按钮列表。
"""

import hashlib

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Static, Button

from netops_toolkit.plugins import PluginCategory, get_registered_plugins
from netops_toolkit.tui.widgets.menu_button import MenuButton


def make_safe_id(name: str) -> str:
    """将名称转换为安全的 widget ID (只含 ASCII)"""
    return f"plugin-{hashlib.md5(name.encode()).hexdigest()[:8]}"


# 插件图标配置
PLUGIN_ICONS = {
    "Ping测试": "🏓",
    "路由追踪": "🗺️",
    "DNS查询": "🌐",
    "端口扫描": "🔌",
    "ARP扫描": "📶",
    "SSH批量执行": "💻",
    "ssh_batch": "💻",
    "配置备份": "💾",
    "配置对比": "📊",
    "网络质量测试": "📈",
    "带宽测速": "🚀",
    "子网计算器": "🔢",
    "IP格式转换": "🔄",
    "MAC地址查询": "🏭",
    "HTTP调试": "🌍",
    "WHOIS查询": "📋",
}


def get_plugins_for_category(category_value: str):
    """获取特定分类的插件列表"""
    plugins = get_registered_plugins()
    category_plugins = []
    
    for name, plugin_class in plugins.items():
        # 处理 category 可能是枚举或字符串的情况
        cat = plugin_class.category
        cat_value = cat.value if hasattr(cat, 'value') else str(cat)
        if cat_value == category_value:
            category_plugins.append((name, plugin_class))
    
    return category_plugins


class CategoryScreen(Screen):
    """分类屏幕 - 显示该分类下的所有插件"""
    
    BINDINGS = [
        ("escape", "go_back", "返回"),
        ("q", "go_back", "返回"),
    ]
    
    def __init__(self, category: str, category_label: str) -> None:
        """
        初始化分类屏幕
        
        Args:
            category: 分类标识
            category_label: 分类显示名称
        """
        super().__init__()
        self.category = category
        self.category_label = category_label
    
    def compose(self) -> ComposeResult:
        """组合界面组件"""
        # 标题
        yield Container(
            Static(
                f"[bold cyan]{self.category_label}[/bold cyan]",
                id="category-title"
            ),
            Static(
                "[dim]选择要执行的功能[/dim]",
                id="category-subtitle"
            ),
            id="welcome-panel"
        )
        
        # 插件列表
        plugins = get_plugins_for_category(self.category)
        
        with ScrollableContainer(id="plugin-list-container"):
            for name, plugin_class in plugins:
                plugin = plugin_class()
                icon = PLUGIN_ICONS.get(plugin.name, "•")
                
                yield MenuButton(
                    icon=icon,
                    label=f"{plugin.name} - {plugin.description}",
                    plugin_name=plugin.name,
                    plugin_class=plugin_class,
                    description=plugin.description,
                    id=make_safe_id(name),
                )
            
            # 返回按钮
            yield Button("⬅️ 返回主菜单", id="back-button", variant="error")
    
    def on_menu_button_selected(self, event: MenuButton.Selected) -> None:
        """处理插件按钮点击事件"""
        from .plugin_screen import PluginScreen
        self.app.push_screen(PluginScreen(event.plugin_name, event.plugin_class))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        if event.button.id == "back-button":
            self.action_go_back()
    
    def action_go_back(self) -> None:
        """返回主屏幕"""
        self.app.pop_screen()


__all__ = ["CategoryScreen"]
