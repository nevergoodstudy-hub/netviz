"""
NetOps Toolkit TUI - 主界面

主界面包含:
- 侧边栏: 插件分类列表（可折叠）
- 内容区: 插件详情/欢迎页面
- 支持鼠标点击和键盘导航
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static, ListItem, ListView, Input
from textual.message import Message
from textual import lazy  # 懒加载支持

if TYPE_CHECKING:
    from ..app import NetOpsApp


class PluginItem(ListItem):
    """可点击的插件列表项
    
    支持鼠标点击和键盘选择
    """
    
    DEFAULT_CSS = """
    PluginItem {
        height: 2;
        padding: 0 1;
    }
    
    PluginItem:hover {
        background: $primary-darken-3;
    }
    
    PluginItem.-highlighted {
        background: $primary;
        color: $text;
    }
    
    PluginItem.-highlighted:hover {
        background: $primary-lighten-1;
    }
    """
    
    class Selected(Message):
        """插件被选中的消息"""
        def __init__(self, plugin_name: str, plugin_info: dict) -> None:
            self.plugin_name = plugin_name
            self.plugin_info = plugin_info
            super().__init__()
    
    class Activated(Message):
        """插件被激活（双击或回车）的消息"""
        def __init__(self, plugin_name: str, plugin_info: dict) -> None:
            self.plugin_name = plugin_name
            self.plugin_info = plugin_info
            super().__init__()
    
    def __init__(self, plugin_name: str, plugin_info: dict, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.plugin_name = plugin_name
        self.plugin_info = plugin_info
        self._last_click_time = 0
    
    def compose(self) -> ComposeResult:
        """渲染插件项"""
        # 图标 + 名称
        icon = self.plugin_info.get("icon", "🔧")
        display_name = self.plugin_info.get("display_name", self.plugin_name)
        yield Label(f"{icon} {display_name}")
    
    def on_click(self, event) -> None:
        """处理点击事件
        
        单击：选中并显示详情
        双击：打开插件执行界面
        """
        import time
        current_time = time.time()
        
        # 检测双击（300ms内）
        if current_time - self._last_click_time < 0.3:
            # 双击 - 激活插件
            self.post_message(self.Activated(self.plugin_name, self.plugin_info))
        else:
            # 单击 - 选中插件
            self.post_message(self.Selected(self.plugin_name, self.plugin_info))
        
        self._last_click_time = current_time


class CategoryGroup(Static):
    """可折叠的分类组
    
    点击标题可展开/折叠插件列表
    """
    
    DEFAULT_CSS = """
    CategoryGroup {
        height: auto;
        margin: 0 0 1 0;
    }
    
    CategoryGroup > .category-title {
        height: 2;
        padding: 0 1;
        text-style: bold;
    }
    
    CategoryGroup > .category-title:hover {
        background: $primary-darken-3;
    }
    
    CategoryGroup > .category-plugins {
        padding-left: 2;
    }
    
    CategoryGroup.-collapsed > .category-plugins {
        display: none;
    }
    """
    
    def __init__(
        self, 
        category_name: str, 
        category_display: str,
        plugins: dict,
        *args, 
        **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.category_name = category_name
        self.category_display = category_display
        self.plugins = plugins
        self._collapsed = False
    
    def compose(self) -> ComposeResult:
        """渲染分类组"""
        # 分类标题（可点击折叠）
        icon = "▼" if not self._collapsed else "▶"
        yield Label(
            f"{icon} {self.category_display} ({len(self.plugins)})",
            classes="category-title",
        )
        
        # 插件列表
        with Vertical(classes="category-plugins"):
            for name, info in self.plugins.items():
                yield PluginItem(name, info, classes="plugin-item")
    
    def on_click(self, event) -> None:
        """处理点击事件 - 折叠/展开"""
        # 只响应标题区域的点击
        if hasattr(event, 'widget') and "category-title" in event.widget.classes:
            self.toggle_collapse()
    
    def toggle_collapse(self) -> None:
        """切换折叠状态"""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.add_class("-collapsed")
        else:
            self.remove_class("-collapsed")
        # 更新图标
        title = self.query_one(".category-title", Label)
        icon = "▶" if self._collapsed else "▼"
        title.update(f"{icon} {self.category_display} ({len(self.plugins)})")


class WelcomePanel(Static):
    """欢迎面板 - 显示在未选择插件时"""
    
    DEFAULT_CSS = """
    WelcomePanel {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    
    WelcomePanel > .welcome-content {
        width: 60;
        height: auto;
        padding: 2 4;
        border: round $primary;
        text-align: center;
    }
    
    WelcomePanel .welcome-title {
        text-style: bold;
        padding: 1 0;
    }
    
    WelcomePanel .welcome-subtitle {
        color: $text-muted;
        padding: 1 0;
    }
    
    WelcomePanel .quick-actions {
        layout: horizontal;
        align: center middle;
        height: auto;
        padding: 2 0 0 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        """渲染欢迎内容"""
        with Container(classes="welcome-content"):
            yield Label("🛠️ NetOps Toolkit", classes="welcome-title")
            yield Label("网络工程实施及测试工具集", classes="welcome-subtitle")
            yield Static("─" * 40)
            yield Label(
                "从左侧选择一个工具开始使用\n"
                "或使用快捷键快速导航",
                classes="welcome-hint"
            )
            with Horizontal(classes="quick-actions"):
                yield Button("📋 查看所有工具", id="btn-all-tools", classes="btn-primary")
                yield Button("❓ 帮助", id="btn-help", classes="btn-secondary")


class PluginDetailPanel(Static):
    """插件详情面板 - 显示选中插件的信息"""
    
    DEFAULT_CSS = """
    PluginDetailPanel {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }
    
    PluginDetailPanel > .detail-header {
        height: 3;
        padding: 0 1;
        border-bottom: solid $primary-darken-2;
    }
    
    PluginDetailPanel > .detail-content {
        height: 1fr;
        padding: 1;
    }
    
    PluginDetailPanel > .detail-actions {
        height: auto;
        padding: 1 0;
        align: center middle;
    }
    """
    
    def __init__(self, plugin_name: str = "", plugin_info: dict = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_name = plugin_name
        self.plugin_info = plugin_info or {}
    
    def compose(self) -> ComposeResult:
        """渲染插件详情"""
        icon = self.plugin_info.get("icon", "🔧")
        display_name = self.plugin_info.get("display_name", self.plugin_name)
        description = self.plugin_info.get("description", "暂无描述")
        
        # 头部
        with Container(classes="detail-header"):
            yield Label(f"{icon} {display_name}", classes="detail-title")
        
        # 内容
        with VerticalScroll(classes="detail-content"):
            yield Label(f"📝 描述: {description}")
            yield Static("─" * 40)
            
            # 显示参数信息
            params = self.plugin_info.get("params", [])
            if params:
                yield Label("📋 参数:", classes="section-title")
                for param in params:
                    param_name = param.get("name", "unknown")
                    param_type = param.get("type", "str")
                    required = "必填" if param.get("required", False) else "可选"
                    yield Label(f"  • {param_name} ({param_type}) - {required}")
        
        # 操作按钮
        with Horizontal(classes="detail-actions"):
            yield Button("▶ 执行", id="btn-execute", classes="btn-primary")
            yield Button("⚙ 配置参数", id="btn-configure", classes="btn-secondary")


class MainScreen(Screen):
    """主界面屏幕
    
    布局:
    ┌──────────┬────────────────────────────┐
    │          │                            │
    │  侧边栏   │         内容区             │
    │  (插件   │   (欢迎页/插件详情)         │
    │   列表)  │                            │
    │          │                            │
    └──────────┴────────────────────────────┘
    """
    
    TITLE = "主页"
    SUB_TITLE = "选择一个工具开始使用"
    
    BINDINGS = [
        Binding("slash", "focus_search", "搜索", show=True),
        Binding("ctrl+p", "command_palette", "命令面板", show=True),
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
        Binding("enter", "select_plugin", "选择", show=False),
        Binding("tab", "focus_next", "下一项", show=False),
        Binding("shift+tab", "focus_previous", "上一项", show=False),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plugins_by_category = {}
        self._all_plugins = {}  # 存储所有插件（用于搜索）
        self._visible_plugin_items: list[PluginItem] = []  # 可见插件项列表
        self._cursor_index = -1  # 当前光标索引
        self._selected_plugin = None
    
    def compose(self) -> ComposeResult:
        """构建主界面
        
        使用懒加载优化启动速度：
        - 搜索框立即显示
        - 插件列表延迟加载
        """
        with Horizontal(id="main-container"):
            # 侧边栏
            with Vertical(id="sidebar"):
                # 搜索框 - 立即显示
                with Container(id="search-box"):
                    yield Input(placeholder="🔍 搜索工具...", id="search-input")
                
                # 插件分类列表 - 懒加载以加快首次渲染
                with lazy.Reveal(VerticalScroll(id="plugin-list")):
                    yield from self._build_plugin_list()
            
            # 内容区
            with Container(id="content-area"):
                yield WelcomePanel(id="welcome-panel")
    
    def _build_plugin_list(self) -> list:
        """构建插件分类列表"""
        # 获取已注册的插件
        self._all_plugins = self._get_plugins()
        
        # 按分类组织
        categories = self._organize_by_category(self._all_plugins)
        
        # 生成分类组件
        widgets = []
        for cat_name, cat_info in categories.items():
            widgets.append(
                CategoryGroup(
                    category_name=cat_name,
                    category_display=cat_info["display"],
                    plugins=cat_info["plugins"],
                    classes="category-group",
                )
            )
        
        return widgets
    
    def on_mount(self) -> None:
        """挂载后更新可见插件列表"""
        self._update_visible_plugins()
    
    def _get_plugins(self) -> dict:
        """获取已注册的插件
        
        从插件系统获取所有已注册的插件信息
        """
        try:
            from ..adapters.plugin_adapter import PluginUIAdapter
            
            adapter = PluginUIAdapter()
            plugins = adapter.get_all_plugins()
            
            # 转换为原有格式以保持兼容
            result = {}
            for plugin_id, info in plugins.items():
                result[plugin_id] = {
                    "display_name": info.display_name,
                    "icon": info.icon,
                    "category": info.category,
                    "description": info.description,
                    "params": info.parameters,
                    "version": info.version,
                    "_plugin_info": info,  # 保存原始PluginInfo
                }
            
            if result:
                return result
            else:
                # 如果没有插件，返回演示数据
                return self._get_demo_plugins()
        except ImportError:
            # 返回示例数据用于开发
            return self._get_demo_plugins()
    
    def _get_demo_plugins(self) -> dict:
        """获取演示用的插件数据"""
        return {
            "ping_test": {
                "display_name": "Ping测试",
                "icon": "📡",
                "category": "connectivity",
                "description": "测试目标主机的网络连通性",
                "params": [
                    {"name": "target", "type": "str", "required": True},
                    {"name": "count", "type": "int", "required": False},
                ]
            },
            "port_scan": {
                "display_name": "端口扫描",
                "icon": "🔍",
                "category": "connectivity",
                "description": "扫描目标主机的开放端口",
                "params": [
                    {"name": "target", "type": "str", "required": True},
                    {"name": "ports", "type": "str", "required": False},
                ]
            },
            "dns_lookup": {
                "display_name": "DNS查询",
                "icon": "🌐",
                "category": "dns",
                "description": "查询域名的DNS记录",
                "params": [
                    {"name": "domain", "type": "str", "required": True},
                    {"name": "record_type", "type": "str", "required": False},
                ]
            },
            "ssh_connect": {
                "display_name": "SSH连接测试",
                "icon": "🔐",
                "category": "remote",
                "description": "测试SSH连接并执行命令",
                "params": [
                    {"name": "host", "type": "str", "required": True},
                    {"name": "username", "type": "str", "required": True},
                ]
            },
            "bandwidth_test": {
                "display_name": "带宽测试",
                "icon": "⚡",
                "category": "performance",
                "description": "测试网络带宽速度",
                "params": []
            },
        }
    
    def _organize_by_category(self, plugins: dict) -> dict:
        """按分类组织插件"""
        # 分类显示名称映射
        category_names = {
            "diagnostics": "🔍 诊断工具",
            "device_mgmt": "🖥️ 设备管理",
            "scanning": "📡 网络扫描",
            "performance": "⚡ 性能测试",
            "utils": "🛠️ 实用工具",
            "connectivity": "🔗 连通性测试",
            "dns": "🌐 DNS工具",
            "remote": "💻 远程管理",
            "security": "🔒 安全工具",
            "config": "⚙️ 配置管理",
            "other": "📦 其他工具",
        }
        
        categories = {}
        for name, info in plugins.items():
            cat = info.get("category", "other")
            if cat not in categories:
                categories[cat] = {
                    "display": category_names.get(cat, f"📁 {cat}"),
                    "plugins": {}
                }
            categories[cat]["plugins"][name] = info
        
        return categories
    
    # ========== 事件处理 ==========
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理搜索输入"""
        if event.input.id == "search-input":
            self._filter_plugins(event.value)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """处理列表选择"""
        if isinstance(event.item, PluginItem):
            self._show_plugin_detail(event.item.plugin_name, event.item.plugin_info)
    
    def on_plugin_item_selected(self, event: PluginItem.Selected) -> None:
        """处理插件选中消息（单击）"""
        self._show_plugin_detail(event.plugin_name, event.plugin_info)
    
    def on_plugin_item_activated(self, event: PluginItem.Activated) -> None:
        """处理插件激活消息（双击）"""
        self._open_plugin_screen(event.plugin_name, event.plugin_info)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-execute":
            self._execute_current_plugin()
        elif event.button.id == "btn-configure":
            self._configure_current_plugin()
        elif event.button.id == "btn-all-tools":
            self.notify("显示所有工具列表", title="提示")
        elif event.button.id == "btn-help":
            self.app.action_show_help()
    
    # ========== Action方法 ==========
    
    def action_focus_search(self) -> None:
        """聚焦到搜索框"""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()
    
    def action_cursor_up(self) -> None:
        """向上移动光标"""
        if not self._visible_plugin_items:
            return
        
        if self._cursor_index > 0:
            self._cursor_index -= 1
        else:
            self._cursor_index = len(self._visible_plugin_items) - 1
        
        self._highlight_current_item()
    
    def action_cursor_down(self) -> None:
        """向下移动光标"""
        if not self._visible_plugin_items:
            return
        
        if self._cursor_index < len(self._visible_plugin_items) - 1:
            self._cursor_index += 1
        else:
            self._cursor_index = 0
        
        self._highlight_current_item()
    
    def action_select_plugin(self) -> None:
        """选择当前插件（回车执行）"""
        if self._cursor_index >= 0 and self._cursor_index < len(self._visible_plugin_items):
            item = self._visible_plugin_items[self._cursor_index]
            self._open_plugin_screen(item.plugin_name, item.plugin_info)
    
    def action_command_palette(self) -> None:
        """打开命令面板"""
        self.app.action_command_palette()
    
    # ========== 私有方法 ==========
    
    def _update_visible_plugins(self) -> None:
        """更新可见插件项列表"""
        self._visible_plugin_items = list(self.query(PluginItem))
        if self._visible_plugin_items and self._cursor_index < 0:
            self._cursor_index = 0
    
    def _highlight_current_item(self) -> None:
        """高亮当前选中项"""
        # 移除所有高亮
        for item in self._visible_plugin_items:
            item.remove_class("-highlighted")
        
        # 添加当前项高亮
        if 0 <= self._cursor_index < len(self._visible_plugin_items):
            current = self._visible_plugin_items[self._cursor_index]
            current.add_class("-highlighted")
            current.scroll_visible()
            
            # 同时更新详情面板
            self._show_plugin_detail(current.plugin_name, current.plugin_info)
    
    def _filter_plugins(self, query: str) -> None:
        """过滤插件列表
        
        根据搜索词过滤显示的插件
        优化：批量更新减少重绘次数
        """
        query_lower = query.lower().strip()
        
        # 禁用布局更新以批量处理变更
        with self.app.batch_update():
            # 获取所有分类组
            for category in self.query(CategoryGroup):
                visible_count = 0
                
                # 遍历分类下的所有插件项
                for plugin_item in category.query(PluginItem):
                    name = plugin_item.plugin_name.lower()
                    display_name = plugin_item.plugin_info.get("display_name", "").lower()
                    description = plugin_item.plugin_info.get("description", "").lower()
                    
                    # 匹配名称、显示名或描述
                    if not query_lower or query_lower in name or query_lower in display_name or query_lower in description:
                        plugin_item.display = True
                        visible_count += 1
                    else:
                        plugin_item.display = False
                
                # 如果分类下没有可见插件，隐藏整个分类
                category.display = visible_count > 0
        
        # 更新可见插件列表
        self._visible_plugin_items = [item for item in self.query(PluginItem) if item.display]
        self._cursor_index = 0 if self._visible_plugin_items else -1
        
        if self._visible_plugin_items:
            self._highlight_current_item()
    
    def _show_plugin_detail(self, plugin_name: str, plugin_info: dict) -> None:
        """显示插件详情"""
        self._selected_plugin = (plugin_name, plugin_info)
        
        # 移除欢迎面板，显示详情面板
        content_area = self.query_one("#content-area")
        
        # 清空内容区
        for child in content_area.children:
            child.remove()
        
        # 添加详情面板
        content_area.mount(PluginDetailPanel(plugin_name, plugin_info))
        
        # 更新副标题
        display_name = plugin_info.get("display_name", plugin_name)
        self.sub_title = f"当前: {display_name}"
    
    def _execute_current_plugin(self) -> None:
        """执行当前选中的插件"""
        if self._selected_plugin:
            name, info = self._selected_plugin
            self._open_plugin_screen(name, info)
    
    def _configure_current_plugin(self) -> None:
        """配置当前选中的插件（也是跳转到执行界面）"""
        if self._selected_plugin:
            name, info = self._selected_plugin
            self._open_plugin_screen(name, info)
    
    def _open_plugin_screen(self, plugin_name: str, plugin_info: dict) -> None:
        """打开插件执行界面
        
        Args:
            plugin_name: 插件ID
            plugin_info: 插件信息字典
        """
        from .plugin_screen import PluginScreen
        self.app.push_screen(PluginScreen(plugin_name, plugin_info))
