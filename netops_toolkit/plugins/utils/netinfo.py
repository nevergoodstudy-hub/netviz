"""
网络接口信息插件

显示本机网络接口信息,包括IP地址、MAC地址、子网掩码、网关等。
"""

import socket
import subprocess
import re
import os
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
from netops_toolkit.ui.components import create_result_table, create_summary_panel

logger = get_logger(__name__)


@register_plugin
class NetInfoPlugin(Plugin):
    """网络接口信息插件"""
    
    name = "网络接口信息"
    category = PluginCategory.UTILS
    description = "显示本机网络接口和IP配置"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return []
    
    def run(self, **kwargs) -> PluginResult:
        """获取网络接口信息"""
        start_time = datetime.now()
        
        console.print("[cyan]正在获取网络接口信息...[/cyan]\n")
        
        try:
            interfaces = self._get_interfaces()
            gateway = self._get_default_gateway()
            dns_servers = self._get_dns_servers()
            hostname = socket.gethostname()
            
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"获取网络信息失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 显示主机信息
        host_info = {
            "主机名": hostname,
            "默认网关": gateway or "未配置",
            "DNS服务器": ", ".join(dns_servers[:3]) if dns_servers else "未配置",
        }
        console.print(create_summary_panel("主机信息", host_info))
        
        # 显示接口列表
        self._display_interfaces(interfaces)
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"获取到 {len(interfaces)} 个网络接口",
            data={
                "hostname": hostname,
                "interfaces": interfaces,
                "gateway": gateway,
                "dns": dns_servers,
            },
            start_time=start_time,
            end_time=datetime.now(),
        )
    
    def _get_interfaces(self) -> List[Dict[str, Any]]:
        """获取网络接口列表"""
        interfaces = []
        
        if os.name == 'nt':
            interfaces = self._get_interfaces_windows()
        else:
            interfaces = self._get_interfaces_unix()
        
        return interfaces
    
    def _get_interfaces_windows(self) -> List[Dict[str, Any]]:
        """Windows系统获取接口"""
        interfaces = []
        
        try:
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore'
            )
            
            output = result.stdout
            
            # 解析输出
            current_adapter = None
            
            for line in output.split('\n'):
                line = line.strip()
                
                # 新适配器
                if '适配器' in line or 'adapter' in line.lower():
                    if current_adapter:
                        interfaces.append(current_adapter)
                    
                    # 提取适配器名称
                    name = line.replace(':', '').strip()
                    current_adapter = {
                        'name': name,
                        'ipv4': '',
                        'ipv6': '',
                        'mac': '',
                        'mask': '',
                        'gateway': '',
                        'dhcp': False,
                        'status': 'up',
                    }
                
                elif current_adapter:
                    # IPv4 地址
                    if 'IPv4' in line or 'IP 地址' in line or 'IP Address' in line:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if match:
                            current_adapter['ipv4'] = match.group(1)
                    
                    # IPv6 地址
                    elif 'IPv6' in line:
                        match = re.search(r'([0-9a-fA-F:]+)(%\d+)?$', line)
                        if match:
                            current_adapter['ipv6'] = match.group(1)
                    
                    # MAC 地址
                    elif '物理地址' in line or 'Physical Address' in line:
                        match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', line)
                        if match:
                            current_adapter['mac'] = match.group(0)
                    
                    # 子网掩码
                    elif '子网掩码' in line or 'Subnet Mask' in line:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if match:
                            current_adapter['mask'] = match.group(1)
                    
                    # 网关
                    elif '默认网关' in line or 'Default Gateway' in line:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if match:
                            current_adapter['gateway'] = match.group(1)
                    
                    # DHCP
                    elif 'DHCP' in line and ('是' in line or 'Yes' in line):
                        current_adapter['dhcp'] = True
                    
                    # 媒体状态断开
                    elif '媒体已断开' in line or 'Media disconnected' in line:
                        current_adapter['status'] = 'down'
            
            if current_adapter:
                interfaces.append(current_adapter)
            
        except Exception as e:
            logger.error(f"获取Windows接口失败: {e}")
        
        # 过滤有IP的接口
        return [i for i in interfaces if i.get('ipv4') or i.get('mac')]
    
    def _get_interfaces_unix(self) -> List[Dict[str, Any]]:
        """Unix/Linux系统获取接口"""
        interfaces = []
        
        try:
            # 使用 ip 命令
            result = subprocess.run(
                ['ip', 'addr'],
                capture_output=True,
                text=True
            )
            
            output = result.stdout
            current_iface = None
            
            for line in output.split('\n'):
                # 新接口
                match = re.match(r'\d+:\s+(\S+):', line)
                if match:
                    if current_iface:
                        interfaces.append(current_iface)
                    
                    current_iface = {
                        'name': match.group(1),
                        'ipv4': '',
                        'ipv6': '',
                        'mac': '',
                        'mask': '',
                        'status': 'down' if 'DOWN' in line else 'up',
                    }
                
                elif current_iface:
                    # MAC
                    match = re.search(r'link/ether\s+([0-9a-fA-F:]+)', line)
                    if match:
                        current_iface['mac'] = match.group(1)
                    
                    # IPv4
                    match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', line)
                    if match:
                        current_iface['ipv4'] = match.group(1)
                        # 计算掩码
                        prefix = int(match.group(2))
                        mask = '.'.join(str((0xffffffff << (32 - prefix) >> i) & 0xff) 
                                       for i in [24, 16, 8, 0])
                        current_iface['mask'] = mask
                    
                    # IPv6
                    match = re.search(r'inet6\s+([0-9a-fA-F:]+)/', line)
                    if match:
                        current_iface['ipv6'] = match.group(1)
            
            if current_iface:
                interfaces.append(current_iface)
                
        except Exception as e:
            logger.error(f"获取Unix接口失败: {e}")
        
        return [i for i in interfaces if i.get('ipv4') or i.get('mac')]
    
    def _get_default_gateway(self) -> Optional[str]:
        """获取默认网关"""
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['route', 'print', '0.0.0.0'],
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore'
                )
                match = re.search(r'0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
            else:
                result = subprocess.run(
                    ['ip', 'route', 'show', 'default'],
                    capture_output=True,
                    text=True
                )
                match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except:
            pass
        return None
    
    def _get_dns_servers(self) -> List[str]:
        """获取DNS服务器"""
        dns_servers = []
        
        try:
            if os.name == 'nt':
                result = subprocess.run(
                    ['ipconfig', '/all'],
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore'
                )
                
                for line in result.stdout.split('\n'):
                    if 'DNS' in line and 'Server' in line or 'DNS 服务器' in line:
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            dns_servers.append(match.group(1))
            else:
                # 读取 /etc/resolv.conf
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                parts = line.split()
                                if len(parts) >= 2:
                                    dns_servers.append(parts[1])
                except:
                    pass
        except:
            pass
        
        return dns_servers
    
    def _display_interfaces(self, interfaces: List[Dict]) -> None:
        """显示接口列表"""
        table = create_result_table(
            title="网络接口列表",
            columns=[
                ("接口名称", "name", "left"),
                ("状态", "status", "center"),
                ("IPv4地址", "ipv4", "left"),
                ("子网掩码", "mask", "left"),
                ("MAC地址", "mac", "left"),
            ],
        )
        
        for iface in interfaces:
            status = "[green]● UP[/green]" if iface.get('status') == 'up' else "[red]● DOWN[/red]"
            
            # 截断长名称
            name = iface.get('name', '')
            if len(name) > 25:
                name = name[:22] + "..."
            
            table.add_row(
                name,
                status,
                iface.get('ipv4', '-') or '-',
                iface.get('mask', '-') or '-',
                iface.get('mac', '-') or '-',
            )
        
        console.print(table)
