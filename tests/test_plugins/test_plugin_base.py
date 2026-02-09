"""
插件基类测试模块

测试覆盖:
- PluginCategory 枚举
- ResultStatus 枚举
- PluginResult 数据类
- ParamSpec 数据类
- Plugin 抽象基类
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from netops_toolkit.plugins.base import (
    PluginCategory,
    ResultStatus,
    PluginResult,
    ParamSpec,
    Plugin,
)


class TestPluginCategory:
    """测试插件分类枚举"""
    
    def test_plugin_categories_exist(self):
        """测试插件分类值存在"""
        assert PluginCategory.DIAGNOSTICS == "diagnostics"
        assert PluginCategory.DEVICE_MGMT == "device_mgmt"
        assert PluginCategory.SCANNING == "scanning"
        assert PluginCategory.PERFORMANCE == "performance"
        assert PluginCategory.UTILS == "utils"
    
    def test_plugin_category_is_string(self):
        """测试插件分类是字符串类型"""
        for category in PluginCategory:
            assert isinstance(category.value, str)


class TestResultStatus:
    """测试结果状态枚举"""
    
    def test_result_status_values(self):
        """测试结果状态值"""
        assert ResultStatus.SUCCESS == "success"
        assert ResultStatus.PARTIAL == "partial"
        assert ResultStatus.FAILED == "failed"
        assert ResultStatus.ERROR == "error"
        assert ResultStatus.CANCELLED == "cancelled"


class TestPluginResult:
    """测试插件结果数据类"""
    
    def test_plugin_result_creation(self):
        """测试创建插件结果"""
        result = PluginResult(
            status=ResultStatus.SUCCESS,
            message="Operation completed",
            data={"items": [1, 2, 3]},
        )
        
        assert result.status == ResultStatus.SUCCESS
        assert result.message == "Operation completed"
        assert result.data == {"items": [1, 2, 3]}
    
    def test_plugin_result_defaults(self):
        """测试插件结果默认值"""
        result = PluginResult(status=ResultStatus.SUCCESS)
        
        assert result.message == ""
        assert result.data is None
        assert result.errors == []
        assert result.start_time is None
        assert result.end_time is None
        assert result.metadata == {}
    
    def test_plugin_result_duration(self):
        """测试计算执行耗时"""
        start = datetime.now()
        end = start + timedelta(seconds=5)
        
        result = PluginResult(
            status=ResultStatus.SUCCESS,
            start_time=start,
            end_time=end,
        )
        
        assert result.duration == 5.0
    
    def test_plugin_result_duration_none(self):
        """测试无时间信息时耗时为 None"""
        result = PluginResult(status=ResultStatus.SUCCESS)
        
        assert result.duration is None
    
    def test_plugin_result_is_success(self):
        """测试是否成功判断"""
        success_result = PluginResult(status=ResultStatus.SUCCESS)
        partial_result = PluginResult(status=ResultStatus.PARTIAL)
        failed_result = PluginResult(status=ResultStatus.FAILED)
        error_result = PluginResult(status=ResultStatus.ERROR)
        
        assert success_result.is_success is True
        assert partial_result.is_success is True
        assert failed_result.is_success is False
        assert error_result.is_success is False
    
    def test_plugin_result_to_dict(self):
        """测试转换为字典"""
        start = datetime(2026, 1, 1, 10, 0, 0)
        end = datetime(2026, 1, 1, 10, 0, 5)
        
        result = PluginResult(
            status=ResultStatus.SUCCESS,
            message="Test",
            data={"key": "value"},
            errors=["Warning 1"],
            start_time=start,
            end_time=end,
            metadata={"extra": True},
        )
        
        data = result.to_dict()
        
        assert data["status"] == "success"
        assert data["message"] == "Test"
        assert data["data"] == {"key": "value"}
        assert data["errors"] == ["Warning 1"]
        assert data["duration"] == 5.0
        assert data["metadata"] == {"extra": True}


class TestParamSpec:
    """测试参数规格数据类"""
    
    def test_param_spec_creation(self):
        """测试创建参数规格"""
        param = ParamSpec(
            name="target",
            param_type=str,
            description="Target IP address",
            required=True,
        )
        
        assert param.name == "target"
        assert param.param_type == str
        assert param.description == "Target IP address"
        assert param.required is True
    
    def test_param_spec_defaults(self):
        """测试参数规格默认值"""
        param = ParamSpec(name="count", param_type=int)
        
        assert param.description == ""
        assert param.required is True
        assert param.default is None
        assert param.choices is None
    
    def test_param_spec_with_choices(self):
        """测试带选项的参数规格"""
        param = ParamSpec(
            name="protocol",
            param_type=str,
            choices=["tcp", "udp", "icmp"],
            default="tcp",
        )
        
        assert param.choices == ["tcp", "udp", "icmp"]
        assert param.default == "tcp"


class TestPluginBase:
    """测试插件抽象基类"""
    
    def test_plugin_is_abstract(self):
        """测试插件类是抽象类"""
        # 不能直接实例化抽象类
        with pytest.raises(TypeError):
            Plugin()
    
    def test_concrete_plugin_implementation(self):
        """测试具体插件实现"""
        class TestPlugin(Plugin):
            name = "TestPlugin"
            category = PluginCategory.UTILS
            description = "A test plugin"
            version = "1.0.0"
            
            def validate_dependencies(self) -> bool:
                return True
            
            def get_required_params(self) -> List[ParamSpec]:
                return [
                    ParamSpec(name="target", param_type=str),
                ]
            
            def run(self, **kwargs) -> PluginResult:
                return PluginResult(
                    status=ResultStatus.SUCCESS,
                    message="Test completed",
                )
        
        plugin = TestPlugin()
        
        assert plugin.name == "TestPlugin"
        assert plugin.category == PluginCategory.UTILS
        assert plugin.description == "A test plugin"
    
    def test_plugin_initialize(self):
        """测试插件初始化"""
        class TestPlugin(Plugin):
            name = "InitPlugin"
            
            def validate_dependencies(self) -> bool:
                return True
            
            def get_required_params(self) -> List[ParamSpec]:
                return []
            
            def run(self, **kwargs) -> PluginResult:
                return PluginResult(status=ResultStatus.SUCCESS)
        
        plugin = TestPlugin()
        result = plugin.initialize()
        
        assert result is True
        assert plugin._initialized is True
    
    def test_plugin_initialize_with_missing_deps(self):
        """测试缺少依赖时初始化失败"""
        class FailingPlugin(Plugin):
            name = "FailingPlugin"
            
            def validate_dependencies(self) -> bool:
                self._missing_deps = ["non_existent_module"]
                return False
            
            def get_required_params(self) -> List[ParamSpec]:
                return []
            
            def run(self, **kwargs) -> PluginResult:
                return PluginResult(status=ResultStatus.SUCCESS)
        
        plugin = FailingPlugin()
        result = plugin.initialize()
        
        assert result is False
        assert plugin._initialized is False
    
    def test_plugin_check_imports(self):
        """测试依赖检查"""
        class ImportCheckPlugin(Plugin):
            name = "ImportCheckPlugin"
            
            def validate_dependencies(self) -> bool:
                ok, missing = self._check_imports(["os", "sys"])
                return ok
            
            def get_required_params(self) -> List[ParamSpec]:
                return []
            
            def run(self, **kwargs) -> PluginResult:
                return PluginResult(status=ResultStatus.SUCCESS)
        
        plugin = ImportCheckPlugin()
        
        # os 和 sys 应该都存在
        assert plugin.validate_dependencies() is True
        assert plugin.get_missing_dependencies() == []
    
    def test_plugin_check_imports_missing(self):
        """测试缺少的依赖检查"""
        class MissingDepPlugin(Plugin):
            name = "MissingDepPlugin"
            
            def validate_dependencies(self) -> bool:
                ok, missing = self._check_imports(["non_existent_module_12345"])
                return ok
            
            def get_required_params(self) -> List[ParamSpec]:
                return []
            
            def run(self, **kwargs) -> PluginResult:
                return PluginResult(status=ResultStatus.SUCCESS)
        
        plugin = MissingDepPlugin()
        
        assert plugin.validate_dependencies() is False
        assert "non_existent_module_12345" in plugin.get_missing_dependencies()
    
    def test_plugin_run(self):
        """测试插件执行"""
        class RunPlugin(Plugin):
            name = "RunPlugin"
            
            def validate_dependencies(self) -> bool:
                return True
            
            def get_required_params(self) -> List[ParamSpec]:
                return [
                    ParamSpec(name="value", param_type=int),
                ]
            
            def run(self, **kwargs) -> PluginResult:
                value = kwargs.get("value", 0)
                return PluginResult(
                    status=ResultStatus.SUCCESS,
                    message=f"Received value: {value}",
                    data={"value": value},
                )
        
        plugin = RunPlugin()
        plugin.initialize()
        
        result = plugin.run(value=42)
        
        assert result.status == ResultStatus.SUCCESS
        assert result.data["value"] == 42


class TestPluginMetadata:
    """测试插件元数据"""
    
    def test_plugin_default_metadata(self):
        """测试默认元数据"""
        class DefaultPlugin(Plugin):
            def validate_dependencies(self) -> bool:
                return True
            
            def get_required_params(self) -> List[ParamSpec]:
                return []
            
            def run(self, **kwargs) -> PluginResult:
                return PluginResult(status=ResultStatus.SUCCESS)
        
        # 检查类属性存在
        assert hasattr(DefaultPlugin, 'name')
        assert hasattr(DefaultPlugin, 'category')
        assert hasattr(DefaultPlugin, 'description')
        assert hasattr(DefaultPlugin, 'version')
        assert hasattr(DefaultPlugin, 'author')
