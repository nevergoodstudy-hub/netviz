"""
系统信息检测模块

自动识别当前系统配置信息，包括操作系统、硬件、网络接口、Python 环境等。
支持 Windows、Linux、macOS、FreeBSD、OpenBSD 等多种系统。
"""

import os
import sys
import platform
import socket
import uuid
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class NetworkInterface:
    """网络接口信息"""
    name: str
    mac_address: str = ""
    ipv4_addresses: List[str] = field(default_factory=list)
    ipv6_addresses: List[str] = field(default_factory=list)
    is_up: bool = False
    mtu: int = 0


@dataclass
class SystemInfo:
    """系统信息数据类"""
    # 操作系统
    os_name: str = ""
    os_version: str = ""
    os_release: str = ""
    os_arch: str = ""
    os_platform: str = ""
    
    # 主机信息
    hostname: str = ""
    fqdn: str = ""
    machine_id: str = ""
    
    # 硬件信息
    cpu_name: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    memory_total_gb: float = 0.0
    memory_available_gb: float = 0.0
    
    # Python 环境
    python_version: str = ""
    python_implementation: str = ""
    python_path: str = ""
    virtual_env: str = ""
    
    # 网络信息
    network_interfaces: List[NetworkInterface] = field(default_factory=list)
    default_gateway: str = ""
    dns_servers: List[str] = field(default_factory=list)
    
    # 时间信息
    timezone: str = ""
    current_time: str = ""
    uptime: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "os": {
                "name": self.os_name,
                "version": self.os_version,
                "release": self.os_release,
                "arch": self.os_arch,
                "platform": self.os_platform,
            },
            "host": {
                "hostname": self.hostname,
                "fqdn": self.fqdn,
                "machine_id": self.machine_id,
            },
            "hardware": {
                "cpu_name": self.cpu_name,
                "cpu_cores": self.cpu_cores,
                "cpu_threads": self.cpu_threads,
                "memory_total_gb": self.memory_total_gb,
                "memory_available_gb": self.memory_available_gb,
            },
            "python": {
                "version": self.python_version,
                "implementation": self.python_implementation,
                "path": self.python_path,
                "virtual_env": self.virtual_env,
            },
            "network": {
                "interfaces": [
                    {
                        "name": iface.name,
                        "mac": iface.mac_address,
                        "ipv4": iface.ipv4_addresses,
                        "ipv6": iface.ipv6_addresses,
                        "is_up": iface.is_up,
                    }
                    for iface in self.network_interfaces
                ],
                "default_gateway": self.default_gateway,
                "dns_servers": self.dns_servers,
            },
            "time": {
                "timezone": self.timezone,
                "current": self.current_time,
                "uptime": self.uptime,
            },
        }


