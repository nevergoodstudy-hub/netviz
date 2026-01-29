"""
Ping测试插件

提供ICMP Ping功能,支持单目标和批量测试。
"""

import statistics
import subprocess
import sys
import platform
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
from netops_toolkit.utils.network_utils import expand_ip_range, is_valid_ip
from netops_toolkit.utils.export_utils import save_report

logger = get_logger(__name__)

# 尝试导入ping3,如果失败则使用系统ping
try:
    import ping3
    PING3_AVAILABLE = True
except ImportError:
    PING3_AVAILABLE = False
    logger.debug("ping3库不可用,将使用系统ping命令")


@register_plugin
class PingPlugin(Plugin):
    """Ping测试插件"""
    
    name = "Ping测试"
    category = PluginCategory.DIAGNOSTICS
    description = "ICMP Ping测试,检测网络连通性"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        """验证依赖"""
        # 即使ping3不可用,也可以使用系统ping
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="targets",
                param_type=str,
                description="目标IP/主机名 (支持逗号分隔或CIDR)",
                required=True,
            ),
            ParamSpec(
                name="count",
                param_type=int,
                description="每个目标的Ping次数",
                required=False,
                default=4,
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
        targets: str,
        count: int = 4,
        timeout: float = 2.0,
        export_path: Optional[str] = None,
        **kwargs,
    ) -> PluginResult:
        """
        执行Ping测试
        
        Args:
            targets: 目标地址 (单个IP, 逗号分隔列表, 或CIDR)
            count: Ping次数
            timeout: 超时时间
            export_path: 导出文件路径
            
        Returns:
            PluginResult
        """
        start_time = datetime.now()
        
        # 解析目标地址
        target_list = expand_ip_range(targets)
        
        if not target_list:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="无有效的目标地址",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        console.print(f"\n[cyan]准备测试 {len(target_list)} 个目标...[/cyan]\n")
        
        results = []
        success_count = 0
        fail_count = 0
        
        # 使用进度条
        with create_progress_bar() as progress:
            task = progress.add_task("Ping测试", total=len(target_list))
            
            # 并发执行Ping
            with ThreadPoolExecutor(max_workers=min(10, len(target_list))) as executor:
                futures = {
                    executor.submit(self._ping_host, target, count, timeout): target
                    for target in target_list
                }
                
                for future in as_completed(futures):
                    target = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if result["status"] == "up":
                            success_count += 1
                        else:
                            fail_count += 1
                            
                    except Exception as e:
                        logger.error(f"Ping {target} 失败: {e}")
                        results.append({
                            "target": target,
                            "status": "down",
                            "latency_ms": None,
                            "min_ms": None,
                            "max_ms": None,
                            "avg_ms": None,
                            "jitter_ms": None,
                            "packet_loss": 100.0,
                            "error": str(e),
                        })
                        fail_count += 1
                    
                    progress.update(task, advance=1)
        
        # 排序结果
        results.sort(key=lambda x: (x["status"] != "up", x["target"]))
        
        # 显示结果表格
        self._display_results(results)
        
        # 显示统计摘要
        stats = {
            "总目标数": len(target_list),
            "可达数量": success_count,
            "不可达数量": fail_count,
            "成功率": f"{(success_count / len(target_list) * 100):.1f}%",
        }
        
        # 计算整体延迟统计
        latencies = [r["avg_ms"] for r in results if r["avg_ms"] is not None]
        if latencies:
            stats["平均延迟"] = f"{statistics.mean(latencies):.2f} ms"
            stats["最低延迟"] = f"{min(latencies):.2f} ms"
            stats["最高延迟"] = f"{max(latencies):.2f} ms"
        
        console.print(create_summary_panel("测试统计", stats, timestamp=datetime.now()))
        
        # 导出报告
        if export_path:
            export_data = {
                "test_time": start_time.isoformat(),
                "targets": targets,
                "count": count,
                "timeout": timeout,
                "statistics": stats,
                "results": results,
            }
            save_report(export_data, Path(export_path).parent, Path(export_path).stem, "json")
        
        end_time = datetime.now()
        
        # 确定结果状态
        if fail_count == 0:
            status = ResultStatus.SUCCESS
            message = f"所有 {success_count} 个目标均可达"
        elif success_count == 0:
            status = ResultStatus.FAILED
            message = f"所有 {fail_count} 个目标均不可达"
        else:
            status = ResultStatus.PARTIAL
            message = f"{success_count} 个可达, {fail_count} 个不可达"
        
        return PluginResult(
            status=status,
            message=message,
            data=results,
            start_time=start_time,
            end_time=end_time,
            metadata={"statistics": stats},
        )
    
    def _ping_host(
        self,
        target: str,
        count: int = 4,
        timeout: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Ping单个主机
        
        Args:
            target: 目标地址
            count: Ping次数
            timeout: 超时时间
            
        Returns:
            结果字典
        """
        latencies = []
        
        if PING3_AVAILABLE:
            # 使用ping3库
            for _ in range(count):
                try:
                    delay = ping3.ping(target, timeout=timeout)
                    if delay is not None:
                        latencies.append(delay * 1000)  # 转换为毫秒
                except Exception as e:
                    logger.debug(f"ping3错误: {e}")
        else:
            # 使用系统ping命令
            latencies = self._system_ping(target, count, timeout)
        
        # 计算统计数据
        if latencies:
            return {
                "target": target,
                "status": "up",
                "latency_ms": latencies[-1],
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "avg_ms": statistics.mean(latencies),
                "jitter_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                "packet_loss": (1 - len(latencies) / count) * 100,
                "error": None,
            }
        else:
            return {
                "target": target,
                "status": "down",
                "latency_ms": None,
                "min_ms": None,
                "max_ms": None,
                "avg_ms": None,
                "jitter_ms": None,
                "packet_loss": 100.0,
                "error": "无响应",
            }
    
    def _system_ping(
        self,
        target: str,
        count: int,
        timeout: float,
    ) -> List[float]:
        """
        使用系统ping命令
        
        Args:
            target: 目标地址
            count: Ping次数
            timeout: 超时时间
            
        Returns:
            延迟列表(毫秒)
        """
        latencies = []
        
        # 根据操作系统构建命令
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), target]
        else:
            cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), target]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 5,
            )
            
            # 解析输出获取延迟
            output = result.stdout
            
            if platform.system().lower() == "windows":
                # Windows: "时间=XXms" 或 "time=XXms"
                import re
                matches = re.findall(r'[时间time]=(\d+)ms', output, re.IGNORECASE)
                latencies = [float(m) for m in matches]
            else:
                # Linux/Mac: "time=XX.X ms"
                import re
                matches = re.findall(r'time=(\d+\.?\d*)\s*ms', output)
                latencies = [float(m) for m in matches]
                
        except subprocess.TimeoutExpired:
            logger.debug(f"系统ping {target} 超时")
        except Exception as e:
            logger.debug(f"系统ping错误: {e}")
        
        return latencies
    
    def _display_results(self, results: List[Dict[str, Any]]) -> None:
        """
        显示结果表格
        
        Args:
            results: 结果列表
        """
        columns = [
            {"header": "目标", "style": NetOpsTheme.IP_ADDRESS, "justify": "left"},
            {"header": "状态", "justify": "center"},
            {"header": "延迟(ms)", "justify": "right"},
            {"header": "最小/最大(ms)", "justify": "right"},
            {"header": "抖动(ms)", "justify": "right"},
            {"header": "丢包率", "justify": "right"},
        ]
        
        rows = []
        for r in results:
            if r["status"] == "up":
                status = f"[{NetOpsTheme.STATUS_ONLINE}]● 可达[/]"
                latency = f"{r['avg_ms']:.2f}" if r['avg_ms'] else "-"
                minmax = f"{r['min_ms']:.1f}/{r['max_ms']:.1f}" if r['min_ms'] else "-"
                jitter = f"{r['jitter_ms']:.2f}" if r['jitter_ms'] is not None else "-"
            else:
                status = f"[{NetOpsTheme.STATUS_OFFLINE}]✕ 不可达[/]"
                latency = "-"
                minmax = "-"
                jitter = "-"
            
            loss = f"{r['packet_loss']:.0f}%"
            loss_style = NetOpsTheme.SUCCESS if r['packet_loss'] == 0 else (
                NetOpsTheme.WARNING if r['packet_loss'] < 50 else NetOpsTheme.ERROR
            )
            loss = f"[{loss_style}]{loss}[/]"
            
            rows.append([r["target"], status, latency, minmax, jitter, loss])
        
        table = create_result_table("Ping测试结果", columns, rows)
        console.print(table)
        console.print()


__all__ = ["PingPlugin"]
