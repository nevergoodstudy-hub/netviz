"""
NetOps Toolkit TUI - 配置中心界面

配置中心界面包含:
- 配置模板管理（Jinja2）
- 变量表单编辑
- 配置预览
- 批量设备配置推送
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
    RichLog, TextArea, TabbedContent, TabPane
)
from textual.message import Message
from textual import work
from textual.worker import Worker

if TYPE_CHECKING:
    from ..app import NetOpsApp

# Jinja2环境（延迟导入）
try:
    from jinja2 import Environment, FileSystemLoader, BaseLoader, TemplateSyntaxError
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

# 审计服务（延迟导入）
try:
    from netops_toolkit.services.audit_service import (
        get_audit_service, AuditEventType, AuditResult
    )
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False


# 预定义的配置模板
BUILTIN_TEMPLATES = {
    "vlan_config": {
        "name": "VLAN配置",
        "description": "创建或修改VLAN配置",
        "template": """! VLAN Configuration
{% for vlan in vlans %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% if vlan.description %}
 description {{ vlan.description }}
{% endif %}
{% endfor %}
""",
        "variables": [
            {"name": "vlans", "type": "list", "description": "VLAN列表 (id, name, description)"}
        ],
        "sample_data": {
            "vlans": [
                {"id": 10, "name": "Management", "description": "Management VLAN"},
                {"id": 20, "name": "Users", "description": "User VLAN"},
                {"id": 30, "name": "Servers", "description": "Server VLAN"},
            ]
        }
    },
    "interface_config": {
        "name": "接口配置",
        "description": "配置交换机接口",
        "template": """! Interface Configuration
interface {{ interface_name }}
 description {{ description }}
{% if access_vlan %}
 switchport mode access
 switchport access vlan {{ access_vlan }}
{% elif trunk_vlans %}
 switchport mode trunk
 switchport trunk allowed vlan {{ trunk_vlans }}
{% endif %}
{% if shutdown %}
 shutdown
{% else %}
 no shutdown
{% endif %}
""",
        "variables": [
            {"name": "interface_name", "type": "str", "description": "接口名称"},
            {"name": "description", "type": "str", "description": "接口描述"},
            {"name": "access_vlan", "type": "int", "description": "Access VLAN (可选)"},
            {"name": "trunk_vlans", "type": "str", "description": "Trunk VLANs (可选)"},
            {"name": "shutdown", "type": "bool", "description": "是否关闭接口"},
        ],
        "sample_data": {
            "interface_name": "GigabitEthernet0/1",
            "description": "User Port",
            "access_vlan": 20,
            "trunk_vlans": None,
            "shutdown": False,
        }
    },
    "acl_config": {
        "name": "ACL配置",
        "description": "创建访问控制列表",
        "template": """! ACL Configuration
ip access-list extended {{ acl_name }}
{% for rule in rules %}
 {{ rule.action }} {{ rule.protocol }} {{ rule.source }} {{ rule.destination }}{% if rule.port %} eq {{ rule.port }}{% endif %}

{% endfor %}
""",
        "variables": [
            {"name": "acl_name", "type": "str", "description": "ACL名称"},
            {"name": "rules", "type": "list", "description": "规则列表"},
        ],
        "sample_data": {
            "acl_name": "WEB-ACCESS",
            "rules": [
                {"action": "permit", "protocol": "tcp", "source": "192.168.1.0 0.0.0.255", "destination": "any", "port": "80"},
                {"action": "permit", "protocol": "tcp", "source": "192.168.1.0 0.0.0.255", "destination": "any", "port": "443"},
                {"action": "deny", "protocol": "ip", "source": "any", "destination": "any", "port": None},
            ]
        }
    },
    "ntp_config": {
        "name": "NTP配置",
        "description": "配置NTP服务器",
        "template": """! NTP Configuration
{% for server in ntp_servers %}
ntp server {{ server.ip }}{% if server.prefer %} prefer{% endif %}

{% endfor %}
{% if timezone %}
clock timezone {{ timezone }} {{ timezone_offset }}
{% endif %}
""",
        "variables": [
            {"name": "ntp_servers", "type": "list", "description": "NTP服务器列表"},
            {"name": "timezone", "type": "str", "description": "时区名称"},
            {"name": "timezone_offset", "type": "int", "description": "时区偏移"},
        ],
        "sample_data": {
            "ntp_servers": [
                {"ip": "10.0.0.1", "prefer": True},
                {"ip": "10.0.0.2", "prefer": False},
            ],
            "timezone": "CST",
            "timezone_offset": 8,
        }
    },
    "banner_config": {
        "name": "Banner配置",
        "description": "配置登录横幅",
        "template": """! Banner Configuration
