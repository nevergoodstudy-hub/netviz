"""
NetOps Toolkit TUI - 设备管理界面

设备管理界面包含:
- 设备清单列表（按组分类）
- 设备详情查看
- 快捷命令执行（show version、接口状态、配置备份）
- 批量操作支持
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any, Dict, List
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, Label, Static, DataTable, Input, Select, 
    RichLog, TabbedContent, TabPane, Checkbox
)
from textual.message import Message
from textual import work
from textual.worker import Worker

if TYPE_CHECKING:
    from ..app import NetOpsApp

# 审计服务（延迟导入）
try:
    from netops_toolkit.services.audit_service import (
        get_audit_service, AuditEventType, AuditResult
    )
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False


@dataclass
class QuickCommand:
    """快捷命令定义"""
    id: str
    name: str
    icon: str
    command: str
    description: str


# 预定义的快捷命令
QUICK_COMMANDS = [
    QuickCommand("show_version", "系统信息", "📋", "show version", "获取设备系统版本信息"),
    QuickCommand("show_interfaces", "接口状态", "🔌", "show ip interface brief", "查看接口IP配置状态"),
    QuickCommand("show_inventory", "硬件清单", "🖥️", "show inventory", "获取设备硬件信息"),
    QuickCommand("show_running", "运行配置", "⚙️", "show running-config", "获取当前运行配置"),
    QuickCommand("show_routes", "路由表", "🗺️", "show ip route", "查看IP路由表"),
    QuickCommand("show_arp", "ARP表", "📍", "show arp", "查看ARP缓存表"),
    QuickCommand("show_mac", "MAC表", "🔗", "show mac address-table", "查看MAC地址表"),
    QuickCommand("show_cdp", "邻居发现", "🔍", "show cdp neighbors", "查看CDP邻居信息"),
]

# 不同厂商的命令映射
VENDOR_COMMANDS = {
    "cisco_ios": {
        "show_version": "show version",
        "show_interfaces": "show ip interface brief",
        "show_inventory": "show inventory",
        "show_running": "show running-config",
        "show_routes": "show ip route",
        "show_arp": "show arp",
        "show_mac": "show mac address-table",
        "show_cdp": "show cdp neighbors",
    },
    "huawei_vrp": {
        "show_version": "display version",
        "show_interfaces": "display ip interface brief",
        "show_inventory": "display device",
        "show_running": "display current-configuration",
        "show_routes": "display ip routing-table",
        "show_arp": "display arp",
        "show_mac": "display mac-address",
        "show_cdp": "display lldp neighbor",
    },
    "juniper_junos": {
        "show_version": "show version",
        "show_interfaces": "show interfaces terse",
        "show_inventory": "show chassis hardware",
        "show_running": "show configuration",
        "show_routes": "show route",
        "show_arp": "show arp",
        "show_mac": "show ethernet-switching table",
        "show_cdp": "show lldp neighbors",
    },
}


class DeviceListPanel(Static):
    """设备列表面板"""
    
    DEFAULT_CSS = """
    DeviceListPanel {
        height: 100%;
        border: round $primary-darken-2;
    }
    
    DeviceListPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    DeviceListPanel > .filter-box {
        height: 3;
        padding: 0 1;
    }
    
    DeviceListPanel > DataTable {
        height: 1fr;
    }
    """
    
    class DeviceSelected(Message):
        """设备选择消息"""
        def __init__(self, device_name: str, device_info: dict) -> None:
            self.device_name = device_name
            self.device_info = device_info
            super().__init__()
    
    class DevicesChecked(Message):
        """设备勾选消息"""
        def __init__(self, devices: List[dict]) -> None:
            self.devices = devices
            super().__init__()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._devices: List[dict] = []
        self._checked_devices: Dict[str, dict] = {}
    
    def compose(self) -> ComposeResult:
        yield Label("🖥️ 设备清单", classes="panel-header")
        with Container(classes="filter-box"):
            yield Input(placeholder="🔍 搜索设备...", id="device-filter")
        yield DataTable(id="device-table", cursor_type="row", zebra_stripes=True)
    
    def on_mount(self) -> None:
        """初始化数据表"""
        table = self.query_one("#device-table", DataTable)
        table.add_columns("☑", "名称", "IP地址", "类型", "组", "状态")
        self._load_devices()
    
    def _load_devices(self) -> None:
        """加载设备清单"""
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory
            
            # 查找设备清单文件
            config_paths = [
                Path("config/devices.yaml"),
                Path.cwd() / "config" / "devices.yaml",
                Path(__file__).parent.parent.parent.parent.parent / "config" / "devices.yaml",
            ]
            
            inventory = None
            for path in config_paths:
                if path.exists():
                    inventory = DeviceInventory(path)
                    break
            
            if not inventory:
                self._show_demo_devices()
                return
            
            # 填充表格
            table = self.query_one("#device-table", DataTable)
            table.clear()
            
            for device in inventory:
                self._devices.append({
                    "name": device.name,
                    "ip": device.ip,
                    "vendor": device.vendor,
                    "group": device.group,
                    "port": device.port,
                    "description": device.description,
                    "tags": device.tags,
                })
                table.add_row(
                    "☐",  # 复选框
                    device.name,
                    device.ip,
                    device.vendor,
                    device.group or "-",
                    "⏳",  # 状态待检测
                    key=device.name,
                )
        except Exception as e:
            self._show_demo_devices()
    
    def _show_demo_devices(self) -> None:
        """显示演示设备数据"""
        table = self.query_one("#device-table", DataTable)
        table.clear()
        
        demo_devices = [
            {"name": "SW-CORE-01", "ip": "192.168.1.10", "vendor": "cisco_ios", "group": "core_switches"},
            {"name": "SW-CORE-02", "ip": "192.168.1.11", "vendor": "cisco_ios", "group": "core_switches"},
            {"name": "R-EDGE-01", "ip": "10.0.0.1", "vendor": "huawei_vrp", "group": "edge_routers"},
            {"name": "FW-BORDER-01", "ip": "10.0.1.1", "vendor": "fortinet", "group": "firewalls"},
        ]
        
        for d in demo_devices:
            self._devices.append(d)
            table.add_row("☐", d["name"], d["ip"], d["vendor"], d["group"], "⏳", key=d["name"])
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理行选择"""
        if event.row_key:
            device_name = str(event.row_key.value)
            device_info = next((d for d in self._devices if d["name"] == device_name), None)
            if device_info:
                self.post_message(self.DeviceSelected(device_name, device_info))
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """处理单元格点击（用于勾选复选框）"""
        if event.coordinate.column == 0:  # 复选框列
            row_key = event.cell_key.row_key
            if row_key:
                device_name = str(row_key.value)
                self._toggle_device_check(device_name)
    
    def _toggle_device_check(self, device_name: str) -> None:
        """切换设备勾选状态"""
        table = self.query_one("#device-table", DataTable)
        device_info = next((d for d in self._devices if d["name"] == device_name), None)
        
        if device_name in self._checked_devices:
            del self._checked_devices[device_name]
            # 更新显示
            row_key = table.get_row_key(device_name)
            # 简化处理：记录状态
        else:
            if device_info:
                self._checked_devices[device_name] = device_info
        
        # 发送勾选状态更新
        self.post_message(self.DevicesChecked(list(self._checked_devices.values())))
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理搜索过滤"""
        if event.input.id == "device-filter":
            self._filter_devices(event.value)
    
    def _filter_devices(self, query: str) -> None:
        """过滤设备列表"""
        table = self.query_one("#device-table", DataTable)
        query_lower = query.lower().strip()
        
        table.clear()
        for d in self._devices:
            if not query_lower or \
               query_lower in d["name"].lower() or \
               query_lower in d["ip"].lower() or \
               query_lower in d.get("vendor", "").lower():
                check_mark = "☑" if d["name"] in self._checked_devices else "☐"
                table.add_row(check_mark, d["name"], d["ip"], d["vendor"], d.get("group", "-"), "⏳", key=d["name"])
    
    def get_checked_devices(self) -> List[dict]:
        """获取已勾选的设备"""
        return list(self._checked_devices.values())


class DeviceDetailPanel(Static):
    """设备详情面板"""
    
    DEFAULT_CSS = """
    DeviceDetailPanel {
        height: 100%;
        border: round $primary-darken-2;
    }
    
    DeviceDetailPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    DeviceDetailPanel > .device-info {
        height: auto;
        padding: 1;
    }
    
    DeviceDetailPanel .info-row {
        height: 1;
        padding: 0 1;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device_name = ""
        self._device_info: dict = {}
    
    def compose(self) -> ComposeResult:
        yield Label("📋 设备详情", classes="panel-header")
        with VerticalScroll(classes="device-info"):
            yield Label("请从左侧选择设备", id="device-detail-content")
    
    def update_device(self, device_name: str, device_info: dict) -> None:
        """更新设备详情显示"""
        self._device_name = device_name
        self._device_info = device_info
        
        content = self.query_one("#device-detail-content", Label)
        
        info_text = f"""[bold]🖥️ {device_name}[/]

📍 IP地址: {device_info.get('ip', '-')}
🔌 端口: {device_info.get('port', 22)}
🏭 设备类型: {device_info.get('vendor', '-')}
📁 设备组: {device_info.get('group', '-')}
📝 描述: {device_info.get('description', '-')}
🏷️ 标签: {', '.join(device_info.get('tags', [])) or '-'}
"""
        content.update(info_text)


class QuickCommandPanel(Static):
    """快捷命令面板"""
    
    DEFAULT_CSS = """
    QuickCommandPanel {
        height: auto;
        border: round $primary-darken-2;
        margin: 1 0;
    }
    
    QuickCommandPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    QuickCommandPanel > .commands-grid {
        layout: grid;
        grid-size: 4;
        grid-gutter: 1;
        padding: 1;
        height: auto;
    }
    
    QuickCommandPanel Button {
        width: 100%;
        height: 3;
    }
    """
    
    class CommandRequested(Message):
        """命令执行请求消息"""
        def __init__(self, command_id: str, command: str) -> None:
            self.command_id = command_id
            self.command = command
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Label("⚡ 快捷命令", classes="panel-header")
        with Container(classes="commands-grid"):
            for cmd in QUICK_COMMANDS:
                yield Button(
                    f"{cmd.icon} {cmd.name}",
                    id=f"cmd-{cmd.id}",
                    tooltip=cmd.description,
                    classes="quick-cmd-btn",
                )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理命令按钮点击"""
        if event.button.id and event.button.id.startswith("cmd-"):
            cmd_id = event.button.id[4:]  # 移除 "cmd-" 前缀
            cmd = next((c for c in QUICK_COMMANDS if c.id == cmd_id), None)
            if cmd:
                self.post_message(self.CommandRequested(cmd_id, cmd.command))


class CommandOutputPanel(Static):
    """命令输出面板"""
    
    DEFAULT_CSS = """
    CommandOutputPanel {
        height: 1fr;
        border: round $primary-darken-2;
    }
    
    CommandOutputPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    CommandOutputPanel > .output-controls {
        height: 3;
        padding: 0 1;
    }
    
    CommandOutputPanel > RichLog {
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("📤 命令输出", classes="panel-header")
        with Horizontal(classes="output-controls"):
            yield Input(placeholder="输入自定义命令...", id="custom-command")
            yield Button("执行", id="btn-exec-custom", variant="primary")
            yield Button("清空", id="btn-clear-output", variant="default")
        yield RichLog(id="command-output", highlight=True, markup=True)
    
    def log(self, message: str, style: str = "") -> None:
        """添加日志"""
        log_widget = self.query_one("#command-output", RichLog)
        if style:
            log_widget.write(f"[{style}]{message}[/]")
        else:
            log_widget.write(message)
    
    def clear(self) -> None:
        """清空输出"""
        log_widget = self.query_one("#command-output", RichLog)
        log_widget.clear()


class DeviceScreen(Screen):
    """设备管理屏幕
    
    布局:
    ┌──────────────────────────────────────────────────────────────┐
    │  设备管理 - 快捷键提示                                        │
    ├─────────────────────────┬────────────────────────────────────┤
    │                         │  设备详情                          │
    │  设备列表                │─────────────────────────────────────│
    │  (可搜索/勾选)           │  快捷命令按钮                       │
    │                         │─────────────────────────────────────│
    │                         │  命令输出                          │
    │                         │                                    │
    └─────────────────────────┴────────────────────────────────────┘
    """
    
    TITLE = "设备管理"
    SUB_TITLE = "管理设备清单、执行快捷命令"
    
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("r", "refresh", "刷新设备", show=True),
        Binding("ctrl+a", "select_all", "全选", show=True),
        Binding("ctrl+b", "backup_selected", "备份选中", show=True),
    ]
    
    DEFAULT_CSS = """
    DeviceScreen {
        layout: vertical;
    }
    
    DeviceScreen > #main-container {
        height: 1fr;
    }
    
    DeviceScreen #left-panel {
        width: 40%;
        min-width: 40;
    }
    
    DeviceScreen #right-panel {
        width: 1fr;
    }
    
    DeviceScreen #status-bar {
        height: 2;
        padding: 0 2;
        background: $surface-darken-1;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_device: Optional[dict] = None
        self._checked_devices: List[dict] = []
        self._current_worker: Optional[Worker] = None
    
    def compose(self) -> ComposeResult:
        """构建界面"""
        with Horizontal(id="main-container"):
            # 左侧：设备列表
            with Vertical(id="left-panel"):
                yield DeviceListPanel(id="device-list")
            
            # 右侧：详情和命令
            with Vertical(id="right-panel"):
                yield DeviceDetailPanel(id="device-detail")
                yield QuickCommandPanel(id="quick-commands")
                yield CommandOutputPanel(id="command-output")
        
        # 状态栏
        with Container(id="status-bar"):
            yield Label("已选择 0 台设备", id="selection-status")
    
    # ========== 事件处理 ==========
    
    def on_device_list_panel_device_selected(self, event: DeviceListPanel.DeviceSelected) -> None:
        """处理设备选择"""
        self._selected_device = event.device_info
        detail_panel = self.query_one("#device-detail", DeviceDetailPanel)
        detail_panel.update_device(event.device_name, event.device_info)
    
    def on_device_list_panel_devices_checked(self, event: DeviceListPanel.DevicesChecked) -> None:
        """处理设备勾选状态变化"""
        self._checked_devices = event.devices
        status_label = self.query_one("#selection-status", Label)
        status_label.update(f"已选择 {len(self._checked_devices)} 台设备")
    
    def on_quick_command_panel_command_requested(self, event: QuickCommandPanel.CommandRequested) -> None:
        """处理快捷命令请求"""
        if not self._selected_device:
            self.notify("请先选择一台设备", title="提示", severity="warning")
            return
        
        self._execute_command(event.command_id, event.command)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-exec-custom":
            self._execute_custom_command()
        elif event.button.id == "btn-clear-output":
            output_panel = self.query_one("#command-output", CommandOutputPanel)
            output_panel.clear()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理回车提交"""
        if event.input.id == "custom-command":
            self._execute_custom_command()
    
    # ========== Action方法 ==========
    
    def action_go_back(self) -> None:
        """返回上一界面"""
        self.app.pop_screen()
    
    def action_refresh(self) -> None:
        """刷新设备列表"""
        device_list = self.query_one("#device-list", DeviceListPanel)
        device_list._load_devices()
        self.notify("设备列表已刷新", title="提示")
    
    def action_select_all(self) -> None:
        """全选设备"""
        self.notify("全选功能开发中...", title="提示")
    
    def action_backup_selected(self) -> None:
        """备份选中设备"""
        if not self._checked_devices:
            self.notify("请先勾选要备份的设备", title="提示", severity="warning")
            return
        
        self._backup_devices(self._checked_devices)
    
    # ========== 命令执行 ==========
    
    def _execute_custom_command(self) -> None:
        """执行自定义命令"""
        if not self._selected_device:
            self.notify("请先选择一台设备", title="提示", severity="warning")
            return
        
        custom_input = self.query_one("#custom-command", Input)
        command = custom_input.value.strip()
        
        if not command:
            self.notify("请输入要执行的命令", title="提示", severity="warning")
            return
        
        self._execute_command("custom", command)
    
    def _execute_command(self, command_id: str, command: str) -> None:
        """执行命令"""
        device = self._selected_device
        if not device:
            return
        
        # 获取厂商特定命令
        vendor = device.get("vendor", "cisco_ios")
        if command_id != "custom" and vendor in VENDOR_COMMANDS:
            command = VENDOR_COMMANDS[vendor].get(command_id, command)
        
        output_panel = self.query_one("#command-output", CommandOutputPanel)
        output_panel.log(f"\n[bold cyan]>>> {device['name']} ({device['ip']})[/]")
        output_panel.log(f"[dim]执行命令: {command}[/]")
        output_panel.log("-" * 50)
        
        # 在后台执行命令
        self._current_worker = self._run_command(device, command)
    
    @work(thread=True)
    def _run_command(self, device: dict, command: str) -> str:
        """在后台线程执行命令"""
        try:
            from netops_toolkit.utils.ssh_utils import SSHConnection, check_netmiko_available
            import os
            
            if not check_netmiko_available():
                self.app.call_from_thread(
                    self._log_output,
                    "[yellow]警告: Netmiko未安装，显示模拟结果[/]"
                )
                return self._mock_command_output(device, command)
            
            # 从环境变量获取凭据
            username = os.environ.get("NETOPS_USERNAME", "admin")
            password = os.environ.get("NETOPS_PASSWORD", "")
            
            if not password:
                self.app.call_from_thread(
                    self._log_output,
                    "[yellow]警告: 未设置NETOPS_PASSWORD环境变量，显示模拟结果[/]"
                )
                return self._mock_command_output(device, command)
            
            with SSHConnection(
                host=device["ip"],
                username=username,
                password=password,
                device_type=device.get("vendor", "cisco_ios"),
                port=device.get("port", 22),
                timeout=30,
            ) as conn:
                if not conn.is_connected():
                    self.app.call_from_thread(
                        self._log_output,
                        "[red]连接失败[/]"
                    )
                    return ""
                
                output = conn.execute_command(command) or ""
                self.app.call_from_thread(self._log_output, output)
                self.app.call_from_thread(
                    self._log_output,
                    "\n[green]✓ 命令执行完成[/]"
                )
                # 记录审计日志
                if AUDIT_AVAILABLE:
                    audit = get_audit_service()
                    audit.log_command_execute(
                        device_name=device.get("name", "unknown"),
                        device_ip=device["ip"],
                        command=command,
                        output=output[:500] if output else "",
                        result=AuditResult.SUCCESS,
                    )
                return output
                
        except Exception as e:
            self.app.call_from_thread(
                self._log_output,
                f"[red]执行失败: {e}[/]"
            )
            # 记录失败审计
            if AUDIT_AVAILABLE:
                audit = get_audit_service()
                audit.log_command_execute(
                    device_name=device.get("name", "unknown"),
                    device_ip=device["ip"],
                    command=command,
                    output="",
                    result=AuditResult.FAILURE,
                    error_message=str(e),
                )
            return ""
    
    def _mock_command_output(self, device: dict, command: str) -> str:
        """生成模拟命令输出"""
        import time
        time.sleep(0.5)  # 模拟网络延迟
        
        mock_outputs = {
            "show version": f"""Cisco IOS Software, Version 15.2(4)M
{device['name']} uptime is 45 days, 12 hours
System image file is "flash:c3750-ipservicesk9-mz.150-2.SE.bin"
Cisco Catalyst 3750 (PowerPC405) processor
512K bytes of flash memory.
""",
            "show ip interface brief": """Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/1     192.168.1.1     YES NVRAM  up                    up
GigabitEthernet0/2     192.168.2.1     YES NVRAM  up                    up
GigabitEthernet0/3     unassigned      YES NVRAM  administratively down down
Vlan1                  10.0.0.1        YES NVRAM  up                    up
""",
            "show arp": """Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  192.168.1.1             -   0000.0c07.ac01  ARPA   GigabitEthernet0/1
Internet  192.168.1.100          45   aabb.ccdd.eeff  ARPA   GigabitEthernet0/1
Internet  192.168.2.1             -   0000.0c07.ac02  ARPA   GigabitEthernet0/2
""",
        }
        
        output = mock_outputs.get(command, f"[模拟输出] 命令: {command}\n设备: {device['name']}\n无更多数据")
        self.app.call_from_thread(self._log_output, output)
        self.app.call_from_thread(self._log_output, "\n[green]✓ 命令执行完成（模拟）[/]")
        return output
    
    def _log_output(self, message: str) -> None:
        """记录输出"""
        output_panel = self.query_one("#command-output", CommandOutputPanel)
        output_panel.log(message)
    
    # ========== 备份功能 ==========
    
    def _backup_devices(self, devices: List[dict]) -> None:
        """备份设备配置"""
        output_panel = self.query_one("#command-output", CommandOutputPanel)
        output_panel.log(f"\n[bold yellow]>>> 开始备份 {len(devices)} 台设备...[/]")
        
        self._current_worker = self._run_backup(devices)
    
    @work(thread=True)
    def _run_backup(self, devices: List[dict]) -> None:
        """在后台执行备份"""
        import os
        from datetime import datetime
        from pathlib import Path
        
        try:
            from netops_toolkit.utils.ssh_utils import SSHConnection, check_netmiko_available
            
            # 创建备份目录
            backup_base = Path("backups")
            backup_base.mkdir(parents=True, exist_ok=True)
            
            username = os.environ.get("NETOPS_USERNAME", "admin")
            password = os.environ.get("NETOPS_PASSWORD", "")
            
            for device in devices:
                device_name = device["name"]
                self.app.call_from_thread(
                    self._log_output,
                    f"\n[cyan]备份设备: {device_name}[/]"
                )
                
                if not password or not check_netmiko_available():
                    # 模拟备份
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    device_dir = backup_base / device_name.replace(".", "_")
                    device_dir.mkdir(parents=True, exist_ok=True)
                    backup_file = device_dir / f"config_{timestamp}.txt"
                    backup_file.write_text(f"# 模拟配置备份\n# 设备: {device_name}\n# 时间: {timestamp}\n")
                    self.app.call_from_thread(
                        self._log_output,
                        f"[green]✓ 备份完成（模拟）: {backup_file}[/]"
                    )
                    continue
                
                try:
                    with SSHConnection(
                        host=device["ip"],
                        username=username,
                        password=password,
                        device_type=device.get("vendor", "cisco_ios"),
                        timeout=60,
                    ) as conn:
                        if conn.is_connected():
                            config = conn.get_config("running")
                            if config:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                device_dir = backup_base / device_name.replace(".", "_")
                                device_dir.mkdir(parents=True, exist_ok=True)
                                backup_file = device_dir / f"config_{timestamp}.txt"
                                backup_file.write_text(config)
                                self.app.call_from_thread(
                                    self._log_output,
                                    f"[green]✓ 备份完成: {backup_file}[/]"
                                )
                                # 记录备份审计
                                if AUDIT_AVAILABLE:
                                    audit = get_audit_service()
                                    audit.log_config_backup(
                                        device_name=device_name,
                                        device_ip=device["ip"],
                                        backup_path=str(backup_file),
                                        result=AuditResult.SUCCESS,
                                    )
                            else:
                                self.app.call_from_thread(
                                    self._log_output,
                                    f"[red]✗ 获取配置失败: {device_name}[/]"
                                )
                                # 记录失败审计
                                if AUDIT_AVAILABLE:
                                    audit = get_audit_service()
                                    audit.log_config_backup(
                                        device_name=device_name,
                                        device_ip=device["ip"],
                                        backup_path="",
                                        result=AuditResult.FAILURE,
                                        error_message="获取配置失败",
                                    )
                        else:
                            self.app.call_from_thread(
                                self._log_output,
                                f"[red]✗ 连接失败: {device_name}[/]"
                            )
                except Exception as e:
                    self.app.call_from_thread(
                        self._log_output,
                        f"[red]✗ 备份失败 {device_name}: {e}[/]"
                    )
            
            self.app.call_from_thread(
                self._log_output,
                f"\n[bold green]>>> 备份任务完成[/]"
            )
            
        except Exception as e:
            self.app.call_from_thread(
                self._log_output,
                f"[red]备份任务异常: {e}[/]"
            )


__all__ = ["DeviceScreen"]
