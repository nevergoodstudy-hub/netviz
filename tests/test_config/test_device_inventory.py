"""
DeviceInventory 设备清单测试模块

测试覆盖:
- 设备数据类验证
- YAML 配置加载
- 设备组解析
- 设备查询功能
- Netmiko 参数生成
"""

import pytest
from pathlib import Path

from netops_toolkit.config.device_inventory import (
    Device,
    DeviceGroup,
    DeviceInventory,
)


class TestDevice:
    """测试设备数据类"""
    
    def test_device_creation(self):
        """测试设备创建"""
        device = Device(
            name="router-01",
            ip="192.168.1.1",
            port=22,
            vendor="cisco_ios",
            description="测试路由器",
        )
        
        assert device.name == "router-01"
        assert device.ip == "192.168.1.1"
        assert device.port == 22
        assert device.vendor == "cisco_ios"
        assert device.description == "测试路由器"
    
    def test_device_default_values(self):
        """测试设备默认值"""
        device = Device(name="test-device", ip="10.0.0.1")
        
        assert device.port == 22
        assert device.vendor == "cisco_ios"
        assert device.credentials == ""
        assert device.description == ""
        assert device.tags == []
        assert device.group == ""
        assert device.extra == {}
    
    def test_device_validation_empty_name(self):
        """测试设备名称验证"""
        with pytest.raises(ValueError, match="设备名称不能为空"):
            Device(name="", ip="10.0.0.1")
    
    def test_device_validation_empty_ip(self):
        """测试设备IP验证"""
        with pytest.raises(ValueError, match="设备IP不能为空"):
            Device(name="test-device", ip="")
    
    def test_device_to_dict(self):
        """测试设备转字典"""
        device = Device(
            name="router-01",
            ip="192.168.1.1",
            port=22,
            vendor="cisco_ios",
            tags=["core", "production"],
        )
        
        data = device.to_dict()
        
        assert data["name"] == "router-01"
        assert data["ip"] == "192.168.1.1"
        assert data["port"] == 22
        assert data["vendor"] == "cisco_ios"
        assert data["tags"] == ["core", "production"]
    
    def test_device_get_netmiko_params(self):
        """测试获取 Netmiko 连接参数"""
        device = Device(
            name="router-01",
            ip="192.168.1.1",
            port=2222,
            vendor="cisco_ios",
        )
        
        params = device.get_netmiko_params()
        
        assert params["device_type"] == "cisco_ios"
        assert params["host"] == "192.168.1.1"
        assert params["port"] == 2222
    
    def test_device_str_representation(self):
        """测试设备字符串表示"""
        device = Device(name="router-01", ip="192.168.1.1")
        
        str_repr = str(device)
        
        assert "router-01" in str_repr
        assert "192.168.1.1" in str_repr
    
    def test_device_with_tags(self):
        """测试带标签的设备"""
        device = Device(
            name="switch-01",
            ip="10.0.0.1",
            tags=["access", "floor1", "building-a"],
        )
        
        assert len(device.tags) == 3
        assert "access" in device.tags
        assert "floor1" in device.tags
    
    def test_device_with_extra_fields(self):
        """测试带额外字段的设备"""
        device = Device(
            name="router-01",
            ip="192.168.1.1",
            extra={
                "location": "机房A",
                "rack": "R01",
                "model": "Cisco ISR 4331",
            },
        )
        
        assert device.extra["location"] == "机房A"
        assert device.extra["rack"] == "R01"


class TestDeviceGroup:
    """测试设备组数据类"""
    
    def test_device_group_creation(self):
        """测试设备组创建"""
        group = DeviceGroup(
            name="core_routers",
            vendor="cisco_ios",
            credentials="default",
            description="核心路由器组",
        )
        
        assert group.name == "core_routers"
        assert group.vendor == "cisco_ios"
        assert group.credentials == "default"
        assert group.description == "核心路由器组"
        assert group.devices == []
    
    def test_device_group_with_devices(self):
        """测试带设备的设备组"""
        devices = [
            Device(name="router-01", ip="10.0.0.1"),
            Device(name="router-02", ip="10.0.0.2"),
        ]
        
        group = DeviceGroup(
            name="routers",
            vendor="cisco_ios",
            credentials="default",
            devices=devices,
        )
        
        assert len(group) == 2
        assert len(group.devices) == 2
    
    def test_device_group_iteration(self):
        """测试设备组迭代"""
        devices = [
            Device(name=f"device-{i}", ip=f"10.0.0.{i}")
            for i in range(3)
        ]
        
        group = DeviceGroup(
            name="test_group",
            vendor="cisco_ios",
            credentials="default",
            devices=devices,
        )
        
        device_names = [d.name for d in group]
        
        assert device_names == ["device-0", "device-1", "device-2"]


