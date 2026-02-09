"""
NetOps Toolkit TUI - 监控仪表板

实时监控功能:
- 设备状态监控（在线/离线/告警）
- Ping延迟检测（毫秒级）
- 自动定时刷新（默认5秒）
- 阈值告警（延迟/丢包）
- 可选SNMP指标扩展
"""

from __future__ import annotations

import asyncio
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button, Label, Static, DataTable, Input, Select,
    RichLog, Switch, ProgressBar, Sparkline
)
from textual.message import Message
from textual import work
from textual.worker import Worker, WorkerState
from textual.timer import Timer

if TYPE_CHECKING:
    from ..app import NetOpsApp


class DeviceStatus(Enum):
    """设备状态枚举"""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class MonitoringMetrics:
    """设备监控指标"""
    device_name: str
    ip: str
    status: DeviceStatus = DeviceStatus.UNKNOWN
    latency_ms: Optional[float] = None
    packet_loss: float = 0.0
    last_check: Optional[datetime] = None
    error_msg: Optional[str] = None
    # 历史延迟记录（用于趋势图）
    latency_history: List[float] = field(default_factory=list)
    # SNMP可选指标
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    uptime: Optional[str] = None


# 告警阈值配置
ALERT_THRESHOLDS = {
    "latency_warning": 100,    # 延迟告警阈值 (ms)
    "latency_critical": 500,   # 延迟严重阈值 (ms)
    "packet_loss_warning": 10, # 丢包告警阈值 (%)
    "packet_loss_critical": 50,# 丢包严重阈值 (%)
}


class StatusIndicator(Static):
    """状态指示器组件"""
    
    DEFAULT_CSS = """
    StatusIndicator {
        width: auto;
        height: 1;
    }
    """
    
    STATUS_ICONS = {
        DeviceStatus.UNKNOWN: ("⏳", "dim"),
        DeviceStatus.ONLINE: ("✅", "green"),
        DeviceStatus.OFFLINE: ("❌", "red"),
        DeviceStatus.WARNING: ("⚠️", "yellow"),
        DeviceStatus.ERROR: ("💥", "red"),
    }
    
    def __init__(self, status: DeviceStatus = DeviceStatus.UNKNOWN, **kwargs):
        super().__init__(**kwargs)
        self._status = status
    
    def update_status(self, status: DeviceStatus) -> None:
        self._status = status
        icon, color = self.STATUS_ICONS.get(status, ("❓", "dim"))
        self.update(f"[{color}]{icon}[/{color}]")


