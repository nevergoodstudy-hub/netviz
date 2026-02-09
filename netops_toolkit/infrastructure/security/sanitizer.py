"""
命令和输入清理器

防止命令注入攻击。
"""

from __future__ import annotations

import re
from typing import Optional

from netops_toolkit.domain.exceptions import CommandInjectionError


# 危险字符/模式
_DANGEROUS_PATTERNS = [
    r"[;&|`$]",       # shell 元字符
    r"\$\(",          # 命令替换
    r">\s*/",         # 重定向到绝对路径
    r"\.\./",         # 路径遍历
    r"\\n|\\r",       # 换行注入
]

_COMPILED_PATTERNS = [re.compile(p) for p in _DANGEROUS_PATTERNS]


def sanitize_command(command: str, strict: bool = True) -> str:
    """
    清理命令字符串

    Args:
        command: 原始命令
        strict: 严格模式 - 发现危险字符则抛异常

    Returns:
        清理后的命令

    Raises:
        CommandInjectionError: 严格模式下发现危险字符
    """
    if not command:
        return command

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(command):
            if strict:
                raise CommandInjectionError(command)
            # 非严格模式: 移除危险字符
            command = pattern.sub("", command)

    return command.strip()


def sanitize_hostname(hostname: str) -> str:
    """
    清理主机名

    只允许字母、数字、点、连字符。

    Args:
        hostname: 原始主机名

    Returns:
        清理后的主机名

    Raises:
        CommandInjectionError: 包含非法字符
    """
    if not hostname:
        return hostname

    # RFC 952 / RFC 1123 合法字符
    cleaned = re.sub(r"[^a-zA-Z0-9.\-:]", "", hostname)

    if cleaned != hostname:
        raise CommandInjectionError(hostname)

    return cleaned


def sanitize_ip(ip: str) -> str:
    """
    清理 IP 地址字符串

    只允许数字、点、冒号、斜杠 (用于 CIDR)。
    """
    if not ip:
        return ip

    cleaned = re.sub(r"[^0-9a-fA-F.:/]", "", ip)

    if cleaned != ip:
        raise CommandInjectionError(ip)

    return cleaned


def escape_for_shell(value: str) -> str:
    """
    转义 shell 特殊字符 (用于必须传递给 shell 的场景)

    用单引号包裹，内部单引号做转义处理。
    """
    return "'" + value.replace("'", "'\"'\"'") + "'"


__all__ = [
    "sanitize_command",
    "sanitize_hostname",
    "sanitize_ip",
    "escape_for_shell",
]
