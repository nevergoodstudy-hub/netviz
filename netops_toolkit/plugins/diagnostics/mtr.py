"""
MTR (My Traceroute) 插件

结合 ping 和 traceroute 功能,实时追踪网络路径,
显示每跳的丢包率、延迟统计等信息。
支持 Windows、Linux、macOS 和 BSD 系统。
"""

import re
import subprocess
import socket
import time
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
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
from netops_toolkit.utils.platform_utils import (
    get_platform,
    command_exists,
    run_command,
    get_ping_command,
)

logger = get_logger(__name__)


@register_plugin
class MtrPlugin(Plugin):
    """MTR 网络诊断插件"""
    
    name = "MTR路径追踪"
    category = PluginCategory.DIAGNOSTICS
    description = "结合Ping和Traceroute,实时显示每跳延迟和丢包"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="target",
                param_type=str,
                description="目标IP或主机名",
                required=True,
            ),
            ParamSpec(
                name="count",
                param_type=int,
                description="每跳测试次数",
                required=False,
                default=10,
            ),
            ParamSpec(
                name="max_hops",
                param_type=int,
                description="最大跳数",
                required=False,
                default=30,
            ),
            ParamSpec(
                name="timeout",
                param_type=float,
                description="超时时间(秒)",
                required=False,
                default=2.0,
            ),
        ]
    
    def run(
        self,
        target: str,
        count: int = 10,
        max_hops: int = 30,
        timeout: float = 2.0,
        **kwargs,
    ) -> PluginResult:
        """
        执行 MTR 路径追踪
        """
        start_time = datetime.now()
        
        # 解析目标地址
        try:
            target_ip = socket.gethostbyname(target)
            console.print(f"[cyan]目标: {target} ({target_ip})[/cyan]")
        except socket.gaierror:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"无法解析主机名: {target}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        console.print(f"[cyan]正在追踪路径 (每跳 {count} 次测试)...[/cyan]\n")
        
        # 首先获取路径
        hops = self._discover_path(target_ip, max_hops, timeout)
        
        if not hops:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="无法发现任何路径跳数",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 对每一跳进行多次 ping 测试
        results = []
        console.print(f"[cyan]正在测试 {len(hops)} 个节点...[/cyan]\n")
        
        for hop_info in hops:
            hop_num = hop_info["hop"]
            hop_ip = hop_info["ip"]
            
            if hop_ip == "*":
                results.append({
                    "hop": hop_num,
                    "ip": "*",
                    "hostname": "*",
                    "loss": 100.0,
                    "sent": count,
                    "recv": 0,
                    "avg": 0,
                    "min": 0,
                    "max": 0,
                    "stdev": 0,
                })
                continue
            
            # 多次 ping 测试
            latencies = []
            received = 0
            
            for _ in range(count):
                rtt = self._ping_host(hop_ip, timeout)
                if rtt is not None:
                    latencies.append(rtt)
                    received += 1
            
            # 计算统计
            loss = ((count - received) / count) * 100
            
            if latencies:
                avg_latency = statistics.mean(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0
            else:
                avg_latency = min_latency = max_latency = stdev = 0
            
            # 解析主机名
            try:
                hostname = socket.gethostbyaddr(hop_ip)[0]
                if len(hostname) > 30:
                    hostname = hostname[:27] + "..."
            except:
                hostname = hop_ip
            
            results.append({
                "hop": hop_num,
                "ip": hop_ip,
                "hostname": hostname,
                "loss": loss,
                "sent": count,
                "recv": received,
                "avg": avg_latency,
                "min": min_latency,
                "max": max_latency,
                "stdev": stdev,
            })
        
        # 显示结果
        self._display_results(results, target)
        
        end_time = datetime.now()
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"MTR 追踪完成: {len(results)} 跳",
            data={"target": target, "hops": results},
            start_time=start_time,
            end_time=end_time,
        )
    
    def _discover_path(
        self,
        target: str,
        max_hops: int,
        timeout: float,
    ) -> List[Dict[str, Any]]:
        """发现到目标的路径"""
        hops = []
        
        for ttl in range(1, max_hops + 1):
            hop_ip = self._trace_hop(target, ttl, timeout)
            
            hops.append({
                "hop": ttl,
                "ip": hop_ip if hop_ip else "*",
            })
            
            # 如果到达目标则停止
            if hop_ip == target:
                break
        
        return hops
    
    def _trace_hop(self, target: str, ttl: int, timeout: float) -> Optional[str]:
        """追踪单跳"""
        platform_info = get_platform()
        
        try:
            if platform_info.is_windows:
                # Windows: 使用 ping 的 TTL 选项
                cmd = ['ping', '-n', '1', '-i', str(ttl), '-w', str(int(timeout * 1000)), target]
                result = run_command(cmd, timeout=timeout + 2)
                
                # 解析响应
                output = result.stdout
                
                # 匹配IP地址
                ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                
                if 'TTL expired' in output or 'TTL 过期' in output or '传输中过期' in output:
                    # TTL 过期,提取中间节点 IP
                    match = re.search(r'[Ff]rom\s+' + ip_pattern, output)
                    if not match:
                        match = re.search(r'来自\s+' + ip_pattern, output)
                    if match:
                        return match.group(1)
                elif 'Reply from' in output or '来自' in output:
                    # 收到回复
                    match = re.search(r'[Ff]rom\s+' + ip_pattern, output)
                    if not match:
                        match = re.search(r'来自\s+' + ip_pattern, output)
                    if match:
                        return match.group(1)
                
            else:
                # Linux/macOS/BSD: 尝试使用原生 socket 或 traceroute
                try:
                    # 尝试使用 raw socket (Linux/BSD, 需要 root 权限)
                    recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                    recv_socket.settimeout(timeout)
                    
                    send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
                    
                    recv_socket.bind(("", 33434))
                    send_socket.sendto(b"", (target, 33434 + ttl))
                    
                    try:
                        data, addr = recv_socket.recvfrom(512)
                        return addr[0]
                    except socket.timeout:
                        pass
                    finally:
                        recv_socket.close()
                        send_socket.close()
                except PermissionError:
                    # 没有 root 权限，使用 traceroute 命令
                    if platform_info.is_macos:
                        cmd = ['traceroute', '-m', str(ttl), '-q', '1', '-w', str(int(timeout)), target]
                    else:
                        cmd = ['traceroute', '-m', str(ttl), '-q', '1', '-w', str(int(timeout)), target]
                    
                    result = run_command(cmd, timeout=timeout + 2)
                    output = result.stdout
                    
                    # 解析最后一跳
                    ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', output)
                    if ip_match:
                        return ip_match.group(1)
                    
        except Exception as e:
            logger.debug(f"Trace hop {ttl} failed: {e}")
        
        return None
    
    def _ping_host(self, host: str, timeout: float) -> Optional[float]:
        """Ping 单个主机,返回延迟(ms)"""
        platform_info = get_platform()
        
        try:
            cmd = get_ping_command(host, count=1, timeout=timeout)
            
            start = time.time()
            result = run_command(cmd, timeout=timeout + 2)
            
            if result.returncode == 0:
                # 解析延迟
                output = result.stdout
                
                if platform_info.is_windows:
                    # Windows: time=XXms 或 时间=XXms
                    match = re.search(r'[时间time][=<](\d+)\s*m?s', output, re.IGNORECASE)
                else:
                    # Linux/macOS/BSD: time=XX.X ms
                    match = re.search(r'time=(\d+\.?\d*)\s*ms', output, re.IGNORECASE)
                
                if match:
                    return float(match.group(1))
                
                # 备用: 使用计时
                return (time.time() - start) * 1000
                
        except Exception as e:
            logger.debug(f"Ping {host} failed: {e}")
        
        return None
    
    def _display_results(self, results: List[Dict], target: str) -> None:
        """显示 MTR 结果"""
        # 创建结果表格
        table = create_result_table(
            title=f"MTR 路径追踪: {target}",
            columns=[
                ("跳数", "hop", "center"),
                ("IP地址", "ip", "left"),
                ("主机名", "hostname", "left"),
                ("丢包%", "loss", "right"),
                ("发送", "sent", "right"),
                ("接收", "recv", "right"),
                ("平均ms", "avg", "right"),
                ("最小ms", "min", "right"),
                ("最大ms", "max", "right"),
                ("标准差", "stdev", "right"),
            ],
        )
        
        for r in results:
            # 根据丢包率决定颜色
            if r["loss"] == 0:
                loss_style = "[green]"
            elif r["loss"] < 10:
                loss_style = "[yellow]"
            else:
                loss_style = "[red]"
            
            table.add_row(
                str(r["hop"]),
                r["ip"],
                r["hostname"],
                f"{loss_style}{r['loss']:.1f}%[/]",
                str(r["sent"]),
                str(r["recv"]),
                f"{r['avg']:.2f}" if r["avg"] > 0 else "-",
                f"{r['min']:.2f}" if r["min"] > 0 else "-",
                f"{r['max']:.2f}" if r["max"] > 0 else "-",
                f"{r['stdev']:.2f}" if r["stdev"] > 0 else "-",
            )
        
        console.print(table)
        
        # 显示统计
        total_hops = len(results)
        reachable_hops = sum(1 for r in results if r["loss"] < 100)
        avg_loss = statistics.mean(r["loss"] for r in results if r["ip"] != "*") if results else 0
        
        stats = {
            "总跳数": total_hops,
            "可达节点": reachable_hops,
            "平均丢包率": f"{avg_loss:.1f}%",
            "目标": target,
        }
        
        console.print(create_summary_panel("MTR 统计", stats, timestamp=datetime.now()))
