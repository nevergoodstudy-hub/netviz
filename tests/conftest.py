"""
NetOps Toolkit 测试配置文件

提供全局 fixtures 和 pytest 配置:
- 异步测试支持 (pytest-asyncio)
- 模拟设备数据
- 临时数据库
- Mock 工具
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any, List
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# 将项目根目录添加到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============== Pytest 配置 ==============

def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "tui: 标记为 TUI 测试"
    )
    config.addinivalue_line(
        "markers", "web: 标记为 Web API 测试"
    )


# ============== 异步测试配置 ==============

@pytest.fixture(scope="session")
def event_loop_policy():
    """为 Windows 提供事件循环策略"""
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def anyio_backend():
    """指定异步后端"""
    return "asyncio"


# ============== 设备数据 Fixtures ==============

@pytest.fixture
def sample_device_data() -> Dict[str, Any]:
    """单个设备数据样例"""
    return {
        "name": "test-router-01",
        "ip": "192.168.1.1",
        "port": 22,
        "vendor": "cisco_ios",
        "credentials": "default",
        "description": "测试路由器",
        "tags": ["core", "production"],
        "group": "routers",
    }


@pytest.fixture
def sample_devices_list() -> List[Dict[str, Any]]:
    """设备列表样例"""
    return [
        {
            "name": "router-01",
            "ip": "192.168.1.1",
            "port": 22,
            "vendor": "cisco_ios",
            "description": "核心路由器1",
            "tags": ["core"],
        },
        {
            "name": "router-02",
            "ip": "192.168.1.2",
            "port": 22,
            "vendor": "cisco_ios",
            "description": "核心路由器2",
            "tags": ["core"],
        },
        {
            "name": "switch-01",
            "ip": "192.168.2.1",
            "port": 22,
            "vendor": "cisco_ios",
            "description": "接入交换机1",
            "tags": ["access"],
        },
        {
            "name": "firewall-01",
            "ip": "192.168.3.1",
            "port": 22,
            "vendor": "cisco_asa",
            "description": "边界防火墙",
            "tags": ["security"],
        },
        {
            "name": "huawei-sw-01",
            "ip": "192.168.4.1",
            "port": 22,
            "vendor": "huawei",
            "description": "华为交换机",
            "tags": ["huawei", "access"],
        },
    ]


@pytest.fixture
def sample_inventory_yaml() -> str:
    """设备清单 YAML 内容"""
    return """
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
        description: 2楼接入交换机
        tags: [access, floor2]

standalone_devices:
  - name: firewall-main
    ip: 10.0.100.1
    vendor: cisco_asa
    description: 主防火墙
    tags: [security, perimeter]
"""


@pytest.fixture
def inventory_yaml_file(sample_inventory_yaml, tmp_path) -> Path:
    """创建临时设备清单文件"""
    yaml_file = tmp_path / "devices.yaml"
    yaml_file.write_text(sample_inventory_yaml, encoding="utf-8")
    return yaml_file


# ============== 配置模板 Fixtures ==============

@pytest.fixture
def sample_jinja_template() -> str:
    """Jinja2 配置模板样例"""
    return """
! VLAN Configuration
{% for vlan in vlans %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% endfor %}

! Interface Configuration
interface {{ interface_name }}
 description {{ description }}
 switchport mode access
 switchport access vlan {{ vlan_id }}
 no shutdown
"""


@pytest.fixture
def template_variables() -> Dict[str, Any]:
    """模板变量样例"""
    return {
        "vlans": [
            {"id": 10, "name": "MANAGEMENT"},
            {"id": 20, "name": "DATA"},
            {"id": 30, "name": "VOICE"},
        ],
        "interface_name": "GigabitEthernet0/1",
        "description": "User Port",
        "vlan_id": 20,
    }


# ============== 数据库 Fixtures ==============

@pytest.fixture
def temp_db_path(tmp_path) -> Path:
    """临时数据库路径"""
    return tmp_path / "test.db"


@pytest.fixture
def temp_audit_db(tmp_path) -> Path:
    """临时审计数据库路径"""
    return tmp_path / "audit.db"


# ============== Mock Fixtures ==============

@pytest.fixture
def mock_netmiko_connection():
    """模拟 Netmiko SSH 连接"""
    mock_conn = MagicMock()
    mock_conn.send_command.return_value = """
Cisco IOS Software, Version 15.1(4)M4
Router uptime is 10 days, 5 hours, 30 minutes
System returned to ROM by reload
"""
    mock_conn.send_config_set.return_value = "Configuration saved."
    mock_conn.disconnect.return_value = None
    mock_conn.is_alive.return_value = True
    return mock_conn


@pytest.fixture
def mock_ping_result():
    """模拟 Ping 结果"""
    return {
        "host": "192.168.1.1",
        "reachable": True,
        "latency_ms": 15.5,
        "packet_loss": 0.0,
        "min_latency": 12.0,
        "max_latency": 20.0,
        "avg_latency": 15.5,
    }


@pytest.fixture
def mock_compliance_config() -> str:
    """模拟设备配置（用于合规检查）"""
    return """
hostname test-router
!
enable secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0
!
aaa new-model
aaa authentication login default local
aaa authorization exec default local
!
username admin privilege 15 secret 5 $1$mERr$hx5rVt7rPNoS4wqbXKX7m0
!
ip ssh version 2
ip ssh time-out 60
!
line vty 0 4
 transport input ssh
 exec-timeout 10 0
