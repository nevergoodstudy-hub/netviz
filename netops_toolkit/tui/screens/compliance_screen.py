"""
NetOps Toolkit - 合规检查界面

功能:
- 设备配置合规检查
- 规则浏览和管理
- 检查结果展示
- 报告导出
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    ProgressBar,
    RichLog,
    Rule,
    Select,
    Static,
    Tab,
    TabbedContent,
    TabPane,
    TextArea,
)

# 导入合规服务
from netops_toolkit.services.compliance_service import (
    ComplianceService,
    ComplianceChecker,
    ComplianceLevel,
    ComplianceRule,
    ComplianceResult,
    DeviceComplianceReport,
    RuleType,
    BUILTIN_RULES,
)


# ============================================================
# 规则列表面板
# ============================================================

class RulesPanel(Static):
    """规则列表面板"""
    
    DEFAULT_CSS = """
    RulesPanel {
        width: 100%;
        height: 100%;
        background: $surface;
    }
    
    RulesPanel .rules-header {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
    }
    
    RulesPanel .rules-title {
        text-style: bold;
    }
    
    RulesPanel .rules-filter {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    RulesPanel DataTable {
        width: 100%;
        height: 1fr;
    }
    """
    
    class RuleSelected(Message):
        """规则选中消息"""
        def __init__(self, rule_id: str) -> None:
            self.rule_id = rule_id
            super().__init__()
    
    def __init__(
        self,
        rules: List[ComplianceRule],
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._rules = rules
        self._filtered_rules = rules.copy()
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="rules-header"):
            yield Label("📋 合规规则", classes="rules-title")
            yield Label(f"共 {len(self._rules)} 条规则")
        
        with Horizontal(classes="rules-filter"):
            yield Select(
                [
                    ("全部厂商", "all"),
                    ("Cisco IOS", "cisco_ios"),
                    ("华为", "huawei"),
                    ("Juniper", "juniper"),
                ],
                value="all",
                id="vendor-filter",
            )
            yield Select(
                [
                    ("全部类别", "all"),
                    ("安全", "security"),
                    ("网络", "network"),
                    ("管理", "management"),
                    ("接口", "interface"),
                ],
                value="all",
                id="category-filter",
            )
        
        yield DataTable(id="rules-table")
    
    def on_mount(self) -> None:
        """挂载时初始化表格"""
        table = self.query_one("#rules-table", DataTable)
        table.add_columns("ID", "名称", "厂商", "严重程度", "类别")
        self._populate_table()
    
    def _populate_table(self) -> None:
        """填充表格数据"""
        table = self.query_one("#rules-table", DataTable)
        table.clear()
        
        severity_icons = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }
        
        for rule in self._filtered_rules:
            icon = severity_icons.get(rule.severity, "⚪")
            table.add_row(
                rule.id,
                rule.name[:30],
                rule.vendor,
                f"{icon} {rule.severity}",
                rule.category,
                key=rule.id,
            )
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """处理筛选器变更"""
        vendor_filter = self.query_one("#vendor-filter", Select).value
        category_filter = self.query_one("#category-filter", Select).value
        
        self._filtered_rules = [
            r for r in self._rules
            if (vendor_filter == "all" or r.vendor == vendor_filter or r.vendor == "all")
            and (category_filter == "all" or r.category == category_filter)
        ]
        
        self._populate_table()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理行选中"""
        if event.row_key:
            self.post_message(self.RuleSelected(str(event.row_key.value)))


# ============================================================
# 配置输入面板
# ============================================================

class ConfigInputPanel(Static):
    """配置输入面板"""
    
    DEFAULT_CSS = """
    ConfigInputPanel {
        width: 100%;
        height: 100%;
        background: $surface;
    }
    
    ConfigInputPanel .input-header {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
    }
    
    ConfigInputPanel .input-title {
        text-style: bold;
    }
    
    ConfigInputPanel .device-info {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    ConfigInputPanel .device-info Input {
        width: 1fr;
        margin: 0 1;
    }
    
    ConfigInputPanel TextArea {
        width: 100%;
        height: 1fr;
    }
    
    ConfigInputPanel .action-bar {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
    }
    
    ConfigInputPanel .action-bar Button {
        margin-right: 1;
    }
    """
    
    class CheckRequested(Message):
        """请求检查消息"""
        def __init__(
            self,
            config: str,
            device_name: str,
            device_ip: str,
            vendor: str,
        ) -> None:
            self.config = config
            self.device_name = device_name
            self.device_ip = device_ip
            self.vendor = vendor
            super().__init__()
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="input-header"):
            yield Label("📝 配置输入", classes="input-title")
            yield Label("输入或粘贴设备配置进行合规检查")
        
        with Horizontal(classes="device-info"):
            yield Input(placeholder="设备名称", id="device-name")
            yield Input(placeholder="设备IP", id="device-ip")
            yield Select(
                [
                    ("Cisco IOS", "cisco_ios"),
                    ("Cisco NXOS", "cisco_nxos"),
                    ("华为", "huawei"),
                    ("Juniper", "juniper"),
                ],
                value="cisco_ios",
                id="device-vendor",
            )
        
        yield TextArea(id="config-input", language="text")
        
        with Horizontal(classes="action-bar"):
            yield Button("🔍 开始检查", id="btn-check", variant="primary")
            yield Button("📂 加载文件", id="btn-load", variant="default")
            yield Button("🗑️ 清空", id="btn-clear", variant="default")
            yield Button("📋 加载示例", id="btn-sample", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        
        if button_id == "btn-check":
            self._request_check()
        elif button_id == "btn-clear":
            self._clear_input()
        elif button_id == "btn-sample":
            self._load_sample()
        elif button_id == "btn-load":
            self._load_from_file()
    
    def _request_check(self) -> None:
        """发起检查请求"""
        config = self.query_one("#config-input", TextArea).text
        device_name = self.query_one("#device-name", Input).value
        device_ip = self.query_one("#device-ip", Input).value
        vendor = self.query_one("#device-vendor", Select).value
        
        if not config.strip():
            self.notify("请输入配置内容", severity="warning")
            return
        
        self.post_message(self.CheckRequested(
            config=config,
            device_name=device_name or "Unknown",
            device_ip=device_ip or "0.0.0.0",
            vendor=str(vendor),
        ))
    
    def _clear_input(self) -> None:
        """清空输入"""
        self.query_one("#config-input", TextArea).clear()
        self.query_one("#device-name", Input).value = ""
        self.query_one("#device-ip", Input).value = ""
    
    def _load_sample(self) -> None:
        """加载示例配置"""
        sample_config = """!
! Cisco IOS Sample Configuration
!
version 15.1
service timestamps debug datetime msec
service timestamps log datetime msec
service password-encryption
!
hostname SW-SAMPLE-01
!
enable secret 5 $1$XXXX$XXXXXXXXXXXXXXXXXXXXX
!
aaa new-model
!
ip ssh version 2
ip domain-name example.com
!
no ip domain lookup
!
interface GigabitEthernet0/1
 description Uplink to Core
 ip address 192.168.1.10 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/2
 description Server Connection
 ip address 192.168.2.10 255.255.255.0
 no shutdown
!
line vty 0 4
 transport input ssh
 login local
!
ntp server 192.168.1.1
logging host 192.168.1.200
!
snmp-server community mycomplex123 RO
!
end
"""
        self.query_one("#config-input", TextArea).text = sample_config
        self.query_one("#device-name", Input).value = "SW-SAMPLE-01"
        self.query_one("#device-ip", Input).value = "192.168.1.10"
        self.query_one("#device-vendor", Select).value = "cisco_ios"
    
    def _load_from_file(self) -> None:
        """从文件加载配置"""
        # 简化实现：尝试从当前目录加载
        config_files = list(Path(".").glob("*.cfg")) + list(Path(".").glob("*.conf"))
        if config_files:
            try:
                config = config_files[0].read_text(encoding="utf-8")
                self.query_one("#config-input", TextArea).text = config
                self.notify(f"已加载: {config_files[0].name}", severity="information")
            except Exception as e:
                self.notify(f"加载失败: {e}", severity="error")
        else:
            self.notify("未找到配置文件 (*.cfg, *.conf)", severity="warning")


# ============================================================
# 结果展示面板
# ============================================================

class ResultsPanel(Static):
    """检查结果面板"""
    
    DEFAULT_CSS = """
    ResultsPanel {
        width: 100%;
        height: 100%;
        background: $surface;
    }
    
    ResultsPanel .results-header {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
    }
    
    ResultsPanel .results-title {
        text-style: bold;
    }
    
    ResultsPanel .summary-panel {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
        border: solid $primary;
        margin: 1;
    }
    
    ResultsPanel .summary-row {
        width: 100%;
        height: auto;
    }
    
    ResultsPanel .summary-item {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    
    ResultsPanel .summary-label {
        color: $text-muted;
    }
    
    ResultsPanel .summary-value {
        text-style: bold;
    }
    
    ResultsPanel .score-high {
        color: $success;
    }
    
    ResultsPanel .score-medium {
        color: $warning;
    }
    
    ResultsPanel .score-low {
        color: $error;
    }
    
    ResultsPanel RichLog {
        width: 100%;
        height: 1fr;
        margin: 1;
    }
    
    ResultsPanel .action-bar {
        width: 100%;
        height: auto;
        padding: 1;
        background: $boost;
    }
    """
    
    def __init__(
        self,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._report: Optional[DeviceComplianceReport] = None
    
    def compose(self) -> ComposeResult:
        with Vertical(classes="results-header"):
            yield Label("📊 检查结果", classes="results-title")
        
        # 摘要面板
        with Container(classes="summary-panel"):
            with Horizontal(classes="summary-row"):
                with Vertical(classes="summary-item"):
                    yield Label("设备", classes="summary-label")
                    yield Label("-", id="result-device", classes="summary-value")
                with Vertical(classes="summary-item"):
                    yield Label("状态", classes="summary-label")
                    yield Label("-", id="result-status", classes="summary-value")
                with Vertical(classes="summary-item"):
                    yield Label("分数", classes="summary-label")
                    yield Label("-", id="result-score", classes="summary-value")
            with Horizontal(classes="summary-row"):
                with Vertical(classes="summary-item"):
                    yield Label("✅ 合规", classes="summary-label")
                    yield Label("0", id="result-compliant", classes="summary-value")
                with Vertical(classes="summary-item"):
                    yield Label("⚠️ 警告", classes="summary-label")
                    yield Label("0", id="result-warning", classes="summary-value")
                with Vertical(classes="summary-item"):
                    yield Label("❌ 不合规", classes="summary-label")
                    yield Label("0", id="result-non-compliant", classes="summary-value")
                with Vertical(classes="summary-item"):
                    yield Label("🔴 错误", classes="summary-label")
                    yield Label("0", id="result-error", classes="summary-value")
        
        # 详细日志
        yield RichLog(id="results-log", highlight=True, markup=True)
        
        # 操作栏
        with Horizontal(classes="action-bar"):
            yield Button("📄 导出报告", id="btn-export", variant="primary")
            yield Button("🗑️ 清空", id="btn-clear-results", variant="default")
    
    def update_results(self, report: DeviceComplianceReport) -> None:
        """更新检查结果"""
        self._report = report
        
        # 更新摘要
        self.query_one("#result-device", Label).update(
            f"{report.device_name} ({report.device_ip})"
        )
        
        # 状态图标
        status_map = {
            ComplianceLevel.COMPLIANT: "✅ 合规",
            ComplianceLevel.WARNING: "⚠️ 警告",
            ComplianceLevel.NON_COMPLIANT: "❌ 不合规",
            ComplianceLevel.ERROR: "🔴 错误",
        }
        self.query_one("#result-status", Label).update(
            status_map.get(report.overall_level, "❓ 未知")
        )
        
        # 分数
        score_label = self.query_one("#result-score", Label)
        score_label.update(f"{report.score:.1f}/100")
        score_label.remove_class("score-high", "score-medium", "score-low")
        if report.score >= 80:
            score_label.add_class("score-high")
        elif report.score >= 60:
            score_label.add_class("score-medium")
        else:
            score_label.add_class("score-low")
        
        # 计数
        self.query_one("#result-compliant", Label).update(str(report.compliant_count))
        self.query_one("#result-warning", Label).update(str(report.warning_count))
        self.query_one("#result-non-compliant", Label).update(str(report.non_compliant_count))
        self.query_one("#result-error", Label).update(str(report.error_count))
        
        # 详细日志
        log = self.query_one("#results-log", RichLog)
        log.clear()
        
        log.write(f"[bold]检查时间: {report.check_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold]")
        log.write(f"厂商: {report.vendor}")
        log.write("")
        
        # 不合规项
        non_compliant = [r for r in report.results if r.level == ComplianceLevel.NON_COMPLIANT]
        if non_compliant:
            log.write("[bold red]❌ 不合规项:[/bold red]")
            for r in non_compliant:
                log.write(f"  [red][{r.rule_id}][/red] {r.rule_name}")
                log.write(f"      {r.message}")
                if r.details.get("remediation"):
                    log.write(f"      [dim]修复: {r.details['remediation']}[/dim]")
            log.write("")
        
        # 警告项
        warnings = [r for r in report.results if r.level == ComplianceLevel.WARNING]
        if warnings:
            log.write("[bold yellow]⚠️ 警告项:[/bold yellow]")
            for r in warnings:
                log.write(f"  [yellow][{r.rule_id}][/yellow] {r.rule_name}")
                log.write(f"      {r.message}")
            log.write("")
        
        # 合规项摘要
        compliant = [r for r in report.results if r.level == ComplianceLevel.COMPLIANT]
        if compliant:
            log.write(f"[bold green]✅ 合规项 ({len(compliant)}项):[/bold green]")
            for r in compliant[:5]:
                log.write(f"  [green][{r.rule_id}][/green] {r.rule_name}")
            if len(compliant) > 5:
                log.write(f"  [dim]... 及其他 {len(compliant) - 5} 项[/dim]")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-export":
            self._export_report()
        elif event.button.id == "btn-clear-results":
            self._clear_results()
    
    def _export_report(self) -> None:
        """导出报告"""
        if not self._report:
            self.notify("没有可导出的报告", severity="warning")
            return
        
        try:
            output_dir = Path("compliance_reports")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"compliance_{self._report.device_name}_{timestamp}.json"
            filepath = output_dir / filename
            
            service = ComplianceService()
            service.export_report_json(self._report, filepath)
            
            self.notify(f"报告已导出: {filepath}", severity="information")
        except Exception as e:
            self.notify(f"导出失败: {e}", severity="error")
    
    def _clear_results(self) -> None:
        """清空结果"""
        self._report = None
        self.query_one("#result-device", Label).update("-")
        self.query_one("#result-status", Label).update("-")
        self.query_one("#result-score", Label).update("-")
        self.query_one("#result-compliant", Label).update("0")
        self.query_one("#result-warning", Label).update("0")
        self.query_one("#result-non-compliant", Label).update("0")
        self.query_one("#result-error", Label).update("0")
        self.query_one("#results-log", RichLog).clear()


# ============================================================
# 主界面
# ============================================================

class ComplianceScreen(Screen):
    """合规检查界面"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "返回"),
        Binding("f5", "run_check", "检查"),
        Binding("ctrl+s", "export_report", "导出"),
    ]
    
    CSS = """
    ComplianceScreen {
        layout: horizontal;
    }
    
    ComplianceScreen #left-panel {
        width: 35%;
        height: 100%;
        border-right: solid $primary;
    }
    
    ComplianceScreen #right-panel {
        width: 65%;
        height: 100%;
    }
    
    ComplianceScreen TabbedContent {
        width: 100%;
        height: 100%;
    }
    
    ComplianceScreen TabPane {
        padding: 0;
    }
    """
    
    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._service = ComplianceService()
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal():
            # 左侧面板：规则列表
            with Vertical(id="left-panel"):
                yield RulesPanel(BUILTIN_RULES, id="rules-panel")
            
            # 右侧面板：配置输入和结果
            with Vertical(id="right-panel"):
                with TabbedContent():
                    with TabPane("配置检查", id="tab-check"):
                        yield ConfigInputPanel(id="config-panel")
                    with TabPane("检查结果", id="tab-results"):
                        yield ResultsPanel(id="results-panel")
        
        yield Footer()
    
    def on_config_input_panel_check_requested(
        self,
        event: ConfigInputPanel.CheckRequested,
    ) -> None:
        """处理检查请求"""
        # 执行检查
        report = self._service.check_device(
            config=event.config,
            device_name=event.device_name,
            device_ip=event.device_ip,
            vendor=event.vendor,
        )
        
        # 更新结果面板
        results_panel = self.query_one("#results-panel", ResultsPanel)
        results_panel.update_results(report)
        
        # 切换到结果标签页
        self.query_one(TabbedContent).active = "tab-results"
        
        # 显示通知
        self.notify(
            f"检查完成: {report.compliant_count} 合规, "
            f"{report.warning_count} 警告, "
            f"{report.non_compliant_count} 不合规",
            severity="information",
        )
    
    def on_rules_panel_rule_selected(self, event: RulesPanel.RuleSelected) -> None:
        """处理规则选中"""
        # 查找规则详情
        rule = next((r for r in BUILTIN_RULES if r.id == event.rule_id), None)
        if rule:
            self.notify(
                f"[{rule.id}] {rule.name}\n{rule.description}",
                title="规则详情",
                severity="information",
            )
    
    def action_run_check(self) -> None:
        """执行检查"""
        config_panel = self.query_one("#config-panel", ConfigInputPanel)
        config_panel._request_check()
    
    def action_export_report(self) -> None:
        """导出报告"""
        results_panel = self.query_one("#results-panel", ResultsPanel)
        results_panel._export_report()
