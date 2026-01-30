"""
路由表查看插件

显示系统路由表信息。
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
    get_route_command,
    run_command,
)
from rich.table import Table

logger = get_logger(__name__)


@register_plugin
class RouteTablePlugin(Plugin):
    """路由表查看插件"""
    
    name = "路由表"
    category = PluginCategory.DIAGNOSTICS
    description = "显示系统路由表信息"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="ipv6",
                param_type=bool,
                description="显示IPv6路由",
                required=False,
                default=False,
            ),
        ]
    
    def run(self, ipv6: bool = False, **kwargs) -> PluginResult:
        """获取路由表"""
        start_time = datetime.now()
        platform_info = get_platform()
        
        console.print(f"[cyan]获取系统路由表...[/cyan]")
        console.print(f"[cyan]操作系统: {platform_info.system.title()}[/cyan]")
        console.print(f"[cyan]协议: {'IPv6' if ipv6 else 'IPv4'}[/cyan]\n")
        
        try:
            if platform_info.is_windows:
                routes = self._get_windows_routes(ipv6)
            else:
                routes = self._get_unix_routes(ipv6, platform_info)
            
            if routes:
                console.print(f"[green]✅ 找到 {len(routes)} 条路由[/green]\n")
                
                # 创建表格
                table = Table(title=f"{'IPv6' if ipv6 else 'IPv4'} 路由表")
                table.add_column("目标网络", style="cyan")
                table.add_column("子网掩码/前缀", style="white")
                table.add_column("网关", style="green")
                table.add_column("接口", style="yellow")
                table.add_column("跃点数", style="magenta", justify="right")
                
                for route in routes:
                    table.add_row(
                        route.get("destination", ""),
                        route.get("mask", ""),
                        route.get("gateway", ""),
                        route.get("interface", ""),
                        str(route.get("metric", "")),
                    )
                
                console.print(table)
                
                # 显示默认网关
                default_routes = [r for r in routes if r.get("destination") in ("0.0.0.0", "::/0", "default")]
                if default_routes:
                    console.print("\n[yellow]默认网关:[/yellow]")
                    for dr in default_routes:
                        console.print(f"  • {dr.get('gateway')} via {dr.get('interface', 'N/A')}")
                
                return PluginResult(
                    status=ResultStatus.SUCCESS,
                    message=f"获取到 {len(routes)} 条路由",
                    data={"routes": routes},
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            else:
                console.print("[yellow]⚠️ 未能获取路由信息[/yellow]")
                return PluginResult(
                    status=ResultStatus.PARTIAL,
                    message="未能获取路由信息",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
                
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"获取路由表失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    def _get_windows_routes(self, ipv6: bool = False) -> List[Dict[str, Any]]:
        """获取Windows路由表"""
        routes = []
        
        try:
            cmd, cmd_type = get_route_command(ipv6)
            result = run_command(cmd, timeout=10)
            
            if result.returncode != 0:
                return routes
            
            output = result.stdout
            
            if ipv6:
                # 解析 netsh ipv6 输出
                for line in output.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('Publish') or line.startswith('Type'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 4:
                        routes.append({
                            "destination": parts[2] if len(parts) > 2 else "",
                            "mask": "",
                            "gateway": parts[3] if len(parts) > 3 else "",
                            "interface": parts[-1] if parts else "",
                            "metric": parts[1] if len(parts) > 1 else "",
                        })
            else:
                # 解析 route print 输出
                in_routes = False
                for line in output.split('\n'):
                    line = line.strip()
                    
                    if 'Network Destination' in line or '网络目标' in line:
                        in_routes = True
                        continue
                    
                    if in_routes and line:
                        # 检查是否到了持久路由部分
                        if '==' in line or 'Persistent' in line or '持久' in line:
                            in_routes = False
                            continue
                        
                        parts = line.split()
                        if len(parts) >= 4:
                            # 验证是否是IP地址格式
                            if re.match(r'\d+\.\d+\.\d+\.\d+', parts[0]):
                                routes.append({
                                    "destination": parts[0],
                                    "mask": parts[1],
                                    "gateway": parts[2],
                                    "interface": parts[3],
                                    "metric": parts[4] if len(parts) > 4 else "",
                                })
            
        except Exception as e:
            logger.error(f"获取Windows路由失败: {e}")
        
        return routes
    
    def _get_unix_routes(self, ipv6: bool = False, platform_info=None) -> List[Dict[str, Any]]:
        """获取Unix/Linux/macOS/BSD 路由表"""
        routes = []
        
        if platform_info is None:
            platform_info = get_platform()
        
        try:
            cmd, cmd_type = get_route_command(ipv6)
            result = run_command(cmd, timeout=10)
            
            if result.returncode != 0:
                # 尝试备用命令
                result = run_command(["netstat", "-rn"], timeout=10)
                cmd_type = "netstat_generic"
            
            if result.returncode != 0:
                return routes
            
            output = result.stdout
            
            # 解析 ip route 输出
            if cmd_type == "ip":
                for line in output.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 1:
                        route = {
                            "destination": parts[0],
                            "mask": "",
                            "gateway": "",
                            "interface": "",
                            "metric": "",
                        }
                        
                        for i, part in enumerate(parts):
                            if part == "via" and i + 1 < len(parts):
                                route["gateway"] = parts[i + 1]
                            elif part == "dev" and i + 1 < len(parts):
                                route["interface"] = parts[i + 1]
                            elif part == "metric" and i + 1 < len(parts):
                                route["metric"] = parts[i + 1]
                        
                        routes.append(route)
            else:
                # 解析 netstat -rn 输出 (macOS/BSD/Linux)
                for line in output.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('Routing') or line.startswith('Destination') or line.startswith('Internet'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 4:
                        if platform_info.is_macos or platform_info.is_bsd:
                            routes.append({
                                "destination": parts[0],
                                "mask": "",
                                "gateway": parts[1],
                                "interface": parts[-1],
                                "metric": "",
                            })
                        else:
                            routes.append({
                                "destination": parts[0],
                                "mask": parts[2] if len(parts) > 2 else "",
                                "gateway": parts[1],
                                "interface": parts[-1],
                                "metric": parts[4] if len(parts) > 4 else "",
                            })
            
        except Exception as e:
            logger.error(f"获取Unix路由失败: {e}")
        
        return routes
