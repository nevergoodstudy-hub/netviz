"""
CLI 输出格式化器

使用 Rich 库渲染表格、进度条等 CLI 输出。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from netops_toolkit.application.dto.network_dto import (
    PingBatchResponseDTO,
    SSHBatchResponseDTO,
)


def format_ping_results(result: PingBatchResponseDTO) -> str:
    """
    格式化 Ping 结果为 ASCII 表格

    尝试使用 Rich 表格，如不可用则回退到纯文本。
    """
    try:
        return _format_ping_rich(result)
    except ImportError:
        return _format_ping_plain(result)


def format_ping_results_json(result: PingBatchResponseDTO) -> str:
    """格式化 Ping 结果为 JSON"""
    return json.dumps(
        result.model_dump(),
        indent=2,
        ensure_ascii=False,
        default=str,
    )


def format_ssh_results(result: SSHBatchResponseDTO) -> str:
    """格式化 SSH 批量结果"""
    try:
        return _format_ssh_rich(result)
    except ImportError:
        return _format_ssh_plain(result)


# ── Rich 格式化 ──


def _format_ping_rich(result: PingBatchResponseDTO) -> str:
    from io import StringIO

    from rich.console import Console
    from rich.table import Table

    table = Table(title="Ping Results", show_lines=True)
    table.add_column("Host", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Packet Loss", justify="right")

    for r in result.results:
        status = "[green]✓ ALIVE[/green]" if r.is_alive else "[red]✗ DOWN[/red]"
        latency = f"{r.avg_latency:.1f}" if r.avg_latency is not None else "-"
        loss = f"{r.packet_loss:.0f}%"
        table.add_row(r.host, status, latency, loss)

    # 摘要行
    table.add_section()
    table.add_row(
        f"Total: {result.total}",
        f"[green]{result.alive_count}[/green] / [red]{result.dead_count}[/red]",
        "",
        f"{result.duration:.2f}s" if result.duration else "-",
    )

    buf = StringIO()
    console = Console(file=buf, force_terminal=False)
    console.print(table)
    return buf.getvalue()


def _format_ssh_rich(result: SSHBatchResponseDTO) -> str:
    from io import StringIO

    from rich.console import Console
    from rich.table import Table

    table = Table(title="SSH Batch Results", show_lines=True)
    table.add_column("Device", style="cyan", no_wrap=True)
    table.add_column("IP", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Output (preview)", max_width=50)

    for r in result.results:
        status_str = (
            "[green]SUCCESS[/green]"
            if r.status.value == "success"
            else "[red]FAILED[/red]"
        )
        preview = (r.output[:80] + "...") if len(r.output) > 80 else r.output
        table.add_row(r.device_name, r.device_ip, status_str, preview)

    table.add_section()
    table.add_row(
        f"Total: {result.total}",
        "",
        f"[green]{result.success_count}[/green] / [red]{result.failed_count}[/red]",
        f"{result.duration:.2f}s" if result.duration else "-",
    )

    buf = StringIO()
    console = Console(file=buf, force_terminal=False)
    console.print(table)
    return buf.getvalue()


# ── 纯文本回退 ──


def _format_ping_plain(result: PingBatchResponseDTO) -> str:
    lines = ["=" * 60, "  Ping Results", "=" * 60]
    for r in result.results:
        status = "ALIVE" if r.is_alive else "DOWN"
        latency = f"{r.avg_latency:.1f}ms" if r.avg_latency is not None else "-"
        lines.append(f"  {r.host:<20} {status:<8} {latency:<10} loss={r.packet_loss:.0f}%")
    lines.append("-" * 60)
    lines.append(
        f"  Total: {result.total}  Alive: {result.alive_count}  "
        f"Dead: {result.dead_count}  Duration: {result.duration:.2f}s"
    )
    return "\n".join(lines)


def _format_ssh_plain(result: SSHBatchResponseDTO) -> str:
    lines = ["=" * 60, "  SSH Batch Results", "=" * 60]
    for r in result.results:
        status = "OK" if r.status.value == "success" else "FAIL"
        lines.append(f"  {r.device_name:<16} {r.device_ip:<16} {status}")
    lines.append("-" * 60)
    lines.append(
        f"  Total: {result.total}  Success: {result.success_count}  "
        f"Failed: {result.failed_count}"
    )
    return "\n".join(lines)


__all__ = [
    "format_ping_results",
    "format_ping_results_json",
    "format_ssh_results",
]