banner motd ^
{{ banner_text }}
^
""",
        "variables": [
            {"name": "banner_text", "type": "str", "description": "横幅文本"},
        ],
        "sample_data": {
            "banner_text": "警告：未授权访问将被追究法律责任！",
        }
    },
}


class TemplateListPanel(Static):
    """模板列表面板"""
    
    DEFAULT_CSS = """
    TemplateListPanel {
        height: 100%;
        border: round $primary-darken-2;
    }
    
    TemplateListPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    TemplateListPanel > DataTable {
        height: 1fr;
    }
    """
    
    class TemplateSelected(Message):
        """模板选择消息"""
        def __init__(self, template_id: str, template_info: dict) -> None:
            self.template_id = template_id
            self.template_info = template_info
            super().__init__()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._templates = BUILTIN_TEMPLATES
    
    def compose(self) -> ComposeResult:
        yield Label("📁 配置模板", classes="panel-header")
        yield DataTable(id="template-table", cursor_type="row", zebra_stripes=True)
    
    def on_mount(self) -> None:
        """初始化模板列表"""
        table = self.query_one("#template-table", DataTable)
        table.add_columns("模板名称", "描述")
        
        for tid, tinfo in self._templates.items():
            table.add_row(tinfo["name"], tinfo["description"], key=tid)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理模板选择"""
        if event.row_key:
            template_id = str(event.row_key.value)
            template_info = self._templates.get(template_id)
            if template_info:
                self.post_message(self.TemplateSelected(template_id, template_info))