class MetricsPanel(Static):
    """指标汇总面板"""
    
    DEFAULT_CSS = """
    MetricsPanel {
        height: 5;
        border: round $primary-darken-2;
        padding: 0 1;
    }
    
    MetricsPanel > .metrics-row {
        height: 3;
    }
    
    MetricsPanel > .metrics-row > .metric-box {
        width: 1fr;
        height: 100%;
        content-align: center middle;
        padding: 0 1;
    }
    
    MetricsPanel > .metrics-row > .metric-box.online {
        background: $success-darken-2;
    }
    
    MetricsPanel > .metrics-row > .metric-box.offline {
        background: $error-darken-2;
    }
    
    MetricsPanel > .metrics-row > .metric-box.warning {
        background: $warning-darken-2;
    }
    
    MetricsPanel > .metrics-row > .metric-box.total {
        background: $surface-darken-2;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="metrics-row"):
            yield Static("📊 总计: 0", id="metric-total", classes="metric-box total")
            yield Static("✅ 在线: 0", id="metric-online", classes="metric-box online")
            yield Static("❌ 离线: 0", id="metric-offline", classes="metric-box offline")
            yield Static("⚠️ 告警: 0", id="metric-warning", classes="metric-box warning")
    
    def update_metrics(self, total: int, online: int, offline: int, warning: int) -> None:
        self.query_one("#metric-total", Static).update(f"📊 总计: {total}")
        self.query_one("#metric-online", Static).update(f"✅ 在线: {online}")
        self.query_one("#metric-offline", Static).update(f"❌ 离线: {offline}")
        self.query_one("#metric-warning", Static).update(f"⚠️ 告警: {warning}")


class MonitoringControlPanel(Static):
    """监控控制面板"""
    
    DEFAULT_CSS = """
    MonitoringControlPanel {
        height: 5;
        border: round $primary-darken-2;
        padding: 0 1;
    }
    
    MonitoringControlPanel > .control-row {
        height: 3;
        align: center middle;
    }
    
    MonitoringControlPanel > .control-row > Button {
        margin: 0 1;
    }
    
    MonitoringControlPanel > .control-row > Label {
        margin: 0 1;
        text-style: bold;
    }
    """
    
    class RefreshRequested(Message):
        """手动刷新请求"""
        pass
    
    class AutoRefreshToggled(Message):
        """自动刷新开关"""
        def __init__(self, enabled: bool) -> None:
            self.enabled = enabled
            super().__init__()
    
    class IntervalChanged(Message):
        """刷新间隔变更"""
        def __init__(self, seconds: int) -> None:
            self.seconds = seconds
            super().__init__()
    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="control-row"):
            yield Button("🔄 立即刷新", id="btn-refresh", variant="primary")
            yield Label("自动刷新:")
            yield Switch(id="switch-auto", value=True)
            yield Label("间隔(秒):")
            yield Select(
                [(str(i), i) for i in [3, 5, 10, 15, 30, 60]],
                value=5,
                id="select-interval",
                allow_blank=False,
            )
            yield Label("⏱️ 上次刷新: -", id="last-refresh-label")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh":
            self.post_message(self.RefreshRequested())
    
    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "switch-auto":
            self.post_message(self.AutoRefreshToggled(event.value))
    
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-interval":
            self.post_message(self.IntervalChanged(int(event.value)))
    
    def update_last_refresh(self, timestamp: datetime) -> None:
        label = self.query_one("#last-refresh-label", Label)
        label.update(f"⏱️ 上次刷新: {timestamp.strftime('%H:%M:%S')}")


class DeviceMonitorTable(Static):
    """设备监控表格"""
    
    DEFAULT_CSS = """
    DeviceMonitorTable {
        height: 1fr;
        border: round $primary-darken-2;
    }
    
    DeviceMonitorTable > .panel-header {
        height: 3;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    DeviceMonitorTable > DataTable {
        height: 1fr;
    }
    """
    
    class DeviceSelected(Message):
        """设备选中事件"""
        def __init__(self, device_name: str) -> None:
            self.device_name = device_name
            super().__init__()
    
    def compose(self) -> ComposeResult:
        yield Label("📡 设备状态监控", classes="panel-header")
        yield DataTable(id="monitor-table", cursor_type="row", zebra_stripes=True)
    
    def on_mount(self) -> None:
        table = self.query_one("#monitor-table", DataTable)
        table.add_columns(
            "状态", "设备名称", "IP地址", "延迟(ms)", 
            "丢包率", "上次检测", "备注"
        )
    
    def update_device(self, metrics: MonitoringMetrics) -> None:
        """更新单个设备状态"""
        table = self.query_one("#monitor-table", DataTable)
        
        # 状态图标
        status_map = {
            DeviceStatus.UNKNOWN: "⏳",
            DeviceStatus.ONLINE: "✅",
            DeviceStatus.OFFLINE: "❌",
            DeviceStatus.WARNING: "⚠️",
            DeviceStatus.ERROR: "💥",
        }
        status_icon = status_map.get(metrics.status, "❓")
        
        # 延迟显示（带颜色）
        if metrics.latency_ms is not None:
            if metrics.latency_ms < ALERT_THRESHOLDS["latency_warning"]:
                latency_str = f"[green]{metrics.latency_ms:.1f}[/green]"
            elif metrics.latency_ms < ALERT_THRESHOLDS["latency_critical"]:
                latency_str = f"[yellow]{metrics.latency_ms:.1f}[/yellow]"
            else:
                latency_str = f"[red]{metrics.latency_ms:.1f}[/red]"
        else:
            latency_str = "-"
        
        # 丢包率显示
        if metrics.packet_loss > ALERT_THRESHOLDS["packet_loss_critical"]:
            loss_str = f"[red]{metrics.packet_loss:.0f}%[/red]"
        elif metrics.packet_loss > ALERT_THRESHOLDS["packet_loss_warning"]:
            loss_str = f"[yellow]{metrics.packet_loss:.0f}%[/yellow]"
        else:
            loss_str = f"[green]{metrics.packet_loss:.0f}%[/green]"
        
        # 最后检测时间
        last_check = metrics.last_check.strftime("%H:%M:%S") if metrics.last_check else "-"
        
        # 备注信息
        note = metrics.error_msg or ""
        
        # 查找或添加行
        row_key = metrics.device_name
        from textual.widgets._data_table import RowKey
        rk = RowKey(row_key)

        if rk in table.rows:
            # 更新现有行
            col_keys = list(table.columns.keys())
            values = [status_icon, metrics.device_name, metrics.ip,
                      latency_str, loss_str, last_check, note]
            for ck, val in zip(col_keys, values):
                table.update_cell(rk, ck, val)
        else:
            # 添加新行
            table.add_row(
                status_icon,
                metrics.device_name,
                metrics.ip,
                latency_str,
                loss_str,
                last_check,
                note,
                key=row_key,
            )
    
    def clear_table(self) -> None:
        """清空表格"""
        table = self.query_one("#monitor-table", DataTable)
        table.clear()


class AlertLog(Static):
    """告警日志面板"""
    
    DEFAULT_CSS = """
    AlertLog {
        height: 10;
        border: round $warning-darken-2;
    }
    
    AlertLog > .panel-header {
        height: 3;
        padding: 0 1;
        background: $warning-darken-3;
        text-style: bold;
    }
    
    AlertLog > RichLog {
        height: 1fr;
        scrollbar-gutter: stable;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("🔔 告警日志", classes="panel-header")
        yield RichLog(id="alert-log", highlight=True, markup=True, wrap=True)
    
    def add_alert(self, level: str, device: str, message: str) -> None:
        """添加告警"""
        log = self.query_one("#alert-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        level_colors = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "critical": "bold red",
        }
        color = level_colors.get(level, "white")
        
        log.write(f"[dim]{timestamp}[/dim] [{color}]{level.upper()}[/{color}] [{device}] {message}")
    
    def clear_log(self) -> None:
        log = self.query_one("#alert-log", RichLog)
        log.clear()


class MonitoringScreen(Screen):
    """监控仪表板屏幕"""
    
    TITLE = "📊 监控仪表板"
    SUB_TITLE = "实时设备状态监控"
    
    BINDINGS = [
        Binding("h", "go_home", "返回主页", key_display="H"),
        Binding("r", "refresh", "刷新", key_display="R"),
        Binding("space", "toggle_auto_refresh", "切换自动刷新", key_display="Space"),
        Binding("escape", "go_back", "返回"),
    ]
    
    DEFAULT_CSS = """
    MonitoringScreen {
        layout: vertical;
    }
    
    MonitoringScreen > .screen-header {
        height: 3;
        background: $primary-darken-2;
        padding: 0 2;
        text-style: bold;
    }
    
    MonitoringScreen > .main-content {
        height: 1fr;
        padding: 1;
    }
    
    MonitoringScreen > .main-content > .top-panels {
        height: auto;
    }
    
    MonitoringScreen > .main-content > .monitor-section {
        height: 1fr;
    }
    
    MonitoringScreen > .main-content > .alert-section {
        height: 10;
    }
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._devices: List[Dict[str, Any]] = []
        self._metrics: Dict[str, MonitoringMetrics] = {}
        self._auto_refresh: bool = True
        self._refresh_interval: int = 5
        self._refresh_timer: Optional[Timer] = None
        self._is_refreshing: bool = False
    
    def compose(self) -> ComposeResult:
        yield Label("📊 监控仪表板 - 设备实时状态监控", classes="screen-header")
        
        with Vertical(classes="main-content"):
            with Horizontal(classes="top-panels"):
                yield MetricsPanel(id="metrics-panel")
                yield MonitoringControlPanel(id="control-panel")
            
            yield DeviceMonitorTable(id="device-table-panel", classes="monitor-section")
            yield AlertLog(id="alert-log-panel", classes="alert-section")
    
    def on_mount(self) -> None:
        """屏幕挂载时初始化"""
        self._load_devices()
        # 启动自动刷新定时器
        if self._auto_refresh:
            self._start_refresh_timer()
        # 初始刷新
        self._trigger_refresh()
    
    def on_unmount(self) -> None:
        """屏幕卸载时停止定时器"""
        self._stop_refresh_timer()
    
    def _load_devices(self) -> None:
        """加载设备清单"""
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory
            
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
            
            if inventory:
                for device in inventory:
                    self._devices.append({
                        "name": device.name,
                        "ip": device.ip,
                        "vendor": device.vendor,
                        "group": device.group,
                    })
                    # 初始化指标
                    self._metrics[device.name] = MonitoringMetrics(
                        device_name=device.name,
                        ip=device.ip,
                    )
            else:
                self._load_demo_devices()
        except Exception:
            self._load_demo_devices()
    
    def _load_demo_devices(self) -> None:
        """加载演示设备数据"""
        demo_devices = [
            {"name": "SW-CORE-01", "ip": "192.168.1.10", "vendor": "cisco_ios", "group": "core"},
            {"name": "SW-DIST-01", "ip": "192.168.1.20", "vendor": "cisco_ios", "group": "distribution"},
            {"name": "SW-DIST-02", "ip": "192.168.1.21", "vendor": "cisco_ios", "group": "distribution"},
            {"name": "RT-EDGE-01", "ip": "192.168.1.1", "vendor": "cisco_ios", "group": "edge"},
            {"name": "FW-MAIN-01", "ip": "192.168.1.254", "vendor": "cisco_ios", "group": "security"},
            {"name": "HW-SW-01", "ip": "192.168.2.10", "vendor": "huawei_vrp", "group": "branch"},
        ]
        
        for dev in demo_devices:
            self._devices.append(dev)
            self._metrics[dev["name"]] = MonitoringMetrics(
                device_name=dev["name"],
                ip=dev["ip"],
            )
        
        # 添加告警日志提示
        alert_log = self.query_one("#alert-log-panel", AlertLog)
        alert_log.add_alert("info", "系统", "正在使用演示设备数据（未找到设备清单文件）")
    
    def _start_refresh_timer(self) -> None:
        """启动自动刷新定时器"""
        if self._refresh_timer is None:
            self._refresh_timer = self.set_interval(
                self._refresh_interval,
                self._trigger_refresh,
            )
    
    def _stop_refresh_timer(self) -> None:
        """停止自动刷新定时器"""
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
            self._refresh_timer = None
    
    def _restart_refresh_timer(self) -> None:
        """重启定时器（间隔变更时）"""
        self._stop_refresh_timer()
        if self._auto_refresh:
            self._start_refresh_timer()
    
    def _trigger_refresh(self) -> None:
        """触发刷新"""
        if not self._is_refreshing:
            self._refresh_all_devices()
    
    @work(exclusive=True, thread=True)
    def _refresh_all_devices(self) -> None:
        """刷新所有设备状态（后台线程）"""
        self._is_refreshing = True
        
        try:
            # 并发ping所有设备
            results = self._ping_all_devices()
            
            # 统计
            total = len(self._devices)
            online = sum(1 for r in results.values() if r.status == DeviceStatus.ONLINE)
            offline = sum(1 for r in results.values() if r.status == DeviceStatus.OFFLINE)
            warning = sum(1 for r in results.values() if r.status == DeviceStatus.WARNING)
            
            # 更新UI（通过消息队列）
            self.app.call_from_thread(self._update_ui, results, total, online, offline, warning)
            
        finally:
            self._is_refreshing = False
    
    def _ping_all_devices(self) -> Dict[str, MonitoringMetrics]:
        """并发ping所有设备"""
        import concurrent.futures
        
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_device = {
                executor.submit(self._ping_device, dev): dev
                for dev in self._devices
            }
            
            for future in concurrent.futures.as_completed(future_to_device):
                dev = future_to_device[future]
                try:
                    metrics = future.result()
                    results[dev["name"]] = metrics
                except Exception as e:
                    results[dev["name"]] = MonitoringMetrics(
                        device_name=dev["name"],
                        ip=dev["ip"],
                        status=DeviceStatus.ERROR,
                        error_msg=str(e),
                        last_check=datetime.now(),
                    )
        
        return results
    
    def _ping_device(self, device: Dict[str, Any]) -> MonitoringMetrics:
        """Ping单个设备"""
        ip = device["ip"]
        name = device["name"]
        
        # 构建ping命令
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "3", "-w", "1000", ip]
        else:
            cmd = ["ping", "-c", "3", "-W", "1", ip]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            output = result.stdout
            
            # 解析ping结果
            latency_ms = None
            packet_loss = 100.0
            
            if platform.system().lower() == "windows":
                # Windows: Average = XXms
                avg_match = re.search(r'Average\s*=\s*(\d+)ms', output)
                if avg_match:
                    latency_ms = float(avg_match.group(1))
                # Windows: Lost = X (XX% loss)
                loss_match = re.search(r'\((\d+)%\s*(?:loss|丢失)\)', output)
                if loss_match:
                    packet_loss = float(loss_match.group(1))
            else:
                # Linux/Mac: rtt min/avg/max/mdev = X/Y/Z/W ms
                rtt_match = re.search(r'rtt\s+.+\s*=\s*[\d.]+/([\d.]+)/', output)
                if rtt_match:
                    latency_ms = float(rtt_match.group(1))
                # Linux: X% packet loss
                loss_match = re.search(r'(\d+)%\s*packet\s*loss', output)
                if loss_match:
                    packet_loss = float(loss_match.group(1))
            
            # 判断状态
            if packet_loss >= 100:
                status = DeviceStatus.OFFLINE
            elif packet_loss > ALERT_THRESHOLDS["packet_loss_warning"]:
                status = DeviceStatus.WARNING
            elif latency_ms and latency_ms > ALERT_THRESHOLDS["latency_warning"]:
                status = DeviceStatus.WARNING
            else:
                status = DeviceStatus.ONLINE
            
            # 更新历史记录
            history = self._metrics.get(name, MonitoringMetrics(name, ip)).latency_history[-19:] if name in self._metrics else []
            if latency_ms is not None:
                history.append(latency_ms)
            
            return MonitoringMetrics(
                device_name=name,
                ip=ip,
                status=status,
                latency_ms=latency_ms,
                packet_loss=packet_loss,
                last_check=datetime.now(),
                latency_history=history,
            )
            
        except subprocess.TimeoutExpired:
            return MonitoringMetrics(
                device_name=name,
                ip=ip,
                status=DeviceStatus.OFFLINE,
                packet_loss=100.0,
                last_check=datetime.now(),
                error_msg="ping超时",
            )
        except Exception as e:
            return MonitoringMetrics(
                device_name=name,
                ip=ip,
                status=DeviceStatus.ERROR,
                last_check=datetime.now(),
                error_msg=str(e),
            )
    
    def _update_ui(
        self,
        results: Dict[str, MonitoringMetrics],
        total: int,
        online: int,
        offline: int,
        warning: int,
    ) -> None:
        """更新UI（主线程）"""
        # 更新汇总面板
        metrics_panel = self.query_one("#metrics-panel", MetricsPanel)
        metrics_panel.update_metrics(total, online, offline, warning)
        
        # 更新设备表格
        table_panel = self.query_one("#device-table-panel", DeviceMonitorTable)
        for name, metrics in results.items():
            # 检查状态变化并记录告警
            old_metrics = self._metrics.get(name)
            if old_metrics and old_metrics.status != metrics.status:
                self._log_status_change(old_metrics, metrics)
            
            table_panel.update_device(metrics)
            self._metrics[name] = metrics
        
        # 更新刷新时间
        control_panel = self.query_one("#control-panel", MonitoringControlPanel)
        control_panel.update_last_refresh(datetime.now())
    
    def _log_status_change(self, old: MonitoringMetrics, new: MonitoringMetrics) -> None:
        """记录状态变化告警"""
        alert_log = self.query_one("#alert-log-panel", AlertLog)
        
        if new.status == DeviceStatus.OFFLINE and old.status == DeviceStatus.ONLINE:
            alert_log.add_alert("error", new.device_name, f"设备离线 ({new.ip})")
        elif new.status == DeviceStatus.ONLINE and old.status == DeviceStatus.OFFLINE:
            alert_log.add_alert("info", new.device_name, f"设备恢复在线 ({new.ip})")
        elif new.status == DeviceStatus.WARNING:
            if new.latency_ms and new.latency_ms > ALERT_THRESHOLDS["latency_warning"]:
                alert_log.add_alert("warning", new.device_name, f"延迟过高: {new.latency_ms:.1f}ms")
            if new.packet_loss > ALERT_THRESHOLDS["packet_loss_warning"]:
                alert_log.add_alert("warning", new.device_name, f"丢包率异常: {new.packet_loss:.0f}%")
    
    # === 消息处理 ===
    
    def on_monitoring_control_panel_refresh_requested(
        self, event: MonitoringControlPanel.RefreshRequested
    ) -> None:
        """处理手动刷新请求"""
        self._trigger_refresh()
    
    def on_monitoring_control_panel_auto_refresh_toggled(
        self, event: MonitoringControlPanel.AutoRefreshToggled
    ) -> None:
        """处理自动刷新开关"""
        self._auto_refresh = event.enabled
        if event.enabled:
            self._start_refresh_timer()
            self.notify("自动刷新已开启", severity="information")
        else:
            self._stop_refresh_timer()
            self.notify("自动刷新已关闭", severity="information")
    
    def on_monitoring_control_panel_interval_changed(
        self, event: MonitoringControlPanel.IntervalChanged
    ) -> None:
        """处理刷新间隔变更"""
        self._refresh_interval = event.seconds
        self._restart_refresh_timer()
        self.notify(f"刷新间隔已设置为 {event.seconds} 秒", severity="information")
    
    # === 快捷键动作 ===
    
    def action_go_home(self) -> None:
        """返回主页"""
        self.app.pop_screen()
    
    def action_go_back(self) -> None:
        """返回上一屏幕"""
        self.app.pop_screen()
    
    def action_refresh(self) -> None:
        """手动刷新"""
        self._trigger_refresh()
    
    def action_toggle_auto_refresh(self) -> None:
        """切换自动刷新"""
        switch = self.query_one("#switch-auto", Switch)
        switch.toggle()
