"""
PluginList组件 - 可交互的插件列表

特性:
- 支持鼠标点击选择
- 支持键盘上下导航
- 支持分类折叠/展开
- 支持搜索过滤
- 悬停高亮效果
"""

from __future__ import annotations

from typing import Optional, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static


class PluginListItem(Static, can_focus=True):
    """单个插件列表项
    
    支持:
    - 鼠标点击选择
    - 键盘Enter选择
    - 悬停高亮
    - 选中状态显示
    """
    
    DEFAULT_CSS = """
    PluginListItem {
        height: 3;
        padding: 0 2;
        content-align: left middle;
        border: none;
    }
    
    PluginListItem:hover {
        background: $primary-darken-3;
    }
    
    PluginListItem:focus {
        background: $primary-darken-2;
        border-left: thick $accent;
    }
    
    PluginListItem.-selected {
        background: $accent-darken-1;
        color: $text;
    }
    
    PluginListItem.-selected:focus {
        background: $accent;
    }
    
    PluginListItem > .plugin-icon {
        width: 3;
    }
    
    PluginListItem > .plugin-name {
        width: 1fr;
        padding-left: 1;
    }
    """
    
    BINDINGS = [
        Binding("enter", "select", "选择", show=False),
        Binding("space", "select", "选择", show=False),
    ]
    
    class Selected(Message):
        """插件被选中时发送的消息"""
        def __init__(self, plugin_id: str, plugin_info: dict) -> None:
            self.plugin_id = plugin_id
            self.plugin_info = plugin_info
            super().__init__()
    
    # 响应式属性：是否选中
    selected: reactive[bool] = reactive(False)
    
    def __init__(
        self,
        plugin_id: str,
        plugin_info: dict,
        *args,
        **kwargs,
    ) -> None:
        """初始化插件列表项
        
        Args:
            plugin_id: 插件唯一标识
            plugin_info: 插件信息字典，包含display_name, icon, description等
        """
        super().__init__(*args, **kwargs)
        self.plugin_id = plugin_id
        self.plugin_info = plugin_info
    
    def compose(self) -> ComposeResult:
        """渲染组件"""
        icon = self.plugin_info.get("icon", "🔧")
        name = self.plugin_info.get("display_name", self.plugin_id)
        yield Label(icon, classes="plugin-icon")
        yield Label(name, classes="plugin-name")
    
    def watch_selected(self, selected: bool) -> None:
        """监听选中状态变化"""
        if selected:
            self.add_class("-selected")
        else:
            self.remove_class("-selected")
    
    def on_click(self) -> None:
        """处理鼠标点击"""
        self.action_select()
    
    def action_select(self) -> None:
        """选择此插件"""
        self.post_message(self.Selected(self.plugin_id, self.plugin_info))


