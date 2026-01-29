"""
MAC地址查询插件

支持MAC地址厂商查询和格式转换。
"""

from typing import Any, Dict, List, Optional, Tuple
import re
import json
from pathlib import Path

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


# 常见厂商OUI数据库(部分)
# 完整数据库可从 https://standards-oui.ieee.org/ 获取
COMMON_OUI_DATABASE = {
    "00:00:0C": "Cisco Systems",
    "00:01:42": "Cisco Systems",
    "00:0C:29": "VMware",
    "00:0C:30": "Cisco Systems",
    "00:0D:3A": "Microsoft Corporation",
    "00:0F:FE": "G-PRO COMPUTER",
    "00:10:18": "Broadcom",
    "00:14:22": "Dell Inc.",
    "00:15:5D": "Microsoft Corporation (Hyper-V)",
    "00:16:3E": "Xen Virtual",
    "00:1A:11": "Google Inc.",
    "00:1A:A0": "Dell Inc.",
    "00:1C:42": "Parallels",
    "00:1D:D8": "Microsoft Corporation",
    "00:21:5A": "Hewlett-Packard",
    "00:23:AE": "Dell Inc.",
    "00:24:D7": "Intel Corporation",
    "00:25:00": "Apple Inc.",
    "00:25:B5": "Cisco Systems",
    "00:26:B9": "Dell Inc.",
    "00:30:48": "Supermicro",
    "00:50:56": "VMware",
    "00:E0:4C": "Realtek Semiconductor",
    "00:E0:81": "Tyan Computer Corp.",
    "08:00:20": "Oracle/Sun Microsystems",
    "08:00:27": "VirtualBox (Oracle)",
    "0C:C4:7A": "Super Micro Computer",
    "14:02:EC": "Hewlett-Packard",
    "18:66:DA": "Dell Inc.",
    "24:6E:96": "Dell Inc.",
    "28:D2:44": "Huawei Technologies",
    "2C:44:FD": "Hewlett-Packard",
    "34:17:EB": "Dell Inc.",
    "38:EA:A7": "Hewlett-Packard",
    "3C:D9:2B": "Hewlett-Packard",
    "44:1E:A1": "Hewlett-Packard",
    "44:A8:42": "Dell Inc.",
    "48:DF:37": "Huawei Technologies",
    "4C:52:62": "Hewlett-Packard",
    "54:9F:35": "Dell Inc.",
    "5C:26:0A": "Dell Inc.",
    "64:00:6A": "Dell Inc.",
    "74:86:7A": "Dell Inc.",
    "78:2B:CB": "Dell Inc.",
    "80:18:44": "Dell Inc.",
    "84:2B:2B": "Dell Inc.",
    "88:51:FB": "Hewlett-Packard",
    "8C:EC:4B": "Dell Inc.",
    "90:B1:1C": "Dell Inc.",
    "98:90:96": "Dell Inc.",
    "A4:1F:72": "Dell Inc.",
    "A4:BA:DB": "Dell Inc.",
    "AC:16:2D": "Hewlett-Packard",
    "B0:83:FE": "Dell Inc.",
    "B4:E1:0F": "Dell Inc.",
    "B8:2A:72": "Dell Inc.",
    "BC:30:5B": "Dell Inc.",
    "C8:1F:66": "Huawei Technologies",
    "C8:F7:50": "Dell Inc.",
    "CC:48:3A": "Dell Inc.",
    "D0:67:E5": "Dell Inc.",
    "D4:81:D7": "Dell Inc.",
    "D4:AE:52": "Dell Inc.",
    "D4:BE:D9": "Dell Inc.",
    "DC:A6:32": "Raspberry Pi Foundation",
    "E0:DB:55": "Dell Inc.",
    "E4:11:5B": "Hewlett-Packard",
    "EC:F4:BB": "Dell Inc.",
    "F0:1F:AF": "Dell Inc.",
    "F4:8E:38": "Dell Inc.",
    "F8:B1:56": "Dell Inc.",
    "FC:15:B4": "Hewlett-Packard",
}


