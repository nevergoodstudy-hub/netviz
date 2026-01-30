"""
跨平台工具模块

提供统一的系统检测、命令执行和路径处理功能，
支持 Windows、Linux、macOS 和 BSD 系统。
"""

import os
import sys
import shutil
import subprocess
import platform
import locale
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


class PlatformType(Enum):
    """平台类型枚举"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    FREEBSD = "freebsd"
    OPENBSD = "openbsd"
    NETBSD = "netbsd"
    SUNOS = "sunos"
    AIX = "aix"
    UNKNOWN = "unknown"


@dataclass
class PlatformInfo:
    """平台信息数据类"""
    platform_type: PlatformType
    system: str
    release: str
    version: str
    machine: str
    is_windows: bool
    is_linux: bool
    is_macos: bool
    is_bsd: bool
    is_unix: bool
    
    @property
    def is_posix(self) -> bool:
        """是否为 POSIX 兼容系统"""
        return not self.is_windows


# 全局平台信息缓存
_platform_info: Optional[PlatformInfo] = None


def get_platform() -> PlatformInfo:
    """
    获取当前平台信息
    
    Returns:
        PlatformInfo 对象
    """
    global _platform_info
    
    if _platform_info is not None:
        return _platform_info
    
    system = platform.system().lower()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    
    # 确定平台类型
    if system == "windows":
        platform_type = PlatformType.WINDOWS
    elif system == "linux":
        platform_type = PlatformType.LINUX
    elif system == "darwin":
        platform_type = PlatformType.MACOS
    elif system == "freebsd":
        platform_type = PlatformType.FREEBSD
    elif system == "openbsd":
        platform_type = PlatformType.OPENBSD
    elif system == "netbsd":
        platform_type = PlatformType.NETBSD
    elif system == "sunos":
        platform_type = PlatformType.SUNOS
    elif system == "aix":
        platform_type = PlatformType.AIX
    else:
        platform_type = PlatformType.UNKNOWN
    
    is_windows = platform_type == PlatformType.WINDOWS
    is_linux = platform_type == PlatformType.LINUX
    is_macos = platform_type == PlatformType.MACOS
    is_bsd = platform_type in (
        PlatformType.FREEBSD, 
        PlatformType.OPENBSD, 
        PlatformType.NETBSD,
        PlatformType.MACOS  # macOS 基于 BSD
    )
    is_unix = not is_windows
    
    _platform_info = PlatformInfo(
        platform_type=platform_type,
        system=system,
        release=release,
        version=version,
        machine=machine,
        is_windows=is_windows,
        is_linux=is_linux,
        is_macos=is_macos,
        is_bsd=is_bsd,
        is_unix=is_unix,
    )
    
    return _platform_info


def command_exists(command: str) -> bool:
    """
    检查命令是否存在
    
    Args:
        command: 命令名称
        
    Returns:
        True 表示命令存在
    """
    return shutil.which(command) is not None


def get_command_path(command: str) -> Optional[str]:
    """
    获取命令的完整路径
    
    Args:
        command: 命令名称
        
    Returns:
        命令的完整路径，不存在返回 None
    """
    return shutil.which(command)


def get_terminal_encoding() -> str:
    """
    获取终端编码
    
    Returns:
        编码名称
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        # Windows 优先使用 GBK，但新版 Windows Terminal 可能使用 UTF-8
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            cp = kernel32.GetConsoleOutputCP()
            if cp == 65001:
                return 'utf-8'
            elif cp == 936:
                return 'gbk'
            elif cp == 950:
                return 'big5'
            else:
                return 'gbk'
        except Exception:
            return 'gbk'
    else:
        # Unix 系统通常使用 UTF-8
        return locale.getpreferredencoding(False) or 'utf-8'