class PluginCategory(Static):
    """可折叠的插件分类
    
    支持:
    - 点击标题折叠/展开
    - 显示分类内插件数量
    - 键盘导航进入分类
    """
    
    DEFAULT_CSS = """
    PluginCategory {
        height: auto;
        margin: 0 0 1 0;
    }
    
    PluginCategory > .category-header {
        height: 2;
        padding: 0 1;
        text-style: bold;
        background: $surface-darken-2;
    }
    
    PluginCategory > .category-header:hover {
        background: $surface-darken-1;
        text-style: bold underline;
    }
    
    PluginCategory > .category-content {
        padding-left: 1;
        height: auto;
    }
    
    PluginCategory.-collapsed > .category-content {
        display: none;
    }
    
    PluginCategory > .category-header > .collapse-icon {
        width: 2;
    }
    
    PluginCategory > .category-header > .category-name {
        width: 1fr;
    }
    
    PluginCategory > .category-header > .category-count {
        width: auto;
        color: $text-muted;
    }
    """
    
    # 响应式属性：是否折叠
    collapsed: reactive[bool] = reactive(False)
    
    def __init__(
        self,
        category_id: str,
        category_name: str,
        plugins: dict,
        *args,
        **kwargs,
    ) -> None:
        """初始化分类组
        
        Args:
            category_id: 分类唯一标识
            category_name: 分类显示名称
            plugins: 该分类下的插件字典
        """
        super().__init__(*args, **kwargs)
        self.category_id = category_id
        self.category_name = category_name
        self.plugins = plugins
    
    def compose(self) -> ComposeResult:
        """渲染组件"""
        # 分类头部
        with Static(classes="category-header"):
            yield Label("▼", classes="collapse-icon", id=f"icon-{self.category_id}")
            yield Label(self.category_name, classes="category-name")
            yield Label(f"({len(self.plugins)})", classes="category-count")
        
        # 分类内容（插件列表）
        with Vertical(classes="category-content"):
            for plugin_id, plugin_info in self.plugins.items():
                yield PluginListItem(plugin_id, plugin_info)
    
    def on_click(self, event) -> None:
        """处理点击事件"""
        # 检查是否点击了header区域
        widget = event.widget
        while widget and widget != self:
            if "category-header" in widget.classes:
                self.toggle_collapse()
                event.stop()
                return
            widget = widget.parent
    
    def toggle_collapse(self) -> None:
        """切换折叠状态"""
        self.collapsed = not self.collapsed
    
    def watch_collapsed(self, collapsed: bool) -> None:
        """监听折叠状态变化"""
        if collapsed:
            self.add_class("-collapsed")
            icon = self.query_one(f"#icon-{self.category_id}", Label)
            icon.update("▶")
        else:
            self.remove_class("-collapsed")
            icon = self.query_one(f"#icon-{self.category_id}", Label)
            icon.update("▼")