@register_plugin
class MACLookupPlugin(Plugin):
    """MAC地址查询插件"""
    
    name = "mac_lookup"
    description = "MAC地址厂商查询"
    category = "utils"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        return True, None
    
    def get_required_params(self) -> List[str]:
        """获取必需参数"""
        return ["mac"]
    
    def run(self, params: Dict[str, Any]) -> PluginResult:
        """
        执行MAC地址查询
        
        参数:
            mac: MAC地址
        """
        mac_input = params.get("mac", "")
        
        if not mac_input:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定MAC地址",
                data={}
            )
        
        # 规范化MAC地址
        normalized = self._normalize_mac(mac_input)
        
        if not normalized:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"无效的MAC地址格式: {mac_input}",
                data={}
            )
        
        # 查询厂商
        vendor = self._lookup_vendor(normalized)
        
        # 获取所有格式
        formats = self._get_all_formats(normalized)
        
        # 显示结果
        self._display_results(mac_input, normalized, vendor, formats)
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"MAC查询完成: {vendor or '未知厂商'}",
            data={
                "input": mac_input,
                "normalized": normalized,
                "vendor": vendor,
                "formats": formats,
            }
        )
    
    def _normalize_mac(self, mac: str) -> Optional[str]:
        """规范化MAC地址为 XX:XX:XX:XX:XX:XX 格式"""
        # 移除常见分隔符
        mac = mac.strip().upper()
        mac = re.sub(r'[:\-\.\s]', '', mac)
        
        # 验证长度
        if len(mac) != 12:
            return None
        
        # 验证是否为十六进制
        if not re.match(r'^[0-9A-F]{12}$', mac):
            return None
        
        # 格式化为 XX:XX:XX:XX:XX:XX
        return ':'.join(mac[i:i+2] for i in range(0, 12, 2))
    
    def _lookup_vendor(self, mac: str) -> Optional[str]:
        """查询MAC地址厂商"""
        # 获取OUI (前3字节)
        oui = mac[:8]  # XX:XX:XX
        
        return COMMON_OUI_DATABASE.get(oui)
    
    def _get_all_formats(self, mac: str) -> Dict[str, str]:
        """获取所有MAC地址格式"""
        # 移除分隔符获取纯净MAC
        raw = mac.replace(':', '')
        
        return {
            "colon": mac,  # XX:XX:XX:XX:XX:XX
            "hyphen": '-'.join(mac.split(':')),  # XX-XX-XX-XX-XX-XX
            "dot": '.'.join(raw[i:i+4] for i in range(0, 12, 4)),  # XXXX.XXXX.XXXX
            "bare": raw,  # XXXXXXXXXXXX
            "cisco": '.'.join(raw[i:i+4].lower() for i in range(0, 12, 4)),  # xxxx.xxxx.xxxx
            "linux": ':'.join(raw[i:i+2].lower() for i in range(0, 12, 2)),  # xx:xx:xx:xx:xx:xx
            "windows": '-'.join(raw[i:i+2] for i in range(0, 12, 2)),  # XX-XX-XX-XX-XX-XX
        }
    
    def _display_results(
        self,
        mac_input: str,
        normalized: str,
        vendor: Optional[str],
        formats: Dict[str, str],
    ) -> None:
        """显示查询结果"""
        from netops_toolkit.ui.theme import console
        
        # 基本信息
        info = {
            "输入": mac_input,
            "规范格式": normalized,
            "厂商": vendor or "[未知]",
            "OUI": normalized[:8],
            "设备ID": normalized[9:],
        }
        
        panel = create_summary_panel("MAC地址查询", info)
        console.print(panel)
        
        # 各种格式
        console.print("\n[bold cyan]格式转换:[/bold cyan]")
        console.print(f"  冒号分隔 (标准): [green]{formats['colon']}[/green]")
        console.print(f"  横线分隔 (Windows): [green]{formats['hyphen']}[/green]")
        console.print(f"  点分隔 (Cisco): [green]{formats['cisco']}[/green]")
        console.print(f"  Linux风格: [green]{formats['linux']}[/green]")
        console.print(f"  无分隔符: [green]{formats['bare']}[/green]")
        
        # MAC类型判断
        first_byte = int(normalized[:2], 16)
        console.print("\n[bold cyan]MAC类型:[/bold cyan]")
        
        if first_byte & 0x01:
            console.print("  [yellow]• 多播地址 (Multicast)[/yellow]")
        else:
            console.print("  [green]• 单播地址 (Unicast)[/green]")
        
        if first_byte & 0x02:
            console.print("  [yellow]• 本地管理地址 (LAA)[/yellow]")
        else:
            console.print("  [green]• 全局唯一地址 (UAA)[/green]")
        
        console.print()


def lookup_mac_vendor(mac: str) -> Optional[str]:
    """
    便捷函数: 查询MAC地址厂商
    
    Args:
        mac: MAC地址
        
    Returns:
        厂商名称或None
    """
    plugin = MACLookupPlugin()
    normalized = plugin._normalize_mac(mac)
    if normalized:
        return plugin._lookup_vendor(normalized)
    return None


def normalize_mac(mac: str, format_type: str = "colon") -> Optional[str]:
    """
    便捷函数: 规范化MAC地址格式
    
    Args:
        mac: MAC地址
        format_type: 格式类型 (colon, hyphen, dot, bare, cisco, linux, windows)
        
    Returns:
        格式化后的MAC地址
    """
    plugin = MACLookupPlugin()
    normalized = plugin._normalize_mac(mac)
    if normalized:
        formats = plugin._get_all_formats(normalized)
        return formats.get(format_type, normalized)
    return None


__all__ = ["MACLookupPlugin", "lookup_mac_vendor", "normalize_mac"]