class SystemDetector:
    """系统信息检测器"""
    
    def __init__(self):
        self._info: Optional[SystemInfo] = None
    
    def detect(self, refresh: bool = False) -> SystemInfo:
        """
        检测系统信息
        
        Args:
            refresh: 是否强制刷新缓存
            
        Returns:
            SystemInfo 对象
        """
        if self._info is not None and not refresh:
            return self._info
        
        logger.info("开始检测系统信息...")
        info = SystemInfo()
        
        # 检测各项信息
        self._detect_os(info)
        self._detect_host(info)
        self._detect_hardware(info)
        self._detect_python(info)
        self._detect_network(info)
        self._detect_time(info)
        
        self._info = info
        logger.info("系统信息检测完成")
        return info
    
    def _detect_os(self, info: SystemInfo) -> None:
        """检测操作系统信息"""
        system = platform.system()  # Windows, Linux, Darwin, FreeBSD, etc.
        info.os_version = platform.version()
        info.os_release = platform.release()
        info.os_arch = platform.machine()
        info.os_platform = platform.platform()
        
        # 获取更友好的 OS 名称
        if system == "Windows":
            info.os_name = f"Windows {platform.win32_ver()[0]}"
        elif system == "Darwin":
            info.os_name = f"macOS {platform.mac_ver()[0]}"
        elif system == "Linux":
            info.os_name = self._get_linux_distro()
        elif system == "FreeBSD":
            info.os_name = f"FreeBSD {info.os_release}"
        elif system == "OpenBSD":
            info.os_name = f"OpenBSD {info.os_release}"
        elif system == "NetBSD":
            info.os_name = f"NetBSD {info.os_release}"
        elif system == "SunOS":
            info.os_name = f"Solaris/SunOS {info.os_release}"
        elif system == "AIX":
            info.os_name = f"AIX {info.os_release}"
        else:
            info.os_name = f"{system} {info.os_release}"
    
    def _get_linux_distro(self) -> str:
        """获取 Linux 发行版信息"""
        # 方法1: 使用 distro 库
        try:
            import distro
            name = distro.name(pretty=True)
            if name:
                return name
        except ImportError:
            pass
        
        # 方法2: 读取 /etc/os-release (最标准的方法)
        try:
            with open("/etc/os-release") as f:
                os_info = {}
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os_info[key] = value.strip('"')
                
                if "PRETTY_NAME" in os_info:
                    return os_info["PRETTY_NAME"]
                elif "NAME" in os_info:
                    version = os_info.get("VERSION", os_info.get("VERSION_ID", ""))
                    return f"{os_info['NAME']} {version}".strip()
        except Exception:
            pass
        
        # 方法3: 读取 /etc/lsb-release (Ubuntu 等)
        try:
            with open("/etc/lsb-release") as f:
                for line in f:
                    if line.startswith("DISTRIB_DESCRIPTION="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        
        # 方法4: 检查特定发行版文件
        distro_files = [
            ("/etc/redhat-release", None),
            ("/etc/centos-release", None),
            ("/etc/fedora-release", None),
            ("/etc/debian_version", "Debian"),
            ("/etc/arch-release", "Arch Linux"),
            ("/etc/gentoo-release", None),
            ("/etc/SuSE-release", None),
            ("/etc/slackware-version", None),
        ]
        
        for filepath, prefix in distro_files:
            try:
                with open(filepath) as f:
                    content = f.read().strip()
                    if prefix:
                        return f"{prefix} {content}"
                    return content
            except Exception:
                continue
        
        # 方法5: 使用 uname
        return f"Linux {platform.release()}"
    
    def _detect_host(self, info: SystemInfo) -> None:
        """检测主机信息"""
        info.hostname = socket.gethostname()
        try:
            info.fqdn = socket.getfqdn()
        except Exception:
            info.fqdn = info.hostname
        
        # 获取机器 ID
        try:
            info.machine_id = str(uuid.getnode())
        except Exception:
            info.machine_id = "unknown"
    
    def _detect_hardware(self, info: SystemInfo) -> None:
        """检测硬件信息"""
        # CPU 信息
        info.cpu_name = self._get_cpu_name()
        
        # CPU 核心数
        try:
            info.cpu_cores = os.cpu_count() or 1
            info.cpu_threads = info.cpu_cores
            
            # 尝试获取物理核心数
            try:
                import psutil
                info.cpu_cores = psutil.cpu_count(logical=False) or info.cpu_cores
                info.cpu_threads = psutil.cpu_count(logical=True) or info.cpu_threads
            except ImportError:
                pass
        except Exception:
            info.cpu_cores = 1
            info.cpu_threads = 1
        
        # 内存信息
        self._detect_memory(info)
    
    def _get_cpu_name(self) -> str:
        """获取 CPU 名称"""
        cpu_name = platform.processor()
        if cpu_name:
            return cpu_name
        
        system = platform.system()
        
        # Linux: 从 /proc/cpuinfo 获取
        if system == "Linux":
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":", 1)[1].strip()
            except Exception:
                pass
        
        # macOS: 使用 sysctl
        elif system == "Darwin":
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
        
        # BSD: 使用 sysctl
        elif system in ("FreeBSD", "OpenBSD", "NetBSD"):
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "hw.model"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                pass
        
        return "Unknown CPU"
    
    def _detect_memory(self, info: SystemInfo) -> None:
        """检测内存信息"""
        # 方法1: 使用 psutil
        try:
            import psutil
            mem = psutil.virtual_memory()
            info.memory_total_gb = round(mem.total / (1024**3), 2)
            info.memory_available_gb = round(mem.available / (1024**3), 2)
            return
        except ImportError:
            pass
        
        system = platform.system()
        
        # 方法2: Windows 专用
        if system == "Windows":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulonglong = ctypes.c_ulonglong
                
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', c_ulonglong),
                        ('ullAvailPhys', c_ulonglong),
                        ('ullTotalPageFile', c_ulonglong),
                        ('ullAvailPageFile', c_ulonglong),
                        ('ullTotalVirtual', c_ulonglong),
                        ('ullAvailVirtual', c_ulonglong),
                        ('ullAvailExtendedVirtual', c_ulonglong),
                    ]
                
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                
                info.memory_total_gb = round(stat.ullTotalPhys / (1024**3), 2)
                info.memory_available_gb = round(stat.ullAvailPhys / (1024**3), 2)
                return
            except Exception:
                pass
        
        # 方法3: Linux - 读取 /proc/meminfo
        elif system == "Linux":
            try:
                with open("/proc/meminfo") as f:
                    mem_info = {}
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            key = parts[0].rstrip(":")
                            value = int(parts[1])  # KB
                            mem_info[key] = value
                    
                    if "MemTotal" in mem_info:
                        info.memory_total_gb = round(mem_info["MemTotal"] / (1024**2), 2)
                    if "MemAvailable" in mem_info:
                        info.memory_available_gb = round(mem_info["MemAvailable"] / (1024**2), 2)
                    elif "MemFree" in mem_info:
                        # 老版本内核没有 MemAvailable
                        info.memory_available_gb = round(mem_info["MemFree"] / (1024**2), 2)
                    return
            except Exception:
                pass
        
        # 方法4: macOS/BSD - 使用 sysctl
        elif system in ("Darwin", "FreeBSD", "OpenBSD", "NetBSD"):
            try:
                # 获取总内存
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize" if system == "Darwin" else "hw.physmem"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    total_bytes = int(result.stdout.strip())
                    info.memory_total_gb = round(total_bytes / (1024**3), 2)
                    # BSD 系统获取可用内存比较复杂，这里简化处理
                    info.memory_available_gb = info.memory_total_gb * 0.5  # 估算值
                return
            except Exception:
                pass
    
    def _detect_python(self, info: SystemInfo) -> None:
        """检测 Python 环境"""
        info.python_version = platform.python_version()
        info.python_implementation = platform.python_implementation()
        info.python_path = sys.executable
        
        # 检测虚拟环境
        info.virtual_env = os.environ.get("VIRTUAL_ENV", "")
        if not info.virtual_env:
            info.virtual_env = os.environ.get("CONDA_DEFAULT_ENV", "")
        if not info.virtual_env:
            # 检查是否在 venv 中
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                info.virtual_env = sys.prefix
    
    def _detect_network(self, info: SystemInfo) -> None:
        """检测网络信息"""
        interfaces = []
        
        try:
            import psutil
            
            # 获取网络接口信息
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for name, addr_list in addrs.items():
                iface = NetworkInterface(name=name)
                
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        iface.ipv4_addresses.append(addr.address)
                    elif addr.family == socket.AF_INET6:
                        iface.ipv6_addresses.append(addr.address)
                    elif addr.family == psutil.AF_LINK:
                        iface.mac_address = addr.address
                
                if name in stats:
                    iface.is_up = stats[name].isup
                    iface.mtu = stats[name].mtu
                
                # 只添加有 IP 地址的接口
                if iface.ipv4_addresses or iface.ipv6_addresses:
                    interfaces.append(iface)
            
            # 获取默认网关
            gws = psutil.net_if_stats()
            
        except ImportError:
            # 备用方案：使用 socket 获取本机 IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                
                iface = NetworkInterface(
                    name="default",
                    ipv4_addresses=[local_ip],
                    is_up=True
                )
                interfaces.append(iface)
            except Exception:
                pass
        
        info.network_interfaces = interfaces
        
        # 获取 DNS 服务器
        info.dns_servers = self._get_dns_servers()
    
    def _get_dns_servers(self) -> List[str]:
        """获取 DNS 服务器列表"""
        dns_servers = []
        
        system = platform.system()
        
        if system == "Windows":
            try:
                result = subprocess.run(
                    ["ipconfig", "/all"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    encoding='gbk',
                    errors='ignore'
                )
                for line in result.stdout.split("\n"):
                    if "DNS" in line and ":" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            ip = parts[-1].strip()
                            if ip and ip[0].isdigit():
                                dns_servers.append(ip)
            except Exception:
                pass
        else:
            # Linux/macOS/BSD: 读取 /etc/resolv.conf
            try:
                with open("/etc/resolv.conf") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) >= 2:
                                dns_servers.append(parts[1])
            except Exception:
                pass
            
            # 如果没有找到，尝试使用 systemd-resolve (现代 Linux)
            if not dns_servers and system == "Linux":
                try:
                    result = subprocess.run(
                        ["systemd-resolve", "--status"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    for line in result.stdout.split("\n"):
                        if "DNS Servers" in line:
                            parts = line.split(":")
                            if len(parts) >= 2:
                                servers = parts[1].strip().split()
                                dns_servers.extend(servers)
                except Exception:
                    pass
        
        # 去重并返回前 5 个
        seen = set()
        unique_servers = []
        for server in dns_servers:
            if server not in seen:
                seen.add(server)
                unique_servers.append(server)
        
        return unique_servers[:5]
    
    def _detect_time(self, info: SystemInfo) -> None:
        """检测时间信息"""
        import time
        
        info.current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 时区
        try:
            info.timezone = time.tzname[0]
        except Exception:
            info.timezone = "Unknown"
        
        # 系统运行时间
        try:
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            info.uptime = f"{days}天 {hours}小时 {minutes}分钟"
        except ImportError:
            info.uptime = "未知"


# 全局检测器实例
_detector: Optional[SystemDetector] = None


def get_system_info(refresh: bool = False) -> SystemInfo:
    """
    获取系统信息
    
    Args:
        refresh: 是否强制刷新
        
    Returns:
        SystemInfo 对象
    """
    global _detector
    
    if _detector is None:
        _detector = SystemDetector()
    
    return _detector.detect(refresh=refresh)


def get_system_summary() -> str:
    """
    获取系统信息摘要（用于显示）
    
    Returns:
        格式化的系统信息字符串
    """
    info = get_system_info()
    
    lines = [
        f"操作系统: {info.os_name}",
        f"系统架构: {info.os_arch}",
        f"主机名: {info.hostname}",
        f"CPU: {info.cpu_name} ({info.cpu_cores}核/{info.cpu_threads}线程)",
        f"内存: {info.memory_available_gb:.1f} GB / {info.memory_total_gb:.1f} GB",
        f"Python: {info.python_version} ({info.python_implementation})",
    ]
    
    if info.virtual_env:
        lines.append(f"虚拟环境: {info.virtual_env}")
    
    if info.network_interfaces:
        iface = info.network_interfaces[0]
        if iface.ipv4_addresses:
            lines.append(f"IP 地址: {iface.ipv4_addresses[0]}")
    
    lines.append(f"系统时间: {info.current_time}")
    
    if info.uptime != "未知":
        lines.append(f"运行时间: {info.uptime}")
    
    return "\n".join(lines)


__all__ = [
    "SystemInfo",
    "NetworkInterface", 
    "SystemDetector",
    "get_system_info",
    "get_system_summary",
]
