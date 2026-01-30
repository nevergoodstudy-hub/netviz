"""
Traceroute路由追踪插件

提供路由追踪功能,支持TTL分析和可视化路径展示。
支持 Windows、Linux、macOS 和 BSD 系统。
"""

import re
import subprocess
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
)
from netops_toolkit.utils.network_utils import is_valid_ip, resolve_hostname
from netops_toolkit.utils.export_utils import save_report
from netops_toolkit.utils.platform_utils import (
    get_platform,
    get_traceroute_command,
    run_command,
)

logger = get_logger(__name__)


@register_plugin
class TraceroutePlugin(Plugin):
    """Traceroute路由追踪插件"""
    
    name = "路由追踪"
    category = PluginCategory.DIAGNOSTICS
    description = "Traceroute路由追踪,分析网络路径"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        """验证依赖"""
        # 使用系统命令,无需额外依赖
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="target",
                param_type=str,
                description="目标IP或主机名",
                required=True,
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
                default=3.0,
            ),
        ]
    
    def run(
        self,
        target: str,
        max_hops: int = 30,
        timeout: float = 3.0,
        export_path: Optional[str] = None,
        **kwargs,
    ) -> PluginResult:
        """
        执行路由追踪
        
        Args:
            target: 目标地址
            max_hops: 最大跳数
            timeout: 超时时间
            export_path: 导出文件路径
            
        Returns:
            PluginResult
        """
        start_time = datetime.now()
        
        # 解析主机名
        target_ip = target
        hostname = None
        
        if not is_valid_ip(target):
            resolved_ip = resolve_hostname(target)
            if resolved_ip:
                target_ip = resolved_ip
                hostname = target
                console.print(f"[cyan]已解析 {target} -> {target_ip}[/cyan]")
            else:
                return PluginResult(
                    status=ResultStatus.ERROR,
                    message=f"无法解析主机名: {target}",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
        
        console.print(f"\n[cyan]开始路由追踪到 {target_ip} (最大 {max_hops} 跳)...[/cyan]\n")
        
        # 执行traceroute
        hops = self._execute_traceroute(target_ip, max_hops, timeout)
        
        if not hops:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="路由追踪失败,未获取到任何跳数信息",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 显示结果
        self._display_results(hops, target_ip)
        
        # 显示路径可视化
        self._display_path_visual(hops, target_ip)
        
        # 显示统计
        stats = self._calculate_stats(hops)
        console.print(create_summary_panel("路由统计", stats, timestamp=datetime.now()))
        
        # 导出报告
        if export_path:
            export_data = {
                "test_time": start_time.isoformat(),
                "target": target,
                "target_ip": target_ip,
                "max_hops": max_hops,
                "timeout": timeout,
                "statistics": stats,
                "hops": hops,
            }
            save_report(export_data, Path(export_path).parent, Path(export_path).stem, "json")
        
        end_time = datetime.now()
        
        # 检查是否到达目标
        reached = any(h.get("ip") == target_ip for h in hops if h.get("ip"))
        
        if reached:
            status = ResultStatus.SUCCESS
            message = f"成功追踪到 {target_ip}, 共 {len(hops)} 跳"
        else:
            status = ResultStatus.PARTIAL
            message = f"追踪未完全到达目标, 已获取 {len(hops)} 跳信息"
        
        return PluginResult(
            status=status,
            message=message,
            data=hops,
            start_time=start_time,
            end_time=end_time,
            metadata={"statistics": stats},
        )
    
    def _execute_traceroute(
        self,
        target: str,
        max_hops: int,
        timeout: float,
    ) -> List[Dict[str, Any]]:
        """
        执行系统traceroute命令
        
        Args:
            target: 目标地址
            max_hops: 最大跳数
            timeout: 超时时间
            
        Returns:
            跳数信息列表
        """
        hops = []
        platform_info = get_platform()
        
        # 使用跨平台工具获取命令
        cmd, cmd_type = get_traceroute_command(target, max_hops, timeout)
        
        try:
            console.print("[dim]正在执行追踪...[/dim]")
            
            result = run_command(
                cmd,
                timeout=max_hops * timeout + 30,
            )
            
            output = result.stdout
            hops = self._parse_traceroute_output(output, platform_info)
            
        except subprocess.TimeoutExpired:
            logger.warning("Traceroute超时")
        except Exception as e:
            logger.error(f"Traceroute执行失败: {e}")
        
        return hops
    
    def _parse_traceroute_output(self, output: str, platform_info=None) -> List[Dict[str, Any]]:
        """
        解析traceroute输出
        
        Args:
            output: 命令输出
            platform_info: 平台信息
            
        Returns:
            跳数信息列表
        """
        hops = []
        
        if platform_info is None:
            platform_info = get_platform()
        
        if platform_info.is_windows:
            # Windows tracert 输出格式:
            # 1    <1 毫秒   <1 毫秒   <1 毫秒 192.168.1.1
            # 2     *        *        *     请求超时。
            
            lines = output.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 跳过头部信息
                if not line or '跟踪' in line or 'Tracing' in line or '通过' in line or 'over' in line:
                    continue
                if '跃点数' in line or 'hops' in line.lower():
                    continue
                if '跟踪完成' in line or 'Trace complete' in line:
                    continue
                
                # 解析跳数行
                # 匹配格式: "数字  时间  时间  时间  IP/主机名"
                match = re.match(
                    r'\s*(\d+)\s+(.+)',
                    line
                )
                
                if match:
                    hop_num = int(match.group(1))
                    rest = match.group(2)
                    
                    # 检查是否超时
                    if '请求超时' in rest or 'Request timed out' in rest or rest.count('*') >= 3:
                        hops.append({
                            "hop": hop_num,
                            "ip": None,
                            "hostname": None,
                            "rtt1": None,
                            "rtt2": None,
                            "rtt3": None,
                            "avg_rtt": None,
                            "status": "timeout",
                        })
                    else:
                        # 解析RTT和IP
                        # 格式: "<1 毫秒   <1 毫秒   <1 毫秒 192.168.1.1"
                        rtt_pattern = r'[<]?(\d+)\s*(?:毫秒|ms)'
                        rtts = re.findall(rtt_pattern, rest, re.IGNORECASE)
                        
                        # 提取IP地址
                        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', rest)
                        ip = ip_match.group(1) if ip_match else None
                        
                        # 提取主机名 (如果有)
                        hostname_match = re.search(r'(\S+)\s+\[(\d+\.\d+\.\d+\.\d+)\]', rest)
                        hostname = hostname_match.group(1) if hostname_match else None
                        
                        rtt_values = [float(r) for r in rtts[:3]] if rtts else []
                        
                        hops.append({
                            "hop": hop_num,
                            "ip": ip,
                            "hostname": hostname,
                            "rtt1": rtt_values[0] if len(rtt_values) > 0 else None,
                            "rtt2": rtt_values[1] if len(rtt_values) > 1 else None,
                            "rtt3": rtt_values[2] if len(rtt_values) > 2 else None,
                            "avg_rtt": sum(rtt_values) / len(rtt_values) if rtt_values else None,
                            "status": "ok",
                        })
        else:
            # Linux/Mac traceroute 输出格式:
            # 1  192.168.1.1 (192.168.1.1)  1.234 ms  1.123 ms  1.456 ms
            
            lines = output.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 跳过头部
                if not line or 'traceroute to' in line.lower():
                    continue
                
                # 解析跳数行
                match = re.match(r'\s*(\d+)\s+(.+)', line)
                
                if match:
                    hop_num = int(match.group(1))
                    rest = match.group(2)
                    
                    # 检查超时
                    if '* * *' in rest or rest.strip() == '* * *':
                        hops.append({
                            "hop": hop_num,
                            "ip": None,
                            "hostname": None,
                            "rtt1": None,
                            "rtt2": None,
                            "rtt3": None,
                            "avg_rtt": None,
                            "status": "timeout",
                        })
                    else:
                        # 提取IP
                        ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+)\)', rest)
                        ip = ip_match.group(1) if ip_match else None
                        
                        # 提取主机名
                        hostname_match = re.match(r'(\S+)\s+\(', rest)
                        hostname = hostname_match.group(1) if hostname_match else None
                        
                        # 提取RTT
                        rtts = re.findall(r'(\d+\.?\d*)\s*ms', rest)
                        rtt_values = [float(r) for r in rtts[:3]] if rtts else []
                        
                        hops.append({
                            "hop": hop_num,
                            "ip": ip,
                            "hostname": hostname if hostname != ip else None,
                            "rtt1": rtt_values[0] if len(rtt_values) > 0 else None,
                            "rtt2": rtt_values[1] if len(rtt_values) > 1 else None,
                            "rtt3": rtt_values[2] if len(rtt_values) > 2 else None,
                            "avg_rtt": sum(rtt_values) / len(rtt_values) if rtt_values else None,
                            "status": "ok",
                        })
        
        return hops
    
    def _calculate_stats(self, hops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算统计数据
        
        Args:
            hops: 跳数信息列表
            
        Returns:
            统计数据字典
        """
        total_hops = len(hops)
        ok_hops = [h for h in hops if h["status"] == "ok"]
        timeout_hops = [h for h in hops if h["status"] == "timeout"]
        
        rtts = [h["avg_rtt"] for h in ok_hops if h["avg_rtt"] is not None]
        
        stats = {
            "总跳数": total_hops,
            "响应跳数": len(ok_hops),
            "超时跳数": len(timeout_hops),
        }
        
        if rtts:
            stats["最小延迟"] = f"{min(rtts):.2f} ms"
            stats["最大延迟"] = f"{max(rtts):.2f} ms"
            stats["平均延迟"] = f"{sum(rtts) / len(rtts):.2f} ms"
        
        return stats
    
    def _display_results(self, hops: List[Dict[str, Any]], target: str) -> None:
        """
        显示结果表格
        
        Args:
            hops: 跳数信息列表
            target: 目标地址
        """
        columns = [
            {"header": "跳数", "justify": "center", "width": 6},
            {"header": "IP地址", "style": NetOpsTheme.IP_ADDRESS, "justify": "left"},
            {"header": "主机名", "style": NetOpsTheme.HOSTNAME, "justify": "left"},
            {"header": "RTT1(ms)", "justify": "right"},
            {"header": "RTT2(ms)", "justify": "right"},
            {"header": "RTT3(ms)", "justify": "right"},
            {"header": "平均(ms)", "justify": "right"},
        ]
        
        rows = []
        for h in hops:
            if h["status"] == "timeout":
                rows.append([
                    str(h["hop"]),
                    f"[{NetOpsTheme.STATUS_OFFLINE}]* * *[/]",
                    f"[{NetOpsTheme.MUTED}]请求超时[/]",
                    "*", "*", "*", "*"
                ])
            else:
                ip = h["ip"] or "-"
                hostname = h["hostname"] or "-"
                rtt1 = f"{h['rtt1']:.1f}" if h['rtt1'] is not None else "-"
                rtt2 = f"{h['rtt2']:.1f}" if h['rtt2'] is not None else "-"
                rtt3 = f"{h['rtt3']:.1f}" if h['rtt3'] is not None else "-"
                avg = f"{h['avg_rtt']:.1f}" if h['avg_rtt'] is not None else "-"
                
                # 高亮目标地址
                if ip == target:
                    ip = f"[{NetOpsTheme.SUCCESS}]{ip} ✓[/]"
                
                rows.append([str(h["hop"]), ip, hostname, rtt1, rtt2, rtt3, avg])
        
        table = create_result_table(f"路由追踪: {target}", columns, rows)
        console.print(table)
        console.print()
    
    def _display_path_visual(self, hops: List[Dict[str, Any]], target: str) -> None:
        """
        显示路径可视化
        
        Args:
            hops: 跳数信息列表
            target: 目标地址
        """
        console.print("[bold cyan]路径可视化:[/bold cyan]")
        console.print()
        
        console.print("  [green]🖥️  本机[/green]")
        
        for i, h in enumerate(hops):
            connector = "  │"
            
            if h["status"] == "timeout":
                node = f"  ├─[{i+1}]─ [dim]* * * (超时)[/dim]"
            else:
                ip = h["ip"] or "unknown"
                hostname = f" ({h['hostname']})" if h['hostname'] else ""
                rtt = f" [{h['avg_rtt']:.1f}ms]" if h['avg_rtt'] else ""
                
                if ip == target:
                    node = f"  └─[{i+1}]─ [green]✓ {ip}{hostname}{rtt}[/green]"
                else:
                    node = f"  ├─[{i+1}]─ {ip}{hostname}{rtt}"
            
            console.print(node)
        
        # 如果最后一跳不是目标
        last_hop = hops[-1] if hops else None
        if last_hop and last_hop.get("ip") != target:
            console.print(f"  └─[?]─ [yellow]⚠ {target} (未到达)[/yellow]")
        
        console.print()


__all__ = ["TraceroutePlugin"]
