"""
SNMP 查询插件

支持SNMP v1/v2c的Get和Walk操作。
"""

import subprocess
import platform
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
from rich.table import Table

logger = get_logger(__name__)

# 常用OID
COMMON_OIDS = {
    "sysDescr": "1.3.6.1.2.1.1.1.0",
    "sysObjectID": "1.3.6.1.2.1.1.2.0",
    "sysUpTime": "1.3.6.1.2.1.1.3.0",
    "sysContact": "1.3.6.1.2.1.1.4.0",
    "sysName": "1.3.6.1.2.1.1.5.0",
    "sysLocation": "1.3.6.1.2.1.1.6.0",
    "ifNumber": "1.3.6.1.2.1.2.1.0",
    "ifTable": "1.3.6.1.2.1.2.2",
}


@register_plugin
class SnmpQueryPlugin(Plugin):
    """SNMP查询插件"""
    
    name = "SNMP查询"
    category = PluginCategory.DIAGNOSTICS
    description = "SNMP Get/Walk查询网络设备"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="host",
                param_type=str,
                description="目标主机",
                required=True,
            ),
            ParamSpec(
                name="oid",
                param_type=str,
                description="OID (可用名称: sysDescr, sysName, sysUpTime等)",
                required=False,
                default="sysDescr",
            ),
            ParamSpec(
                name="community",
                param_type=str,
                description="Community字符串",
                required=False,
                default="public",
            ),
            ParamSpec(
                name="operation",
                param_type=str,
                description="操作类型: get 或 walk",
                required=False,
                default="get",
            ),
            ParamSpec(
                name="version",
                param_type=str,
                description="SNMP版本: 1 或 2c",
                required=False,
                default="2c",
            ),
        ]
    
    def run(
        self,
        host: str,
        oid: str = "sysDescr",
        community: str = "public",
        operation: str = "get",
        version: str = "2c",
        **kwargs,
    ) -> PluginResult:
        """执行SNMP查询"""
        start_time = datetime.now()
        
        # 解析OID
        actual_oid = COMMON_OIDS.get(oid, oid)
        
        console.print(f"[cyan]SNMP {operation.upper()} 查询[/cyan]")
        console.print(f"[cyan]目标: {host}[/cyan]")
        console.print(f"[cyan]OID: {actual_oid} ({oid})[/cyan]")
        console.print(f"[cyan]版本: SNMPv{version}[/cyan]\n")
        
        # 显示常用OID参考
        console.print("[dim]常用OID参考:[/dim]")
        for name, oid_val in list(COMMON_OIDS.items())[:6]:
            console.print(f"  [dim]{name}: {oid_val}[/dim]")
        console.print()
        
        # 尝试使用Python原生实现简单SNMP
        try:
            result = self._simple_snmp_get(host, actual_oid, community, version)
            
            if result:
                console.print("[green]✅ 查询成功[/green]\n")
                
                table = Table(title="SNMP查询结果")
                table.add_column("属性", style="cyan")
                table.add_column("值", style="green")
                
                table.add_row("主机", host)
                table.add_row("OID", actual_oid)
                table.add_row("值", result)
                
                console.print(table)
                
                return PluginResult(
                    status=ResultStatus.SUCCESS,
                    message=f"SNMP查询成功",
                    data={"host": host, "oid": actual_oid, "value": result},
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            else:
                raise Exception("无响应")
                
        except Exception as e:
            # 如果原生实现失败,尝试系统命令
            cmd_result = self._try_snmp_command(host, actual_oid, community, version, operation)
            
            if cmd_result:
                console.print("[green]✅ 查询成功 (via snmpget/snmpwalk)[/green]\n")
                console.print(cmd_result)
                
                return PluginResult(
                    status=ResultStatus.SUCCESS,
                    message="SNMP查询成功",
                    data={"host": host, "oid": actual_oid, "output": cmd_result},
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            
            console.print(f"[yellow]⚠️ SNMP查询失败: {e}[/yellow]\n")
            console.print("[yellow]提示:[/yellow]")
            console.print("  • 确保目标设备已启用SNMP服务")
            console.print("  • 检查community字符串是否正确")
            console.print("  • 检查防火墙是否允许UDP 161端口")
            console.print("  • 可安装 net-snmp 工具获得更好支持")
            
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"SNMP查询失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    def _simple_snmp_get(
        self, host: str, oid: str, community: str, version: str
    ) -> Optional[str]:
        """简单的SNMP GET实现 (使用socket)"""
        import socket
        import struct
        
        # 这是一个简化的SNMP v2c GET请求
        # 在生产环境中建议使用 pysnmp 库
        
        try:
            # 构建简化的SNMP GET请求包
            # 这里只做基本实现,实际应用建议使用专业库
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            
            # 解析OID为数字序列
            oid_parts = [int(x) for x in oid.split('.')]
            
            # 编码OID
            oid_encoded = self._encode_oid(oid_parts)
            
            # 构建SNMP消息
            request_id = 1
            error_status = 0
            error_index = 0
            
            # varbind (OID + NULL)
            varbind = (
                bytes([0x30]) +  # SEQUENCE
                self._encode_length(len(oid_encoded) + 2) +
                oid_encoded +
                bytes([0x05, 0x00])  # NULL
            )
            
            # varbind list
            varbind_list = (
                bytes([0x30]) +  # SEQUENCE
                self._encode_length(len(varbind)) +
                varbind
            )
            
            # PDU
            pdu_content = (
                self._encode_integer(request_id) +
                self._encode_integer(error_status) +
                self._encode_integer(error_index) +
                varbind_list
            )
            
            pdu = (
                bytes([0xa0]) +  # GET-REQUEST
                self._encode_length(len(pdu_content)) +
                pdu_content
            )
            
            # community string
            community_encoded = (
                bytes([0x04]) +  # OCTET STRING
                self._encode_length(len(community)) +
                community.encode('ascii')
            )
            
            # version
            snmp_version = 0 if version == "1" else 1
            version_encoded = self._encode_integer(snmp_version)
            
            # 完整消息
            message_content = version_encoded + community_encoded + pdu
            message = (
                bytes([0x30]) +  # SEQUENCE
                self._encode_length(len(message_content)) +
                message_content
            )
            
            # 发送请求
            sock.sendto(message, (host, 161))
            
            # 接收响应
            response, addr = sock.recvfrom(65535)
            sock.close()
            
            # 解析响应 (简化)
            return self._parse_snmp_response(response)
            
        except socket.timeout:
            return None
        except Exception as e:
            logger.debug(f"SNMP native error: {e}")
            return None
    
    def _encode_length(self, length: int) -> bytes:
        """编码BER长度"""
        if length < 128:
            return bytes([length])
        elif length < 256:
            return bytes([0x81, length])
        else:
            return bytes([0x82, (length >> 8) & 0xff, length & 0xff])
    
    def _encode_integer(self, value: int) -> bytes:
        """编码BER整数"""
        if value == 0:
            return bytes([0x02, 0x01, 0x00])
        
        result = []
        while value > 0:
            result.insert(0, value & 0xff)
            value >>= 8
        
        # 如果最高位为1,需要添加前导0
        if result[0] & 0x80:
            result.insert(0, 0)
        
        return bytes([0x02, len(result)] + result)
    
    def _encode_oid(self, oid_parts: List[int]) -> bytes:
        """编码OID"""
        if len(oid_parts) < 2:
            return bytes([0x06, 0x00])
        
        # 前两个数字特殊编码
        result = [oid_parts[0] * 40 + oid_parts[1]]
        
        for part in oid_parts[2:]:
            if part < 128:
                result.append(part)
            else:
                # 多字节编码
                temp = []
                while part > 0:
                    temp.insert(0, (part & 0x7f) | 0x80)
                    part >>= 7
                temp[-1] &= 0x7f  # 最后一个字节不设置高位
                result.extend(temp)
        
        return bytes([0x06, len(result)] + result)
    
    def _parse_snmp_response(self, response: bytes) -> Optional[str]:
        """解析SNMP响应 (简化版)"""
        try:
            # 跳过外层SEQUENCE
            idx = 2 if response[1] < 128 else (2 + (response[1] & 0x7f))
            
            # 跳过version
            idx += 3
            
            # 解析community长度并跳过
            comm_len = response[idx + 1]
            idx += 2 + comm_len
            
            # 跳过PDU头
            idx += 2 if response[idx + 1] < 128 else (2 + (response[idx + 1] & 0x7f))
            
            # 跳过request-id, error-status, error-index
            for _ in range(3):
                tag_len = response[idx + 1]
                idx += 2 + tag_len
            
            # 进入varbind-list
            idx += 2 if response[idx + 1] < 128 else (2 + (response[idx + 1] & 0x7f))
            
            # 进入varbind
            idx += 2 if response[idx + 1] < 128 else (2 + (response[idx + 1] & 0x7f))
            
            # 跳过OID
            oid_len = response[idx + 1]
            idx += 2 + oid_len
            
            # 解析值
            value_type = response[idx]
            value_len = response[idx + 1]
            value_data = response[idx + 2:idx + 2 + value_len]
            
            if value_type == 0x04:  # OCTET STRING
                return value_data.decode('utf-8', errors='replace')
            elif value_type == 0x02:  # INTEGER
                result = 0
                for b in value_data:
                    result = (result << 8) | b
                return str(result)
            elif value_type == 0x43:  # TimeTicks
                ticks = 0
                for b in value_data:
                    ticks = (ticks << 8) | b
                # 转换为可读时间
                seconds = ticks // 100
                days = seconds // 86400
                hours = (seconds % 86400) // 3600
                minutes = (seconds % 3600) // 60
                secs = seconds % 60
                return f"{days}天 {hours}小时 {minutes}分钟 {secs}秒"
            else:
                return value_data.hex()
                
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
    
    def _try_snmp_command(
        self, host: str, oid: str, community: str, version: str, operation: str
    ) -> Optional[str]:
        """尝试使用系统SNMP命令"""
        if platform.system() == "Windows":
            return None
        
        try:
            cmd = "snmpget" if operation == "get" else "snmpwalk"
            result = subprocess.run(
                [cmd, "-v", version, "-c", community, host, oid],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            return None
            
        except FileNotFoundError:
            return None
        except Exception:
            return None