def run_command(
    cmd: Union[str, List[str]],
    timeout: Optional[float] = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = False,
    shell: bool = False,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    跨平台运行命令
    
    自动处理编码和平台差异。
    
    Args:
        cmd: 命令（字符串或列表）
        timeout: 超时时间（秒）
        capture_output: 是否捕获输出
        text: 是否返回文本（而非字节）
        check: 是否检查返回码
        shell: 是否通过 shell 执行
        cwd: 工作目录
        env: 环境变量
        
    Returns:
        subprocess.CompletedProcess 对象
    """
    platform_info = get_platform()
    encoding = get_terminal_encoding()
    
    kwargs = {
        "timeout": timeout,
        "capture_output": capture_output,
        "check": check,
        "shell": shell,
    }
    
    if cwd:
        kwargs["cwd"] = str(cwd)
    
    if env:
        kwargs["env"] = {**os.environ, **env}
    
    if text:
        kwargs["text"] = True
        kwargs["encoding"] = encoding
        kwargs["errors"] = "ignore"
    
    # 如果是字符串命令且需要 shell
    if isinstance(cmd, str) and not shell:
        cmd = cmd.split()
    
    try:
        return subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        logger.warning(f"命令超时: {cmd}")
        raise
    except FileNotFoundError as e:
        logger.error(f"命令不存在: {cmd}")
        raise


def normalize_path(path: Union[str, Path]) -> Path:
    """
    规范化路径
    
    Args:
        path: 路径字符串或 Path 对象
        
    Returns:
        规范化后的 Path 对象
    """
    return Path(path).resolve()


def get_home_dir() -> Path:
    """
    获取用户主目录
    
    Returns:
        主目录路径
    """
    return Path.home()


def get_config_dir(app_name: str = "netops-toolkit") -> Path:
    """
    获取配置目录
    
    根据操作系统返回适当的配置目录：
    - Windows: %APPDATA%/app_name
    - macOS: ~/Library/Application Support/app_name
    - Linux/Unix: ~/.config/app_name
    
    Args:
        app_name: 应用名称
        
    Returns:
        配置目录路径
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        base = Path(os.environ.get("APPDATA", "~"))
    elif platform_info.is_macos:
        base = get_home_dir() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
    
    return base.expanduser() / app_name


def get_cache_dir(app_name: str = "netops-toolkit") -> Path:
    """
    获取缓存目录
    
    Args:
        app_name: 应用名称
        
    Returns:
        缓存目录路径
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        base = Path(os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", "~")))
    elif platform_info.is_macos:
        base = get_home_dir() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache"))
    
    return base.expanduser() / app_name


def get_log_dir(app_name: str = "netops-toolkit") -> Path:
    """
    获取日志目录
    
    Args:
        app_name: 应用名称
        
    Returns:
        日志目录路径
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        base = Path(os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", "~")))
        return base.expanduser() / app_name / "logs"
    elif platform_info.is_macos:
        return get_home_dir() / "Library" / "Logs" / app_name
    else:
        # Linux/Unix: 使用 /var/log (需要权限) 或 ~/.local/share/app_name/logs
        base = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share"))
        return base.expanduser() / app_name / "logs"


def is_root() -> bool:
    """
    检查是否以 root/管理员权限运行
    
    Returns:
        True 表示有管理员权限
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def get_network_commands() -> Dict[str, Optional[str]]:
    """
    获取网络相关命令的路径
    
    Returns:
        命令名到路径的映射
    """
    commands = [
        "ping",
        "traceroute",
        "tracert",
        "mtr",
        "netstat",
        "ss",
        "arp",
        "ip",
        "ifconfig",
        "route",
        "nslookup",
        "dig",
        "host",
        "curl",
        "wget",
    ]
    
    return {cmd: get_command_path(cmd) for cmd in commands}


def get_ping_command(
    target: str,
    count: int = 4,
    timeout: float = 2.0,
) -> List[str]:
    """
    获取适用于当前平台的 ping 命令
    
    Args:
        target: 目标地址
        count: ping 次数
        timeout: 超时时间（秒）
        
    Returns:
        命令参数列表
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        return ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), target]
    elif platform_info.is_macos:
        return ["ping", "-c", str(count), "-W", str(int(timeout * 1000)), target]
    elif platform_info.is_bsd:
        # BSD 系统 (FreeBSD, OpenBSD 等)
        return ["ping", "-c", str(count), "-W", str(int(timeout * 1000)), target]
    else:
        # Linux
        return ["ping", "-c", str(count), "-W", str(int(timeout)), target]


