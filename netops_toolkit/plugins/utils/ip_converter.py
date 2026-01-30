"""
IP转换工具插件

支持IP地址在不同格式间的转换(十进制、二进制、十六进制、整数)。
"""

from typing import Any, Dict, List, Optional, Tuple
import ipaddress
import re

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, ParamSpec, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class IPConverterPlugin(Plugin):
    """IP转换工具插件"""
    
    name = "ip_converter"
    description = "IP地址格式转换"
    category = "utils"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        return True, None
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="ip",
                param_type=str,
                description="IP地址(支持多种输入格式)",
                required=True,
            ),
        ]
    
    def run(
        self,
        ip: str,
        **kwargs,
    ) -> PluginResult:
        """
        执行IP格式转换
        
        参数:
            ip: IP地址(支持多种输入格式)
        """
        ip_input = ip
        
        if not ip_input:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定IP地址",
                data={}
            )
        
        # 尝试解析输入
        parsed = self._parse_input(ip_input)
        
        if not parsed:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"无法解析输入: {ip_input}",
                data={}
            )
        
        # 转换为所有格式
        conversions = self._convert_to_all_formats(parsed)
        
        # 显示结果
        self._display_results(ip_input, conversions)
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message="IP转换完成",
            data={
                "input": ip_input,
                "conversions": conversions,
            }
        )
    
    def _parse_input(self, ip_input: str) -> Optional[ipaddress.IPv4Address]:
        """
        解析输入,支持多种格式
        
        支持格式:
        - 标准点分十进制: 192.168.1.1
        - 整数形式: 3232235777
        - 十六进制: 0xC0A80101
        - 二进制点分: 11000000.10101000.00000001.00000001
        """
        ip_input = ip_input.strip()
        
        # 1. 尝试标准格式
        try:
            return ipaddress.IPv4Address(ip_input)
        except ValueError:
            pass
        
        # 2. 尝试整数格式
        try:
            if ip_input.isdigit():
                int_value = int(ip_input)
                if 0 <= int_value <= 0xFFFFFFFF:
                    return ipaddress.IPv4Address(int_value)
        except ValueError:
            pass
        
        # 3. 尝试十六进制格式
        try:
            if ip_input.lower().startswith("0x"):
                int_value = int(ip_input, 16)
                if 0 <= int_value <= 0xFFFFFFFF:
                    return ipaddress.IPv4Address(int_value)
        except ValueError:
            pass
        
        # 4. 尝试二进制点分格式
        try:
            if "." in ip_input and all(c in "01." for c in ip_input):
                parts = ip_input.split(".")
                if len(parts) == 4:
                    octets = [int(p, 2) for p in parts]
                    if all(0 <= o <= 255 for o in octets):
                        return ipaddress.IPv4Address(".".join(str(o) for o in octets))
        except ValueError:
            pass
        
        return None
    
    def _convert_to_all_formats(
        self,
        ip: ipaddress.IPv4Address,
    ) -> Dict[str, Any]:
        """转换为所有格式"""
        int_value = int(ip)
        octets = [int(o) for o in str(ip).split(".")]
        
        return {
            # 基本格式
            "decimal": str(ip),
            "integer": int_value,
            "hex": f"0x{int_value:08X}",
            "hex_lower": f"0x{int_value:08x}",
            
            # 二进制格式
            "binary_dotted": ".".join(f"{o:08b}" for o in octets),
            "binary_full": f"{int_value:032b}",
            
            # 八进制
            "octal": f"0o{int_value:o}",
            
            # 单独的字节
            "octets": {
                "decimal": octets,
                "hex": [f"0x{o:02X}" for o in octets],
                "binary": [f"{o:08b}" for o in octets],
            },
            
            # 网络相关信息
            "class": self._get_ip_class(ip),
            "type": self._get_ip_type(ip),
            "reverse_dns": ip.reverse_pointer,
        }
    
    def _get_ip_class(self, ip: ipaddress.IPv4Address) -> str:
        """获取IP地址类别"""
        first_octet = int(str(ip).split(".")[0])
        
        if first_octet < 128:
            return "A"
        elif first_octet < 192:
            return "B"
        elif first_octet < 224:
            return "C"
        elif first_octet < 240:
            return "D (多播)"
        else:
            return "E (保留)"
    
    def _get_ip_type(self, ip: ipaddress.IPv4Address) -> str:
        """获取IP类型"""
        if ip.is_private:
            return "私有地址"
        elif ip.is_loopback:
            return "环回地址"
        elif ip.is_multicast:
            return "多播地址"
        elif ip.is_reserved:
            return "保留地址"
        elif ip.is_link_local:
            return "链路本地"
        elif ip.is_global:
            return "公网地址"
        else:
            return "未知"
    
    def _display_results(
        self,
        ip_input: str,
        conversions: Dict[str, Any],
    ) -> None:
        """显示转换结果"""
        from netops_toolkit.ui.theme import console
        
        # 主要格式
        main_formats = {
            "点分十进制": conversions["decimal"],
            "整数值": f"{conversions['integer']:,}",
            "十六进制": conversions["hex"],
            "二进制(点分)": conversions["binary_dotted"],
            "二进制(完整)": conversions["binary_full"],
            "八进制": conversions["octal"],
        }
        
        panel = create_summary_panel(f"IP转换: {ip_input}", main_formats)
        console.print(panel)
        
        # 附加信息
        console.print("\n[bold cyan]附加信息:[/bold cyan]")
        console.print(f"  IP类别: [green]{conversions['class']}[/green]")
        console.print(f"  地址类型: [green]{conversions['type']}[/green]")
        console.print(f"  反向DNS: [dim]{conversions['reverse_dns']}[/dim]")
        
        # 字节分解
        octets = conversions["octets"]
        console.print("\n[bold cyan]字节分解:[/bold cyan]")
        console.print(f"  十进制: {'.'.join(str(o) for o in octets['decimal'])}")
        console.print(f"  十六进制: {'.'.join(octets['hex'])}")
        console.print(f"  二进制: {'.'.join(octets['binary'])}")
        console.print()


def convert_ip(ip_input: str) -> Dict[str, Any]:
    """
    便捷函数: 转换IP地址
    
    Args:
        ip_input: IP地址输入
        
    Returns:
        转换结果字典
    """
    plugin = IPConverterPlugin()
    result = plugin.run({"ip": ip_input})
    return result.data.get("conversions", {})


def ip_to_int(ip: str) -> Optional[int]:
    """IP地址转整数"""
    try:
        return int(ipaddress.IPv4Address(ip))
    except ValueError:
        return None


def int_to_ip(value: int) -> Optional[str]:
    """整数转IP地址"""
    try:
        return str(ipaddress.IPv4Address(value))
    except ValueError:
        return None


__all__ = ["IPConverterPlugin", "convert_ip", "ip_to_int", "int_to_ip"]
