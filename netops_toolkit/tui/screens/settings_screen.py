"""
NetOps Toolkit TUI 系统设置屏幕

显示系统信息和配置管理界面。
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import (
    Static, Button, Input, Switch, Select, 
    Label, TabbedContent, TabPane, DataTable
)

from netops_toolkit.core.system_info import get_system_info, SystemInfo
from netops_toolkit.config.config_manager import get_config, ConfigManager
from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


class SettingsScreen(Screen):
    """系统设置屏幕 - 系统信息 + 配置管理"""
    
    BINDINGS = [
        ("escape", "go_back", "返回"),
        ("r", "refresh", "刷新"),
        ("s", "save_config", "保存配置"),
    ]
    
    def __init__(self) -> None:
        super().__init__()
        self._system_info: Optional[SystemInfo] = None
        self._config: Optional[ConfigManager] = None
        self._modified_settings: Dict[str, Any] = {}
    
    def compose(self) -> ComposeResult:
        """组合界面组件"""
        # 标题
        yield Container(
            Static(
                "[bold cyan]⚙️ 系统设置[/bold cyan]",
                id="settings-title"
            ),
            Static(
                "[dim]查看系统信息和修改配置[/dim]",
                id="settings-subtitle"
            ),
            id="welcome-panel"
        )
        
        # 选项卡内容
        with TabbedContent(id="settings-tabs"):
            # 系统信息选项卡
            with TabPane("💻 系统信息", id="tab-system"):
                yield ScrollableContainer(
                    Static(id="system-info-content"),
                    id="system-info-container"
                )
            
            # 网络接口选项卡
            with TabPane("🌐 网络接口", id="tab-network"):
                yield DataTable(id="network-table")
            
            # 应用配置选项卡
            with TabPane("🔧 应用配置", id="tab-config"):
                yield ScrollableContainer(
                    Vertical(id="config-form"),
                    id="config-container"
                )
            
            # 关于选项卡
            with TabPane("ℹ️ 关于", id="tab-about"):
                yield ScrollableContainer(
                    Static(id="about-content"),
                    id="about-container"
                )
        
        # 底部按钮
        with Horizontal(id="settings-buttons"):
            yield Button("🔄 刷新", id="refresh-btn", variant="primary")
            yield Button("💾 保存配置", id="save-btn", variant="success")
            yield Button("⬅️ 返回", id="back-btn", variant="warning")
    
    def on_mount(self) -> None:
        """屏幕挂载时加载数据"""
        # 使用 call_later 确保界面完全渲染后再加载数据
        self.call_later(self._load_all_data)
    
    def _load_all_data(self) -> None:
        """加载所有数据"""
        try:
            self._load_system_info()
            self._load_network_info()
            self._load_config()
            self._load_about()
        except Exception as e:
            logger.error(f"加载设置数据失败: {e}")
            self.app.notify(f"加载失败: {e}", title="错误")
    
    def _load_system_info(self) -> None:
        """加载系统信息"""
        try:
            info = get_system_info(refresh=True)
            self._system_info = info
            
            # 格式化显示内容
            content = self._format_system_info(info)
            
            static = self.query_one("#system-info-content", Static)
            static.update(content)
        except Exception as e:
            logger.error(f"加载系统信息失败: {e}")
            static = self.query_one("#system-info-content", Static)
            static.update(f"[red]加载系统信息失败: {e}[/red]")
    
    def _format_system_info(self, info: SystemInfo) -> str:
        """格式化系统信息显示"""
        sections = []
        
        # 操作系统
        sections.append(
            "[bold cyan]📋 操作系统[/bold cyan]\n"
            f"  系统名称: [green]{info.os_name}[/green]\n"
            f"  系统版本: {info.os_version}\n"
            f"  系统架构: [yellow]{info.os_arch}[/yellow]\n"
            f"  平台信息: {info.os_platform}"
        )
        
        # 主机信息
        sections.append(
            "[bold cyan]🖥️ 主机信息[/bold cyan]\n"
            f"  主机名: [green]{info.hostname}[/green]\n"
            f"  FQDN: {info.fqdn}\n"
            f"  机器ID: {info.machine_id}"
        )
        
        # 硬件信息
        mem_percent = (info.memory_available_gb / info.memory_total_gb * 100) if info.memory_total_gb > 0 else 0
        sections.append(
            "[bold cyan]⚡ 硬件信息[/bold cyan]\n"
            f"  CPU: [green]{info.cpu_name}[/green]\n"
            f"  核心数: {info.cpu_cores} 物理核 / {info.cpu_threads} 逻辑核\n"
            f"  总内存: [yellow]{info.memory_total_gb:.1f} GB[/yellow]\n"
            f"  可用内存: [green]{info.memory_available_gb:.1f} GB[/green] ({mem_percent:.1f}%)"
        )
        
        # Python 环境
        venv_info = f"\n  虚拟环境: [green]{info.virtual_env}[/green]" if info.virtual_env else ""
        sections.append(
            "[bold cyan]🐍 Python 环境[/bold cyan]\n"
            f"  版本: [green]{info.python_version}[/green]\n"
            f"  实现: {info.python_implementation}\n"
            f"  路径: {info.python_path}"
            f"{venv_info}"
        )
        
        # DNS 服务器
        if info.dns_servers:
            dns_list = "\n".join(f"    • {dns}" for dns in info.dns_servers)
            sections.append(
                "[bold cyan]🔗 DNS 服务器[/bold cyan]\n"
                f"{dns_list}"
            )
        
        # 时间信息
        sections.append(
            "[bold cyan]🕐 时间信息[/bold cyan]\n"
            f"  时区: {info.timezone}\n"
            f"  系统时间: [green]{info.current_time}[/green]\n"
            f"  运行时间: {info.uptime}"
        )
        
        return "\n\n".join(sections)
    
    def _load_network_info(self) -> None:
        """加载网络接口信息"""
        try:
            info = get_system_info()
            table = self.query_one("#network-table", DataTable)
            
            # 清空并设置列
            table.clear(columns=True)
            table.add_columns("接口名称", "状态", "IPv4 地址", "IPv6 地址", "MAC 地址", "MTU")
            
            # 添加行
            for iface in info.network_interfaces:
                status = "[green]●[/green] UP" if iface.is_up else "[red]●[/red] DOWN"
                ipv4 = ", ".join(iface.ipv4_addresses) if iface.ipv4_addresses else "-"
                ipv6 = iface.ipv6_addresses[0][:20] + "..." if iface.ipv6_addresses else "-"
                mac = iface.mac_address or "-"
                mtu = str(iface.mtu) if iface.mtu else "-"
                
                table.add_row(
                    iface.name,
                    status,
                    ipv4,
                    ipv6,
                    mac,
                    mtu
                )
        except Exception as e:
            logger.error(f"加载网络接口信息失败: {e}")
    
    def _load_config(self) -> None:
        """加载配置表单"""
        try:
            self._config = get_config()
            settings = self._config._settings or {}
            
            form = self.query_one("#config-form", Vertical)
            
            # 清空现有内容
            form.remove_children()
            
            # 添加配置分组
            config_groups = [
                ("network", "🌐 网络配置", [
                    ("ssh_timeout", "SSH 超时(秒)", "int", 30),
                    ("connect_retry", "连接重试次数", "int", 3),
                    ("max_workers", "最大并发数", "int", 10),
                    ("ping_count", "Ping 次数", "int", 4),
                    ("ping_timeout", "Ping 超时(秒)", "float", 2.0),
                ]),
                ("security", "🔒 安全配置", [
                    ("encrypt_passwords", "加密密码存储", "bool", True),
                    ("audit_logging", "审计日志", "bool", True),
                    ("session_timeout", "会话超时(秒)", "int", 3600),
                ]),
                ("ui", "🎨 界面配置", [
                    ("theme", "主题", "choice", "default", ["default", "dark", "light"]),
                    ("show_banner", "显示横幅", "bool", True),
                    ("animation", "启用动画", "bool", True),
                    ("confirm_dangerous", "危险操作确认", "bool", True),
                ]),
                ("output", "📁 输出配置", [
                    ("reports_dir", "报告目录", "str", "./reports"),
                    ("log_dir", "日志目录", "str", "./logs"),
                    ("export_format", "导出格式", "choice", "json", ["json", "csv", "xlsx"]),
                ]),
            ]
            
            for group_key, group_label, items in config_groups:
                # 分组标题
                form.mount(Static(f"\n[bold cyan]{group_label}[/bold cyan]", classes="config-group-title"))
                
                group_settings = settings.get(group_key, {})
                
                for item in items:
                    if len(item) == 4:
                        key, label, type_, default = item
                        choices = None
                    elif len(item) == 5:
                        key, label, type_, default, choices = item
                    else:
                        continue  # 跳过无效配置项
                    
                    current_value = group_settings.get(key, default)
                    
                    # 创建行容器
                    row = Horizontal(classes="config-row")
                    
                    # 创建标签
                    row_label = Label(f"{label}:", classes="config-label")
                    
                    # 创建输入控件
                    widget_id = f"config-{group_key}-{key}"
                    
                    if type_ == "bool":
                        widget = Switch(value=bool(current_value), id=widget_id)
                    elif type_ == "choice" and choices:
                        options = [(c, c) for c in choices]
                        widget = Select(options, value=str(current_value), id=widget_id)
                    elif type_ == "int":
                        widget = Input(value=str(current_value), id=widget_id, type="integer")
                    elif type_ == "float":
                        widget = Input(value=str(current_value), id=widget_id, type="number")
                    else:
                        widget = Input(value=str(current_value), id=widget_id)
                    
                    widget.add_class("config-input")
                    
                    # 挂载到表单
                    form.mount(row)
                    row.mount(row_label)
                    row.mount(widget)
                    
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            form = self.query_one("#config-form", Vertical)
            form.mount(Static(f"[red]加载配置失败: {e}[/red]"))
    
    def _load_about(self) -> None:
        """加载关于信息"""
        from netops_toolkit import __version__
        
        about_text = f"""