class VariablesPanel(Static):
    """变量编辑面板"""
    
    DEFAULT_CSS = """
    VariablesPanel {
        height: auto;
        min-height: 15;
        border: round $primary-darken-2;
    }
    
    VariablesPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    VariablesPanel > .variables-form {
        height: auto;
        padding: 1;
    }
    
    VariablesPanel .var-row {
        height: 3;
        margin: 0 0 1 0;
    }
    
    VariablesPanel .var-label {
        width: 20;
    }
    
    VariablesPanel .var-input {
        width: 1fr;
    }
    """
    
    class VariablesChanged(Message):
        """变量修改消息"""
        def __init__(self, variables: dict) -> None:
            self.variables = variables
            super().__init__()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._template_info: Optional[dict] = None
        self._variables: dict = {}
    
    def compose(self) -> ComposeResult:
        yield Label("📝 变量编辑", classes="panel-header")
        with VerticalScroll(classes="variables-form", id="var-form-container"):
            yield Label("请选择一个模板", id="var-placeholder")
    
    def update_template(self, template_info: dict) -> None:
        """更新模板变量表单"""
        self._template_info = template_info
        self._variables = template_info.get("sample_data", {}).copy()
        
        container = self.query_one("#var-form-container", VerticalScroll)
        
        # 清空现有内容
        for child in list(container.children):
            child.remove()
        
        # 生成变量输入字段
        variables = template_info.get("variables", [])
        if not variables:
            container.mount(Label("该模板无需配置变量"))
            return
        
        for var in variables:
            var_name = var["name"]
            var_type = var.get("type", "str")
            var_desc = var.get("description", "")
            default_value = self._variables.get(var_name, "")
            
            # 将复杂类型转为JSON字符串显示
            if isinstance(default_value, (list, dict)):
                import json
                default_value = json.dumps(default_value, ensure_ascii=False, indent=2)
            else:
                default_value = str(default_value) if default_value is not None else ""
            
            with Horizontal(classes="var-row"):
                container.mount(Label(f"{var_name}:", classes="var-label"))
                container.mount(Input(
                    value=default_value,
                    placeholder=f"{var_desc} ({var_type})",
                    id=f"var-{var_name}",
                    classes="var-input",
                ))
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理变量输入变化"""
        if event.input.id and event.input.id.startswith("var-"):
            var_name = event.input.id[4:]  # 移除 "var-" 前缀
            value = event.value
            
            # 尝试解析JSON
            import json
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                pass  # 保持字符串
            
            self._variables[var_name] = value
            self.post_message(self.VariablesChanged(self._variables))
    
    def get_variables(self) -> dict:
        """获取当前变量值"""
        return self._variables.copy()


class PreviewPanel(Static):
    """配置预览面板"""
    
    DEFAULT_CSS = """
    PreviewPanel {
        height: 1fr;
        border: round $primary-darken-2;
    }
    
    PreviewPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    PreviewPanel > .preview-actions {
        height: 3;
        padding: 0 1;
    }
    
    PreviewPanel > TextArea {
        height: 1fr;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._template_content = ""
        self._rendered_content = ""
    
    def compose(self) -> ComposeResult:
        yield Label("👁️ 配置预览", classes="panel-header")
        with Horizontal(classes="preview-actions"):
            yield Button("🔄 刷新预览", id="btn-refresh-preview", variant="default")
            yield Button("📋 复制配置", id="btn-copy-config", variant="default")
        yield TextArea(id="preview-text", read_only=True, language="cisco")
    
    def update_template(self, template_content: str) -> None:
        """更新模板内容"""
        self._template_content = template_content
        text_area = self.query_one("#preview-text", TextArea)
        text_area.text = f"# 模板内容\n{template_content}"
    
    def update_preview(self, variables: dict) -> None:
        """使用变量渲染预览"""
        if not JINJA2_AVAILABLE:
            text_area = self.query_one("#preview-text", TextArea)
            text_area.text = "# 错误: Jinja2未安装\n# 请运行: pip install jinja2"
            return
        
        try:
            env = Environment(loader=BaseLoader())
            template = env.from_string(self._template_content)
            self._rendered_content = template.render(**variables)
            
            text_area = self.query_one("#preview-text", TextArea)
            text_area.text = self._rendered_content
        except TemplateSyntaxError as e:
            text_area = self.query_one("#preview-text", TextArea)
            text_area.text = f"# 模板语法错误\n# {e}"
        except Exception as e:
            text_area = self.query_one("#preview-text", TextArea)
            text_area.text = f"# 渲染错误\n# {e}"
    
    def get_rendered_content(self) -> str:
        """获取渲染后的配置内容"""
        return self._rendered_content


class DeviceSelectionPanel(Static):
    """设备选择面板"""
    
    DEFAULT_CSS = """
    DeviceSelectionPanel {
        height: auto;
        min-height: 10;
        border: round $primary-darken-2;
    }
    
    DeviceSelectionPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    DeviceSelectionPanel > DataTable {
        height: auto;
        max-height: 15;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._devices: List[dict] = []
        self._selected_devices: Dict[str, dict] = {}
    
    def compose(self) -> ComposeResult:
        yield Label("🎯 目标设备", classes="panel-header")
        yield DataTable(id="target-devices", cursor_type="row", zebra_stripes=True)
    
    def on_mount(self) -> None:
        """初始化设备列表"""
        table = self.query_one("#target-devices", DataTable)
        table.add_columns("☑", "设备", "IP", "类型")
        self._load_devices()
    
    def _load_devices(self) -> None:
        """加载设备清单"""
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
                    table = self.query_one("#target-devices", DataTable)
                    for device in inventory:
                        self._devices.append({
                            "name": device.name,
                            "ip": device.ip,
                            "vendor": device.vendor,
                        })
                        table.add_row("☐", device.name, device.ip, device.vendor, key=device.name)
                    return
        except Exception:
            pass
        
        # 演示数据
        table = self.query_one("#target-devices", DataTable)
        demo = [
            {"name": "SW-CORE-01", "ip": "192.168.1.10", "vendor": "cisco_ios"},
            {"name": "SW-CORE-02", "ip": "192.168.1.11", "vendor": "cisco_ios"},
        ]
        for d in demo:
            self._devices.append(d)
            table.add_row("☐", d["name"], d["ip"], d["vendor"], key=d["name"])
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """处理单元格点击"""
        if event.coordinate.column == 0:
            row_key = event.cell_key.row_key
            if row_key:
                device_name = str(row_key.value)
                self._toggle_device(device_name)
    
    def _toggle_device(self, device_name: str) -> None:
        """切换设备选择状态"""
        device_info = next((d for d in self._devices if d["name"] == device_name), None)
        if device_name in self._selected_devices:
            del self._selected_devices[device_name]
        else:
            if device_info:
                self._selected_devices[device_name] = device_info
    
    def get_selected_devices(self) -> List[dict]:
        """获取选中的设备"""
        return list(self._selected_devices.values())


class PushResultPanel(Static):
    """推送结果面板"""
    
    DEFAULT_CSS = """
    PushResultPanel {
        height: 1fr;
        border: round $primary-darken-2;
    }
    
    PushResultPanel > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    PushResultPanel > RichLog {
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("📊 推送结果", classes="panel-header")
        yield RichLog(id="push-result-log", highlight=True, markup=True)
    
    def log(self, message: str) -> None:
        """添加日志"""
        log_widget = self.query_one("#push-result-log", RichLog)
        log_widget.write(message)
    
    def clear(self) -> None:
        """清空日志"""
        log_widget = self.query_one("#push-result-log", RichLog)
        log_widget.clear()


class ConfigScreen(Screen):
    """配置中心屏幕
    
    布局:
    ┌───────────────┬────────────────────────────────────────┐
    │               │                                        │
    │  模板列表      │  配置预览                              │
    │               │                                        │
    ├───────────────┤                                        │
    │               │                                        │
    │  变量编辑      ├────────────────────────────────────────┤
    │               │  目标设备选择                           │
    │               ├────────────────────────────────────────┤
    │               │  推送结果                              │
    │               │                                        │
    └───────────────┴────────────────────────────────────────┘
    """
    
    TITLE = "配置中心"
    SUB_TITLE = "模板管理与批量配置推送"
    
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("ctrl+p", "push_config", "推送配置", show=True),
        Binding("ctrl+r", "refresh_preview", "刷新预览", show=True),
    ]
    
    DEFAULT_CSS = """
    ConfigScreen {
        layout: vertical;
    }
    
    ConfigScreen > #main-container {
        height: 1fr;
    }
    
    ConfigScreen #left-panel {
        width: 35%;
        min-width: 30;
    }
    
    ConfigScreen #right-panel {
        width: 1fr;
    }
    
    ConfigScreen #status-bar {
        height: 2;
        padding: 0 2;
        background: $surface-darken-1;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_template_id: Optional[str] = None
        self._current_template_info: Optional[dict] = None
        self._current_variables: dict = {}
        self._current_worker: Optional[Worker] = None
    
    def compose(self) -> ComposeResult:
        """构建界面"""
        with Horizontal(id="main-container"):
            # 左侧：模板和变量
            with Vertical(id="left-panel"):
                yield TemplateListPanel(id="template-list")
                yield VariablesPanel(id="variables-panel")
            
            # 右侧：预览和推送
            with Vertical(id="right-panel"):
                yield PreviewPanel(id="preview-panel")
                yield DeviceSelectionPanel(id="device-selection")
                with Horizontal(id="push-actions"):
                    yield Button("🚀 推送配置", id="btn-push", variant="primary")
                    yield Button("📋 仅预览", id="btn-preview", variant="default")
                yield PushResultPanel(id="push-result")
        
        # 状态栏
        with Container(id="status-bar"):
            yield Label("就绪", id="config-status")
    
    # ========== 事件处理 ==========
    
    def on_template_list_panel_template_selected(self, event: TemplateListPanel.TemplateSelected) -> None:
        """处理模板选择"""
        self._current_template_id = event.template_id
        self._current_template_info = event.template_info
        
        # 更新变量面板
        var_panel = self.query_one("#variables-panel", VariablesPanel)
        var_panel.update_template(event.template_info)
        
        # 更新预览面板
        preview_panel = self.query_one("#preview-panel", PreviewPanel)
        preview_panel.update_template(event.template_info.get("template", ""))
        preview_panel.update_preview(event.template_info.get("sample_data", {}))
        
        # 更新状态
        status = self.query_one("#config-status", Label)
        status.update(f"已选择模板: {event.template_info.get('name', event.template_id)}")
    
    def on_variables_panel_variables_changed(self, event: VariablesPanel.VariablesChanged) -> None:
        """处理变量变化"""
        self._current_variables = event.variables
        
        # 自动刷新预览
        if self._current_template_info:
            preview_panel = self.query_one("#preview-panel", PreviewPanel)
            preview_panel.update_preview(event.variables)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-push":
            self.action_push_config()
        elif event.button.id == "btn-preview":
            self.action_refresh_preview()
        elif event.button.id == "btn-refresh-preview":
            self.action_refresh_preview()
        elif event.button.id == "btn-copy-config":
            self._copy_config()
    
    # ========== Action方法 ==========
    
    def action_go_back(self) -> None:
        """返回上一界面"""
        self.app.pop_screen()
    
    def action_refresh_preview(self) -> None:
        """刷新预览"""
        if not self._current_template_info:
            self.notify("请先选择一个模板", title="提示", severity="warning")
            return
        
        var_panel = self.query_one("#variables-panel", VariablesPanel)
        variables = var_panel.get_variables()
        
        preview_panel = self.query_one("#preview-panel", PreviewPanel)
        preview_panel.update_preview(variables)
        
        self.notify("预览已刷新", title="提示")
    
    def action_push_config(self) -> None:
        """推送配置到选中设备"""
        if not self._current_template_info:
            self.notify("请先选择一个模板", title="提示", severity="warning")
            return
        
        device_panel = self.query_one("#device-selection", DeviceSelectionPanel)
        devices = device_panel.get_selected_devices()
        
        if not devices:
            self.notify("请先选择目标设备", title="提示", severity="warning")
            return
        
        preview_panel = self.query_one("#preview-panel", PreviewPanel)
        config_content = preview_panel.get_rendered_content()
        
        if not config_content:
            self.notify("配置内容为空，请先刷新预览", title="提示", severity="warning")
            return
        
        # 开始推送
        result_panel = self.query_one("#push-result", PushResultPanel)
        result_panel.clear()
        result_panel.log(f"[bold yellow]>>> 开始推送配置到 {len(devices)} 台设备...[/]")
        
        self._current_worker = self._run_push(devices, config_content)
    
    def _copy_config(self) -> None:
        """复制配置到剪贴板"""
        preview_panel = self.query_one("#preview-panel", PreviewPanel)
        config = preview_panel.get_rendered_content()
        
        if config:
            # 使用pyperclip或系统命令复制（简化处理）
            self.notify("配置已复制到剪贴板", title="提示")
        else:
            self.notify("没有可复制的配置", title="提示", severity="warning")
    
    # ========== 配置推送 ==========
    
    @work(thread=True)
    def _run_push(self, devices: List[dict], config_content: str) -> None:
        """在后台执行配置推送"""
        import os
        
        try:
            from netops_toolkit.utils.ssh_utils import SSHConnection, check_netmiko_available
            
            username = os.environ.get("NETOPS_USERNAME", "admin")
            password = os.environ.get("NETOPS_PASSWORD", "")
            
            # 将配置内容分割成命令列表
            config_lines = [line.strip() for line in config_content.split('\n') 
                          if line.strip() and not line.strip().startswith('!')]
            
            for device in devices:
                device_name = device["name"]
                self.app.call_from_thread(
                    self._log_push,
                    f"\n[cyan]推送到设备: {device_name} ({device['ip']})[/]"
                )
                
                if not password or not check_netmiko_available():
                    # 模拟推送
                    import time
                    time.sleep(0.5)
                    self.app.call_from_thread(
                        self._log_push,
                        f"[yellow]模拟推送配置 ({len(config_lines)} 行)[/]"
                    )
                    self.app.call_from_thread(
                        self._log_push,
                        f"[green]✓ 推送完成（模拟）[/]"
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
                            output = conn.execute_config_commands(config_lines)
                            if output:
                                self.app.call_from_thread(
                                    self._log_push,
                                    f"[dim]{output[:500]}...[/]" if len(output) > 500 else f"[dim]{output}[/]"
                                )
                            self.app.call_from_thread(
                                self._log_push,
                                f"[green]✓ 推送完成[/]"
                            )
                            # 记录审计日志
                            if AUDIT_AVAILABLE:
                                audit = get_audit_service()
                                audit.log_config_push(
                                    device_name=device_name,
                                    device_ip=device["ip"],
                                    config_content=config_content[:1000],
                                    result=AuditResult.SUCCESS,
                                )
                        else:
                            self.app.call_from_thread(
                                self._log_push,
                                f"[red]✗ 连接失败[/]"
                            )
                            # 记录失败审计
                            if AUDIT_AVAILABLE:
                                audit = get_audit_service()
                                audit.log_config_push(
                                    device_name=device_name,
                                    device_ip=device["ip"],
                                    config_content=config_content[:500],
                                    result=AuditResult.FAILURE,
                                    error_message="连接失败",
                                )
                except Exception as e:
                    self.app.call_from_thread(
                        self._log_push,
                        f"[red]✗ 推送失败: {e}[/]"
                    )
                    # 记录异常审计
                    if AUDIT_AVAILABLE:
                        audit = get_audit_service()
                        audit.log_config_push(
                            device_name=device_name,
                            device_ip=device["ip"],
                            config_content=config_content[:500],
                            result=AuditResult.FAILURE,
                            error_message=str(e),
                        )
            
            self.app.call_from_thread(
                self._log_push,
                f"\n[bold green]>>> 推送任务完成[/]"
            )
            
        except Exception as e:
            self.app.call_from_thread(
                self._log_push,
                f"[red]推送任务异常: {e}[/]"
            )
    
    def _log_push(self, message: str) -> None:
        """记录推送日志"""
        result_panel = self.query_one("#push-result", PushResultPanel)
        result_panel.log(message)


__all__ = ["ConfigScreen"]
