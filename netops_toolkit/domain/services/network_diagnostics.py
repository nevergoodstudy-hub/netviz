"""
网络诊断领域服务

纯业务逻辑：根据诊断结果做出决策，不依赖任何外部基础设施。
"""

from __future__ import annotations

from netops_toolkit.domain.entities.scan_result import PingResult, ResultStatus


def classify_latency(avg_ms: float | None) -> str:
    """分类延迟等级"""
    if avg_ms is None:
        return "unreachable"
    if avg_ms < 10:
        return "excellent"
    if avg_ms < 50:
        return "good"
    if avg_ms < 100:
        return "fair"
    return "poor"


def calculate_health_score(results: list[PingResult]) -> float:
    """
    根据 Ping 结果计算网络健康评分 (0-100)

    公式: alive_ratio * 70 + (1 - avg_loss/100) * 30
    """
    if not results:
        return 0.0

    total = len(results)
    alive = sum(1 for r in results if r.is_alive)
    alive_ratio = alive / total

    losses = [r.packet_loss for r in results if r.is_alive]
    avg_loss = sum(losses) / len(losses) if losses else 100.0

    return round(alive_ratio * 70 + (1 - avg_loss / 100) * 30, 1)


def summarize_results(results: list[PingResult]) -> dict:
    """生成诊断摘要"""
    total = len(results)
    alive = sum(1 for r in results if r.is_alive)
    latencies = [r.avg_latency for r in results if r.avg_latency is not None]

    return {
        "total": total,
        "alive": alive,
        "dead": total - alive,
        "availability": f"{(alive / total * 100):.1f}%" if total else "N/A",
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "health_score": calculate_health_score(results),
    }


__all__ = ["classify_latency", "calculate_health_score", "summarize_results"]
