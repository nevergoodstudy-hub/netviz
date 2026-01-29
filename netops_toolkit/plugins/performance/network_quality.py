"""
网络质量测试插件

综合测试延迟、抖动、丢包率,评估网络质量等级。
"""

from typing import Any, Dict, List, Optional, Tuple
from statistics import mean, stdev
from datetime import datetime
import time

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.utils.network_utils import is_valid_ip
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)

try:
    from ping3 import ping
    PING3_AVAILABLE = True
except ImportError:
    PING3_AVAILABLE = False


@register_plugin
class NetworkQualityPlugin(Plugin):
    """网络质量测试插件"""
    
    name = "network_quality"
    description = "网络质量综合测试"
    category = "performance"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        if not PING3_AVAILABLE:
            return False, "ping3库未安装, 请运行: pip install ping3"
        return True, None
    
    def get_required_params(self) -> List[str]:
        """获取必需参数"""
        return ["target"]
    
    def run(self, params: Dict[str, Any]) -> PluginResult:
        """
        执行网络质量测试
        
        参数:
            target: 目标IP或主机名
            count: 测试次数 (默认50)
            interval: 测试间隔秒数 (默认0.2)
            timeout: 超时时间 (默认3秒)
            packet_size: 包大小字节 (默认56)
        """
        target = params.get("target")
        count = params.get("count", 50)
        interval = params.get("interval", 0.2)
        timeout = params.get("timeout", 3.0)
        packet_size = params.get("packet_size", 56)
        
        if not target:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定目标",
                data={}
            )
        
        logger.info(f"开始网络质量测试: {target} (测试次数: {count})")
        
        # 执行测试
        start_time = datetime.now()
        results = self._perform_quality_test(
            target=target,
            count=count,
            interval=interval,
            timeout=timeout,
            packet_size=packet_size,
        )
        duration = (datetime.now() - start_time).total_seconds()
        
        if not results["success"]:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=results.get("error", "测试失败"),
                data=results
            )
        
        # 分析结果
        analysis = self._analyze_quality(results)
        
        # 显示结果
        self._display_results(target, results, analysis)
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"网络质量: {analysis['grade']} - {analysis['description']}",
            data={
                "target": target,
                "results": results,
                "analysis": analysis,
                "duration": duration,
                "timestamp": start_time.isoformat(),
            }
        )
    
    def _perform_quality_test(
        self,
        target: str,
        count: int,
        interval: float,
        timeout: float,
        packet_size: int,
    ) -> Dict[str, Any]:
        """执行质量测试"""
        latencies = []
        sent = 0
        received = 0
        errors = []
        
        for i in range(count):
            sent += 1
            try:
                delay = ping(target, timeout=timeout, unit="ms", size=packet_size)
                
                if delay is None:
                    errors.append(f"No.{i+1}: 超时")
                elif delay is False:
                    errors.append(f"No.{i+1}: 无法到达")
                else:
                    latencies.append(delay)
                    received += 1
                    logger.debug(f"Ping {target}: 序号={i+1}, 延迟={delay:.2f}ms")
                
            except Exception as e:
                errors.append(f"No.{i+1}: {str(e)}")
                logger.debug(f"Ping错误: {e}")
            
            if i < count - 1:  # 最后一次不需要等待
                time.sleep(interval)
        
        if not latencies:
            return {
                "success": False,
                "error": "所有测试都失败",
                "sent": sent,
                "received": 0,
                "errors": errors[:10],  # 只保留前10个错误
            }
        
        # 计算统计数据
        latencies_sorted = sorted(latencies)
        loss_rate = ((sent - received) / sent) * 100
        
        # 计算抖动 (连续测量值的差异)
        jitters = []
        for i in range(1, len(latencies)):
            jitter = abs(latencies[i] - latencies[i-1])
            jitters.append(jitter)
        
        return {
            "success": True,
            "sent": sent,
            "received": received,
            "loss_rate": loss_rate,
            "latencies": {
                "min": min(latencies),
                "max": max(latencies),
                "avg": mean(latencies),
                "median": latencies_sorted[len(latencies_sorted) // 2],
                "stdev": stdev(latencies) if len(latencies) > 1 else 0,
                "samples": latencies,
            },
            "jitter": {
                "min": min(jitters) if jitters else 0,
                "max": max(jitters) if jitters else 0,
                "avg": mean(jitters) if jitters else 0,
                "samples": jitters,
            },
            "errors": errors[:10] if errors else [],
        }
    
    def _analyze_quality(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析网络质量并评级
        
        评级标准:
        - A (优秀): 延迟<30ms, 抖动<5ms, 丢包<1%
        - B (良好): 延迟<50ms, 抖动<10ms, 丢包<3%
        - C (一般): 延迟<100ms, 抖动<20ms, 丢包<5%
        - D (较差): 延迟<200ms, 抖动<50ms, 丢包<10%
        - F (很差): 超过D标准
        """
        avg_latency = results["latencies"]["avg"]
        avg_jitter = results["jitter"]["avg"]
        loss_rate = results["loss_rate"]
        
        # 延迟评分
        if avg_latency < 30:
            latency_score = 5
        elif avg_latency < 50:
            latency_score = 4
        elif avg_latency < 100:
            latency_score = 3
        elif avg_latency < 200:
            latency_score = 2
        else:
            latency_score = 1
        
        # 抖动评分
        if avg_jitter < 5:
            jitter_score = 5
        elif avg_jitter < 10:
            jitter_score = 4
        elif avg_jitter < 20:
            jitter_score = 3
        elif avg_jitter < 50:
            jitter_score = 2
        else:
            jitter_score = 1
        
        # 丢包评分
        if loss_rate < 1:
            loss_score = 5
        elif loss_rate < 3:
            loss_score = 4
        elif loss_rate < 5:
            loss_score = 3
        elif loss_rate < 10:
            loss_score = 2
        else:
            loss_score = 1
        
        # 综合评分 (加权平均: 延迟40%, 抖动30%, 丢包30%)
        total_score = (latency_score * 0.4 + jitter_score * 0.3 + loss_score * 0.3)
        
        # 确定等级
        if total_score >= 4.5:
            grade = "A"
            description = "优秀"
            color = "green"
        elif total_score >= 3.5:
            grade = "B"
            description = "良好"
            color = "cyan"
        elif total_score >= 2.5:
            grade = "C"
            description = "一般"
            color = "yellow"
        elif total_score >= 1.5:
            grade = "D"
            description = "较差"
            color = "magenta"
        else:
            grade = "F"
            description = "很差"
            color = "red"
        
        # 问题诊断
        issues = []
        if avg_latency > 100:
            issues.append("高延迟")
        if avg_jitter > 20:
            issues.append("高抖动")
        if loss_rate > 5:
            issues.append("高丢包率")
        
        # 使用建议
        recommendations = []
        if grade in ["A", "B"]:
            recommendations.append("网络质量良好,适合实时应用(VoIP、视频会议)")
        elif grade == "C":
            recommendations.append("网络质量一般,基本可用但可能影响体验")
        else:
            recommendations.append("网络质量较差,建议检查网络配置")
            if avg_latency > 100:
                recommendations.append("检查路由路径和网络拥塞")
            if avg_jitter > 20:
                recommendations.append("检查网络设备QoS配置")
            if loss_rate > 5:
                recommendations.append("检查链路质量和设备故障")
        
        return {
            "grade": grade,
            "description": description,
            "color": color,
            "score": round(total_score, 2),
            "scores": {
                "latency": latency_score,
                "jitter": jitter_score,
                "loss": loss_score,
            },
            "issues": issues,
            "recommendations": recommendations,
        }
    
    def _display_results(
        self,
        target: str,
        results: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> None:
        """显示测试结果"""
        from netops_toolkit.ui.theme import console
        
        # 基本统计
        stats = {
            "发送": results["sent"],
            "接收": results["received"],
            "丢包率": f"{results['loss_rate']:.2f}%",
            "最小延迟": f"{results['latencies']['min']:.2f}ms",
            "平均延迟": f"{results['latencies']['avg']:.2f}ms",
            "最大延迟": f"{results['latencies']['max']:.2f}ms",
            "延迟标准差": f"{results['latencies']['stdev']:.2f}ms",
            "平均抖动": f"{results['jitter']['avg']:.2f}ms",
        }
        
        panel = create_summary_panel(f"网络质量测试: {target}", stats)
        console.print(panel)
        
        # 质量评级
        grade_color = analysis["color"]
        console.print(f"\n[bold {grade_color}]质量等级: {analysis['grade']} ({analysis['description']})[/bold {grade_color}]")
        console.print(f"[dim]综合评分: {analysis['score']}/5.0[/dim]\n")
        
        # 问题诊断
        if analysis["issues"]:
            console.print("[bold red]发现问题:[/bold red]")
            for issue in analysis["issues"]:
                console.print(f"  [red]• {issue}[/red]")
            console.print()
        
        # 建议
        if analysis["recommendations"]:
            console.print("[bold cyan]建议:[/bold cyan]")
            for rec in analysis["recommendations"]:
                console.print(f"  [cyan]• {rec}[/cyan]")
            console.print()


__all__ = ["NetworkQualityPlugin"]
