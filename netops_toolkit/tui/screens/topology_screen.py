"""
NetOps Toolkit - 拓扑可视化界面

功能:
- ASCII/Unicode 网络拓扑展示
- 多种渲染样式（层级、树形、盒子、矩阵）
- 从设备清单自动构建拓扑
- 可滚动查看大型拓扑
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    RadioButton,
    RadioSet,
    RichLog,
    Rule,
    Select,
    Static,
    Switch,
    Tab,
    TabbedContent,
    TabPane,
)

# 条件导入拓扑服务
TOPOLOGY_AVAILABLE = False
try:
    from netops_toolkit.services.topology_service import (
        TopologyService,
        TopologyBuilder,
        ASCIITopologyRenderer,
        NodeType,
        TopologyNode,
        TopologyLink,
        NETWORKX_AVAILABLE,
    )
    TOPOLOGY_AVAILABLE = NETWORKX_AVAILABLE
except ImportError:
    pass


class RenderStyle(Enum):
    """渲染样式"""
    HIERARCHICAL = "hierarchical"
    TREE = "tree"
    BOX = "box"
    MATRIX = "matrix"


# ============================================================
# 拓扑显示面板
# ============================================================

class TopologyDisplay(Static):
    """拓扑显示组件
    
    可滚动的 ASCII 拓扑视图
    """
    
    DEFAULT_CSS = """
    TopologyDisplay {
        width: 100%;
        height: 100%;
        background: $surface;
        color: $text;
        padding: 1;
        overflow: auto auto;
    }
    """
    
    content = reactive("", layout=True)
    
    def __init__(
        self,
        content: str = "",
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self.content = content
    
    def render(self) -> str:
        return self.content or "(无拓扑数据)"


class TopologyStatsPanel(Static):
    """拓扑统计面板"""
    
    DEFAULT_CSS = """
    TopologyStatsPanel {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 1;
        border: solid $primary;
    }
    
    TopologyStatsPanel .stats-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    
    TopologyStatsPanel .stats-row {
        width: 100%;
        height: auto;
    }
    
    TopologyStatsPanel .stat-item {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    
    TopologyStatsPanel .stat-label {
        color: $text-muted;
    }
    
    TopologyStatsPanel .stat-value {
        color: $text;
        text-style: bold;
    }
    """
    
    def __init__(
        self,
        stats: Dict[str, Any] | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._stats = stats or {}
    
    def compose(self) -> ComposeResult:
        yield Label("📊 拓扑统计", classes="stats-title")
        with Horizontal(classes="stats-row"):
            with Vertical(classes="stat-item"):
                yield Label("节点数", classes="stat-label")
                yield Label(str(self._stats.get("nodes", 0)), id="stat-nodes", classes="stat-value")
            with Vertical(classes="stat-item"):
                yield Label("链路数", classes="stat-label")
                yield Label(str(self._stats.get("edges", 0)), id="stat-edges", classes="stat-value")
            with Vertical(classes="stat-item"):
                yield Label("连通性", classes="stat-label")
                connected = "✅ 是" if self._stats.get("connected", False) else "❌ 否"
                yield Label(connected, id="stat-connected", classes="stat-value")
            with Vertical(classes="stat-item"):
                yield Label("密度", classes="stat-label")
                density = f"{self._stats.get('density', 0):.2%}"
                yield Label(density, id="stat-density", classes="stat-value")
    
    def update_stats(self, stats: Dict[str, Any]) -> None:
        """更新统计数据"""
        self._stats = stats
        
        try:
            self.query_one("#stat-nodes", Label).update(str(stats.get("nodes", 0)))
            self.query_one("#stat-edges", Label).update(str(stats.get("edges", 0)))
            
            connected = "✅ 是" if stats.get("connected", False) else "❌ 否"
            self.query_one("#stat-connected", Label).update(connected)
            
            density = f"{stats.get('density', 0):.2%}"
            self.query_one("#stat-density", Label).update(density)
        except Exception:
            pass


class StyleSelector(Static):
    """渲染样式选择器"""
    
    DEFAULT_CSS = """
    StyleSelector {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 1;
        border: solid $primary;
    }
    
    StyleSelector .selector-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    StyleSelector RadioSet {
        width: 100%;
        height: auto;
    }
    """
    
    class StyleChanged(Message):
        """样式变更消息"""
        def __init__(self, style: str) -> None:
            self.style = style
            super().__init__()
    
    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
    
    def compose(self) -> ComposeResult:
        yield Label("🎨 渲染样式", classes="selector-title")
        with RadioSet(id="style-radio"):
            yield RadioButton("层级视图", value=True, id="style-hierarchical")
            yield RadioButton("树形视图", id="style-tree")
            yield RadioButton("分组盒子", id="style-box")
            yield RadioButton("邻接矩阵", id="style-matrix")
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """处理样式选择变更"""
        button_id = event.pressed.id
        if button_id:
            style = button_id.replace("style-", "")
            self.post_message(self.StyleChanged(style))


class OptionsPanel(Static):
    """选项面板"""
    
    DEFAULT_CSS = """
    OptionsPanel {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 1;
        border: solid $primary;
    }
    
    OptionsPanel .options-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    OptionsPanel .option-row {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    
    OptionsPanel .option-label {
        width: auto;
        margin-right: 1;
    }
    """
    
    class OptionChanged(Message):
        """选项变更消息"""
        def __init__(self, option: str, value: bool) -> None:
            self.option = option
            self.value = value
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Label("⚙️ 显示选项", classes="options-title")
        with Horizontal(classes="option-row"):
            yield Label("Unicode 图标", classes="option-label")
            yield Switch(value=True, id="opt-unicode")
        with Horizontal(classes="option-row"):
            yield Label("自动连接", classes="option-label")
            yield Switch(value=True, id="opt-autoconnect")
    
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """处理开关变更"""
        switch_id = event.switch.id
        if switch_id:
            option = switch_id.replace("opt-", "")
            self.post_message(self.OptionChanged(option, event.value))


class LegendPanel(Static):
    """图例面板"""
    
    DEFAULT_CSS = """
    LegendPanel {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 1;
        border: solid $primary;
    }
    
    LegendPanel .legend-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    LegendPanel .legend-item {
        width: 100%;
        height: auto;
    }
    """
    
    def __init__(
        self,
        use_unicode: bool = True,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._use_unicode = use_unicode
    
    def compose(self) -> ComposeResult:
        yield Label("📖 图例", classes="legend-title")
        
        if self._use_unicode:
            legends = [
                ("🔀", "路由器"),
                ("🔲", "交换机"),
                ("🛡️", "防火墙"),
                ("🖥️", "服务器"),
                ("💻", "工作站"),
                ("☁️", "云"),
            ]
        else:
            legends = [
                ("[R]", "路由器"),
                ("[S]", "交换机"),
                ("[F]", "防火墙"),
                ("[H]", "服务器"),
                ("[W]", "工作站"),
                ("[C]", "云"),
            ]
        
        for icon, name in legends:
            yield Label(f"  {icon}  {name}", classes="legend-item")
    
    def update_unicode(self, use_unicode: bool) -> None:
        """更新图例显示模式"""
        self._use_unicode = use_unicode
        self.refresh(layout=True)


# ============================================================
# 主界面
# ============================================================

class TopologyScreen(Screen):
    """拓扑可视化界面"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "返回"),
        Binding("r", "refresh_topology", "刷新"),
        Binding("1", "set_style('hierarchical')", "层级"),
        Binding("2", "set_style('tree')", "树形"),
        Binding("3", "set_style('box')", "盒子"),
        Binding("4", "set_style('matrix')", "矩阵"),
        Binding("u", "toggle_unicode", "Unicode"),
    ]
    
    CSS = """
    TopologyScreen {
        layout: horizontal;
    }
    
    TopologyScreen #sidebar {
        width: 30;
        height: 100%;
        background: $surface;
        border-right: solid $primary;
        padding: 1;
    }
    
    TopologyScreen #main-area {
        width: 1fr;
        height: 100%;
    }
    
    TopologyScreen #topology-container {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    
    TopologyScreen #action-bar {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
        dock: bottom;
    }
    
    TopologyScreen #action-bar Button {
        margin-right: 1;
    }
    
    TopologyScreen .sidebar-section {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    
    TopologyScreen .not-available {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-style: bold;
        color: $error;
    }
    """
    
    # 响应式属性
    current_style = reactive("hierarchical")
    use_unicode = reactive(True)
    auto_connect = reactive(True)
    
    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._topology_service: Optional[TopologyService] = None
        self._topology_text: str = ""
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        if not TOPOLOGY_AVAILABLE:
            yield Static(
                "❌ 拓扑功能不可用\n\n"
                "请安装 networkx:\n"
                "pip install networkx>=3.0",
                classes="not-available",
            )
        else:
            # 侧边栏
            with Vertical(id="sidebar"):
                with Container(classes="sidebar-section"):
                    yield TopologyStatsPanel(id="stats-panel")
                with Container(classes="sidebar-section"):
                    yield StyleSelector(id="style-selector")
                with Container(classes="sidebar-section"):
                    yield OptionsPanel(id="options-panel")
                with Container(classes="sidebar-section"):
                    yield LegendPanel(id="legend-panel")
            
            # 主区域
            with Vertical(id="main-area"):
                with VerticalScroll(id="topology-container"):
                    yield TopologyDisplay(id="topology-display")
                
                # 操作栏
                with Horizontal(id="action-bar"):
                    yield Button("🔄 刷新", id="btn-refresh", variant="primary")
                    yield Button("📋 复制", id="btn-copy", variant="default")
                    yield Button("💾 导出", id="btn-export", variant="default")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """界面挂载时初始化"""
        if TOPOLOGY_AVAILABLE:
            self._topology_service = TopologyService()
            self._refresh_topology()
    
    def _refresh_topology(self) -> None:
        """刷新拓扑显示"""
        if not self._topology_service:
            return
        
        try:
            # 构建拓扑
            self._topology_service.build_from_inventory(
                auto_connect=self.auto_connect,
            )
            
            # 渲染拓扑
            self._topology_text = self._topology_service.render(
                style=self.current_style,
                use_unicode=self.use_unicode,
            )
            
            # 更新显示
            display = self.query_one("#topology-display", TopologyDisplay)
            display.content = self._topology_text
            
            # 更新统计
            stats = self._topology_service.get_summary()
            stats_panel = self.query_one("#stats-panel", TopologyStatsPanel)
            stats_panel.update_stats(stats)
            
        except Exception as e:
            display = self.query_one("#topology-display", TopologyDisplay)
            display.content = f"错误: {e}"
    
    def watch_current_style(self, style: str) -> None:
        """监听样式变化"""
        if self._topology_service:
            self._refresh_topology()
    
    def watch_use_unicode(self, use_unicode: bool) -> None:
        """监听 Unicode 选项变化"""
        if self._topology_service:
            self._refresh_topology()
            # 更新图例
            try:
                legend = self.query_one("#legend-panel", LegendPanel)
                legend.update_unicode(use_unicode)
            except Exception:
                pass
    
    def watch_auto_connect(self, auto_connect: bool) -> None:
        """监听自动连接选项变化"""
        if self._topology_service:
            self._refresh_topology()
    
    # 消息处理
    def on_style_selector_style_changed(self, event: StyleSelector.StyleChanged) -> None:
        """处理样式变更"""
        self.current_style = event.style
    
    def on_options_panel_option_changed(self, event: OptionsPanel.OptionChanged) -> None:
        """处理选项变更"""
        if event.option == "unicode":
            self.use_unicode = event.value
        elif event.option == "autoconnect":
            self.auto_connect = event.value
    
    # 按钮事件
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "btn-refresh":
            self._refresh_topology()
        elif button_id == "btn-copy":
            self._copy_to_clipboard()
        elif button_id == "btn-export":
            self._export_topology()
    
    def _copy_to_clipboard(self) -> None:
        """复制拓扑到剪贴板"""
        if self._topology_text:
            try:
                import pyperclip
                pyperclip.copy(self._topology_text)
                self.notify("已复制到剪贴板", severity="information")
            except ImportError:
                self.notify("需要安装 pyperclip: pip install pyperclip", severity="warning")
            except Exception as e:
                self.notify(f"复制失败: {e}", severity="error")
    
    def _export_topology(self) -> None:
        """导出拓扑到文件"""
        if self._topology_text:
            try:
                output_dir = Path("topology_output")
                output_dir.mkdir(exist_ok=True)
                
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"topology_{self.current_style}_{timestamp}.txt"
                filepath = output_dir / filename
                
                filepath.write_text(self._topology_text, encoding="utf-8")
                self.notify(f"已导出到: {filepath}", severity="information")
            except Exception as e:
                self.notify(f"导出失败: {e}", severity="error")
    
    # 快捷键动作
    def action_refresh_topology(self) -> None:
        """刷新拓扑"""
        self._refresh_topology()
    
    def action_set_style(self, style: str) -> None:
        """设置渲染样式"""
        self.current_style = style
        
        # 更新 RadioButton 选中状态
        try:
            radio_id = f"style-{style}"
            radio = self.query_one(f"#{radio_id}", RadioButton)
            radio.value = True
        except Exception:
            pass
    
    def action_toggle_unicode(self) -> None:
        """切换 Unicode 模式"""
        self.use_unicode = not self.use_unicode
        
        # 更新开关状态
        try:
            switch = self.query_one("#opt-unicode", Switch)
            switch.value = self.use_unicode
        except Exception:
            pass
