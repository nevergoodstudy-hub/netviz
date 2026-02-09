"""
NetOps Toolkit TUI - 诊断工具界面

诊断工具界面包含:
- 多设备选择
- 并发命令执行
- 结果表格展示
- 结果导出
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any, Dict, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, Label, Static, DataTable, Input, Select,
    RichLog, TextArea, TabbedContent, TabPane
)
from textual.message import Message
from textual import work
from textual.worker import Worker

if TYPE_CHECKING:
    from ..app import NetOpsApp


# 常用诊断命令预设
DIAGNOSTIC_PRESETS = {
    "connectivity": {
        "name": "连通性检查",
        "commands": ["ping {target}", "traceroute {target}"],
        "description": "检查网络连通性",
    },
    "interface_status": {
        "name": "接口状态",
        "commands": ["show ip interface brief", "show interfaces status"],
        "description": "查看所有接口状态",
    },
    "routing": {
        "name": "路由诊断",
        "commands": ["show ip route", "show ip protocols", "show ip bgp summary"],
        "description": "路由协议和路由表状态",
    },
    "switching": {
        "name": "交换诊断",
        "commands": ["show vlan brief", "show mac address-table", "show spanning-tree summary"],
        "description": "VLAN和二层交换状态",
    },
    "hardware": {
        "name": "硬件状态",
        "commands": ["show version", "show inventory", "show environment all"],
        "description": "硬件和环境信息",
    },
    "logs": {
        "name": "日志检查",
        "commands": ["show logging last 50"],
        "description": "查看最近日志条目",
    },
}


class DeviceSelector(Static):
    """设备多选面板"""
    
    DEFAULT_CSS = """
    DeviceSelector {
        height: auto;
        min-height: 15;
        max-height: 25;
        border: round $primary-darken-2;
    }
    
    DeviceSelector > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    DeviceSelector > .selector-controls {
        height: 3;
        padding: 0 1;
    }
    
    DeviceSelector > DataTable {
        height: 1fr;
    }
    """
    
    class SelectionChanged(Message):
        """选择变化消息"""
        def __init__(self, selected_devices: List[dict]) -> None:
            self.selected_devices = selected_devices
            super().__init__()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._devices: List[dict] = []
        self._selected: Dict[str, dict] = {}
    
    def compose(self) -> ComposeResult:
        yield Label("🎯 目标设备（可多选）", classes="panel-header")
        with Horizontal(classes="selector-controls"):
            yield Button("全选", id="btn-select-all", variant="default")
            yield Button("取消全选", id="btn-deselect-all", variant="default")
            yield Input(placeholder="🔍 搜索...", id="device-search")
        yield DataTable(id="device-selector-table", cursor_type="row", zebra_stripes=True)
    
    def on_mount(self) -> None:
        """初始化表格"""
        table = self.query_one("#device-selector-table", DataTable)
        table.add_columns("☑", "设备", "IP", "类型", "组")
        self._load_devices()
    
    def _load_devices(self) -> None:
        """加载设备"""
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory
            
            config_paths = [
                Path("config/devices.yaml"),
                Path.cwd() / "config" / "devices.yaml",
                Path(__file__).parent.parent.parent.parent.parent / "config" / "devices.yaml",
            ]
            
            for path in config_paths:
                if path.exists():
                    inventory = DeviceInventory(path)
                    table = self.query_one("#device-selector-table", DataTable)
                    for device in inventory:
                        d = {
                            "name": device.name,
                            "ip": device.ip,
                            "vendor": device.vendor,
                            "group": device.group or "-",
                            "port": device.port,
                        }
                        self._devices.append(d)
                        table.add_row("☐", d["name"], d["ip"], d["vendor"], d["group"], key=d["name"])
                    return
        except Exception:
            pass
        
        # 演示数据
        table = self.query_one("#device-selector-table", DataTable)
        demo = [
            {"name": "SW-CORE-01", "ip": "192.168.1.10", "vendor": "cisco_ios", "group": "core"},
            {"name": "SW-CORE-02", "ip": "192.168.1.11", "vendor": "cisco_ios", "group": "core"},
            {"name": "R-EDGE-01", "ip": "10.0.0.1", "vendor": "cisco_ios", "group": "edge"},
            {"name": "R-EDGE-02", "ip": "10.0.0.2", "vendor": "cisco_ios", "group": "edge"},
        ]
        for d in demo:
            self._devices.append(d)
            table.add_row("☐", d["name"], d["ip"], d["vendor"], d["group"], key=d["name"])
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮"""
        if event.button.id == "btn-select-all":
            self._select_all()
        elif event.button.id == "btn-deselect-all":
            self._deselect_all()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理行选择"""
        if event.row_key:
            device_name = str(event.row_key.value)
            self._toggle_selection(device_name)
    
    def _toggle_selection(self, device_name: str) -> None:
        """切换选择状态"""
        device = next((d for d in self._devices if d["name"] == device_name), None)
        if device_name in self._selected:
            del self._selected[device_name]
        else:
            if device:
                self._selected[device_name] = device
        
        self._update_table_display()
        self.post_message(self.SelectionChanged(list(self._selected.values())))
    
    def _select_all(self) -> None:
        """全选"""
        for d in self._devices:
            self._selected[d["name"]] = d
        self._update_table_display()
        self.post_message(self.SelectionChanged(list(self._selected.values())))
    
    def _deselect_all(self) -> None:
        """取消全选"""
        self._selected.clear()
        self._update_table_display()
        self.post_message(self.SelectionChanged([]))
    
    def _update_table_display(self) -> None:
        """更新表格显示"""
        table = self.query_one("#device-selector-table", DataTable)
        table.clear()
        for d in self._devices:
            check = "☑" if d["name"] in self._selected else "☐"
            table.add_row(check, d["name"], d["ip"], d["vendor"], d["group"], key=d["name"])
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """搜索过滤"""
        if event.input.id == "device-search":
            query = event.value.lower().strip()
            table = self.query_one("#device-selector-table", DataTable)
            table.clear()
            for d in self._devices:
                if not query or query in d["name"].lower() or query in d["ip"].lower():
                    check = "☑" if d["name"] in self._selected else "☐"
                    table.add_row(check, d["name"], d["ip"], d["vendor"], d["group"], key=d["name"])
    
    def get_selected_devices(self) -> List[dict]:
        """获取选中设备"""
        return list(self._selected.values())


class CommandInput(Static):
    """命令输入面板"""
    
    DEFAULT_CSS = """
    CommandInput {
        height: auto;
        border: round $primary-darken-2;
    }
    
    CommandInput > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    CommandInput > .preset-buttons {
        height: auto;
        padding: 1;
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
    }
    
    CommandInput > .command-area {
        height: auto;
        padding: 1;
    }
    """
    
    class CommandSubmitted(Message):
        """命令提交消息"""
        def __init__(self, commands: List[str]) -> None:
            self.commands = commands
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Label("⚡ 命令输入", classes="panel-header")
        
        # 预设按钮
        with Container(classes="preset-buttons"):
            for preset_id, preset_info in DIAGNOSTIC_PRESETS.items():
                yield Button(
                    f"📋 {preset_info['name']}",
                    id=f"preset-{preset_id}",
                    tooltip=preset_info["description"],
                )
        
        # 命令输入区
        with Container(classes="command-area"):
            yield Label("输入命令（每行一条）:")
            yield TextArea(id="commands-input", language="bash")
            with Horizontal():
                yield Button("▶ 执行命令", id="btn-run-commands", variant="primary")
                yield Button("🗑️ 清空", id="btn-clear-commands", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮"""
        if event.button.id == "btn-run-commands":
            self._submit_commands()
        elif event.button.id == "btn-clear-commands":
            text_area = self.query_one("#commands-input", TextArea)
            text_area.text = ""
        elif event.button.id and event.button.id.startswith("preset-"):
            preset_id = event.button.id[7:]  # 移除 "preset-"
            self._apply_preset(preset_id)
    
    def _apply_preset(self, preset_id: str) -> None:
        """应用预设命令"""
        preset = DIAGNOSTIC_PRESETS.get(preset_id)
        if preset:
            text_area = self.query_one("#commands-input", TextArea)
            text_area.text = "\n".join(preset["commands"])
    
    def _submit_commands(self) -> None:
        """提交命令"""
        text_area = self.query_one("#commands-input", TextArea)
        commands = [line.strip() for line in text_area.text.split("\n") if line.strip()]
        if commands:
            self.post_message(self.CommandSubmitted(commands))


