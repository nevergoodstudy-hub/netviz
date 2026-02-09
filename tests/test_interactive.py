"""
Interactive 模块测试

测试覆盖:
- ParameterCollector 类
- 各种诊断函数
- 辅助函数
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


class TestParameterCollector:
    """测试参数收集器 (从 ui.menu 模块)"""
    
    def test_parameter_collector_import(self):
        """测试导入"""
        from netops_toolkit.ui.menu import ParameterCollector
        
        assert ParameterCollector is not None
    
    def test_parameter_collector_creation(self):
        """测试创建"""
        from netops_toolkit.ui.menu import ParameterCollector
        from rich.console import Console
        
        console = Console(file=StringIO())
        collector = ParameterCollector(console)
        assert collector is not None
    
    def test_parameter_collector_with_console(self):
        """测试带控制台的收集器"""
        from netops_toolkit.ui.menu import ParameterCollector
        from rich.console import Console
        
        console = Console(file=StringIO())
        collector = ParameterCollector(console)
        assert collector.console is console


class TestInteractiveFunctions:
    """测试 interactive 模块中的函数"""
    
    def test_run_ping_import(self):
        """测试 run_ping 导入"""
        from netops_toolkit.interactive import run_ping
        
        assert callable(run_ping)
    
    def test_run_traceroute_import(self):
        """测试 run_traceroute 导入"""
        from netops_toolkit.interactive import run_traceroute
        
        assert callable(run_traceroute)
    
    def test_run_dns_import(self):
        """测试 run_dns 导入"""
        from netops_toolkit.interactive import run_dns
        
        assert callable(run_dns)
    
    def test_run_port_scan_import(self):
        """测试 run_port_scan 导入"""
        from netops_toolkit.interactive import run_port_scan
        
        assert callable(run_port_scan)
    
    def test_run_arp_scan_import(self):
        """测试 run_arp_scan 导入"""
        from netops_toolkit.interactive import run_arp_scan
        
        assert callable(run_arp_scan)


class TestPlugins:
    """测试插件基础类"""
    
    def test_plugin_category_import(self):
        """测试插件类别导入"""
        from netops_toolkit.plugins import PluginCategory
        
        assert PluginCategory is not None
    
    def test_result_status_import(self):
        """测试结果状态导入"""
        from netops_toolkit.plugins import ResultStatus
        
        assert ResultStatus is not None
    
    def test_plugin_result_import(self):
        """测试插件结果导入"""
        from netops_toolkit.plugins import PluginResult
        
        assert PluginResult is not None
    
    def test_param_spec_import(self):
        """测试参数规格导入"""
        from netops_toolkit.plugins import ParamSpec
        
        assert ParamSpec is not None


class TestMenuSystem:
    """测试菜单系统"""
    
    def test_menu_import(self):
        """测试菜单导入"""
        from netops_toolkit.ui.menu import Menu
        
        assert Menu is not None
    
    def test_menu_item_import(self):
        """测试菜单项导入"""
        from netops_toolkit.ui.menu import MenuItem
        
        assert MenuItem is not None
    
    def test_menu_system_import(self):
        """测试菜单系统导入"""
        from netops_toolkit.ui.menu import MenuSystem
        
        assert MenuSystem is not None
    
    def test_menu_creation(self):
        """测试菜单创建"""
        from netops_toolkit.ui.menu import Menu, MenuItem
        
        menu = Menu(
            title="Test Menu",
            items=[
                MenuItem(key="1", label="Option 1", action=lambda: None),
                MenuItem(key="2", label="Option 2", action=lambda: None),
            ]
        )
        
        assert menu.title == "Test Menu"
        assert len(menu.items) == 2


class TestUITheme:
    """测试 UI 主题"""
    
    def test_theme_import(self):
        """测试主题导入"""
        from netops_toolkit.ui.theme import NetOpsTheme
        
        assert NetOpsTheme is not None
    
    def test_console_import(self):
        """测试控制台导入"""
        from netops_toolkit.ui.theme import console
        
        assert console is not None


class TestInteractiveModule:
    """测试 interactive 模块整体功能"""
    
    def test_module_import(self):
        """测试模块导入"""
        import netops_toolkit.interactive
        
        assert netops_toolkit.interactive is not None
    
    def test_collector_variable(self):
        """测试模块级收集器"""
        from netops_toolkit.interactive import collector
        
        assert collector is not None
