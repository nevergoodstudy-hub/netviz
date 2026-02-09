"""
NetOps Toolkit TUI - 报表中心

报表功能:
- 巡检摘要报表
- 设备明细报表
- 异常汇总报表
- 监控状态报表
- PDF/Excel 格式导出
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, Label, Static, DataTable, Input, Select,
    RichLog, RadioButton, RadioSet, Checkbox
)
from textual.message import Message
from textual import work

if TYPE_CHECKING:
    from ..app import NetOpsApp


# 报表模板定义
REPORT_TEMPLATES = {
    "inspection_summary": {
        "name": "巡检摘要报表",
        "description": "包含设备状态汇总、在线/离线统计、异常告警",
        "icon": "📊",
    },
    "device_detail": {
        "name": "设备明细报表",
        "description": "设备清单详情，包含IP、厂商、型号等信息",
        "icon": "📋",
    },
    "anomaly_report": {
        "name": "异常汇总报表",
        "description": "异常事件汇总，按严重程度分类",
        "icon": "⚠️",
    },
    "monitoring_status": {
        "name": "监控状态报表",
        "description": "当前监控状态快照，含延迟和丢包率",
        "icon": "📡",
    },
}


class ReportTemplateSelector(Static):
    """报表模板选择器"""
    
    DEFAULT_CSS = """
    ReportTemplateSelector {
        height: auto;
        border: round $primary-darken-2;
        padding: 1;
    }
    
    ReportTemplateSelector > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    ReportTemplateSelector > .template-list {
        height: auto;
        padding: 1;
    }
    
    ReportTemplateSelector .template-item {
        height: 4;
        padding: 1;
        margin: 0 0 1 0;
        background: $surface;
        border: solid $primary-darken-3;
    }
    
    ReportTemplateSelector .template-item:hover {
        background: $primary-darken-2;
    }
    
    ReportTemplateSelector .template-item.selected {
        background: $primary;
        border: solid $secondary;
    }
    """
    
    class TemplateSelected(Message):
        """模板选择消息"""
        def __init__(self, template_id: str) -> None:
            self.template_id = template_id
            super().__init__()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_template: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        yield Label("📁 选择报表模板", classes="panel-header")
        with RadioSet(id="template-radio"):
            for template_id, info in REPORT_TEMPLATES.items():
                yield RadioButton(
                    f"{info['icon']} {info['name']}",
                    id=f"template-{template_id}",
                    value=template_id == "inspection_summary",
                )
    
    def on_mount(self) -> None:
        self._selected_template = "inspection_summary"
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.pressed:
            # 从 ID 提取模板名称
            template_id = event.pressed.id.replace("template-", "")
            self._selected_template = template_id
            self.post_message(self.TemplateSelected(template_id))
    
    @property
    def selected_template(self) -> Optional[str]:
        return self._selected_template


class ReportFormatSelector(Static):
    """报表格式选择器"""
    
    DEFAULT_CSS = """
    ReportFormatSelector {
        height: auto;
        border: round $primary-darken-2;
        padding: 1;
    }
    
    ReportFormatSelector > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    ReportFormatSelector > .format-options {
        height: auto;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("📄 输出格式", classes="panel-header")
        with Vertical(classes="format-options"):
            yield Checkbox("PDF 格式 (.pdf)", id="format-pdf", value=True)
            yield Checkbox("Excel 格式 (.xlsx)", id="format-excel", value=True)
    
    @property
    def selected_formats(self) -> List[str]:
        formats = []
        if self.query_one("#format-pdf", Checkbox).value:
            formats.append("pdf")
        if self.query_one("#format-excel", Checkbox).value:
            formats.append("excel")
        return formats


class ReportOptionsPanel(Static):
    """报表选项面板"""
    
    DEFAULT_CSS = """
    ReportOptionsPanel {
        height: auto;
        border: round $primary-darken-2;
        padding: 1;
    }
    
    ReportOptionsPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    ReportOptionsPanel > .options-form {
        height: auto;
        padding: 1;
    }
    
    ReportOptionsPanel > .options-form > .form-row {
        height: 3;
        margin: 0 0 1 0;
    }
    
    ReportOptionsPanel > .options-form > .form-row > Label {
        width: 15;
    }
    
    ReportOptionsPanel > .options-form > .form-row > Input {
        width: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("⚙️ 报表选项", classes="panel-header")
        with Vertical(classes="options-form"):
            with Horizontal(classes="form-row"):
                yield Label("报表标题:")
                yield Input(
                    placeholder="留空使用默认标题",
                    id="report-title",
                )
            with Horizontal(classes="form-row"):
                yield Label("作者/组织:")
                yield Input(
                    value="NetOps Team",
                    id="report-author",
                )
            with Horizontal(classes="form-row"):
                yield Label("输出目录:")
                yield Input(
                    value="reports",
                    id="report-output-dir",
                )
    
    @property
    def options(self) -> Dict[str, str]:
        return {
            "title": self.query_one("#report-title", Input).value,
            "author": self.query_one("#report-author", Input).value,
            "output_dir": self.query_one("#report-output-dir", Input).value,
        }


class ReportPreviewPanel(Static):
    """报表预览面板"""
    
    DEFAULT_CSS = """
    ReportPreviewPanel {
        height: 1fr;
        border: round $primary-darken-2;
    }
    
    ReportPreviewPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    ReportPreviewPanel > RichLog {
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("👁️ 报表预览 / 生成日志", classes="panel-header")
        yield RichLog(id="preview-log", highlight=True, markup=True, wrap=True)
    
    def show_template_info(self, template_id: str) -> None:
        """显示模板信息"""
        log = self.query_one("#preview-log", RichLog)
        info = REPORT_TEMPLATES.get(template_id, {})
        
        log.clear()
        log.write(f"[bold]{info.get('icon', '')} {info.get('name', template_id)}[/bold]")
        log.write(f"\n{info.get('description', '')}")
        log.write("\n\n[dim]─" * 40 + "[/dim]")
        log.write("\n[bold]报表内容预览:[/bold]")
        
        if template_id == "inspection_summary":
            log.write("\n• 巡检概况统计（总设备数、在线、离线、告警）")
            log.write("\n• 设备状态详情表格")
            log.write("\n• 异常事件汇总")
        elif template_id == "device_detail":
            log.write("\n• 设备清单表格")
            log.write("\n• 包含：名称、IP、厂商、型号、分组、端口、描述")
        elif template_id == "anomaly_report":
            log.write("\n• 异常统计（严重/警告/信息）")
            log.write("\n• 异常详情表格")
            log.write("\n• 按时间排序")
        elif template_id == "monitoring_status":
            log.write("\n• 实时监控状态快照")
            log.write("\n• 设备延迟和丢包率")
            log.write("\n• 状态着色（绿色正常/黄色警告/红色离线）")
    
    def log_message(self, message: str, level: str = "info") -> None:
        """添加日志消息"""
        log = self.query_one("#preview-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        level_styles = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        color = level_styles.get(level, "white")
        
        log.write(f"\n[dim]{timestamp}[/dim] [{color}]{message}[/{color}]")
    
    def clear_log(self) -> None:
        log = self.query_one("#preview-log", RichLog)
        log.clear()


class ReportsScreen(Screen):
    """报表中心屏幕"""
    
    TITLE = "📊 报表中心"
    SUB_TITLE = "生成和导出网络运维报表"
    
    BINDINGS = [
        Binding("h", "go_home", "返回主页", key_display="H"),
        Binding("g", "generate_report", "生成报表", key_display="G"),
        Binding("escape", "go_back", "返回"),
    ]
    
    DEFAULT_CSS = """
    ReportsScreen {
        layout: vertical;
    }
    
    ReportsScreen > .screen-header {
        height: 3;
        background: $primary-darken-2;
        padding: 0 2;
        text-style: bold;
    }
    
    ReportsScreen > .main-content {
        height: 1fr;
        padding: 1;
    }
    
    ReportsScreen > .main-content > .left-panel {
        width: 40;
    }
    
    ReportsScreen > .main-content > .right-panel {
        width: 1fr;
    }
    
    ReportsScreen > .action-bar {
        height: 5;
        padding: 1;
        background: $surface-darken-2;
    }
    
    ReportsScreen > .action-bar > Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._generating = False
    
    def compose(self) -> ComposeResult:
        yield Label("📊 报表中心 - 生成和导出运维报表", classes="screen-header")
        
        with Horizontal(classes="main-content"):
            with Vertical(classes="left-panel"):
                yield ReportTemplateSelector(id="template-selector")
                yield ReportFormatSelector(id="format-selector")
                yield ReportOptionsPanel(id="options-panel")
            
            with Vertical(classes="right-panel"):
                yield ReportPreviewPanel(id="preview-panel")
        
        with Horizontal(classes="action-bar"):
            yield Button("📥 生成报表", id="btn-generate", variant="primary")
            yield Button("📂 打开报表目录", id="btn-open-dir", variant="default")
            yield Button("🗑️ 清空日志", id="btn-clear-log", variant="warning")
    
    def on_mount(self) -> None:
        """初始化显示"""
        preview = self.query_one("#preview-panel", ReportPreviewPanel)
        preview.show_template_info("inspection_summary")
    
    def on_report_template_selector_template_selected(
        self, event: ReportTemplateSelector.TemplateSelected
    ) -> None:
        """处理模板选择"""
        preview = self.query_one("#preview-panel", ReportPreviewPanel)
        preview.show_template_info(event.template_id)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-generate":
            self._generate_report()
        elif event.button.id == "btn-open-dir":
            self._open_reports_dir()
        elif event.button.id == "btn-clear-log":
            preview = self.query_one("#preview-panel", ReportPreviewPanel)
            preview.clear_log()
    
    def _generate_report(self) -> None:
        """生成报表"""
        if self._generating:
            self.notify("报表正在生成中，请稍候...", severity="warning")
            return
        
        template_selector = self.query_one("#template-selector", ReportTemplateSelector)
        format_selector = self.query_one("#format-selector", ReportFormatSelector)
        options_panel = self.query_one("#options-panel", ReportOptionsPanel)
        preview = self.query_one("#preview-panel", ReportPreviewPanel)
        
        template_id = template_selector.selected_template
        formats = format_selector.selected_formats
        options = options_panel.options
        
        if not formats:
            self.notify("请至少选择一种输出格式", severity="error")
            return
        
        preview.log_message(f"开始生成报表: {REPORT_TEMPLATES[template_id]['name']}")
        preview.log_message(f"输出格式: {', '.join(formats)}")
        
        self._run_report_generation(template_id, formats, options)
    
    @work(exclusive=True, thread=True)
    def _run_report_generation(
        self, template_id: str, formats: List[str], options: Dict[str, str]
    ) -> None:
        """后台生成报表"""
        self._generating = True
        
        try:
            from netops_toolkit.services.report_engine import (
                ReportEngine, ReportTemplate, ReportFormat, ReportMetadata
            )
            
            # 确定输出目录
            output_dir = Path(options.get("output_dir", "reports"))
            if not output_dir.is_absolute():
                output_dir = Path.cwd() / output_dir
            
            engine = ReportEngine(output_dir)
            
            # 映射模板
            template_map = {
                "inspection_summary": ReportTemplate.INSPECTION_SUMMARY,
                "device_detail": ReportTemplate.DEVICE_DETAIL,
                "anomaly_report": ReportTemplate.ANOMALY_REPORT,
                "monitoring_status": ReportTemplate.MONITORING_STATUS,
            }
            template = template_map.get(template_id, ReportTemplate.CUSTOM)
            
            # 确定格式
            if len(formats) == 2:
                report_format = ReportFormat.BOTH
            elif "pdf" in formats:
                report_format = ReportFormat.PDF
            else:
                report_format = ReportFormat.EXCEL
            
            # 准备数据（从设备清单和模拟监控数据获取）
            data = self._collect_report_data(template_id)
            
            # 元数据
            title = options.get("title") or f"NetOps {REPORT_TEMPLATES[template_id]['name']}"
            metadata = ReportMetadata(
                title=title,
                author=options.get("author", "NetOps Team"),
                template=template,
            )
            
            # 生成报表
            self.app.call_from_thread(
                self._log_progress, f"正在生成报表到: {output_dir}"
            )
            
            results = engine.generate_report(
                template=template,
                data=data,
                metadata=metadata,
                format=report_format,
            )
            
            # 报告结果
            for fmt, path in results.items():
                if path:
                    self.app.call_from_thread(
                        self._log_progress,
                        f"✅ {fmt.upper()} 生成成功: {path.name}",
                        "success"
                    )
            
            self.app.call_from_thread(self._on_generation_complete, results)
            
        except Exception as e:
            self.app.call_from_thread(
                self._log_progress, f"❌ 生成失败: {str(e)}", "error"
            )
        finally:
            self._generating = False
    
    def _collect_report_data(self, template_id: str) -> Dict[str, Any]:
        """收集报表数据"""
        data: Dict[str, Any] = {}
        
        # 尝试加载设备清单
        devices = []
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory
            
            config_paths = [
                Path("config/devices.yaml"),
                Path.cwd() / "config" / "devices.yaml",
            ]
            
            for path in config_paths:
                if path.exists():
                    inventory = DeviceInventory(path)
                    for device in inventory:
                        devices.append({
                            "name": device.name,
                            "device_name": device.name,
                            "ip": device.ip,
                            "vendor": device.vendor,
                            "group": device.group or "",
                            "port": device.port,
                            "description": device.description or "",
                            "tags": device.tags or [],
                            "model": "",
                        })
                    break
        except Exception:
            pass
        
        # 如果没有设备，使用演示数据
        if not devices:
            devices = [
                {"name": "SW-CORE-01", "device_name": "SW-CORE-01", "ip": "192.168.1.10", 
                 "vendor": "cisco_ios", "group": "core", "status": "online", 
                 "latency_ms": 5.2, "packet_loss": 0},
                {"name": "SW-DIST-01", "device_name": "SW-DIST-01", "ip": "192.168.1.20", 
                 "vendor": "cisco_ios", "group": "distribution", "status": "online",
                 "latency_ms": 8.1, "packet_loss": 0},
                {"name": "RT-EDGE-01", "device_name": "RT-EDGE-01", "ip": "192.168.1.1", 
                 "vendor": "cisco_ios", "group": "edge", "status": "warning",
                 "latency_ms": 125.5, "packet_loss": 5},
                {"name": "FW-MAIN-01", "device_name": "FW-MAIN-01", "ip": "192.168.1.254", 
                 "vendor": "cisco_ios", "group": "security", "status": "offline",
                 "latency_ms": None, "packet_loss": 100},
            ]
        
        data["devices"] = devices
        
        # 根据模板添加额外数据
        if template_id in ("inspection_summary", "monitoring_status"):
            online = sum(1 for d in devices if d.get("status") == "online")
            offline = sum(1 for d in devices if d.get("status") == "offline")
            warning = sum(1 for d in devices if d.get("status") == "warning")
            
            data["summary"] = {
                "total_devices": len(devices),
                "online_devices": online,
                "offline_devices": offline,
                "alerts": warning + offline,
                "duration_seconds": 12.5,
            }
        
        if template_id in ("inspection_summary", "anomaly_report"):
            anomalies = []
            for d in devices:
                if d.get("status") == "offline":
                    anomalies.append({
                        "device_name": d.get("device_name", d.get("name", "")),
                        "ip": d.get("ip", ""),
                        "anomaly_type": "device_offline",
                        "severity": "critical",
                        "description": f"设备 {d.get('name', '')} 无法连接",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                elif d.get("status") == "warning":
                    anomalies.append({
                        "device_name": d.get("device_name", d.get("name", "")),
                        "ip": d.get("ip", ""),
                        "anomaly_type": "high_latency",
                        "severity": "warning",
                        "description": f"设备延迟过高: {d.get('latency_ms', 0):.1f}ms",
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
            data["anomalies"] = anomalies
        
        return data
    
    def _log_progress(self, message: str, level: str = "info") -> None:
        """记录进度"""
        preview = self.query_one("#preview-panel", ReportPreviewPanel)
        preview.log_message(message, level)
    
    def _on_generation_complete(self, results: Dict[str, Optional[Path]]) -> None:
        """生成完成回调"""
        generated = [f for f, p in results.items() if p]
        if generated:
            self.notify(
                f"报表生成完成: {', '.join(generated)}",
                title="成功",
                severity="information"
            )
    
    def _open_reports_dir(self) -> None:
        """打开报表目录"""
        import subprocess
        import platform
        
        options_panel = self.query_one("#options-panel", ReportOptionsPanel)
        output_dir = Path(options_panel.options.get("output_dir", "reports"))
        if not output_dir.is_absolute():
            output_dir = Path.cwd() / output_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", str(output_dir)], check=False)
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(output_dir)], check=False)
            else:
                subprocess.run(["xdg-open", str(output_dir)], check=False)
            
            self.notify(f"已打开目录: {output_dir}", severity="information")
        except Exception as e:
            self.notify(f"无法打开目录: {e}", severity="error")
    
    # === 快捷键动作 ===
    
    def action_go_home(self) -> None:
        self.app.pop_screen()
    
    def action_go_back(self) -> None:
        self.app.pop_screen()
    
    def action_generate_report(self) -> None:
        self._generate_report()