class ResultsPanel(Static):
    """结果面板"""
    
    DEFAULT_CSS = """
    ResultsPanel {
        height: 1fr;
        border: round $primary-darken-2;
    }
    
    ResultsPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    ResultsPanel > .results-controls {
        height: 3;
        padding: 0 1;
    }
    
    ResultsPanel > TabbedContent {
        height: 1fr;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._results: Dict[str, Dict[str, str]] = {}  # {device: {command: output}}
    
    def compose(self) -> ComposeResult:
        yield Label("📊 执行结果", classes="panel-header")
        with Horizontal(classes="results-controls"):
            yield Button("📥 导出JSON", id="btn-export-json", variant="default")
            yield Button("📄 导出文本", id="btn-export-text", variant="default")
            yield Button("🗑️ 清空结果", id="btn-clear-results", variant="default")
        
        with TabbedContent(id="results-tabs"):
            with TabPane("📋 表格视图", id="tab-table"):
                yield DataTable(id="results-table", zebra_stripes=True)
            with TabPane("📝 详情视图", id="tab-detail"):
                yield RichLog(id="results-log", highlight=True, markup=True)
    
    def on_mount(self) -> None:
        """初始化表格"""
        table = self.query_one("#results-table", DataTable)
        table.add_columns("设备", "命令", "状态", "摘要")
    
    def add_result(self, device: str, command: str, output: str, success: bool) -> None:
        """添加结果"""
        if device not in self._results:
            self._results[device] = {}
        self._results[device][command] = output
        
        # 更新表格
        table = self.query_one("#results-table", DataTable)
        status = "✅" if success else "❌"
        summary = output[:50] + "..." if len(output) > 50 else output
        summary = summary.replace("\n", " ")
        table.add_row(device, command, status, summary)
        
        # 更新详情日志
        log = self.query_one("#results-log", RichLog)
        style = "green" if success else "red"
        log.write(f"\n[bold {style}]>>> {device}: {command}[/]")
        log.write("-" * 60)
        log.write(output[:1000] if len(output) > 1000 else output)
    
    def clear_results(self) -> None:
        """清空结果"""
        self._results.clear()
        table = self.query_one("#results-table", DataTable)
        table.clear()
        log = self.query_one("#results-log", RichLog)
        log.clear()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮"""
        if event.button.id == "btn-export-json":
            self._export_json()
        elif event.button.id == "btn-export-text":
            self._export_text()
        elif event.button.id == "btn-clear-results":
            self.clear_results()
    
    def _export_json(self) -> None:
        """导出为JSON"""
        if not self._results:
            self.app.notify("没有可导出的结果", title="提示", severity="warning")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"diagnostics_{timestamp}.json"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self._results, f, ensure_ascii=False, indent=2)
            self.app.notify(f"已导出到 {filename}", title="导出成功")
        except Exception as e:
            self.app.notify(f"导出失败: {e}", title="错误", severity="error")
    
    def _export_text(self) -> None:
        """导出为文本"""
        if not self._results:
            self.app.notify("没有可导出的结果", title="提示", severity="warning")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"diagnostics_{timestamp}.txt"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for device, commands in self._results.items():
                    f.write(f"{'='*60}\n")
                    f.write(f"Device: {device}\n")
                    f.write(f"{'='*60}\n\n")
                    for cmd, output in commands.items():
                        f.write(f">>> {cmd}\n")
                        f.write(f"{'-'*40}\n")
                        f.write(f"{output}\n\n")
            self.app.notify(f"已导出到 {filename}", title="导出成功")
        except Exception as e:
            self.app.notify(f"导出失败: {e}", title="错误", severity="error")


