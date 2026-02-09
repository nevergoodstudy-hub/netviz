"""
TUI 屏幕测试模块

测试覆盖:
- 主屏幕
- 设备屏幕
- 配置屏幕
- 诊断屏幕
"""

import pytest

# 尝试导入 Textual 测试工具
try:
    from textual.testing import AppTest
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not TEXTUAL_AVAILABLE,
    reason="Textual testing not available"
)


class TestMainScreen:
    """测试主屏幕"""
    
    def test_main_screen_import(self):
        """测试主屏幕导入"""
        from netops_toolkit.tui.screens.main_screen import MainScreen
        
        assert MainScreen is not None
    
    def test_main_screen_creation(self):
        """测试主屏幕创建"""
        from netops_toolkit.tui.screens.main_screen import MainScreen
        
        screen = MainScreen()
        assert screen is not None


class TestDeviceScreen:
    """测试设备屏幕"""
    
    def test_device_screen_import(self):
        """测试设备屏幕导入"""
        from netops_toolkit.tui.screens.device_screen import DeviceScreen
        
        assert DeviceScreen is not None
    
    def test_device_screen_creation(self):
        """测试设备屏幕创建"""
        from netops_toolkit.tui.screens.device_screen import DeviceScreen
        
        screen = DeviceScreen()
        assert screen is not None


class TestConfigScreen:
    """测试配置屏幕"""
    
    def test_config_screen_import(self):
        """测试配置屏幕导入"""
        from netops_toolkit.tui.screens.config_screen import ConfigScreen
        
        assert ConfigScreen is not None
    
    def test_config_screen_creation(self):
        """测试配置屏幕创建"""
        from netops_toolkit.tui.screens.config_screen import ConfigScreen
        
        screen = ConfigScreen()
        assert screen is not None


class TestDiagnosticsScreen:
    """测试诊断屏幕"""
    
    def test_diagnostics_screen_import(self):
        """测试诊断屏幕导入"""
        from netops_toolkit.tui.screens.diagnostics_screen import DiagnosticsScreen
        
        assert DiagnosticsScreen is not None
    
    def test_diagnostics_screen_creation(self):
        """测试诊断屏幕创建"""
        from netops_toolkit.tui.screens.diagnostics_screen import DiagnosticsScreen
        
        screen = DiagnosticsScreen()
        assert screen is not None


class TestMonitoringScreen:
    """测试监控屏幕"""
    
    def test_monitoring_screen_import(self):
        """测试监控屏幕导入"""
        from netops_toolkit.tui.screens.monitoring_screen import MonitoringScreen
        
        assert MonitoringScreen is not None
    
    def test_monitoring_screen_creation(self):
        """测试监控屏幕创建"""
        from netops_toolkit.tui.screens.monitoring_screen import MonitoringScreen
        
        screen = MonitoringScreen()
        assert screen is not None


class TestComplianceScreen:
    """测试合规屏幕"""
    
    def test_compliance_screen_import(self):
        """测试合规屏幕导入"""
        from netops_toolkit.tui.screens.compliance_screen import ComplianceScreen
        
        assert ComplianceScreen is not None
    
    def test_compliance_screen_creation(self):
        """测试合规屏幕创建"""
        from netops_toolkit.tui.screens.compliance_screen import ComplianceScreen
        
        screen = ComplianceScreen()
        assert screen is not None


class TestAuditScreen:
    """测试审计屏幕"""
    
    def test_audit_screen_import(self):
        """测试审计屏幕导入"""
        from netops_toolkit.tui.screens.audit_screen import AuditScreen
        
        assert AuditScreen is not None
    
    def test_audit_screen_creation(self):
        """测试审计屏幕创建"""
        from netops_toolkit.tui.screens.audit_screen import AuditScreen
        
        screen = AuditScreen()
        assert screen is not None


class TestTopologyScreen:
    """测试拓扑屏幕"""
    
    def test_topology_screen_import(self):
        """测试拓扑屏幕导入"""
        from netops_toolkit.tui.screens.topology_screen import TopologyScreen
        
        assert TopologyScreen is not None
    
    def test_topology_screen_creation(self):
        """测试拓扑屏幕创建"""
        from netops_toolkit.tui.screens.topology_screen import TopologyScreen
        
        screen = TopologyScreen()
        assert screen is not None


class TestReportsScreen:
    """测试报表屏幕"""
    
    def test_reports_screen_import(self):
        """测试报表屏幕导入"""
        from netops_toolkit.tui.screens.reports_screen import ReportsScreen
        
        assert ReportsScreen is not None
    
    def test_reports_screen_creation(self):
        """测试报表屏幕创建"""
        from netops_toolkit.tui.screens.reports_screen import ReportsScreen
        
        screen = ReportsScreen()
        assert screen is not None
