"""
网络工具函数模块

提供IP地址处理、网络范围计算、端口验证等通用网络工具函数。
"""

import ipaddress
import re
import socket
from functools import wraps
from time import sleep
from typing import List, Optional, Union

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


def is_valid_ip(ip: str) -> bool:
    """
    验证IP地址是否有效
    
    Args:
        ip: IP地址字符串
        
    Returns:
        True表示有效, False表示无效
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_valid_network(network: str) -> bool:
    """
    验证网络地址(CIDR)是否有效
    
    Args:
        network: 网络地址字符串 (e.g., "192.168.1.0/24")
        
    Returns:
        True表示有效, False表示无效
    """
    try:
        ipaddress.ip_network(network, strict=False)
        return True
    except ValueError:
        return False


def expand_ip_range(ip_input: str) -> List[str]:
    """
    展开IP范围为IP列表
    
    支持多种输入格式:
    - 单个IP: "192.168.1.1"
    - CIDR: "192.168.1.0/24"
    - 范围: "192.168.1.1-10"
    - 列表: "192.168.1.1,192.168.1.2"
    
    Args:
        ip_input: IP输入字符串
        
    Returns:
        IP地址列表
    """
    ips = []
    
    # 处理逗号分隔的列表
    if "," in ip_input:
        for part in ip_input.split(","):
            ips.extend(expand_ip_range(part.strip()))
        return ips
    
    # 处理CIDR格式
    if "/" in ip_input:
        try:
            network = ipaddress.ip_network(ip_input, strict=False)
            # 跳过网络地址和广播地址(如果子网大于/31)
            if network.num_addresses > 2:
                return [str(ip) for ip in network.hosts()]
            else:
                return [str(ip) for ip in network]
        except ValueError as e:
            logger.warning(f"无效的CIDR格式: {ip_input} | {e}")
            return []
    
    # 处理范围格式 (e.g., 192.168.1.1-10)
    if "-" in ip_input:
        match = re.match(r"(\d+\.\d+\.\d+\.)(\d+)-(\d+)", ip_input)
        if match:
            prefix = match.group(1)
            start = int(match.group(2))
            end = int(match.group(3))
            return [f"{prefix}{i}" for i in range(start, end + 1)]
        else:
            logger.warning(f"无效的IP范围格式: {ip_input}")
            return []
    
    # 单个IP
    if is_valid_ip(ip_input):
        return [ip_input]
    
    logger.warning(f"无法解析的IP输入: {ip_input}")
    return []


def is_valid_port(port: Union[int, str]) -> bool:
    """
    验证端口号是否有效
    
    Args:
        port: 端口号
        
    Returns:
        True表示有效, False表示无效
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


def resolve_hostname(hostname: str, timeout: float = 2.0) -> Optional[str]:
    """
    解析主机名为IP地址
    
    Args:
        hostname: 主机名
        timeout: 超时时间(秒)
        
    Returns:
        IP地址字符串, 失败返回None
    """
    try:
        socket.setdefaulttimeout(timeout)
        ip = socket.gethostbyname(hostname)
        return ip
    except (socket.gaierror, socket.timeout) as e:
        logger.debug(f"主机名解析失败: {hostname} | {e}")
        return None


def reverse_dns_lookup(ip: str, timeout: float = 2.0) -> Optional[str]:
    """
    反向DNS查询
    
    Args:
        ip: IP地址
        timeout: 超时时间(秒)
        
    Returns:
        主机名字符串, 失败返回None
    """
    try:
        socket.setdefaulttimeout(timeout)
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except (socket.herror, socket.timeout) as e:
        logger.debug(f"反向DNS查询失败: {ip} | {e}")
        return None


def get_network_info(cidr: str) -> dict:
    """
    获取网络信息
    
    Args:
        cidr: CIDR格式的网络地址
        
    Returns:
        包含网络信息的字典
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        return {
            "network": str(network.network_address),
            "broadcast": str(network.broadcast_address),
            "netmask": str(network.netmask),
            "prefix_length": network.prefixlen,
            "num_addresses": network.num_addresses,
            "num_hosts": network.num_addresses - 2 if network.num_addresses > 2 else network.num_addresses,
            "first_host": str(list(network.hosts())[0]) if network.num_addresses > 2 else str(network.network_address),
            "last_host": str(list(network.hosts())[-1]) if network.num_addresses > 2 else str(network.broadcast_address),
        }
    except ValueError as e:
        logger.error(f"获取网络信息失败: {cidr} | {e}")
        return {}


def retry_on_exception(retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    重试装饰器
    
    Args:
        retries: 重试次数
        delay: 重试间隔(秒)
        exceptions: 需要捕获的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries - 1:
                        logger.debug(f"函数 {func.__name__} 执行失败 (尝试 {attempt + 1}/{retries}): {e}")
                        sleep(delay)
                    else:
                        logger.error(f"函数 {func.__name__} 执行失败,已达最大重试次数: {e}")
            raise last_exception
        return wrapper
    return decorator


def parse_port_list(port_input: str) -> List[int]:
    """
    解析端口列表字符串
    
    支持格式: "80,443,8080-8090"
    
    Args:
        port_input: 端口输入字符串
        
    Returns:
        端口号列表
    """
    ports = []
    
    for part in port_input.split(","):
        part = part.strip()
        
        # 处理范围
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                if is_valid_port(start) and is_valid_port(end):
                    ports.extend(range(start, end + 1))
            except ValueError:
                logger.warning(f"无效的端口范围: {part}")
        else:
            # 单个端口
            try:
                port = int(part)
                if is_valid_port(port):
                    ports.append(port)
            except ValueError:
                logger.warning(f"无效的端口号: {part}")
    
    return sorted(list(set(ports)))


# 常用端口定义
COMMON_PORTS = {
    "web": [80, 443, 8080, 8443],
    "ssh": [22],
    "telnet": [23],
    "ftp": [20, 21],
    "dns": [53],
    "smtp": [25, 465, 587],
    "pop3": [110, 995],
    "imap": [143, 993],
    "mysql": [3306],
    "postgresql": [5432],
    "redis": [6379],
    "mongodb": [27017],
    "all": [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 6379, 8080, 27017],
}


def get_common_ports(category: str = "all") -> List[int]:
    """
    获取常用端口列表
    
    Args:
        category: 端口分类 (web, ssh, all等)
        
    Returns:
        端口列表
    """
    return COMMON_PORTS.get(category.lower(), COMMON_PORTS["all"])


__all__ = [
    "is_valid_ip",
    "is_valid_network",
    "expand_ip_range",
    "is_valid_port",
    "resolve_hostname",
    "reverse_dns_lookup",
    "get_network_info",
    "retry_on_exception",
    "parse_port_list",
    "get_common_ports",
    "COMMON_PORTS",
]
