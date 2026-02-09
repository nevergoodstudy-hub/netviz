"""
Ping CLI 命令

通过 DI 容器获取 PingCommand, 委托给应用层执行。
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

import typer

from netops_toolkit.application.dto.network_dto import PingRequestDTO

app = typer.Typer(help="Ping 连通性测试")


def _get_ping_command():
    """延迟导入并获取 PingCommand 实例"""
    from netops_toolkit.container import Container

    container = Container()
    return container.ping_command()


@app.command("run")
def ping_run(
    targets: List[str] = typer.Argument(..., help="目标 IP/主机名列表"),
    count: int = typer.Option(4, "-c", "--count", help="Ping 次数"),
    timeout: float = typer.Option(2.0, "-t", "--timeout", help="超时 (秒)"),
    concurrency: int = typer.Option(50, "--concurrency", help="并发数"),
    json_output: bool = typer.Option(False, "--json", help="JSON 格式输出"),
) -> None:
    """对目标执行 Ping 测试"""
    from netops_toolkit.presentation.cli.formatters.table_formatter import (
        format_ping_results,
        format_ping_results_json,
    )

    request = PingRequestDTO(
        targets=targets,
        count=count,
        timeout=timeout,
        concurrency=concurrency,
    )

    ping_cmd = _get_ping_command()
    result = asyncio.run(ping_cmd.execute(request))

    if json_output:
        typer.echo(format_ping_results_json(result))
    else:
        typer.echo(format_ping_results(result))


@app.command("quick")
def ping_quick(
    target: str = typer.Argument(..., help="单个目标 IP/主机名"),
) -> None:
    """快速 Ping 单个目标 (4 次)"""
    from netops_toolkit.presentation.cli.formatters.table_formatter import (
        format_ping_results,
    )

    request = PingRequestDTO(targets=[target], count=4, timeout=2.0)
    ping_cmd = _get_ping_command()
    result = asyncio.run(ping_cmd.execute(request))
    typer.echo(format_ping_results(result))


__all__ = ["app"]