class DiagnosticsScreen(Screen):
    """诊断工具屏幕
    
    支持:
    - 多设备选择
    - 并发命令执行
    - 结果表格/详情展示
    - 结果导出
    """
    
    TITLE = "诊断工具"
    SUB_TITLE = "多设备并发命令执行"
    
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("ctrl+enter", "run_commands", "执行", show=True),
        Binding("ctrl+e", "export_results", "导出", show=True),
    ]
    
    DEFAULT_CSS = """
    DiagnosticsScreen {
        layout: vertical;
    }
    
    DiagnosticsScreen > #main-container {
        height: 1fr;
    }
    
    DiagnosticsScreen #left-panel {
        width: 40%;
        min-width: 40;
    }
    
    DiagnosticsScreen #right-panel {
        width: 1fr;
    }
    
    DiagnosticsScreen #status-bar {
        height: 2;
        padding: 0 2;
        background: $surface-darken-1;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_devices: List[dict] = []
        self._current_worker: Optional[Worker] = None
        self._is_running = False
    
    def compose(self) -> ComposeResult:
        """构建界面"""
        with Horizontal(id="main-container"):
            # 左侧：设备选择和命令输入
            with Vertical(id="left-panel"):
                yield DeviceSelector(id="device-selector")
                yield CommandInput(id="command-input")
            
            # 右侧：结果展示
            with Vertical(id="right-panel"):
                yield ResultsPanel(id="results-panel")
        
        # 状态栏
        with Container(id="status-bar"):
            yield Label("就绪 | 已选择 0 台设备", id="diag-status")
    
    # ========== 事件处理 ==========
    
    def on_device_selector_selection_changed(self, event: DeviceSelector.SelectionChanged) -> None:
        """处理设备选择变化"""
        self._selected_devices = event.selected_devices
        status = self.query_one("#diag-status", Label)
        status.update(f"就绪 | 已选择 {len(self._selected_devices)} 台设备")
    
    def on_command_input_command_submitted(self, event: CommandInput.CommandSubmitted) -> None:
        """处理命令提交"""
        if not self._selected_devices:
            self.notify("请先选择目标设备", title="提示", severity="warning")
            return
        
        if self._is_running:
            self.notify("命令正在执行中，请稍候", title="提示", severity="warning")
            return
        
        self._run_commands(event.commands)
    
    # ========== Action方法 ==========
    
    def action_go_back(self) -> None:
        """返回上一界面"""
        if self._is_running:
            self.notify("请等待命令执行完成", title="提示", severity="warning")
            return
        self.app.pop_screen()
    
    def action_run_commands(self) -> None:
        """执行命令"""
        command_panel = self.query_one("#command-input", CommandInput)
        text_area = command_panel.query_one("#commands-input", TextArea)
        commands = [line.strip() for line in text_area.text.split("\n") if line.strip()]
        
        if commands and self._selected_devices:
            self._run_commands(commands)
    
    def action_export_results(self) -> None:
        """导出结果"""
        results_panel = self.query_one("#results-panel", ResultsPanel)
        results_panel._export_json()
    
    # ========== 命令执行 ==========
    
    def _run_commands(self, commands: List[str]) -> None:
        """运行命令"""
        self._is_running = True
        status = self.query_one("#diag-status", Label)
        status.update(f"执行中... | {len(self._selected_devices)} 台设备 x {len(commands)} 条命令")
        
        results_panel = self.query_one("#results-panel", ResultsPanel)
        results_panel.clear_results()
        
        self._current_worker = self._execute_commands(self._selected_devices, commands)
    
    @work(thread=True)
    def _execute_commands(self, devices: List[dict], commands: List[str]) -> None:
        """在后台线程并发执行命令"""
        import os
        
        try:
            from netops_toolkit.utils.ssh_utils import SSHConnection, check_netmiko_available
            
            username = os.environ.get("NETOPS_USERNAME", "admin")
            password = os.environ.get("NETOPS_PASSWORD", "")
            
            # 定义单设备执行函数
            def execute_on_device(device: dict) -> Dict[str, Any]:
                results = {"device": device["name"], "commands": {}}
                
                if not password or not check_netmiko_available():
                    # 模拟执行
                    import time
                    for cmd in commands:
                        time.sleep(0.3)
                        output = f"[模拟输出] {device['name']}: {cmd}\n执行成功（模拟）"
                        results["commands"][cmd] = {"output": output, "success": True}
                        self.app.call_from_thread(
                            self._add_result,
                            device["name"], cmd, output, True
                        )
                    return results
                
                try:
                    with SSHConnection(
                        host=device["ip"],
                        username=username,
                        password=password,
                        device_type=device.get("vendor", "cisco_ios"),
                        port=device.get("port", 22),
                        timeout=30,
                    ) as conn:
                        if conn.is_connected():
                            for cmd in commands:
                                try:
                                    output = conn.execute_command(cmd) or ""
                                    results["commands"][cmd] = {"output": output, "success": True}
                                    self.app.call_from_thread(
                                        self._add_result,
                                        device["name"], cmd, output, True
                                    )
                                except Exception as e:
                                    results["commands"][cmd] = {"output": str(e), "success": False}
                                    self.app.call_from_thread(
                                        self._add_result,
                                        device["name"], cmd, str(e), False
                                    )
                        else:
                            for cmd in commands:
                                results["commands"][cmd] = {"output": "连接失败", "success": False}
                                self.app.call_from_thread(
                                    self._add_result,
                                    device["name"], cmd, "连接失败", False
                                )
                except Exception as e:
                    for cmd in commands:
                        results["commands"][cmd] = {"output": str(e), "success": False}
                        self.app.call_from_thread(
                            self._add_result,
                            device["name"], cmd, str(e), False
                        )
                
                return results
            
            # 并发执行
            max_workers = min(10, len(devices))  # 最多10个并发
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(execute_on_device, d): d["name"] for d in devices}
                
                for future in as_completed(futures):
                    device_name = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        self.app.call_from_thread(
                            self._add_result,
                            device_name, "执行异常", str(e), False
                        )
            
            self.app.call_from_thread(self._execution_completed)
            
        except Exception as e:
            self.app.call_from_thread(self._execution_completed)
            self.app.call_from_thread(
                self.notify,
                f"执行异常: {e}", title="错误", severity="error"
            )
    
    def _add_result(self, device: str, command: str, output: str, success: bool) -> None:
        """添加结果到面板"""
        results_panel = self.query_one("#results-panel", ResultsPanel)
        results_panel.add_result(device, command, output, success)
    
    def _execution_completed(self) -> None:
        """执行完成回调"""
        self._is_running = False
        status = self.query_one("#diag-status", Label)
        status.update(f"完成 | 已选择 {len(self._selected_devices)} 台设备")
        self.notify("命令执行完成", title="提示")


__all__ = ["DiagnosticsScreen"]
