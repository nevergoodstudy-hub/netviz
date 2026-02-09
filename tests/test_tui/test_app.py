"""
TUI 应用测试模块

测试覆盖:
- NetOpsApp 应用类
- 快捷键绑定
- 主题切换
- 屏幕导航
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


class TestNetOpsAppBasic:
    """测试 NetOpsApp 基本功能"""
    
    @pytest.fixture
    def app(self):
        """创建应用实例"""
        from netops_toolkit.tui.app import NetOpsApp
        return NetOpsApp()
    
    def test_app_creation(self, app):
        """测试应用创建"""
        assert app is not None
        assert app.TITLE == "NetOps Toolkit"
    
    def test_app_has_bindings(self, app):
        """测试应用有快捷键绑定"""
        assert len(app.BINDINGS) > 0
    
    def test_app_has_css_path(self, app):
        """测试应用有 CSS 路径"""
        assert len(app.CSS_PATH) > 0


@pytest.mark.asyncio
class TestNetOpsAppAsync:
    """测试 NetOpsApp 异步功能"""
    
    async def test_app_startup(self):
        """测试应用启动"""
        from netops_toolkit.tui.app import NetOpsApp
        
        app = NetOpsApp()
        async with app.run_test() as pilot:
            # 应用应该已启动
            assert app.is_running
    
    async def test_app_quit(self):
        """测试应用退出"""
        from netops_toolkit.tui.app import NetOpsApp
        
        app = NetOpsApp()
        async with app.run_test() as pilot:
            # 按 q 退出
            await pilot.press("q")
            # 应用应该退出
    
    async def test_theme_toggle(self):
        """测试主题切换"""
        from netops_toolkit.tui.app import NetOpsApp
        
        app = NetOpsApp()
        async with app.run_test() as pilot:
            initial_theme = app.theme
            
            # 按 t 切换主题
            await pilot.press("t")
            
            # 主题应该已更改
            assert app.theme != initial_theme


class TestAppBindings:
    """测试应用快捷键"""
    
    def test_quit_binding_exists(self):
        """测试退出快捷键存在"""
        from netops_toolkit.tui.app import NetOpsApp
        
        app = NetOpsApp()
        binding_keys = [b.key for b in app.BINDINGS]
        
        assert "q" in binding_keys
        assert "ctrl+q" in binding_keys
    
    def test_navigation_bindings_exist(self):
        """测试导航快捷键存在"""
        from netops_toolkit.tui.app import NetOpsApp
        
        app = NetOpsApp()
        binding_keys = [b.key for b in app.BINDINGS]
        
        assert "h" in binding_keys  # 主页
        assert "d" in binding_keys  # 设备管理
        assert "c" in binding_keys  # 配置中心
        assert "x" in binding_keys  # 诊断工具
    
    def test_theme_binding_exists(self):
        """测试主题切换快捷键存在"""
        from netops_toolkit.tui.app import NetOpsApp
        
        app = NetOpsApp()
        binding_keys = [b.key for b in app.BINDINGS]
        
        assert "t" in binding_keys


class TestAppConfiguration:
    """测试应用配置"""
    
    def test_command_palette_enabled(self):
        """测试命令面板启用"""
        from netops_toolkit.tui.app import NetOpsApp
        
        assert NetOpsApp.ENABLE_COMMAND_PALETTE is True
    
    def test_app_has_commands(self):
        """测试应用有命令"""
        from netops_toolkit.tui.app import NetOpsApp
        
        assert len(NetOpsApp.COMMANDS) > 0