def get_traceroute_command(
    target: str,
    max_hops: int = 30,
    timeout: float = 3.0,
) -> Tuple[List[str], str]:
    """
    获取适用于当前平台的 traceroute 命令
    
    Args:
        target: 目标地址
        max_hops: 最大跳数
        timeout: 超时时间（秒）
        
    Returns:
        (命令参数列表, 命令名称)
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        return (
            ["tracert", "-h", str(max_hops), "-w", str(int(timeout * 1000)), target],
            "tracert"
        )
    elif platform_info.is_macos:
        return (
            ["traceroute", "-m", str(max_hops), "-w", str(int(timeout)), target],
            "traceroute"
        )
    elif platform_info.is_bsd:
        return (
            ["traceroute", "-m", str(max_hops), "-w", str(int(timeout)), target],
            "traceroute"
        )
    else:
        # Linux
        return (
            ["traceroute", "-m", str(max_hops), "-w", str(int(timeout)), target],
            "traceroute"
        )


def get_netstat_command(mode: str = "listen") -> Tuple[List[str], str]:
    """
    获取适用于当前平台的 netstat 命令
    
    Args:
        mode: 模式 (listen, established, all)
        
    Returns:
        (命令参数列表, 命令类型)
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        return (["netstat", "-ano"], "windows")
    elif platform_info.is_linux:
        # 优先使用 ss 命令
        if command_exists("ss"):
            if mode == "listen":
                return (["ss", "-tuln"], "ss")
            elif mode == "established":
                return (["ss", "-tun", "state", "established"], "ss")
            else:
                return (["ss", "-tuna"], "ss")
        else:
            if mode == "listen":
                return (["netstat", "-tuln"], "netstat_linux")
            elif mode == "established":
                return (["netstat", "-tun"], "netstat_linux")
            else:
                return (["netstat", "-tuna"], "netstat_linux")
    elif platform_info.is_macos:
        return (["netstat", "-an"], "netstat_bsd")
    elif platform_info.is_bsd:
        return (["netstat", "-an"], "netstat_bsd")
    else:
        return (["netstat", "-an"], "netstat_generic")


def get_route_command(ipv6: bool = False) -> Tuple[List[str], str]:
    """
    获取适用于当前平台的路由表命令
    
    Args:
        ipv6: 是否显示 IPv6 路由
        
    Returns:
        (命令参数列表, 命令类型)
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        if ipv6:
            return (["netsh", "interface", "ipv6", "show", "route"], "windows_ipv6")
        else:
            return (["route", "print", "-4"], "windows")
    elif platform_info.is_linux:
        if command_exists("ip"):
            if ipv6:
                return (["ip", "-6", "route", "show"], "ip")
            else:
                return (["ip", "route", "show"], "ip")
        else:
            return (["netstat", "-rn"], "netstat_route")
    elif platform_info.is_macos:
        family = "inet6" if ipv6 else "inet"
        return (["netstat", "-rn", "-f", family], "netstat_bsd")
    elif platform_info.is_bsd:
        family = "inet6" if ipv6 else "inet"
        return (["netstat", "-rn", "-f", family], "netstat_bsd")
    else:
        return (["netstat", "-rn"], "netstat_generic")


def get_arp_command(target: Optional[str] = None) -> Tuple[List[str], str]:
    """
    获取适用于当前平台的 ARP 命令
    
    Args:
        target: 目标 IP (可选)
        
    Returns:
        (命令参数列表, 命令类型)
    """
    platform_info = get_platform()
    
    if platform_info.is_windows:
        if target:
            return (["arp", "-a", target], "windows")
        else:
            return (["arp", "-a"], "windows")
    elif platform_info.is_linux:
        if command_exists("ip"):
            if target:
                return (["ip", "neigh", "show", target], "ip")
            else:
                return (["ip", "neigh", "show"], "ip")
        else:
            if target:
                return (["arp", "-n", target], "arp_linux")
            else:
                return (["arp", "-an"], "arp_linux")
    elif platform_info.is_macos or platform_info.is_bsd:
        if target:
            return (["arp", "-n", target], "arp_bsd")
        else:
            return (["arp", "-an"], "arp_bsd")
    else:
        if target:
            return (["arp", "-n", target], "arp_generic")
        else:
            return (["arp", "-an"], "arp_generic")


__all__ = [
    "PlatformType",
    "PlatformInfo",
    "get_platform",
    "command_exists",
    "get_command_path",
    "get_terminal_encoding",
    "run_command",
    "normalize_path",
    "get_home_dir",
    "get_config_dir",
    "get_cache_dir",
    "get_log_dir",
    "is_root",
    "get_network_commands",
    "get_ping_command",
    "get_traceroute_command",
    "get_netstat_command",
    "get_route_command",
    "get_arp_command",
]
