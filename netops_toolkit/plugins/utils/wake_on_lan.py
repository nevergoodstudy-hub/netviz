"""
Wake-on-LAN 插件

发送魔术包(Magic Packet)唤醒远程设备。
"""

import socket
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from netops_toolkit.core.logger import get_logger
from netops_toolkit.plugins import (
    Plugin,
    PluginCategory,
    PluginResult,
    ResultStatus,
    ParamSpec,
    register_plugin,
)
from netops_toolkit.ui.theme import console
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class WakeOnLanPlugin(Plugin):
    """Wake-on-LAN 插件"""
    
    name = "Wake-on-LAN"
    category = PluginCategory.UTILS
    description = "发送魔术包唤醒远程设备"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="mac",
                param_type=str,
                description="目标MAC地址",
                required=True,
            ),
            ParamSpec(
                name="broadcast",
                param_type=str,
                description="广播地址",
                required=False,
                default="255.255.255.255",
            ),
            ParamSpec(
                name="port",
                param_type=int,
                description="端口",
                required=False,
                default=9,
            ),
        ]
    
    def run(
        self,
        mac: str,
        broadcast: str = "255.255.255.255",
        port: int = 9,
        **kwargs,
    ) -> PluginResult:
        """发送Wake-on-LAN魔术包"""
        start_time = datetime.now()
        
        # 规范化MAC地址
        mac_normalized = self._normalize_mac(mac)
        
        if not mac_normalized:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"无效的MAC地址: {mac}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        console.print(f"[cyan]正在发送Wake-on-LAN魔术包...[/cyan]")
        console.print(f"[cyan]目标MAC: {mac_normalized}[/cyan]")
        console.print(f"[cyan]广播地址: {broadcast}:{port}[/cyan]\n")
        
        try:
            # 构造魔术包
            magic_packet = self._create_magic_packet(mac_normalized)
            
            # 发送
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, (broadcast, port))
            sock.close()
            
            console.print("[green]✅ 魔术包已发送![/green]\n")
            
            # 显示信息
            info = {
                "目标MAC": mac_normalized,
                "广播地址": broadcast,
                "端口": port,
                "包大小": f"{len(magic_packet)} 字节",
                "状态": "已发送",
            }
            
            console.print(create_summary_panel("Wake-on-LAN", info, timestamp=datetime.now()))
            
            console.print("\n[yellow]提示:[/yellow]")
            console.print("  • 确保目标设备已启用 Wake-on-LAN 功能")
            console.print("  • 确保目标设备在同一广播域内")
            console.print("  • 设备唤醒可能需要几秒钟时间")
            
            return PluginResult(
                status=ResultStatus.SUCCESS,
                message=f"已向 {mac_normalized} 发送魔术包",
                data={
                    "mac": mac_normalized,
                    "broadcast": broadcast,
                    "port": port,
                },
                start_time=start_time,
                end_time=datetime.now(),
            )
            
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"发送失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    def _normalize_mac(self, mac: str) -> Optional[str]:
        """规范化MAC地址"""
        # 移除所有分隔符
        mac_clean = re.sub(r'[^0-9a-fA-F]', '', mac)
        
        if len(mac_clean) != 12:
            return None
        
        # 验证十六进制
        try:
            int(mac_clean, 16)
        except ValueError:
            return None
        
        # 格式化为 XX:XX:XX:XX:XX:XX
        mac_upper = mac_clean.upper()
        return ':'.join(mac_upper[i:i+2] for i in range(0, 12, 2))
    
    def _create_magic_packet(self, mac: str) -> bytes:
        """创建魔术包"""
        # 将MAC地址转换为字节
        mac_bytes = bytes.fromhex(mac.replace(':', ''))
        
        # 魔术包格式: 6个0xFF + 16次MAC地址
        magic = b'\xff' * 6 + mac_bytes * 16
        
        return magic
