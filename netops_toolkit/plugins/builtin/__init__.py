"""
内置插件包

内置插件随 NetOps Toolkit 一起分发，提供核心网络运维功能。
通过 PluginRegistry.discover("netops_toolkit.plugins.builtin") 自动加载。

内置插件分类:
- diagnostics: 网络诊断 (ping, traceroute, dns_lookup ...)
- scanning: 网络扫描 (port_scan, arp_scan ...)
- device_mgmt: 设备管理 (ssh_batch, config_backup ...)
- performance: 性能测试 (bandwidth_test ...)
- utils: 工具类 (subnet_calc, ip_converter ...)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# 内置插件包标识
BUILTIN_PACKAGE = "netops_toolkit.plugins.builtin"

__all__ = ["BUILTIN_PACKAGE"]
