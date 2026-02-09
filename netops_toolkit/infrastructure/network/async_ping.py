"""
异步 Ping 服务

使用 asyncio 实现非阻塞的 ICMP Ping 操作。
优先使用 ping3 库，回退到系统 ping 命令。
"""

from __future__ import annotations

import asyncio
import re
import statistics
from typing import Optional

from loguru import logger

from netops_toolkit.application.interfaces.services import PingService
from netops_toolkit.domain.entities.scan_result import PingResult


class AsyncPingService(PingService):
    """
    异步 Ping 服务

    实现 PingService 接口，替代旧版基于 ThreadPoolExecutor 的同步实现。
    """

    def __init__(self) -> None:
        # 延迟检测 ping3 可用性
        self._ping3_available: Optional[bool] = None

    def _check_ping3(self) -> bool:
        if self._ping3_available is None:
            try:
                import ping3  # noqa: F401

                self._ping3_available = True
            except ImportError:
                self._ping3_available = False
        return self._ping3_available

    async def ping(
        self,
        host: str,
        count: int = 4,
        timeout: float = 2.0,
    ) -> PingResult:
        """对单个主机执行 Ping"""
        if self._check_ping3():
            return await self._ping_with_ping3(host, count, timeout)
        return await self._ping_with_system(host, count, timeout)

    async def ping_batch(
        self,
        hosts: list[str],
        count: int = 4,
        timeout: float = 2.0,
        concurrency: int = 50,
    ) -> list[PingResult]:
        """
        批量 Ping

        使用 asyncio.Semaphore 控制并发。
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _limited_ping(h: str) -> PingResult:
            async with semaphore:
                return await self.ping(h, count, timeout)

        tasks = [_limited_ping(h) for h in hosts]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    # ── ping3 实现 ──

    async def _ping_with_ping3(
        self, host: str, count: int, timeout: float
    ) -> PingResult:
        """使用 ping3 库 (在线程中运行以避免阻塞)"""
        import ping3 as _ping3

        loop = asyncio.get_running_loop()
        latencies: list[float] = []

        for _ in range(count):
            try:
                delay = await loop.run_in_executor(
                    None, lambda: _ping3.ping(host, timeout=timeout)
                )
                if delay is not None and delay is not False:
                    latencies.append(delay * 1000)  # → ms
            except Exception as e:
                logger.debug(f"ping3 error for {host}: {e}")

        return self._build_result(host, latencies, count)

    # ── 系统 ping 实现 ──

    async def _ping_with_system(
        self, host: str, count: int, timeout: float
    ) -> PingResult:
        """使用系统 ping 命令 (asyncio subprocess)"""
        import sys

        if sys.platform == "win32":
            cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), host]
        else:
            cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), host]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout * count + 5,
            )
            output = stdout.decode(errors="replace")
            latencies = self._parse_ping_output(output)
        except asyncio.TimeoutError:
            logger.debug(f"system ping {host} timed out")
            latencies = []
        except Exception as e:
            logger.debug(f"system ping error for {host}: {e}")
            latencies = []

        return self._build_result(host, latencies, count)

    # ── 工具方法 ──

    @staticmethod
    def _parse_ping_output(output: str) -> list[float]:
        """解析系统 ping 输出，提取延迟值"""
        import sys

        if sys.platform == "win32":
            matches = re.findall(
                r"[时间time][=<](\d+)\s*m?s", output, re.IGNORECASE
            )
        else:
            matches = re.findall(
                r"time=(\d+\.?\d*)\s*ms", output, re.IGNORECASE
            )
        return [float(m) for m in matches]

    @staticmethod
    def _build_result(
        host: str, latencies: list[float], count: int
    ) -> PingResult:
        """从延迟列表构建 PingResult"""
        if latencies:
            return PingResult(
                host=host,
                is_alive=True,
                min_latency=min(latencies),
                avg_latency=statistics.mean(latencies),
                max_latency=max(latencies),
                jitter=(
                    statistics.stdev(latencies) if len(latencies) > 1 else 0.0
                ),
                packet_loss=(1 - len(latencies) / count) * 100,
                packets_sent=count,
                packets_received=len(latencies),
            )
        return PingResult(
            host=host,
            is_alive=False,
            packet_loss=100.0,
            packets_sent=count,
            packets_received=0,
        )


__all__ = ["AsyncPingService"]