[bold cyan]🌐 NetOps Toolkit[/bold cyan]
[dim]网络工程实施及测试工具集[/dim]

[bold]版本信息[/bold]
  版本号: [green]v{__version__}[/green]
  许可证: MIT License

[bold]功能特性[/bold]
  • 🔍 网络诊断 (Ping/Traceroute/DNS)
  • 📡 网络扫描 (端口扫描/ARP扫描)
  • 🖥️ 设备管理 (SSH批量执行/配置备份)
  • ⚡ 性能测试 (网络质量/带宽测速)
  • 🛠️ 实用工具 (子网计算/IP转换/MAC查询)

[bold]技术栈[/bold]
  • Python 3.9+
  • Textual TUI 框架
  • Rich 终端美化
  • Paramiko SSH

[bold]项目信息[/bold]
  • GitHub: https://github.com/yourname/netops-toolkit
  • 文档: https://netops-toolkit.readthedocs.io

[dim]Copyright © 2024 NetOps Team[/dim]
"""
        
        static = self.query_one("#about-content", Static)
        static.update(about_text)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "refresh-btn":
            self.action_refresh()
        elif event.button.id == "save-btn":
            self.action_save_config()
        elif event.button.id == "back-btn":
            self.action_go_back()
    
    def action_go_back(self) -> None:
        """返回主屏幕"""
        self.app.pop_screen()
    
    def action_refresh(self) -> None:
        """刷新系统信息"""
        self._load_system_info()
        self._load_network_info()
        self.app.notify("系统信息已刷新", title="刷新")
    
    def action_save_config(self) -> None:
        """保存配置"""
        try:
            # 收集配置值
            new_settings = self._collect_config_values()
            
            if not new_settings:
                self.app.notify("没有配置需要保存", title="提示")
                return
            
            # 合并到现有配置
            config = get_config()
            current = config._settings or {}
            
            for group_key, group_values in new_settings.items():
                if group_key not in current:
                    current[group_key] = {}
                current[group_key].update(group_values)
            
            # 保存到文件
            config_path = config.config_dir / config.DEFAULT_SETTINGS_FILE
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(current, f, allow_unicode=True, default_flow_style=False)
            
            self.app.notify("配置已保存", title="成功", timeout=3)
            logger.info(f"配置已保存到: {config_path}")
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            self.app.notify(f"保存失败: {e}", title="错误", timeout=5)
    
    def _collect_config_values(self) -> Dict[str, Dict[str, Any]]:
        """收集配置表单的值"""
        result = {}
        
        # 遍历所有配置输入
        for widget in self.query(".config-input"):
            widget_id = widget.id
            if not widget_id or not widget_id.startswith("config-"):
                continue
            
            parts = widget_id.split("-")
            if len(parts) < 3:
                continue
            
            group_key = parts[1]
            setting_key = "-".join(parts[2:])
            
            # 获取值
            if isinstance(widget, Switch):
                value = widget.value
            elif isinstance(widget, Select):
                value = widget.value
            elif isinstance(widget, Input):
                raw_value = widget.value.strip()
                # 尝试转换类型
                if widget.type == "integer":
                    try:
                        value = int(raw_value)
                    except ValueError:
                        value = raw_value
                elif widget.type == "number":
                    try:
                        value = float(raw_value)
                    except ValueError:
                        value = raw_value
                else:
                    value = raw_value
            else:
                continue
            
            if group_key not in result:
                result[group_key] = {}
            result[group_key][setting_key] = value
        
        return result


__all__ = ["SettingsScreen"]