class TestDeviceInventory:
    """测试设备清单管理类"""
    
    @pytest.fixture
    def sample_yaml(self, tmp_path):
        """创建测试用 YAML 文件"""
        yaml_content = """
groups:
  core_routers:
    vendor: cisco_ios
    credentials: default
    description: 核心路由器组
    devices:
      - name: core-rtr-01
        ip: 10.0.0.1
        description: 主核心路由器
        tags: [core, primary]
      - name: core-rtr-02
        ip: 10.0.0.2
        description: 备核心路由器
        tags: [core, backup]

  access_switches:
    vendor: cisco_ios
    credentials: default
    description: 接入交换机组
    devices:
      - name: acc-sw-01
        ip: 10.0.1.1
        description: 1楼接入交换机
        tags: [access, floor1]
      - name: acc-sw-02
        ip: 10.0.1.2
        port: 2222
        description: 2楼接入交换机
        tags: [access, floor2]

  huawei_devices:
    vendor: huawei
    credentials: huawei_creds
    description: 华为设备
    devices:
      - name: huawei-sw-01
        ip: 10.0.2.1
        tags: [huawei]

standalone_devices:
  - name: firewall-main
    ip: 10.0.100.1
    vendor: cisco_asa
    credentials: fw_creds
    description: 主防火墙
    tags: [security, perimeter]
"""
        yaml_file = tmp_path / "devices.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        return yaml_file
    
    def test_inventory_initialization(self):
        """测试清单初始化（无文件）"""
        inventory = DeviceInventory()
        
        assert len(inventory.get_all_devices()) == 0
        assert len(inventory.get_all_groups()) == 0
    
    def test_inventory_load_from_file(self, sample_yaml):
        """测试从文件加载清单"""
        inventory = DeviceInventory(sample_yaml)
        
        # 验证设备总数
        all_devices = inventory.get_all_devices()
        assert len(all_devices) == 6  # 2 + 2 + 1 + 1
        
        # 验证组数量
        groups = inventory.get_all_groups()
        assert len(groups) == 3
    
    def test_inventory_get_device_by_name(self, sample_yaml):
        """测试按名称获取设备"""
        inventory = DeviceInventory(sample_yaml)
        
        device = inventory.get_device("core-rtr-01")
        
        assert device is not None
        assert device.name == "core-rtr-01"
        assert device.ip == "10.0.0.1"
        assert device.vendor == "cisco_ios"
    
    def test_inventory_get_device_not_found(self, sample_yaml):
        """测试获取不存在的设备"""
        inventory = DeviceInventory(sample_yaml)
        
        device = inventory.get_device("nonexistent-device")
        
        assert device is None
    
    def test_inventory_get_device_by_ip(self, sample_yaml):
        """测试按 IP 获取设备"""
        inventory = DeviceInventory(sample_yaml)
        
        device = inventory.get_device_by_ip("10.0.0.1")
        
        assert device is not None
        assert device.name == "core-rtr-01"
    
    def test_inventory_get_devices_by_tag(self, sample_yaml):
        """测试按标签筛选设备"""
        inventory = DeviceInventory(sample_yaml)
        
        # 获取核心设备
        core_devices = inventory.get_devices_by_tag("core")
        assert len(core_devices) == 2
        
        # 获取接入层设备
        access_devices = inventory.get_devices_by_tag("access")
        assert len(access_devices) == 2
    
    def test_inventory_get_devices_by_vendor(self, sample_yaml):
        """测试按厂商筛选设备"""
        inventory = DeviceInventory(sample_yaml)
        
        # Cisco IOS 设备
        cisco_devices = inventory.get_devices_by_vendor("cisco_ios")
        assert len(cisco_devices) == 4  # 2 routers + 2 switches
        
        # 华为设备
        huawei_devices = inventory.get_devices_by_vendor("huawei")
        assert len(huawei_devices) == 1
        
        # Cisco ASA 设备
        asa_devices = inventory.get_devices_by_vendor("cisco_asa")
        assert len(asa_devices) == 1
    
    def test_inventory_get_group(self, sample_yaml):
        """测试获取设备组"""
        inventory = DeviceInventory(sample_yaml)
        
        group = inventory.get_group("core_routers")
        
        assert group is not None
        assert group.name == "core_routers"
        assert len(group.devices) == 2
    
    def test_inventory_device_inherits_group_vendor(self, sample_yaml):
        """测试设备继承组的厂商设置"""
        inventory = DeviceInventory(sample_yaml)
        
        # 华为组中的设备应该继承 huawei vendor
        device = inventory.get_device("huawei-sw-01")
        
        assert device.vendor == "huawei"
    
    def test_inventory_device_inherits_group_credentials(self, sample_yaml):
        """测试设备继承组的凭据设置"""
        inventory = DeviceInventory(sample_yaml)
        
        device = inventory.get_device("acc-sw-01")
        
        assert device.credentials == "default"
    
    def test_inventory_device_custom_port(self, sample_yaml):
        """测试设备自定义端口"""
        inventory = DeviceInventory(sample_yaml)
        
        # 默认端口
        device1 = inventory.get_device("acc-sw-01")
        assert device1.port == 22
        
        # 自定义端口
        device2 = inventory.get_device("acc-sw-02")
        assert device2.port == 2222
    
    def test_inventory_standalone_devices(self, sample_yaml):
        """测试独立设备（不属于任何组）"""
        inventory = DeviceInventory(sample_yaml)
        
        firewall = inventory.get_device("firewall-main")
        
        assert firewall is not None
        assert firewall.vendor == "cisco_asa"
        assert firewall.group == ""  # 无组
        assert "security" in firewall.tags
    
    def test_inventory_load_nonexistent_file(self, tmp_path):
        """测试加载不存在的文件"""
        nonexistent_path = tmp_path / "nonexistent.yaml"
        
        # 不应抛出异常，只是返回空清单
        inventory = DeviceInventory(nonexistent_path)
        
        assert len(inventory.get_all_devices()) == 0
    
    def test_inventory_load_empty_file(self, tmp_path):
        """测试加载空文件"""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("", encoding="utf-8")
        
        inventory = DeviceInventory(empty_file)
        
        assert len(inventory.get_all_devices()) == 0
    
    def test_inventory_load_invalid_yaml(self, tmp_path):
        """测试加载无效 YAML"""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("{{invalid yaml::", encoding="utf-8")
        
        # 应该捕获错误，不抛出异常
        inventory = DeviceInventory(invalid_file)
        
        assert len(inventory.get_all_devices()) == 0


