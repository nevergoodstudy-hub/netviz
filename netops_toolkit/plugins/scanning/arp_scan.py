"""
ARP扫描插件

扫描局域网中的活跃主机,获取IP和MAC地址映射。
"""

from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import socket
import struct
import subprocess
import re
import platform

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.utils.network_utils import expand_ip_range, is_valid_network
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class ARPScanPlugin(Plugin):
    """ARP扫描插件"""
    
    name = "arp_scan"
    description = "局域网ARP扫描"
    category = "scanning"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        return True, None
    
    def get_required_params(self) -> List[str]:
        """获取必需参数"""
        return ["network"]
    
    def run(self, params: Dict[str, Any]) -> PluginResult:
        """
        执行ARP扫描
        
        参数:
            network: 网络地址 (CIDR格式,如 192.168.1.0/24)
            timeout: 超时时间 (默认1秒)
            max_workers: 最大并发数 (默认50)
        """
        network = params.get("network", "")
        timeout = params.get("timeout", 1)
        max_workers = params.get("max_workers", 50)
        
        if not network:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定网络地址",
                data={}
            )
        
        if not is_valid_network(network):
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"无效的网络地址: {network}",
                data={}
            )
        
        # 展开CIDR获取IP列表
        ip_list = expand_ip_range(network)
        
        if len(ip_list) > 1024:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"网络范围过大 ({len(ip_list)} 个地址),请使用更小的子网",
                data={}
            )
        
        logger.info(f"开始ARP扫描: {network} ({len(ip_list)} 个地址)")
        
        from netops_toolkit.ui.theme import console
        console.print(f"[cyan]正在扫描 {len(ip_list)} 个地址...[/cyan]")
        
        # 执行扫描
        start_time = datetime.now()
        results = self._scan_network(ip_list, timeout, max_workers)
        duration = (datetime.now() - start_time).total_seconds()
        
        # 显示结果
        self._display_results(network, results, duration)
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"扫描完成: 发现 {len(results)} 个活跃主机",
            data={
                "network": network,
                "hosts": results,
                "total_scanned": len(ip_list),
                "active_count": len(results),
                "duration": duration,
            }
        )
    
    def _scan_network(
        self,
        ip_list: List[str],
        timeout: int,
        max_workers: int,
    ) -> List[Dict[str, Any]]:
        """扫描网络"""
        active_hosts = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._ping_host, ip, timeout): ip
                for ip in ip_list
            }
            
            for future in as_completed(futures):
                ip = futures[future]
                try:
                    is_alive = future.result()
                    if is_alive:
                        # 获取MAC地址
                        mac = self._get_mac_address(ip)
                        active_hosts.append({
                            "ip": ip,
                            "mac": mac,
                            "hostname": self._get_hostname(ip),
                        })
                except Exception as e:
                    logger.debug(f"扫描 {ip} 时出错: {e}")
        
        # 按IP排序
        active_hosts.sort(key=lambda x: tuple(map(int, x["ip"].split("."))))
        
        return active_hosts
    
    def _ping_host(self, ip: str, timeout: int) -> bool:
        """Ping主机检查是否存活"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
            else:
                cmd = ["ping", "-c", "1", "-W", str(timeout), ip]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout + 2,
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _get_mac_address(self, ip: str) -> Optional[str]:
        """从ARP缓存获取MAC地址"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                result = subprocess.run(
                    ["arp", "-a", ip],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # Windows ARP输出格式: 192.168.1.1  00-0c-29-12-34-56  动态
                match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', result.stdout)
                if match:
                    return match.group(0).upper().replace("-", ":")
            else:
                result = subprocess.run(
                    ["arp", "-n", ip],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # Linux ARP输出格式: 192.168.1.1 ether 00:0c:29:12:34:56 C eth0
                match = re.search(r'([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', result.stdout)
                if match:
                    return match.group(0).upper()
            
            return None
            
        except Exception:
            return None
    
    def _get_hostname(self, ip: str) -> Optional[str]:
        """获取主机名"""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except Exception:
            return None
    
    def _display_results(
        self,
        network: str,
        hosts: List[Dict[str, Any]],
        duration: float,
    ) -> None:
        """显示扫描结果"""
        from netops_toolkit.ui.theme import console
        from rich.table import Table
        
        # 摘要信息
        summary = {
            "网络地址": network,
            "活跃主机": len(hosts),
            "扫描耗时": f"{duration:.2f}秒",
        }
        
        panel = create_summary_panel("ARP扫描结果", summary)
        console.print(panel)
        
        if not hosts:
            console.print("[yellow]未发现活跃主机[/yellow]\n")
            return
        
        # 主机列表
        table = Table(title="活跃主机列表", show_header=True)
        table.add_column("IP地址", style="green")
        table.add_column("MAC地址", style="cyan")
        table.add_column("主机名", style="yellow")
        
        for host in hosts:
            table.add_row(
                host["ip"],
                host["mac"] or "[dim]未知[/dim]",
                host["hostname"] or "[dim]-[/dim]",
            )
        
        console.print(table)
        console.print()


__all__ = ["ARPScanPlugin"]
