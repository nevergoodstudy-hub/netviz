"""
TUI屏幕模块

包含所有应用界面:
- MainScreen: 主界面（插件列表、分类导航）
- PluginScreen: 插件执行界面（参数表单、执行控制）
- ResultScreen: 结果展示界面（实时数据表、导出）
- SettingsScreen: 设置界面（主题、偏好配置）
- DeviceScreen: 设备管理界面（设备清单、快捷命令）
- ConfigScreen: 配置中心界面（模板管理、批量推送）
- DiagnosticsScreen: 诊断工具界面（多设备并发命令）
- MonitoringScreen: 监控仪表板界面（实时状态、Ping监控）
- ReportsScreen: 报表中心界面（PDF/Excel导出）
- TopologyScreen: 网络拓扑可视化界面（ASCII渲染）
- ComplianceScreen: 合规检查界面（配置审计）
- AuditScreen: 变更审计界面（操作日志）
"""

# 延迟导入避免循环引用
__all__ = [
    "MainScreen",
    "PluginScreen", 
    "ResultScreen",
    "SettingsScreen",
    "DeviceScreen",
    "ConfigScreen",
    "DiagnosticsScreen",
    "MonitoringScreen",
    "ReportsScreen",
    "TopologyScreen",
    "ComplianceScreen",
    "AuditScreen",
]

def __getattr__(name):
    if name == "MainScreen":
        from .main_screen import MainScreen
        return MainScreen
    if name == "PluginScreen":
        from .plugin_screen import PluginScreen
        return PluginScreen
    if name == "ResultScreen":
        from .result_screen import ResultScreen
        return ResultScreen
    if name == "SettingsScreen":
        from .settings_screen import SettingsScreen
        return SettingsScreen
    if name == "DeviceScreen":
        from .device_screen import DeviceScreen
        return DeviceScreen
    if name == "ConfigScreen":
        from .config_screen import ConfigScreen
        return ConfigScreen
    if name == "DiagnosticsScreen":
        from .diagnostics_screen import DiagnosticsScreen
        return DiagnosticsScreen
    if name == "MonitoringScreen":
        from .monitoring_screen import MonitoringScreen
        return MonitoringScreen
    if name == "ReportsScreen":
        from .reports_screen import ReportsScreen
        return ReportsScreen
    if name == "TopologyScreen":
        from .topology_screen import TopologyScreen
        return TopologyScreen
    if name == "ComplianceScreen":
        from .compliance_screen import ComplianceScreen
        return ComplianceScreen
    if name == "AuditScreen":
        from .audit_screen import AuditScreen
        return AuditScreen
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
