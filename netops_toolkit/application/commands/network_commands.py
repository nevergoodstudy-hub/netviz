"""
网络操作命令 (Command)

遵循 CQRS 模式: 命令执行有副作用的操作。
命令通过接口依赖服务，不直接依赖基础设施。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from loguru import logger

from netops_toolkit.application.dto.network_dto import (
    PingBatchResponseDTO,
    PingRequestDTO,
    PingResultDTO,
    SSHBatchResponseDTO,
    SSHCommandRequestDTO,
    SSHCommandResultDTO,
)
from netops_toolkit.application.interfaces.repositories import (
    CredentialRepository,
    DeviceRepository,
)
from netops_toolkit.application.interfaces.services import PingService, SSHService
from netops_toolkit.domain.exceptions import (
    CredentialNotFoundError,
    DeviceNotFoundError,
)


class PingCommand:
    """
    Ping 命令

    编排 Ping 操作: 解析目标 → 调用服务 → 聚合结果。
    """

    def __init__(self, ping_service: PingService) -> None:
        self._ping = ping_service

    async def execute(self, request: PingRequestDTO) -> PingBatchResponseDTO:
        start = datetime.now()

        results = await self._ping.ping_batch(
            hosts=request.targets,
            count=request.count,
            timeout=request.timeout,
            concurrency=request.concurrency,
        )

        end = datetime.now()
        duration = (end - start).total_seconds()

        dto_results = [
            PingResultDTO(
                host=r.host,
                is_alive=r.is_alive,
                avg_latency=r.avg_latency,
                packet_loss=r.packet_loss,
            )
            for r in results
        ]

        alive = sum(1 for r in results if r.is_alive)

        return PingBatchResponseDTO(
            results=dto_results,
            total=len(results),
            alive_count=alive,
            dead_count=len(results) - alive,
            duration=duration,
        )


class SSHBatchCommand:
    """
    SSH 批量命令

    编排 SSH 操作: 解析设备/凭证 → 调用服务 → 聚合结果。
    """

    def __init__(
        self,
        ssh_service: SSHService,
        device_repo: DeviceRepository,
        credential_repo: CredentialRepository,
    ) -> None:
        self._ssh = ssh_service
        self._devices = device_repo
        self._credentials = credential_repo

    async def execute(self, request: SSHCommandRequestDTO) -> SSHBatchResponseDTO:
        start = datetime.now()

        # 1. 解析设备列表
        devices = []
        if request.group:
            devices = self._devices.get_by_group(request.group)
        for name in request.device_names:
            dev = self._devices.get_by_name(name)
            if dev is None:
                raise DeviceNotFoundError(name)
            devices.append(dev)

        if not devices:
            return SSHBatchResponseDTO(total=0, duration=0)

        # 2. 解析凭证
        cred = self._credentials.get(request.credential_name)
        if cred is None:
            raise CredentialNotFoundError(request.credential_name)

        # 3. 执行
        results = await self._ssh.execute_batch(
            devices=devices,
            credential=cred,
            commands=request.commands,
            timeout=request.timeout,
            concurrency=request.concurrency,
        )

        end = datetime.now()
        duration = (end - start).total_seconds()

        # 4. 映射为 DTO
        dto_results = []
        success = 0
        for r, dev in zip(results, devices):
            is_ok = r.is_success
            if is_ok:
                success += 1
            dto_results.append(
                SSHCommandResultDTO(
                    device_name=dev.name,
                    device_ip=dev.ip,
                    status=r.status,
                    output=r.data.get("output", "") if isinstance(r.data, dict) else "",
                    error=r.errors[0] if r.errors else "",
                    duration=r.duration,
                )
            )

        return SSHBatchResponseDTO(
            results=dto_results,
            total=len(devices),
            success_count=success,
            failed_count=len(devices) - success,
            duration=duration,
        )


__all__ = ["PingCommand", "SSHBatchCommand"]
