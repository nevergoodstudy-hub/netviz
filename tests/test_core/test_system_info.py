"""
系统信息模块测试

测试覆盖:
- SystemInfo 数据类
- NetworkInterface 数据类
- SystemDetector 检测器
- 工具函数
"""

import pytest
import platform
from unittest.mock import patch, MagicMock

from netops_toolkit.core.system_info import (
    SystemInfo,
    NetworkInterface,
    SystemDetector,
    get_system_info,
    get_system_summary,
)


class TestNetworkInterface:
    """测试网络接口数据类"""
    
    def test_network_interface_creation(self):
        """测试创建网络接口"""
        iface = NetworkInterface(
            name="eth0",
            mac_address="00:11:22:33:44:55",
            ipv4_addresses=["192.168.1.100"],
            ipv6_addresses=["fe80::1"],
            is_up=True,
            mtu=1500,
        )
        
        assert iface.name == "eth0"
        assert iface.mac_address == "00:11:22:33:44:55"
        assert "192.168.1.100" in iface.ipv4_addresses
        assert iface.is_up is True
        assert iface.mtu == 1500
    
    def test_network_interface_defaults(self):
        """测试网络接口默认值"""
        iface = NetworkInterface(name="lo")
        
        assert iface.name == "lo"
        assert iface.mac_address == ""
        assert iface.ipv4_addresses == []
        assert iface.ipv6_addresses == []
        assert iface.is_up is False


class TestSystemInfo:
    """测试系统信息数据类"""
    
    def test_system_info_creation(self):
        """测试创建系统信息"""
        info = SystemInfo()
        
        assert info.os_name == ""
        assert info.hostname == ""
        assert info.cpu_cores == 0
        assert info.network_interfaces == []
    
    def test_system_info_to_dict(self):
        """测试转换为字典"""
        info = SystemInfo(
            os_name="Windows 11",
            os_version="10.0.22000",
            hostname="test-pc",
            cpu_name="Intel Core i7",
            cpu_cores=8,
            memory_total_gb=16.0,
        )
        
        data = info.to_dict()
        
        assert isinstance(data, dict)
        assert data["os"]["name"] == "Windows 11"
        assert data["host"]["hostname"] == "test-pc"
        assert data["hardware"]["cpu_cores"] == 8
        assert data["hardware"]["memory_total_gb"] == 16.0
    
    def test_system_info_with_interfaces(self):
        """测试带网络接口的系统信息"""
        iface = NetworkInterface(
            name="eth0",
            ipv4_addresses=["192.168.1.100"],
            is_up=True,
        )
        
        info = SystemInfo(network_interfaces=[iface])
        data = info.to_dict()
        
        assert len(data["network"]["interfaces"]) == 1
        assert data["network"]["interfaces"][0]["name"] == "eth0"


class TestSystemDetector:
    """测试系统检测器"""
    
    def test_detector_creation(self):
        """测试创建检测器"""
        detector = SystemDetector()
        assert detector._info is None
    
    def test_detector_detect(self):
        """测试检测系统信息"""
        detector = SystemDetector()
        info = detector.detect()
        
        assert isinstance(info, SystemInfo)
        assert info.os_name != ""
        assert info.hostname != ""
        assert info.python_version != ""
    
    def test_detector_caching(self):
        """测试检测结果缓存"""
        detector = SystemDetector()
        
        info1 = detector.detect()
        info2 = detector.detect(refresh=False)
        
        # 应该返回相同的对象
        assert info1 is info2
    
    def test_detector_refresh(self):
        """测试强制刷新"""
        detector = SystemDetector()
        
        info1 = detector.detect()
        info2 = detector.detect(refresh=True)
        
        # 刷新后应该是新对象
        # 但内容可能相同
        assert isinstance(info2, SystemInfo)
    
    def test_detect_os(self):
        """测试操作系统检测"""
        detector = SystemDetector()
        info = SystemInfo()
        
        detector._detect_os(info)
        
        assert info.os_name != ""
        assert info.os_arch != ""
    
    def test_detect_host(self):
        """测试主机信息检测"""
        detector = SystemDetector()
        info = SystemInfo()
        
        detector._detect_host(info)
        
        assert info.hostname != ""
        assert info.fqdn != ""
    
    def test_detect_hardware(self):
        """测试硬件信息检测"""
        detector = SystemDetector()
        info = SystemInfo()
        
        detector._detect_hardware(info)
        
        assert info.cpu_cores > 0
        assert info.cpu_threads > 0
    
    def test_detect_python(self):
        """测试 Python 环境检测"""
        detector = SystemDetector()
        info = SystemInfo()
        
        detector._detect_python(info)
        
        assert info.python_version != ""
        assert info.python_implementation != ""
        assert info.python_path != ""
    
    def test_detect_network(self):
        """测试网络信息检测"""
        detector = SystemDetector()
        info = SystemInfo()
        
        detector._detect_network(info)
        
        # 可能有也可能没有网络接口
        assert isinstance(info.network_interfaces, list)
    
    def test_detect_time(self):
        """测试时间信息检测"""
        detector = SystemDetector()
        info = SystemInfo()
        
        detector._detect_time(info)
        
        assert info.current_time != ""
        assert info.timezone != ""


class TestUtilityFunctions:
    """测试工具函数"""
    
    def test_get_system_info(self):
        """测试获取系统信息函数"""
        info = get_system_info()
        
        assert isinstance(info, SystemInfo)
        assert info.os_name != ""
    
    def test_get_system_info_refresh(self):
        """测试刷新系统信息"""
        info1 = get_system_info()
        info2 = get_system_info(refresh=True)
        
        assert isinstance(info2, SystemInfo)
    
    def test_get_system_summary(self):
        """测试获取系统摘要"""
        summary = get_system_summary()
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "操作系统" in summary or "Python" in summary


class TestPlatformSpecific:
    """测试平台特定功能"""
    
    def test_current_platform_detected(self):
        """测试当前平台被正确检测"""
        info = get_system_info(refresh=True)
        
        current_system = platform.system()
        
        if current_system == "Windows":
            assert "Windows" in info.os_name
        elif current_system == "Linux":
            assert "Linux" in info.os_name or len(info.os_name) > 0
        elif current_system == "Darwin":
            assert "macOS" in info.os_name
    
    def test_cpu_cores_positive(self):
        """测试 CPU 核心数为正数"""
        info = get_system_info()
        
        assert info.cpu_cores > 0
        assert info.cpu_threads > 0
        assert info.cpu_threads >= info.cpu_cores
