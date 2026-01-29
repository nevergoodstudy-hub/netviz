"""
TCP端口连通性测试插件

类似telnet测试TCP端口连通性,支持超时设置和多端口批量测试。
"""

import socket
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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
class TcpConnectPlugin(Plugin):
    """TCP端口连通性测试插件"""
    
    name = "TCP连通测试"
    category = PluginCategory.DIAGNOSTICS
    description = "测试TCP端口连通性,类似telnet"
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
                name="ports",
                param_type=str,
                description="端口 (单个或逗号分隔)",
                required=True,
            ),
            ParamSpec(
                name="timeout",
                param_type=float,
                description="超时时间(秒)",
                required=False,
                default=5.0,
            ),
        ]
    
    def run(
        self,
        host: str,
        ports: str,
        timeout: float = 5.0,
        **kwargs,
    ) -> PluginResult:
        """执行TCP连通性测试"""
        start_time = datetime.now()
        
        # 解析端口
        port_list = self._parse_ports(ports)
        if not port_list:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="无效的端口参数",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 解析主机名
        try:
            ip_addr = socket.gethostbyname(host)
            console.print(f"[cyan]目标: {host} ({ip_addr})[/cyan]")
        except socket.gaierror:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"无法解析主机名: {host}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        console.print(f"[cyan]测试 {len(port_list)} 个端口 (超时: {timeout}s)...[/cyan]\n")
        
        # 测试每个端口
        results = []
        open_count = 0
        closed_count = 0
        
        for port in port_list:
            result = self._test_port(host, port, timeout)
            results.append(result)
            
            if result["status"] == "open":
                open_count += 1
            else:
                closed_count += 1
        
        # 显示结果
        self._display_results(results, host)
        
        # 统计
        stats = {
            "目标主机": f"{host} ({ip_addr})",
            "测试端口数": len(port_list),
            "开放端口": open_count,
            "关闭/超时": closed_count,
            "超时设置": f"{timeout}s",
        }
        
        console.print(create_summary_panel("TCP连通测试统计", stats, timestamp=datetime.now()))
        
        return PluginResult(
            status=ResultStatus.SUCCESS if open_count > 0 else ResultStatus.PARTIAL,
            message=f"测试完成: {open_count} 开放, {closed_count} 关闭",
            data={"host": host, "results": results},
            start_time=start_time,
            end_time=datetime.now(),
        )
    
    def _parse_ports(self, ports: str) -> List[int]:
        """解析端口参数"""
        port_list = []
        
        for part in ports.split(","):
            part = part.strip()
            
            if "-" in part:
                # 端口范围
                try:
                    start, end = part.split("-")
                    for p in range(int(start), int(end) + 1):
                        if 1 <= p <= 65535:
                            port_list.append(p)
                except:
                    pass
            else:
                # 单个端口
                try:
                    p = int(part)
                    if 1 <= p <= 65535:
                        port_list.append(p)
                except:
                    pass
        
        return port_list
    
    def _test_port(self, host: str, port: int, timeout: float) -> Dict[str, Any]:
        """测试单个端口"""
        result = {
            "port": port,
            "status": "closed",
            "latency": None,
            "service": self._get_service_name(port),
            "banner": None,
            "error": None,
        }
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            start = time.time()
            connect_result = sock.connect_ex((host, port))
            latency = (time.time() - start) * 1000
            
            if connect_result == 0:
                result["status"] = "open"
                result["latency"] = latency
                
                # 尝试获取 banner
                try:
                    sock.settimeout(1)
                    sock.send(b"\r\n")
                    banner = sock.recv(1024)
                    if banner:
                        result["banner"] = banner.decode('utf-8', errors='ignore').strip()[:50]
                except:
                    pass
            else:
                result["status"] = "closed"
                result["error"] = f"错误码: {connect_result}"
                
        except socket.timeout:
            result["status"] = "timeout"
            result["error"] = "连接超时"
        except socket.error as e:
            result["status"] = "error"
            result["error"] = str(e)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        finally:
            try:
                sock.close()
            except:
                pass
        
        return result
    
    def _get_service_name(self, port: int) -> str:
        """获取端口对应的服务名"""
        services = {
            20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet",
            25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
            143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS",
            995: "POP3S", 1433: "MSSQL", 1521: "Oracle", 3306: "MySQL",
            3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
            8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
        }
        return services.get(port, "-")
    
    def _display_results(self, results: List[Dict], host: str) -> None:
        """显示测试结果"""
        table = create_result_table(
            title=f"TCP连通测试结果: {host}",
            columns=[
                ("端口", "port", "center"),
                ("状态", "status", "center"),
                ("服务", "service", "left"),
                ("延迟(ms)", "latency", "right"),
                ("Banner", "banner", "left"),
            ],
        )
        
        for r in results:
            if r["status"] == "open":
                status_display = "[green]● 开放[/green]"
            elif r["status"] == "timeout":
                status_display = "[yellow]● 超时[/yellow]"
            else:
                status_display = "[red]● 关闭[/red]"
            
            table.add_row(
                str(r["port"]),
                status_display,
                r["service"],
                f"{r['latency']:.2f}" if r["latency"] else "-",
                r["banner"] or "-",
            )
        
        console.print(table)
