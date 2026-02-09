"""
诊断插件测试模块

测试覆盖:
- PingPlugin
- TraceroutePlugin
- DnsLookupPlugin
- PortScanPlugin
- ArpScanPlugin
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess


class TestPingPlugin:
    """测试 Ping 插件"""
    
    def test_ping_plugin_import(self):
        """测试导入"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        
        assert PingPlugin is not None
    
    def test_ping_plugin_creation(self):
        """测试创建"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        
        plugin = PingPlugin()
        assert plugin is not None
    
    def test_ping_plugin_name(self):
        """测试插件名称"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        
        plugin = PingPlugin()
        assert plugin.name is not None
        assert len(plugin.name) > 0
    
    def test_ping_plugin_category(self):
        """测试插件类别"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        from netops_toolkit.plugins import PluginCategory
        
        plugin = PingPlugin()
        assert plugin.category == PluginCategory.DIAGNOSTICS
    
    def test_ping_plugin_description(self):
        """测试插件描述"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        
        plugin = PingPlugin()
        assert plugin.description is not None
        assert len(plugin.description) > 0
    
    def test_ping_plugin_required_params(self):
        """测试必需参数"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        
        plugin = PingPlugin()
        params = plugin.get_required_params()
        
        assert isinstance(params, list)
        # 应该有 targets 参数
        param_names = [p.name for p in params]
        assert "targets" in param_names
    
    def test_ping_plugin_validate_dependencies(self):
        """测试依赖验证"""
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
        
        plugin = PingPlugin()
        # 在大多数系统上 ping 应该可用
        result = plugin.validate_dependencies()
        assert isinstance(result, bool)


class TestTraceroutePlugin:
    """测试 Traceroute 插件"""
    
    def test_traceroute_plugin_import(self):
        """测试导入"""
        from netops_toolkit.plugins.diagnostics.traceroute import TraceroutePlugin
        
        assert TraceroutePlugin is not None
    
    def test_traceroute_plugin_creation(self):
        """测试创建"""
        from netops_toolkit.plugins.diagnostics.traceroute import TraceroutePlugin
        
        plugin = TraceroutePlugin()
        assert plugin is not None
    
    def test_traceroute_plugin_category(self):
        """测试插件类别"""
        from netops_toolkit.plugins.diagnostics.traceroute import TraceroutePlugin
        from netops_toolkit.plugins import PluginCategory
        
        plugin = TraceroutePlugin()
        assert plugin.category == PluginCategory.DIAGNOSTICS
    
    def test_traceroute_plugin_required_params(self):
        """测试必需参数"""
        from netops_toolkit.plugins.diagnostics.traceroute import TraceroutePlugin
        
        plugin = TraceroutePlugin()
        params = plugin.get_required_params()
        
        assert isinstance(params, list)
        param_names = [p.name for p in params]
        assert "target" in param_names


class TestDnsLookupPlugin:
    """测试 DNS 查询插件"""
    
    def test_dns_plugin_import(self):
        """测试导入"""
        from netops_toolkit.plugins.diagnostics.dns_lookup import DNSLookupPlugin
        
        assert DNSLookupPlugin is not None
    
    def test_dns_plugin_creation(self):
        """测试创建"""
        from netops_toolkit.plugins.diagnostics.dns_lookup import DNSLookupPlugin
        
        plugin = DNSLookupPlugin()
        assert plugin is not None
    
    def test_dns_plugin_category(self):
        """测试插件类别"""
        from netops_toolkit.plugins.diagnostics.dns_lookup import DNSLookupPlugin
        from netops_toolkit.plugins import PluginCategory
        
        plugin = DNSLookupPlugin()
        assert plugin.category == PluginCategory.DIAGNOSTICS
    
    def test_dns_plugin_required_params(self):
        """测试必需参数"""
        from netops_toolkit.plugins.diagnostics.dns_lookup import DNSLookupPlugin
        
        plugin = DNSLookupPlugin()
        params = plugin.get_required_params()
        
        assert isinstance(params, list)
        param_names = [p.name for p in params]
        assert "domain" in param_names or "hostname" in param_names or "target" in param_names


class TestPortScanPlugin:
    """测试端口扫描插件"""
    
    def test_port_scan_plugin_import(self):
        """测试导入"""
        from netops_toolkit.plugins.scanning.port_scan import PortScanPlugin
        
        assert PortScanPlugin is not None
    
    def test_port_scan_plugin_creation(self):
        """测试创建"""
        from netops_toolkit.plugins.scanning.port_scan import PortScanPlugin
        
        plugin = PortScanPlugin()
        assert plugin is not None
    
    def test_port_scan_plugin_category(self):
        """测试插件类别"""
        from netops_toolkit.plugins.scanning.port_scan import PortScanPlugin
        from netops_toolkit.plugins import PluginCategory
        
        plugin = PortScanPlugin()
        assert plugin.category == PluginCategory.SCANNING
    
    def test_port_scan_plugin_required_params(self):
        """测试必需参数"""
        from netops_toolkit.plugins.scanning.port_scan import PortScanPlugin
        
        plugin = PortScanPlugin()
        params = plugin.get_required_params()
        
        assert isinstance(params, list)
        param_names = [p.name for p in params]
        assert "target" in param_names


class TestArpScanPlugin:
    """测试 ARP 扫描插件"""
    
    def test_arp_scan_plugin_import(self):
        """测试导入"""
        from netops_toolkit.plugins.scanning.arp_scan import ARPScanPlugin
        
        assert ARPScanPlugin is not None
    
    def test_arp_scan_plugin_creation(self):
        """测试创建"""
        from netops_toolkit.plugins.scanning.arp_scan import ARPScanPlugin
        
        plugin = ARPScanPlugin()
        assert plugin is not None
    
    def test_arp_scan_plugin_name(self):
        """测试插件名称"""
        from netops_toolkit.plugins.scanning.arp_scan import ARPScanPlugin
        
        plugin = ARPScanPlugin()
        assert plugin.name == "arp_scan"
    
    def test_arp_scan_plugin_required_params(self):
        """测试必需参数"""
        from netops_toolkit.plugins.scanning.arp_scan import ARPScanPlugin
        
        plugin = ARPScanPlugin()
        params = plugin.get_required_params()
        
        assert isinstance(params, list)


class TestPluginBase:
    """测试插件基础类"""
    
    def test_plugin_import(self):
        """测试插件类导入"""
        from netops_toolkit.plugins import Plugin
        
        assert Plugin is not None
    
    def test_plugin_result_creation(self):
        """测试插件结果创建"""
        from netops_toolkit.plugins import PluginResult, ResultStatus
        from datetime import datetime
        
        result = PluginResult(
            status=ResultStatus.SUCCESS,
            message="Test message",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )
        
        assert result.status == ResultStatus.SUCCESS
        assert result.message == "Test message"
    
    def test_param_spec_creation(self):
        """测试参数规格创建"""
        from netops_toolkit.plugins import ParamSpec
        
        param = ParamSpec(
            name="target",
            param_type=str,
            description="Target host",
            required=True,
        )
        
        assert param.name == "target"
        assert param.param_type == str
        assert param.required is True


class TestPluginCategory:
    """测试插件类别"""
    
    def test_category_values(self):
        """测试类别值"""
        from netops_toolkit.plugins import PluginCategory
        
        # 应该有诊断和扫描类别
        assert hasattr(PluginCategory, 'DIAGNOSTICS')
        assert hasattr(PluginCategory, 'SCANNING')


class TestResultStatus:
    """测试结果状态"""
    
    def test_status_values(self):
        """测试状态值"""
        from netops_toolkit.plugins import ResultStatus
        
        # 应该有成功和错误状态
        assert hasattr(ResultStatus, 'SUCCESS')
        assert hasattr(ResultStatus, 'ERROR')