class TestDeviceInventorySearch:
    """测试设备清单搜索功能 (使用现有 API 方法)"""
    
    @pytest.fixture
    def inventory(self, tmp_path):
        """创建测试清单"""
        yaml_content = """
groups:
  routers:
    vendor: cisco_ios
    credentials: default
    devices:
      - name: core-router-01
        ip: 10.0.0.1
        description: 数据中心核心路由器
        tags: [core, datacenter, critical]
      - name: edge-router-01
        ip: 10.0.0.2
        description: 边界路由器
        tags: [edge, perimeter]

  switches:
    vendor: cisco_ios
    credentials: default
    devices:
      - name: core-switch-01
        ip: 10.0.1.1
        description: 核心交换机
        tags: [core, datacenter]
      - name: access-switch-01
        ip: 10.0.1.2
        description: 接入交换机
        tags: [access, floor1]
"""
        yaml_file = tmp_path / "search_test.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        return DeviceInventory(yaml_file)
    
    def test_filter_by_tag(self, inventory):
        """测试按标签过滤"""
        # 使用 get_devices_by_tag 替代 search
        core_devices = inventory.get_devices_by_tag("core")
        
        assert len(core_devices) == 2
        assert all("core" in d.tags for d in core_devices)
    
    def test_filter_by_vendor(self, inventory):
        """测试按厂商过滤"""
        cisco_devices = inventory.get_devices_by_vendor("cisco_ios")
        
        assert len(cisco_devices) == 4
        assert all(d.vendor == "cisco_ios" for d in cisco_devices)
    
    def test_get_all_ips(self, inventory):
        """测试获取所有 IP"""
        ips = inventory.get_all_ips()
        
        assert len(ips) == 4
        assert "10.0.0.1" in ips
    
    def test_get_device_by_ip(self, inventory):
        """测试按 IP 获取设备"""
        device = inventory.get_device_by_ip("10.0.0.1")
        
        assert device is not None
        assert device.name == "core-router-01"


class TestDeviceInventoryNetmikoIntegration:
    """测试与 Netmiko 的集成"""
    
    def test_get_netmiko_params_for_cisco(self):
        """测试 Cisco 设备的 Netmiko 参数"""
        device = Device(
            name="cisco-router",
            ip="10.0.0.1",
            port=22,
            vendor="cisco_ios",
        )
        
        params = device.get_netmiko_params()
        
        assert params["device_type"] == "cisco_ios"
        assert params["host"] == "10.0.0.1"
        assert params["port"] == 22
    
    def test_get_netmiko_params_for_huawei(self):
        """测试华为设备的 Netmiko 参数"""
        device = Device(
            name="huawei-switch",
            ip="10.0.0.2",
            port=22,
            vendor="huawei",
        )
        
        params = device.get_netmiko_params()
        
        assert params["device_type"] == "huawei"
    
    def test_get_netmiko_params_for_juniper(self):
        """测试 Juniper 设备的 Netmiko 参数"""
        device = Device(
            name="juniper-firewall",
            ip="10.0.0.3",
            port=22,
            vendor="juniper_junos",
        )
        
        params = device.get_netmiko_params()
        
        assert params["device_type"] == "juniper_junos"
