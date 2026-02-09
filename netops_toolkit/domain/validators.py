"""
领域验证器模块

提供网络相关的输入验证工具。
所有验证器均为纯函数，不依赖外部基础设施。
"""

from __future__ import annotations

import re
from ipaddress import IPv4Address, IPv4Network, IPv6Address, ip_address, ip_network

from netops_toolkit.domain.exceptions import (
    InvalidCIDRError,
    InvalidCronExpressionError,
    InvalidHostnameError,
    InvalidIPAddressError,
    InvalidPortError,
)


# ==================== IP 地址验证 ====================


def validate_ip(value: str) -> str:
    """
    验证 IP 地址 (IPv4 或 IPv6)

    Args:
        value: IP 地址字符串

    Returns:
        规范化的 IP 地址

    Raises:
        InvalidIPAddressError: 无效的 IP 地址
    """
    try:
        addr = ip_address(value.strip())
        return str(addr)
    except ValueError:
        raise InvalidIPAddressError(value)


def is_valid_ip(value: str) -> bool:
    """检查是否为有效 IP 地址"""
    try:
        ip_address(value.strip())
        return True
    except ValueError:
        return False


def is_ipv4(value: str) -> bool:
    """检查是否为 IPv4 地址"""
    try:
        return isinstance(ip_address(value.strip()), IPv4Address)
    except ValueError:
        return False


def is_ipv6(value: str) -> bool:
    """检查是否为 IPv6 地址"""
    try:
        return isinstance(ip_address(value.strip()), IPv6Address)
    except ValueError:
        return False


# ==================== CIDR / 网段验证 ====================


def validate_cidr(value: str) -> str:
    """
    验证 CIDR 格式

    Args:
        value: CIDR 格式字符串 (e.g., "192.168.1.0/24")

    Returns:
        规范化的 CIDR

    Raises:
        InvalidCIDRError: 无效的 CIDR 格式
    """
    try:
        network = ip_network(value.strip(), strict=False)
        return str(network)
    except ValueError:
        raise InvalidCIDRError(value)


def is_valid_cidr(value: str) -> bool:
    """检查是否为有效 CIDR 格式"""
    try:
        ip_network(value.strip(), strict=False)
        return True
    except ValueError:
        return False


# ==================== 主机名验证 ====================

_HOSTNAME_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
)


def validate_hostname(value: str) -> str:
    """
    验证主机名

    Args:
        value: 主机名

    Returns:
        主机名

    Raises:
        InvalidHostnameError: 无效的主机名
    """
    stripped = value.strip()
    if not stripped or len(stripped) > 253:
        raise InvalidHostnameError(value)

    if not _HOSTNAME_PATTERN.match(stripped):
        raise InvalidHostnameError(value)

    return stripped


def is_valid_hostname(value: str) -> bool:
    """检查是否为有效主机名"""
    try:
        validate_hostname(value)
        return True
    except InvalidHostnameError:
        return False


# ==================== 端口验证 ====================


def validate_port(value: int) -> int:
    """
    验证端口号

    Args:
        value: 端口号

    Returns:
        端口号

    Raises:
        InvalidPortError: 无效的端口号
    """
    if not isinstance(value, int) or not 1 <= value <= 65535:
        raise InvalidPortError(value)
    return value


def is_valid_port(value: int) -> bool:
    """检查是否为有效端口号"""
    return isinstance(value, int) and 1 <= value <= 65535


def parse_port_range(port_str: str) -> list[int]:
    """
    解析端口范围字符串

    支持格式: "22", "80,443", "1-1024", "22,80,443,8000-8100"

    Args:
        port_str: 端口范围字符串

    Returns:
        端口号列表
    """
    ports: list[int] = []
    for part in port_str.split(","):
        part = part.strip()
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start = int(start_str.strip())
            end = int(end_str.strip())
            if not (1 <= start <= 65535 and 1 <= end <= 65535 and start <= end):
                raise InvalidPortError(start)
            ports.extend(range(start, end + 1))
        else:
            p = int(part)
            if not 1 <= p <= 65535:
                raise InvalidPortError(p)
            ports.append(p)
    return sorted(set(ports))


# ==================== 目标解析 ====================


def is_ip_or_hostname(value: str) -> bool:
    """检查字符串是否为有效的 IP 地址或主机名"""
    return is_valid_ip(value) or is_valid_hostname(value)


def parse_targets(target_str: str) -> list[str]:
    """
    解析目标字符串 (逗号分隔的 IP/主机名/CIDR)

    Args:
        target_str: 逗号分隔的目标

    Returns:
        目标列表 (CIDR 会展开为单个 IP)
    """
    targets: list[str] = []
    for part in target_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" in part and is_valid_cidr(part):
            # 展开 CIDR 为单个主机 IP
            network = ip_network(part, strict=False)
            if isinstance(network, IPv4Network):
                targets.extend(str(host) for host in network.hosts())
            else:
                # IPv6 网段不展开 (太大)
                targets.append(part)
        else:
            targets.append(part)
    return targets


# ==================== Cron 表达式验证 ====================


_CRON_FIELD_PATTERN = re.compile(
    r"^(\*|[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*)(/[0-9]+)?$"
)


def validate_cron_expression(value: str) -> str:
    """
    验证 Cron 表达式 (5 字段格式)

    Args:
        value: Cron 表达式 (e.g., "0 * * * *")

    Returns:
        Cron 表达式

    Raises:
        InvalidCronExpressionError: 无效的 Cron 表达式
    """
    parts = value.strip().split()
    if len(parts) != 5:
        raise InvalidCronExpressionError(value)

    for part in parts:
        if not _CRON_FIELD_PATTERN.match(part):
            raise InvalidCronExpressionError(value)

    return value.strip()


__all__ = [
    "validate_ip",
    "is_valid_ip",
    "is_ipv4",
    "is_ipv6",
    "validate_cidr",
    "is_valid_cidr",
    "validate_hostname",
    "is_valid_hostname",
    "validate_port",
    "is_valid_port",
    "parse_port_range",
    "is_ip_or_hostname",
    "parse_targets",
    "validate_cron_expression",
]