class PluginList(Widget, can_focus=True):
    """完整的插件列表组件
    
    支持:
    - 分类展示
    - 鼠标/键盘导航
    - 搜索过滤
    - 选中状态管理
    """
    
    DEFAULT_CSS = """
    PluginList {
        width: 100%;
        height: 100%;
    }
    
    PluginList > VerticalScroll {
        height: 100%;
    }
    """
    
    BINDINGS = [
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
        Binding("enter", "select_current", "选择", show=False),
        Binding("space", "toggle_category", "折叠/展开", show=False),
    ]
    
    class PluginSelected(Message):
        """插件选中事件"""
        def __init__(self, plugin_id: str, plugin_info: dict) -> None:
            self.plugin_id = plugin_id
            self.plugin_info = plugin_info
            super().__init__()
    
    # 当前选中的插件ID
    current_plugin: reactive[Optional[str]] = reactive(None)
    
    # 搜索过滤关键词
    filter_query: reactive[str] = reactive("")
    
    def __init__(
        self,
        plugins: dict = None,
        categories: dict = None,
        *args,
        **kwargs,
    ) -> None:
        """初始化插件列表
        
        Args:
            plugins: 所有插件的字典 {plugin_id: plugin_info}
            categories: 分类配置 {category_id: {"name": str, "icon": str}}
        """
        super().__init__(*args, **kwargs)
        self._plugins = plugins or {}
        self._categories = categories or self._default_categories()
        self._plugin_items: list[PluginListItem] = []
        self._cursor_index = 0
    
    def _default_categories(self) -> dict:
        """默认分类配置"""
        return {
            "connectivity": {"name": "🔗 连通性测试", "order": 1},
            "dns": {"name": "🌐 DNS工具", "order": 2},
            "remote": {"name": "🖥️ 远程管理", "order": 3},
            "performance": {"name": "📊 性能测试", "order": 4},
            "security": {"name": "🔒 安全工具", "order": 5},
            "config": {"name": "⚙️ 配置管理", "order": 6},
            "other": {"name": "📦 其他工具", "order": 99},
        }
    
    def compose(self) -> ComposeResult:
        """渲染组件"""
        with VerticalScroll():
            # 按分类组织插件
            categorized = self._organize_plugins()
            
            # 按order排序分类
            sorted_categories = sorted(
                categorized.items(),
                key=lambda x: self._categories.get(x[0], {}).get("order", 99)
            )
            
            for cat_id, plugins in sorted_categories:
                if plugins:  # 只显示有插件的分类
                    cat_info = self._categories.get(cat_id, {})
                    cat_name = cat_info.get("name", f"📁 {cat_id}")
                    yield PluginCategory(cat_id, cat_name, plugins)
    
    def _organize_plugins(self) -> dict:
        """将插件按分类组织"""
        categorized = {}
        
        for plugin_id, plugin_info in self._plugins.items():
            # 应用过滤
            if self.filter_query:
                name = plugin_info.get("display_name", plugin_id).lower()
                desc = plugin_info.get("description", "").lower()
                query = self.filter_query.lower()
                if query not in name and query not in desc:
                    continue
            
            cat = plugin_info.get("category", "other")
            if cat not in categorized:
                categorized[cat] = {}
            categorized[cat][plugin_id] = plugin_info
        
        return categorized
    
    def on_mount(self) -> None:
        """挂载后初始化"""
        self._update_plugin_items()
    
    def _update_plugin_items(self) -> None:
        """更新插件项列表"""
        self._plugin_items = list(self.query(PluginListItem))
    
    def on_plugin_list_item_selected(self, event: PluginListItem.Selected) -> None:
        """处理插件项选中事件"""
        # 更新选中状态
        self._update_selection(event.plugin_id)
        
        # 向上传递事件
        self.post_message(self.PluginSelected(event.plugin_id, event.plugin_info))
    
    def _update_selection(self, plugin_id: str) -> None:
        """更新选中状态"""
        self.current_plugin = plugin_id
        
        # 更新所有项的选中状态
        for item in self._plugin_items:
            item.selected = (item.plugin_id == plugin_id)
    
    def watch_filter_query(self, query: str) -> None:
        """监听过滤关键词变化"""
        # 重新渲染列表
        self.refresh(recompose=True)
    
    # ========== Action方法 ==========
    
    def action_cursor_up(self) -> None:
        """向上移动光标"""
        if not self._plugin_items:
            return
        
        self._cursor_index = max(0, self._cursor_index - 1)
        self._focus_current()
    
    def action_cursor_down(self) -> None:
        """向下移动光标"""
        if not self._plugin_items:
            return
        
        self._cursor_index = min(len(self._plugin_items) - 1, self._cursor_index + 1)
        self._focus_current()
    
    def action_select_current(self) -> None:
        """选择当前光标所在的插件"""
        if self._plugin_items and 0 <= self._cursor_index < len(self._plugin_items):
            item = self._plugin_items[self._cursor_index]
            item.action_select()
    
    def action_toggle_category(self) -> None:
        """折叠/展开当前分类"""
        # 找到当前项所属的分类
        if self._plugin_items and 0 <= self._cursor_index < len(self._plugin_items):
            item = self._plugin_items[self._cursor_index]
            category = item.ancestors_with_self
            for ancestor in item.ancestors:
                if isinstance(ancestor, PluginCategory):
                    ancestor.toggle_collapse()
                    break
    
    def _focus_current(self) -> None:
        """聚焦当前光标所在项"""
        if self._plugin_items and 0 <= self._cursor_index < len(self._plugin_items):
            self._plugin_items[self._cursor_index].focus()
    
    # ========== 公共方法 ==========
    
    def set_filter(self, query: str) -> None:
        """设置过滤关键词"""
        self.filter_query = query
    
    def select_plugin(self, plugin_id: str) -> None:
        """选择指定插件"""
        self._update_selection(plugin_id)
        
        # 查找并聚焦该插件项
        for i, item in enumerate(self._plugin_items):
            if item.plugin_id == plugin_id:
                self._cursor_index = i
                item.focus()
                break
    
    def refresh_plugins(self, plugins: dict) -> None:
        """刷新插件数据"""
        self._plugins = plugins
        self.refresh(recompose=True)
