"""
批量主机存活检测插件

快速扫描网段内存活主机,支持ICMP和TCP多种探测方式。
"""

import socket
import struct
import time
import ipaddress
import concurrent.futures
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

logger = get_logger(__name__)


@register_plugin
class HostDiscoveryPlugin(Plugin):
    """批量主机存活检测插件"""
    
    name = "主机发现"
    category = PluginCategory.DIAGNOSTICS
    description = "批量检测网段内存活主机"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="target",
                param_type=str,
                description="目标网段 (如: 192.168.1.0/24) 或IP范围 (如: 192.168.1.1-254)",
                required=True,
            ),
            ParamSpec(
                name="method",
                param_type=str,
                description="探测方式: ping, tcp, both",
                required=False,
                default="tcp",
            ),
            ParamSpec(
                name="ports",
                param_type=str,
                description="TCP探测端口 (逗号分隔)",
                required=False,
                default="22,80,443,3389",
            ),
            ParamSpec(
                name="timeout",
                param_type=float,
                description="超时时间(秒)",
                required=False,
                default=1.0,
            ),
            ParamSpec(
                name="workers",
                param_type=int,
                description="并发数",
                required=False,
                default=50,
            ),
        ]
    
    def run(
        self,
        target: str,
        method: str = "tcp",
        ports: str = "22,80,443,3389",
        timeout: float = 1.0,
        workers: int = 50,
        **kwargs,
    ) -> PluginResult:
        """执行主机发现"""
        start_time = datetime.now()
        
        # 解析目标
        try:
            hosts = self._parse_target(target)
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"无效的目标: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        if not hosts:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="未找到有效的目标主机",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 解析端口
        tcp_ports = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
        
        console.print(f"[cyan]开始主机发现扫描...[/cyan]")
        console.print(f"[cyan]目标: {target} ({len(hosts)} 个IP)[/cyan]")
        console.print(f"[cyan]方式: {method}[/cyan]")
        if method in ("tcp", "both"):
            console.print(f"[cyan]端口: {', '.join(map(str, tcp_ports))}[/cyan]")
        console.print(f"[cyan]并发: {workers}, 超时: {timeout}s[/cyan]\n")
        
        # 执行扫描
        alive_hosts = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("扫描中...", total=len(hosts))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {}
                
                for host in hosts:
                    future = executor.submit(
                        self._check_host, host, method, tcp_ports, timeout
                    )
                    futures[future] = host
                
                for future in concurrent.futures.as_completed(futures):
                    host = futures[future]
                    progress.update(task, advance=1)
                    
                    try:
                        result = future.result()
                        if result["alive"]:
                            alive_hosts.append(result)
                    except Exception as e:
                        logger.debug(f"检测 {host} 失败: {e}")
        
        # 排序结果
        alive_hosts.sort(key=lambda x: [int(i) for i in x["ip"].split(".")])
        
        # 显示结果
        console.print(f"\n[green]✅ 发现 {len(alive_hosts)} 个存活主机[/green]\n")
        
        if alive_hosts:
            table = Table(title="存活主机列表")
            table.add_column("IP地址", style="cyan")
            table.add_column("响应方式", style="green")
            table.add_column("开放端口", style="yellow")
            table.add_column("延迟", style="magenta", justify="right")
            
            for host in alive_hosts:
                open_ports = ", ".join(map(str, host.get("open_ports", [])))
                latency = f"{host.get('latency', 0)*1000:.1f}ms" if host.get("latency") else "-"
                
                table.add_row(
                    host["ip"],
                    host.get("method", ""),
                    open_ports or "-",
                    latency,
                )
            
            console.print(table)
            
            # 统计
            console.print(f"\n[yellow]统计:[/yellow]")
            console.print(f"  • 扫描范围: {len(hosts)} 个IP")
            console.print(f"  • 存活主机: {len(alive_hosts)} 个")
            console.print(f"  • 存活率: {len(alive_hosts)/len(hosts)*100:.1f}%")
            
            # 按端口统计
            port_stats = {}
            for host in alive_hosts:
                for port in host.get("open_ports", []):
                    port_stats[port] = port_stats.get(port, 0) + 1
            
            if port_stats:
                console.print(f"\n[yellow]端口统计:[/yellow]")
                for port, count in sorted(port_stats.items()):
                    service = self._get_service_name(port)
                    console.print(f"  • 端口 {port} ({service}): {count} 个主机")
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"发现 {len(alive_hosts)} 个存活主机",
            data={
                "alive_hosts": alive_hosts,
                "total_scanned": len(hosts),
            },
            start_time=start_time,
            end_time=datetime.now(),
        )
    
    def _parse_target(self, target: str) -> List[str]:
        """解析目标为IP列表"""
        hosts = []
        
        # CIDR格式
        if "/" in target:
            try:
                network = ipaddress.ip_network(target, strict=False)
                hosts = [str(ip) for ip in network.hosts()]
            except ValueError:
                pass
        
        # IP范围格式 (192.168.1.1-254)
        elif "-" in target:
            try:
                base, end = target.rsplit("-", 1)
                if "." in end:
                    # 完整IP范围
                    start_ip = ipaddress.ip_address(base)
                    end_ip = ipaddress.ip_address(end)
                    hosts = [str(ipaddress.ip_address(i)) 
                            for i in range(int(start_ip), int(end_ip) + 1)]
                else:
                    # 最后一段范围
                    base_parts = base.rsplit(".", 1)
                    if len(base_parts) == 2:
                        prefix = base_parts[0]
                        start = int(base_parts[1])
                        end_num = int(end)
                        hosts = [f"{prefix}.{i}" for i in range(start, end_num + 1)]
            except Exception:
                pass
        
        # 单个IP
        else:
            try:
                ipaddress.ip_address(target)
                hosts = [target]
            except ValueError:
                # 可能是主机名
                try:
                    ip = socket.gethostbyname(target)
                    hosts = [ip]
                except socket.gaierror:
                    pass
        
        return hosts
    
    def _check_host(
        self, ip: str, method: str, ports: List[int], timeout: float
    ) -> Dict[str, Any]:
        """检测单个主机"""
        result = {
            "ip": ip,
            "alive": False,
            "method": "",
            "open_ports": [],
            "latency": None,
        }
        
        # ICMP ping
        if method in ("ping", "both"):
            ping_result = self._icmp_ping(ip, timeout)
            if ping_result:
                result["alive"] = True
                result["method"] = "ICMP"
                result["latency"] = ping_result
        
        # TCP探测
        if method in ("tcp", "both"):
            for port in ports:
                start = time.time()
                if self._tcp_connect(ip, port, timeout):
                    result["alive"] = True
                    result["open_ports"].append(port)
                    if not result["latency"]:
                        result["latency"] = time.time() - start
                    if not result["method"]:
                        result["method"] = "TCP"
                    elif "TCP" not in result["method"]:
                        result["method"] += "+TCP"
        
        return result
    
    def _icmp_ping(self, ip: str, timeout: float) -> Optional[float]:
        """ICMP ping (简化版,需要管理员权限)"""
        try:
            import ping3
            ping3.EXCEPTIONS = True
            latency = ping3.ping(ip, timeout=timeout)
            return latency if latency else None
        except ImportError:
            # 没有ping3库,跳过ICMP
            return None
        except Exception:
            return None
    
    def _tcp_connect(self, ip: str, port: int, timeout: float) -> bool:
        """TCP连接探测"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _get_service_name(self, port: int) -> str:
        """获取常见端口服务名"""
        services = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            6379: "Redis",
            8080: "HTTP-Alt",
            27017: "MongoDB",
        }
        return services.get(port, "Unknown")