!
banner motd ^C
==============================
Authorized Access Only
==============================
^C
!
logging buffered 64000 informational
logging console informational
!
ntp server 10.0.0.100
ntp server 10.0.0.101
!
snmp-server community public RO
snmp-server community private RW
!
"""


@pytest.fixture
def mock_noncompliant_config() -> str:
    """模拟不合规设备配置"""
    return """
hostname test-router
!
enable password cisco123
!
username admin password cisco123
!
ip ssh version 1
!
line vty 0 4
 transport input telnet ssh
 no exec-timeout
!
snmp-server community public RW
!
"""


# ============== 审计服务 Fixtures ==============

@pytest.fixture
def sample_audit_record() -> Dict[str, Any]:
    """审计记录样例"""
    return {
        "event_type": "CONFIG_CHANGE",
        "severity": "INFO",
        "user": "admin",
        "device": "router-01",
        "action": "配置推送",
        "old_value": "interface Gi0/1\n no shutdown",
        "new_value": "interface Gi0/1\n shutdown",
        "result": "SUCCESS",
        "message": "接口配置已更新",
    }


# ============== 报表 Fixtures ==============

@pytest.fixture
def sample_report_data() -> Dict[str, Any]:
    """报表数据样例"""
    return {
        "title": "网络设备巡检报告",
        "generated_at": "2026-02-01T12:00:00",
        "summary": {
            "total_devices": 10,
            "online_devices": 9,
            "offline_devices": 1,
            "alerts": 3,
        },
        "devices": [
            {
                "name": "router-01",
                "ip": "192.168.1.1",
                "status": "online",
                "uptime": "10d 5h",
                "cpu_usage": 35,
                "memory_usage": 60,
            },
            {
                "name": "switch-01",
                "ip": "192.168.2.1",
                "status": "online",
                "uptime": "30d 12h",
                "cpu_usage": 15,
                "memory_usage": 45,
            },
        ],
    }


# ============== Web API Fixtures ==============

@pytest.fixture
def test_client():
    """FastAPI 测试客户端"""
    try:
        from fastapi.testclient import TestClient
        from netops_toolkit.web.app import app
        return TestClient(app)
    except ImportError:
        pytest.skip("FastAPI not available")


@pytest.fixture
async def async_client():
    """异步 FastAPI 测试客户端"""
    try:
        from httpx import AsyncClient, ASGITransport
        from netops_toolkit.web.app import app
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client
    except ImportError:
        pytest.skip("httpx not available")


# ============== TUI 测试 Fixtures ==============

@pytest.fixture
def mock_app_context():
    """模拟 TUI 应用上下文"""
    return {
        "inventory": MagicMock(),
        "audit_service": MagicMock(),
        "scheduler_service": MagicMock(),
    }


# ============== DI 容器 Fixtures ==============

@pytest.fixture
def di_container():
    """创建干净的 DI 容器实例 (无全局副作用)"""
    from netops_toolkit.container import Container
    container = Container()
    yield container
    container.shutdown_resources()


@pytest.fixture
def mock_ping_service_di():
    """Mock PingService (符合接口契约)"""
    from netops_toolkit.domain.entities.scan_result import PingResult
    service = AsyncMock()
    service.ping_batch.return_value = [
        PingResult(
            host="10.0.0.1",
            is_alive=True,
            avg_latency=5.0,
            packet_loss=0.0,
            packets_sent=4,
            packets_received=4,
        )
    ]
    return service


@pytest.fixture
def mock_ssh_service_di():
    """Mock SSHService (符合接口契约)"""
    from netops_toolkit.domain.entities.scan_result import OperationResult, ResultStatus
    service = AsyncMock()
    service.execute_batch.return_value = [
        OperationResult(
            status=ResultStatus.SUCCESS,
            data={"output": "show version output"},
        )
    ]
    return service


@pytest.fixture
def di_container_with_mocks(di_container, mock_ping_service_di, mock_ssh_service_di):
    """已注入 Mock 服务的 DI 容器"""
    from dependency_injector import providers
    di_container.ping_service.override(providers.Object(mock_ping_service_di))
    di_container.ssh_service.override(providers.Object(mock_ssh_service_di))
    yield di_container
    di_container.ping_service.reset_override()
    di_container.ssh_service.reset_override()


@pytest.fixture
def ping_command_from_container(di_container_with_mocks):
    """从 DI 容器获取 PingCommand 实例"""
    return di_container_with_mocks.ping_command()


# ============== 工具函数 ==============

def assert_dict_contains(actual: Dict, expected: Dict):
    """断言字典包含预期的键值对"""
    for key, value in expected.items():
        assert key in actual, f"缺少键: {key}"
        assert actual[key] == value, f"键 {key} 的值不匹配: {actual[key]} != {value}"


def assert_file_exists(path: Path):
    """断言文件存在"""
    assert path.exists(), f"文件不存在: {path}"
    assert path.is_file(), f"不是文件: {path}"


def assert_valid_json(content: str) -> Dict:
    """断言是有效的 JSON 并返回解析结果"""
    import json
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        pytest.fail(f"无效的 JSON: {e}")
