"""
Netstat 插件

查看本机网络连接和监听端口。
支持 Windows、Linux、macOS 和 BSD 系统。
"""

import subprocess
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
from netops_toolkit.utils.platform_utils import (
    get_platform,
    get_netstat_command,
    run_command,
)
from rich.table import Table

logger = get_logger(__name__)


@register_plugin
class NetstatPlugin(Plugin):
    """Netstat插件"""
    
    name = "Netstat"
    category = PluginCategory.DIAGNOSTICS
    description = "查看网络连接和监听端口"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="mode",
                param_type=str,
                description="模式: listen(监听端口), established(已建立), all(全部)",
                required=False,
                default="listen",
            ),
            ParamSpec(
                name="protocol",
                param_type=str,
                description="协议: tcp, udp, all",
                required=False,
                default="all",
            ),
        ]
    
    def run(
        self,
        mode: str = "listen",
        protocol: str = "all",
        **kwargs,
    ) -> PluginResult:
        """获取网络连接信息"""
        start_time = datetime.now()
        platform_info = get_platform()
        
        console.print(f"[cyan]获取网络连接信息...[/cyan]")
        console.print(f"[cyan]模式: {mode}[/cyan]")
        console.print(f"[cyan]协议: {protocol}[/cyan]\n")
        
        try:
            if platform_info.is_windows:
                connections = self._get_windows_netstat(mode, protocol)
            else:
                connections = self._get_unix_netstat(mode, protocol, platform_info)
            
            if connections:
                # 统计
                tcp_count = len([c for c in connections if c.get("protocol", "").upper().startswith("TCP")])
                udp_count = len([c for c in connections if c.get("protocol", "").upper().startswith("UDP")])
                
                console.print(f"[green]✅ 找到 {len(connections)} 个连接[/green]")
                console.print(f"[dim]TCP: {tcp_count}, UDP: {udp_count}[/dim]\n")
                
                # 创建表格
                table = Table(title=f"网络连接 ({mode})")
                table.add_column("协议", style="cyan", width=8)
                table.add_column("本地地址", style="green")
                table.add_column("远程地址", style="yellow")
                table.add_column("状态", style="magenta")
                table.add_column("PID/进程", style="white")
                
                for conn in connections[:50]:  # 限制显示数量
                    status = conn.get("state", "")
                    status_color = self._get_status_color(status)
                    
                    table.add_row(
                        conn.get("protocol", ""),
                        conn.get("local_address", ""),
                        conn.get("remote_address", ""),
                        f"[{status_color}]{status}[/{status_color}]",
                        conn.get("pid", ""),
                    )
                
                if len(connections) > 50:
                    console.print(f"[dim](仅显示前50条,共 {len(connections)} 条)[/dim]\n")
                
                console.print(table)
                
                # 按端口统计监听服务
                if mode == "listen":
                    listen_ports = {}
                    for conn in connections:
                        local = conn.get("local_address", "")
                        if ":" in local:
                            port = local.rsplit(":", 1)[-1]
                            proto = conn.get("protocol", "TCP")
                            key = f"{proto}:{port}"
                            listen_ports[key] = conn.get("pid", "")
                    
                    if listen_ports:
                        console.print("\n[yellow]监听端口汇总:[/yellow]")
                        for port_key, pid in sorted(listen_ports.items(), key=lambda x: int(x[0].split(":")[1]) if x[0].split(":")[1].isdigit() else 0):
                            console.print(f"  • {port_key} - PID: {pid or 'N/A'}")
                
                return PluginResult(
                    status=ResultStatus.SUCCESS,
                    message=f"获取到 {len(connections)} 个连接",
                    data={"connections": connections},
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            else:
                console.print("[yellow]⚠️ 未找到符合条件的连接[/yellow]")
                return PluginResult(
                    status=ResultStatus.PARTIAL,
                    message="未找到连接",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
                
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"获取网络连接失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    def _get_status_color(self, status: str) -> str:
        """获取状态颜色"""
        status_colors = {
            "LISTEN": "green",
            "LISTENING": "green",
            "ESTABLISHED": "cyan",
            "TIME_WAIT": "yellow",
            "CLOSE_WAIT": "yellow",
            "SYN_SENT": "magenta",
            "SYN_RECV": "magenta",
            "FIN_WAIT1": "red",
            "FIN_WAIT2": "red",
            "CLOSED": "dim",
        }
        return status_colors.get(status.upper(), "white")
    
    def _get_windows_netstat(self, mode: str, protocol: str) -> List[Dict[str, Any]]:
        """获取Windows网络连接"""
        connections = []
        
        try:
            # Windows netstat -ano
            result = run_command(
                ["netstat", "-ano"],
                timeout=30,
            )
            
            if result.returncode != 0:
                return connections
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 4:
                    continue
                
                proto = parts[0].upper()
                
                # 过滤协议
                if protocol != "all":
                    if protocol.upper() == "TCP" and not proto.startswith("TCP"):
                        continue
                    if protocol.upper() == "UDP" and not proto.startswith("UDP"):
                        continue
                
                # 解析
                if proto.startswith("TCP"):
                    if len(parts) >= 5:
                        local_addr = parts[1]
                        remote_addr = parts[2]
                        state = parts[3]
                        pid = parts[4]
                        
                        # 过滤模式
                        if mode == "listen" and state.upper() not in ("LISTENING", "LISTEN"):
                            continue
                        if mode == "established" and state.upper() != "ESTABLISHED":
                            continue
                        
                        connections.append({
                            "protocol": proto,
                            "local_address": local_addr,
                            "remote_address": remote_addr,
                            "state": state,
                            "pid": pid,
                        })
                elif proto.startswith("UDP"):
                    if len(parts) >= 4:
                        local_addr = parts[1]
                        remote_addr = parts[2] if parts[2] != "*:*" else ""
                        pid = parts[-1]
                        
                        if mode == "established":
                            continue  # UDP没有established状态
                        
                        connections.append({
                            "protocol": proto,
                            "local_address": local_addr,
                            "remote_address": remote_addr,
                            "state": "LISTEN" if mode == "listen" else "",
                            "pid": pid,
                        })
            
        except Exception as e:
            logger.error(f"获取Windows netstat失败: {e}")
        
        return connections
    
    def _get_unix_netstat(self, mode: str, protocol: str, platform_info=None) -> List[Dict[str, Any]]:
        """获取Unix/Linux/macOS/BSD 网络连接"""
        connections = []
        
        if platform_info is None:
            platform_info = get_platform()
        
        try:
            # 使用跨平台工具获取命令
            cmd, cmd_type = get_netstat_command(mode)
            
            result = run_command(cmd, timeout=30)
            
            if result.returncode != 0:
                return connections
            
            # 根据命令类型选择解析器
            if cmd_type == "ss":
                return self._parse_ss_output(result.stdout, mode, protocol)
            elif cmd_type in ("netstat_bsd", "netstat_generic"):
                return self._parse_netstat_output(result.stdout, mode, protocol, platform_info)
            else:
                return self._parse_netstat_output(result.stdout, mode, protocol, platform_info)
            
        except Exception as e:
            logger.error(f"获取Unix netstat失败: {e}")
        
        return connections
    
    def _parse_ss_output(self, output: str, mode: str, protocol: str) -> List[Dict[str, Any]]:
        """解析ss命令输出"""
        connections = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('Netid') or line.startswith('State'):
                continue
            
            parts = line.split()
            if len(parts) < 5:
                continue
            
            proto = parts[0].upper()
            
            # 过滤协议
            if protocol != "all":
                if protocol.upper() == "TCP" and proto != "TCP":
                    continue
                if protocol.upper() == "UDP" and proto != "UDP":
                    continue
            
            state = parts[1]
            local_addr = parts[4]
            remote_addr = parts[5] if len(parts) > 5 else ""
            
            # 过滤模式
            if mode == "listen" and state.upper() not in ("LISTEN", "UNCONN"):
                continue
            if mode == "established" and state.upper() != "ESTAB":
                continue
            
            connections.append({
                "protocol": proto,
                "local_address": local_addr,
                "remote_address": remote_addr,
                "state": state,
                "pid": "",
            })
        
        return connections
    
    def _parse_netstat_output(
        self, output: str, mode: str, protocol: str, platform_info
    ) -> List[Dict[str, Any]]:
        """解析netstat命令输出"""
        connections = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or 'Active' in line or 'Proto' in line:
                continue
            
            parts = line.split()
            if len(parts) < 4:
                continue
            
            proto = parts[0].upper()
            
            # 过滤协议
            if protocol != "all":
                if protocol.upper() == "TCP" and not proto.startswith("TCP"):
                    continue
                if protocol.upper() == "UDP" and not proto.startswith("UDP"):
                    continue
            
            if platform_info.is_macos or platform_info.is_bsd:
                # macOS/BSD 格式
                if proto.startswith("TCP"):
                    local_addr = parts[3] if len(parts) > 3 else ""
                    remote_addr = parts[4] if len(parts) > 4 else ""
                    state = parts[5] if len(parts) > 5 else ""
                else:
                    local_addr = parts[3] if len(parts) > 3 else ""
                    remote_addr = parts[4] if len(parts) > 4 else ""
                    state = ""
            else:
                # Linux 格式
                local_addr = parts[3] if len(parts) > 3 else ""
                remote_addr = parts[4] if len(parts) > 4 else ""
                state = parts[5] if len(parts) > 5 and proto.startswith("TCP") else ""
            
            # 过滤模式
            if mode == "listen" and state.upper() not in ("LISTEN", "LISTENING", ""):
                if proto.startswith("TCP"):
                    continue
            if mode == "established" and state.upper() != "ESTABLISHED":
                continue
            
            connections.append({
                "protocol": proto,
                "local_address": local_addr,
                "remote_address": remote_addr,
                "state": state,
                "pid": "",
            })
        
        return connections
