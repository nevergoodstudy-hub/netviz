"""
CLI 模块测试

测试覆盖:
- CLI 应用创建
- 菜单构建
- 版本信息
"""

import pytest
from unittest.mock import patch, MagicMock

# 尝试导入 typer 测试工具
try:
    from typer.testing import CliRunner
    TYPER_AVAILABLE = True
except ImportError:
    TYPER_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not TYPER_AVAILABLE,
    reason="Typer not available"
)


class TestCLIApp:
    """测试 CLI 应用"""
    
    def test_cli_app_exists(self):
        """测试 CLI 应用存在"""
        from netops_toolkit.cli import app
        
        assert app is not None
    
    def test_cli_app_name(self):
        """测试 CLI 应用名称"""
        from netops_toolkit.cli import app
        
        assert app.info.name == "netops"
    
    def test_cli_app_help(self):
        """测试 CLI 应用帮助信息"""
        from netops_toolkit.cli import app
        
        assert "NetOps Toolkit" in app.info.help


class TestMenuBuilding:
    """测试菜单构建"""
    
    def test_build_main_menu(self):
        """测试构建主菜单"""
        from netops_toolkit.cli import build_main_menu
        
        menu = build_main_menu()
        
        assert isinstance(menu, list)
        assert len(menu) > 0
    
    @patch('netops_toolkit.cli.get_plugins_by_category')
    def test_build_main_menu_with_plugins(self, mock_get_plugins):
        """测试有插件时构建主菜单"""
        from netops_toolkit.cli import build_main_menu
        from netops_toolkit.plugins.base import PluginCategory
        
        # 模拟返回空插件
        mock_get_plugins.return_value = {}
        
        menu = build_main_menu()
        
        assert isinstance(menu, list)


class TestUtilityFunctions:
    """测试工具函数"""
    
    def test_show_about(self, capsys):
        """测试显示关于信息"""
        from netops_toolkit.cli import show_about
        
        # 应该不抛出异常
        show_about()
    
    @patch('netops_toolkit.cli.get_config')
    def test_show_settings(self, mock_config):
        """测试显示设置信息"""
        from netops_toolkit.cli import show_settings
        
        # 模拟配置
        mock_config.return_value.get = MagicMock(return_value="test_value")
        
        # 应该不抛出异常
        show_settings()


class TestPluginIntegration:
    """测试插件集成"""
    
    def test_get_plugins_by_category(self):
        """测试按分类获取插件"""
        from netops_toolkit.cli import get_plugins_by_category
        
        result = get_plugins_by_category()
        
        assert isinstance(result, dict)
    
    @patch('netops_toolkit.cli.get_plugins_by_category')
    def test_build_plugin_menu(self, mock_get_plugins):
        """测试构建插件菜单"""
        from netops_toolkit.cli import build_plugin_menu
        from netops_toolkit.plugins.base import PluginCategory
        
        # 模拟返回空插件
        mock_get_plugins.return_value = {PluginCategory.UTILS: []}
        
        menu = build_plugin_menu(PluginCategory.UTILS)
        
        assert isinstance(menu, list)
        # 至少有返回选项
        assert len(menu) >= 1


class TestAppInitialization:
    """测试应用初始化"""
    
    @patch('netops_toolkit.cli.get_config')
    @patch('netops_toolkit.cli.setup_logging')
    def test_init_app(self, mock_setup_logging, mock_get_config):
        """测试初始化应用"""
        from netops_toolkit.cli import init_app
        
        # 模拟配置
        mock_get_config.return_value.get = MagicMock(return_value="INFO")
        
        # 应该不抛出异常
        init_app()
        
        # 应该调用日志设置
        mock_setup_logging.assert_called_once()
    
    @patch('netops_toolkit.cli.get_config')
    def test_show_banner(self, mock_get_config):
        """测试显示横幅"""
        from netops_toolkit.cli import show_banner
        
        # 模拟配置允许显示横幅
        mock_get_config.return_value.get = MagicMock(return_value=True)
        
        # 应该不抛出异常
        show_banner()


class TestVersionInfo:
    """测试版本信息"""
    
    def test_version_exists(self):
        """测试版本号存在"""
        from netops_toolkit import __version__
        
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0
    
    def test_version_format(self):
        """测试版本号格式"""
        from netops_toolkit import __version__
        
        # 版本号应该包含数字和点
        parts = __version__.split('.')
        assert len(parts) >= 2
