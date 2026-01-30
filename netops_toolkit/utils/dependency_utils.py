"""
依赖管理工具模块

提供插件依赖检测和自动安装功能。
"""

import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DependencyInfo:
    """依赖信息数据类"""
    package_name: str        # PyPI 包名
    import_name: str         # Python 导入名 (可能与包名不同)
    version: Optional[str] = None  # 要求的版本
    description: str = ""    # 描述
    
    def __str__(self) -> str:
        if self.version:
            return f"{self.package_name}>={self.version}"
        return self.package_name


def check_dependency(dependency: DependencyInfo) -> bool:
    """
    检查单个依赖是否已安装
    
    Args:
        dependency: 依赖信息
        
    Returns:
        True 表示已安装，False 表示未安装
    """
    try:
        __import__(dependency.import_name)
        return True
    except ImportError:
        return False


def check_dependencies(dependencies: List[DependencyInfo]) -> Tuple[List[DependencyInfo], List[DependencyInfo]]:
    """
    批量检查依赖安装状态
    
    Args:
        dependencies: 依赖信息列表
        
    Returns:
        (已安装列表, 缺失列表)
    """
    installed = []
    missing = []
    
    for dep in dependencies:
        if check_dependency(dep):
            installed.append(dep)
        else:
            missing.append(dep)
    
    return installed, missing


def install_dependency(dependency: DependencyInfo, upgrade: bool = False) -> Tuple[bool, str]:
    """
    安装单个依赖
    
    Args:
        dependency: 依赖信息
        upgrade: 是否升级已有包
        
    Returns:
        (是否成功, 消息)
    """
    package_spec = str(dependency)
    
    # 安全检查：过滤包名中的危险字符
    if not _validate_package_name(dependency.package_name):
        return False, f"无效的包名: {dependency.package_name}"
    
    try:
        cmd = [sys.executable, "-m", "pip", "install"]
        
        if upgrade:
            cmd.append("--upgrade")
        
        cmd.append(package_spec)
        
        logger.info(f"正在安装依赖: {package_spec}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
        )
        
        if result.returncode == 0:
            logger.info(f"依赖安装成功: {package_spec}")
            return True, f"成功安装 {package_spec}"
        else:
            error_msg = result.stderr or result.stdout or "未知错误"
            logger.error(f"依赖安装失败: {error_msg}")
            return False, f"安装失败: {error_msg[:200]}"
            
    except subprocess.TimeoutExpired:
        return False, "安装超时"
    except Exception as e:
        logger.error(f"安装依赖异常: {e}")
        return False, f"安装异常: {str(e)}"


def install_dependencies(
    dependencies: List[DependencyInfo],
    skip_installed: bool = True
) -> Tuple[List[str], List[str]]:
    """
    批量安装依赖
    
    Args:
        dependencies: 依赖信息列表
        skip_installed: 是否跳过已安装的依赖
        
    Returns:
        (成功列表, 失败列表)
    """
    success = []
    failed = []
    
    for dep in dependencies:
        if skip_installed and check_dependency(dep):
            logger.info(f"跳过已安装的依赖: {dep.package_name}")
            success.append(dep.package_name)
            continue
        
        ok, msg = install_dependency(dep)
        if ok:
            success.append(dep.package_name)
        else:
            failed.append(f"{dep.package_name}: {msg}")
    
    return success, failed


def _validate_package_name(name: str) -> bool:
    """
    验证包名安全性
    
    防止命令注入攻击
    
    Args:
        name: 包名
        
    Returns:
        True 表示安全，False 表示不安全
    """
    if not name:
        return False
    
    # 包名只能包含字母、数字、连字符、下划线、点
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
        return False
    
    # 检查危险模式
    dangerous_patterns = [
        ';', '&', '|', '$', '`', 
        '$(', '${', 
        '..', 
        '/', '\\',
    ]
    for pattern in dangerous_patterns:
        if pattern in name:
            return False
    
    return True


def get_pip_version() -> Optional[str]:
    """获取 pip 版本"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            # pip 23.0 from /path/to/pip (python 3.x)
            return result.stdout.split()[1]
    except Exception:
        pass
    return None


# 常用工具依赖定义
COMMON_DEPENDENCIES = {
    "speedtest": DependencyInfo(
        package_name="speedtest-cli",
        import_name="speedtest",
        description="网络速度测试工具"
    ),
    "scapy": DependencyInfo(
        package_name="scapy",
        import_name="scapy",
        description="网络数据包分析工具"
    ),
    "netmiko": DependencyInfo(
        package_name="netmiko",
        import_name="netmiko",
        description="SSH网络设备连接库"
    ),
    "paramiko": DependencyInfo(
        package_name="paramiko",
        import_name="paramiko",
        description="SSH2协议库"
    ),
    "requests": DependencyInfo(
        package_name="requests",
        import_name="requests",
        description="HTTP请求库"
    ),
    "dnspython": DependencyInfo(
        package_name="dnspython",
        import_name="dns",
        description="DNS查询库"
    ),
    "pysnmp": DependencyInfo(
        package_name="pysnmp",
        import_name="pysnmp",
        description="SNMP协议库"
    ),
}


def get_dependency_info(name: str) -> Optional[DependencyInfo]:
    """
    获取常用依赖信息
    
    Args:
        name: 依赖名称 (包名或导入名)
        
    Returns:
        依赖信息，如果不存在返回 None
    """
    # 直接查找
    if name in COMMON_DEPENDENCIES:
        return COMMON_DEPENDENCIES[name]
    
    # 按导入名查找
    for dep in COMMON_DEPENDENCIES.values():
        if dep.import_name == name:
            return dep
    
    # 创建基本依赖信息
    return DependencyInfo(package_name=name, import_name=name)


__all__ = [
    "DependencyInfo",
    "check_dependency",
    "check_dependencies",
    "install_dependency",
    "install_dependencies",
    "get_dependency_info",
    "get_pip_version",
    "COMMON_DEPENDENCIES",
]
