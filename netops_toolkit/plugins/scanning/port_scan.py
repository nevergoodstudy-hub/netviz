"""
端口扫描插件

提供TCP端口扫描功能,支持并发扫描和服务识别。
"""

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
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
from netops_toolkit.ui.theme import NetOpsTheme, console
from netops_toolkit.ui.components import (
    create_result_table,
    create_summary_panel,
    create_progress_bar,
)
from netops_toolkit.utils.network_utils import (
    expand_ip_range,
    parse_port_list,
    get_common_ports,
)
from netops_toolkit.utils.export_utils import save_report

logger = get_logger(__name__)


# 常见服务端口映射
COMMON_SERVICES = {
    20: "FTP-DATA",
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
    8080: "HTTP-Proxy",
    8443: "HTTPS-Alt",
    27017: "MongoDB",
}


@register_plugin
class PortScanPlugin(Plugin):
    """端口扫描插件"""
    
    name = "端口扫描"
    category = PluginCategory.SCANNING
    description = "TCP端口扫描,检测开放端口"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        """验证依赖"""
        # 使用标准库socket,无需额外依赖
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="target",
                param_type=str,
                description="目标IP或网段",
                required=True,
            ),
            ParamSpec(
                name="ports",
                param_type=str,
                description="端口范围 (e.g., 80,443,8000-8100)",
                required=False,
                default="1-1024",
            ),
            ParamSpec(
                name="threads",
                param_type=int,
                description="线程数",
                required=False,
                default=50,
            ),
        ]
    
    def run(
        self,
        target: str,
        ports: str = "1-1024",
        threads: int = 50,
        timeout: float = 1.0,
        export_path: Optional[str] = None,
        **kwargs,
    ) -> PluginResult:
        """
        执行端口扫描
        
        Args:
            target: 目标地址或网段
            ports: 端口范围
            threads: 线程数
            timeout: 连接超时
            export_path: 导出文件路径
            
        Returns:
            PluginResult
        """
        start_time = datetime.now()
        
        # 解析目标IP
        targets = expand_ip_range(target)
        if not targets:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="无有效的目标地址",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 解析端口
        port_list = []
        if ports.lower() == "common":
            port_list = get_common_ports("all")
        elif ports.lower() in ["web", "ssh", "ftp", "dns", "smtp"]:
            port_list = get_common_ports(ports.lower())
        else:
            port_list = parse_port_list(ports)
        
        if not port_list:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="无有效的端口范围",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        console.print(f"\n[cyan]扫描 {len(targets)} 个目标的 {len(port_list)} 个端口...[/cyan]\n")
        
        # 执行扫描
        results = []
        total_scans = len(targets) * len(port_list)
        open_count = 0
        closed_count = 0
        
        with create_progress_bar() as progress:
            task = progress.add_task("端口扫描", total=total_scans)
            
            # 为每个目标扫描端口
            for ip in targets:
                with ThreadPoolExecutor(max_workers=threads) as executor:
                    futures = {
                        executor.submit(self._scan_port, ip, port, timeout): (ip, port)
                        for port in port_list
                    }
                    
                    for future in as_completed(futures):
                        ip, port = futures[future]
                        try:
                            result = future.result()
                            if result["status"] == "open":
                                results.append(result)
                                open_count += 1
                            else:
                                closed_count += 1
                        except Exception as e:
                            logger.debug(f"扫描 {ip}:{port} 失败: {e}")
                            closed_count += 1
                        
                        progress.update(task, advance=1)
        
        # 显示结果
        if results:
            self._display_results(results)
        else:
            console.print("[yellow]未发现开放端口[/yellow]\n")
        
        # 显示统计
        stats = {
            "目标数量": len(targets),
            "扫描端口数": len(port_list),
            "总扫描次数": total_scans,
            "开放端口": open_count,
            "关闭端口": closed_count,
            "开放率": f"{(open_count / total_scans * 100):.2f}%" if total_scans > 0 else "0%",
        }
        
        console.print(create_summary_panel("扫描统计", stats, timestamp=datetime.now()))
        
        # 导出报告
        if export_path:
            export_data = {
                "test_time": start_time.isoformat(),
                "target": target,
                "ports": ports,
                "threads": threads,
                "timeout": timeout,
                "statistics": stats,
                "results": results,
            }
            save_report(export_data, Path(export_path).parent, Path(export_path).stem, "json")
        
        end_time = datetime.now()
        
        # 确定结果状态
        if open_count > 0:
            status = ResultStatus.SUCCESS
            message = f"发现 {open_count} 个开放端口"
        else:
            status = ResultStatus.FAILED
            message = "未发现开放端口"
        
        return PluginResult(
            status=status,
            message=message,
            data=results,
            start_time=start_time,
            end_time=end_time,
            metadata={"statistics": stats},
        )
    
    def _scan_port(
        self,
        ip: str,
        port: int,
        timeout: float,
    ) -> Dict[str, Any]:
        """
        扫描单个端口
        
        Args:
            ip: 目标IP
            port: 端口号
            timeout: 超时时间
            
        Returns:
            扫描结果字典
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        try:
            result = sock.connect_ex((ip, port))
            if result == 0:
                # 尝试获取服务信息
                service = self._identify_service(ip, port)
                
                return {
                    "ip": ip,
                    "port": port,
                    "status": "open",
                    "service": service,
                }
            else:
                return {
                    "ip": ip,
                    "port": port,
                    "status": "closed",
                    "service": None,
                }
        except socket.timeout:
            return {
                "ip": ip,
                "port": port,
                "status": "filtered",
                "service": None,
            }
        except Exception:
            return {
                "ip": ip,
                "port": port,
                "status": "error",
                "service": None,
            }
        finally:
            sock.close()
    
    def _identify_service(self, ip: str, port: int) -> str:
        """
        识别服务
        
        Args:
            ip: IP地址
            port: 端口号
            
        Returns:
            服务名称
        """
        # 首先查看常见服务映射
        if port in COMMON_SERVICES:
            return COMMON_SERVICES[port]
        
        # 尝试使用socket.getservbyport
        try:
            service = socket.getservbyport(port, "tcp")
            return service
        except OSError:
            pass
        
        return "unknown"
    
    def _display_results(self, results: List[Dict[str, Any]]) -> None:
        """
        显示扫描结果
        
        Args:
            results: 结果列表
        """
        # 按IP和端口排序
        results.sort(key=lambda x: (x["ip"], x["port"]))
        
        columns = [
            {"header": "IP地址", "style": NetOpsTheme.IP_ADDRESS, "justify": "left"},
            {"header": "端口", "justify": "center", "width": 8},
            {"header": "状态", "justify": "center"},
            {"header": "服务", "justify": "left"},
        ]
        
        rows = []
        for r in results:
            status_text = "开放"
            status_style = NetOpsTheme.STATUS_ONLINE
            
            if r["status"] == "closed":
                status_text = "关闭"
                status_style = NetOpsTheme.STATUS_OFFLINE
            elif r["status"] == "filtered":
                status_text = "过滤"
                status_style = NetOpsTheme.WARNING
            elif r["status"] == "error":
                status_text = "错误"
                status_style = NetOpsTheme.ERROR
            
            rows.append([
                r["ip"],
                str(r["port"]),
                f"[{status_style}]{status_text}[/]",
                r.get("service", "unknown"),
            ])
        
        table = create_result_table("开放端口列表", columns, rows)
        console.print(table)
        console.print()


__all__ = ["PortScanPlugin"]
