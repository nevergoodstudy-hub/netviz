"""
NetOps Toolkit - 审计日志界面

功能:
- 审计日志列表展示（DataTable）
- 多维度筛选（时间/类型/设备/结果）
- 详情查看和变更对比
- JSON/CSV 导出
- 统计摘要
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    RichLog,
    Rule,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

# 导入审计服务
from netops_toolkit.services.audit_service import (
    AuditService,
    AuditEventType,
    AuditSeverity,
    AuditResult,
    AuditRecord,
    AuditQuery,
    AuditSummary,
    get_audit_service,
)


# ============================================================
# 统计摘要面板
# ============================================================

class AuditStatsPanel(Static):
    """审计统计面板"""
    
    DEFAULT_CSS = """
    AuditStatsPanel {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 1;
        border: solid $primary;
    }
    
    AuditStatsPanel .stats-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    AuditStatsPanel .stats-row {
        width: 100%;
        height: auto;
    }
    
    AuditStatsPanel .stat-item {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    
    AuditStatsPanel .stat-label {
        color: $text-muted;
    }
    
    AuditStatsPanel .stat-value {
        text-style: bold;
    }
    
    AuditStatsPanel .stat-success {
        color: $success;
    }
    
    AuditStatsPanel .stat-failure {
        color: $error;
    }
    """
    
    def __init__(
        self,
        summary: Optional[AuditSummary] = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._summary = summary or AuditSummary()
    
    def compose(self) -> ComposeResult:
        yield Label("📊 审计统计", classes="stats-title")
        with Horizontal(classes="stats-row"):
            with Vertical(classes="stat-item"):
                yield Label("总记录", classes="stat-label")
                yield Label(str(self._summary.total_records), id="stat-total", classes="stat-value")
            with Vertical(classes="stat-item"):
                yield Label("✅ 成功", classes="stat-label")
                yield Label(str(self._summary.success_count), id="stat-success", classes="stat-value stat-success")
            with Vertical(classes="stat-item"):
                yield Label("❌ 失败", classes="stat-label")
                yield Label(str(self._summary.failure_count), id="stat-failure", classes="stat-value stat-failure")
            with Vertical(classes="stat-item"):
                yield Label("⚠️ 部分", classes="stat-label")
                yield Label(str(self._summary.partial_count), id="stat-partial", classes="stat-value")
    
    def update_stats(self, summary: AuditSummary) -> None:
        """更新统计"""
        self._summary = summary
        try:
            self.query_one("#stat-total", Label).update(str(summary.total_records))
            self.query_one("#stat-success", Label).update(str(summary.success_count))
            self.query_one("#stat-failure", Label).update(str(summary.failure_count))
            self.query_one("#stat-partial", Label).update(str(summary.partial_count))
        except Exception:
            pass


# ============================================================
# 筛选面板
# ============================================================

class FilterPanel(Static):
    """筛选面板"""
    
    DEFAULT_CSS = """
    FilterPanel {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 1;
        border: solid $primary;
    }
    
    FilterPanel .filter-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    FilterPanel .filter-row {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    
    FilterPanel .filter-label {
        width: auto;
        margin-right: 1;
    }
    
    FilterPanel Select {
        width: 100%;
    }
    
    FilterPanel Input {
        width: 100%;
    }
    
    FilterPanel .filter-actions {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    
    FilterPanel .filter-actions Button {
        margin-right: 1;
    }
    """
    
    class FilterChanged(Message):
        """筛选条件变更"""
        def __init__(self, query: AuditQuery) -> None:
            self.query = query
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Label("🔍 筛选条件", classes="filter-title")
        
        # 时间范围
        with Vertical(classes="filter-row"):
            yield Label("时间范围", classes="filter-label")
            yield Select(
                [
                    ("最近1小时", "1h"),
                    ("最近24小时", "24h"),
                    ("最近7天", "7d"),
                    ("最近30天", "30d"),
                    ("全部", "all"),
                ],
                value="24h",
                id="filter-time",
            )
        
        # 事件类型
        with Vertical(classes="filter-row"):
            yield Label("事件类型", classes="filter-label")
            yield Select(
                [
                    ("全部类型", "all"),
                    ("配置备份", "config_backup"),
                    ("配置推送", "config_push"),
                    ("命令执行", "command_execute"),
                    ("设备连接", "device_connect"),
                    ("报表生成", "report_generate"),
                    ("合规检查", "compliance_check"),
                ],
                value="all",
                id="filter-type",
            )
        
        # 结果
        with Vertical(classes="filter-row"):
            yield Label("操作结果", classes="filter-label")
            yield Select(
                [
                    ("全部结果", "all"),
                    ("✅ 成功", "success"),
                    ("❌ 失败", "failure"),
                    ("⚠️ 部分成功", "partial"),
                ],
                value="all",
                id="filter-result",
            )
        
        # 关键字
        with Vertical(classes="filter-row"):
            yield Label("关键字", classes="filter-label")
            yield Input(placeholder="搜索描述...", id="filter-keyword")
        
        # 操作按钮
        with Horizontal(classes="filter-actions"):
            yield Button("🔍 筛选", id="btn-filter", variant="primary")
            yield Button("🔄 重置", id="btn-reset", variant="default")
    
    def build_query(self) -> AuditQuery:
        """构建查询"""
        query = AuditQuery()
        
        # 时间范围
        time_value = self.query_one("#filter-time", Select).value
        now = datetime.now()
        if time_value == "1h":
            query.start_time = now - timedelta(hours=1)
        elif time_value == "24h":
            query.start_time = now - timedelta(hours=24)
        elif time_value == "7d":
            query.start_time = now - timedelta(days=7)
        elif time_value == "30d":
            query.start_time = now - timedelta(days=30)
        # "all" 不设置时间限制
        
        # 事件类型
        type_value = self.query_one("#filter-type", Select).value
        if type_value != "all":
            try:
                query.event_types = [AuditEventType(type_value)]
            except ValueError:
                pass
        
        # 结果
        result_value = self.query_one("#filter-result", Select).value
        if result_value != "all":
            try:
                query.results = [AuditResult(result_value)]
            except ValueError:
                pass
        
        # 关键字
        keyword = self.query_one("#filter-keyword", Input).value
        if keyword:
            query.keyword = keyword
        
        query.limit = 500
        return query
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-filter":
            self.post_message(self.FilterChanged(self.build_query()))
        elif event.button.id == "btn-reset":
            self._reset_filters()
            self.post_message(self.FilterChanged(self.build_query()))
    
    def _reset_filters(self) -> None:
        """重置筛选器"""
        self.query_one("#filter-time", Select).value = "24h"
        self.query_one("#filter-type", Select).value = "all"
        self.query_one("#filter-result", Select).value = "all"
        self.query_one("#filter-keyword", Input).value = ""


# ============================================================
# 详情面板
# ============================================================

class DetailPanel(Static):
    """审计详情面板"""
    
    DEFAULT_CSS = """
    DetailPanel {
        width: 100%;
        height: 100%;
        background: $surface;
    }
    
    DetailPanel .detail-header {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
    }
    
    DetailPanel .detail-title {
        text-style: bold;
    }
    
    DetailPanel .detail-content {
        width: 100%;
        height: 1fr;
        padding: 1;
    }
    
    DetailPanel .detail-section {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    
    DetailPanel .section-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    DetailPanel .field-row {
        width: 100%;
        height: auto;
    }
    
    DetailPanel .field-label {
        width: 15;
        color: $text-muted;
    }
    
    DetailPanel .field-value {
        width: 1fr;
    }
    
    DetailPanel .value-box {
        width: 100%;
        height: auto;
        max-height: 10;
        background: $boost;
        padding: 1;
        border: solid $primary-background;
        overflow: auto;
    }
    
    DetailPanel .diff-old {
        color: $error;
    }
    
    DetailPanel .diff-new {
        color: $success;
    }
    """
    
    def __init__(
        self,
        record: Optional[AuditRecord] = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._record = record
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="detail-header"):
            yield Label("📋 详情", classes="detail-title")
        
        with VerticalScroll(classes="detail-content"):
            # 基本信息
            with Vertical(classes="detail-section"):
                yield Label("基本信息", classes="section-title")
                with Horizontal(classes="field-row"):
                    yield Label("ID:", classes="field-label")
                    yield Label("-", id="detail-id", classes="field-value")
                with Horizontal(classes="field-row"):
                    yield Label("时间:", classes="field-label")
                    yield Label("-", id="detail-time", classes="field-value")
                with Horizontal(classes="field-row"):
                    yield Label("类型:", classes="field-label")
                    yield Label("-", id="detail-type", classes="field-value")
                with Horizontal(classes="field-row"):
                    yield Label("操作人:", classes="field-label")
                    yield Label("-", id="detail-operator", classes="field-value")
                with Horizontal(classes="field-row"):
                    yield Label("结果:", classes="field-label")
                    yield Label("-", id="detail-result", classes="field-value")
            
            # 设备信息
            with Vertical(classes="detail-section"):
                yield Label("设备信息", classes="section-title")
                with Horizontal(classes="field-row"):
                    yield Label("设备名:", classes="field-label")
                    yield Label("-", id="detail-device", classes="field-value")
                with Horizontal(classes="field-row"):
                    yield Label("IP地址:", classes="field-label")
                    yield Label("-", id="detail-ip", classes="field-value")
            
            # 描述
            with Vertical(classes="detail-section"):
                yield Label("操作描述", classes="section-title")
                yield Static("-", id="detail-desc", classes="value-box")
            
            # 变更对比
            with Vertical(classes="detail-section"):
                yield Label("变更对比", classes="section-title")
                yield Label("变更前:", classes="field-label")
                yield Static("-", id="detail-old", classes="value-box diff-old")
                yield Label("变更后:", classes="field-label")
                yield Static("-", id="detail-new", classes="value-box diff-new")
            
            # 错误信息
            with Vertical(classes="detail-section"):
                yield Label("错误信息", classes="section-title")
                yield Static("-", id="detail-error", classes="value-box")
    
    def update_record(self, record: AuditRecord) -> None:
        """更新记录"""
        self._record = record
        
        result_icons = {
            AuditResult.SUCCESS: "✅ 成功",
            AuditResult.FAILURE: "❌ 失败",
            AuditResult.PARTIAL: "⚠️ 部分成功",
            AuditResult.SKIPPED: "⏭️ 跳过",
        }
        
        try:
            self.query_one("#detail-id", Label).update(str(record.id or "-"))
            self.query_one("#detail-time", Label).update(
                record.timestamp.strftime("%Y-%m-%d %H:%M:%S") if record.timestamp else "-"
            )
            self.query_one("#detail-type", Label).update(record.event_type.value)
            self.query_one("#detail-operator", Label).update(record.operator or "-")
            self.query_one("#detail-result", Label).update(result_icons.get(record.result, "-"))
            self.query_one("#detail-device", Label).update(record.device_name or "-")
            self.query_one("#detail-ip", Label).update(record.device_ip or "-")
            self.query_one("#detail-desc", Static).update(record.description or "-")
            self.query_one("#detail-old", Static).update(record.old_value or "(无)")
            self.query_one("#detail-new", Static).update(record.new_value or "(无)")
            self.query_one("#detail-error", Static).update(record.error_message or "(无)")
        except Exception:
            pass
    
    def clear(self) -> None:
        """清空详情"""
        self._record = None
        try:
            self.query_one("#detail-id", Label).update("-")
            self.query_one("#detail-time", Label).update("-")
            self.query_one("#detail-type", Label).update("-")
            self.query_one("#detail-operator", Label).update("-")
            self.query_one("#detail-result", Label).update("-")
            self.query_one("#detail-device", Label).update("-")
            self.query_one("#detail-ip", Label).update("-")
            self.query_one("#detail-desc", Static).update("-")
            self.query_one("#detail-old", Static).update("-")
            self.query_one("#detail-new", Static).update("-")
            self.query_one("#detail-error", Static).update("-")
        except Exception:
            pass


# ============================================================
# 审计日志列表
# ============================================================

class AuditLogTable(Static):
    """审计日志表格"""
    
    DEFAULT_CSS = """
    AuditLogTable {
        width: 100%;
        height: 100%;
    }
    
    AuditLogTable DataTable {
        width: 100%;
        height: 100%;
    }
    """
    
    class RecordSelected(Message):
        """记录选中消息"""
        def __init__(self, record_id: int) -> None:
            self.record_id = record_id
            super().__init__()
    
    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._records: List[AuditRecord] = []
    
    def compose(self) -> ComposeResult:
        yield DataTable(id="audit-table")
    
    def on_mount(self) -> None:
        """挂载时初始化表格"""
        table = self.query_one("#audit-table", DataTable)
        table.add_columns("ID", "时间", "类型", "设备", "描述", "结果")
        table.cursor_type = "row"
    
    def update_records(self, records: List[AuditRecord]) -> None:
        """更新记录"""
        self._records = records
        table = self.query_one("#audit-table", DataTable)
        table.clear()
        
        result_icons = {
            AuditResult.SUCCESS: "✅",
            AuditResult.FAILURE: "❌",
            AuditResult.PARTIAL: "⚠️",
            AuditResult.SKIPPED: "⏭️",
        }
        
        for record in records:
            time_str = record.timestamp.strftime("%m-%d %H:%M") if record.timestamp else "-"
            device = record.device_name[:15] if record.device_name else "-"
            desc = record.description[:30] + "..." if len(record.description) > 30 else record.description
            icon = result_icons.get(record.result, "❓")
            
            table.add_row(
                str(record.id),
                time_str,
                record.event_type.value[:15],
                device,
                desc,
                icon,
                key=str(record.id),
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理行选中"""
        if event.row_key:
            try:
                record_id = int(event.row_key.value)
                self.post_message(self.RecordSelected(record_id))
            except (ValueError, TypeError):
                pass


# ============================================================
# 主界面
# ============================================================

class AuditScreen(Screen):
    """审计日志界面"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "返回"),
        Binding("r", "refresh", "刷新"),
        Binding("e", "export_json", "导出JSON"),
        Binding("c", "export_csv", "导出CSV"),
    ]
    
    CSS = """
    AuditScreen {
        layout: horizontal;
    }
    
    AuditScreen #left-panel {
        width: 30;
        height: 100%;
        background: $surface;
        border-right: solid $primary;
    }
    
    AuditScreen #center-panel {
        width: 1fr;
        height: 100%;
    }
    
    AuditScreen #right-panel {
        width: 40;
        height: 100%;
        background: $surface;
        border-left: solid $primary;
    }
    
    AuditScreen .panel-section {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    AuditScreen #log-container {
        width: 100%;
        height: 1fr;
    }
    
    AuditScreen #action-bar {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
        dock: bottom;
    }
    
    AuditScreen #action-bar Button {
        margin-right: 1;
    }
    """
    
    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._service = get_audit_service()
        self._records: List[AuditRecord] = []
        self._current_query = AuditQuery(
            start_time=datetime.now() - timedelta(hours=24),
            limit=500,
        )
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal():
            # 左侧面板：统计和筛选
            with Vertical(id="left-panel"):
                with Container(classes="panel-section"):
                    yield AuditStatsPanel(id="stats-panel")
                with Container(classes="panel-section"):
                    yield FilterPanel(id="filter-panel")
            
            # 中间面板：日志列表
            with Vertical(id="center-panel"):
                with Container(id="log-container"):
                    yield AuditLogTable(id="log-table")
                
                # 操作栏
                with Horizontal(id="action-bar"):
                    yield Button("🔄 刷新", id="btn-refresh", variant="primary")
                    yield Button("📄 导出JSON", id="btn-export-json", variant="default")
                    yield Button("📊 导出CSV", id="btn-export-csv", variant="default")
                    yield Button("🗑️ 清理旧记录", id="btn-cleanup", variant="warning")
            
            # 右侧面板：详情
            with Vertical(id="right-panel"):
                yield DetailPanel(id="detail-panel")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """界面挂载时初始化"""
        self._refresh_data()
    
    def _refresh_data(self) -> None:
        """刷新数据"""
        # 查询记录
        self._records = self._service.query(self._current_query)
        
        # 更新表格
        log_table = self.query_one("#log-table", AuditLogTable)
        log_table.update_records(self._records)
        
        # 更新统计
        summary = self._service.get_summary(
            self._current_query.start_time,
            self._current_query.end_time,
        )
        stats_panel = self.query_one("#stats-panel", AuditStatsPanel)
        stats_panel.update_stats(summary)
        
        # 清空详情
        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.clear()
    
    def on_filter_panel_filter_changed(self, event: FilterPanel.FilterChanged) -> None:
        """处理筛选变更"""
        self._current_query = event.query
        self._refresh_data()
    
    def on_audit_log_table_record_selected(self, event: AuditLogTable.RecordSelected) -> None:
        """处理记录选中"""
        record = self._service.get_by_id(event.record_id)
        if record:
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            detail_panel.update_record(record)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "btn-refresh":
            self._refresh_data()
        elif button_id == "btn-export-json":
            self._export_json()
        elif button_id == "btn-export-csv":
            self._export_csv()
        elif button_id == "btn-cleanup":
            self._cleanup_old_records()
    
    def _export_json(self) -> None:
        """导出 JSON"""
        try:
            output_dir = Path("audit_exports")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = output_dir / f"audit_log_{timestamp}.json"
            
            count = self._service.export_json(filepath, self._current_query)
            self.notify(f"已导出 {count} 条记录到: {filepath}", severity="information")
        except Exception as e:
            self.notify(f"导出失败: {e}", severity="error")
    
    def _export_csv(self) -> None:
        """导出 CSV"""
        try:
            output_dir = Path("audit_exports")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = output_dir / f"audit_log_{timestamp}.csv"
            
            count = self._service.export_csv(filepath, self._current_query)
            self.notify(f"已导出 {count} 条记录到: {filepath}", severity="information")
        except Exception as e:
            self.notify(f"导出失败: {e}", severity="error")
    
    def _cleanup_old_records(self) -> None:
        """清理旧记录"""
        try:
            count = self._service.cleanup(days=90)
            if count > 0:
                self.notify(f"已清理 {count} 条过期记录", severity="information")
                self._refresh_data()
            else:
                self.notify("没有需要清理的记录", severity="information")
        except Exception as e:
            self.notify(f"清理失败: {e}", severity="error")
    
    # 快捷键动作
    def action_refresh(self) -> None:
        """刷新"""
        self._refresh_data()
    
    def action_export_json(self) -> None:
        """导出 JSON"""
        self._export_json()
    
    def action_export_csv(self) -> None:
        """导出 CSV"""
        self._export_csv()
