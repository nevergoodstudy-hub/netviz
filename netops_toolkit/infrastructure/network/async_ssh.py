"""
异步 SSH 服务

将 Netmiko 的阻塞操作包装为 async 接口，
使用 run_in_executor 避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict

from loguru import logger

from netops_toolkit.application.interfaces.services import SSHService
from netops_toolkit.domain.entities.credential import Credential
from netops_toolkit.domain.entities.device import Device
from netops_toolkit.domain.entities.scan_result import OperationResult, ResultStatus
from netops_toolkit.domain.exceptions import (
    DeviceAuthenticationError,
    DeviceCommandError,
    DeviceConnectionError,
    DeviceTimeoutError,
    SSHConnectionError,
)


class AsyncSSHService(SSHService):
    """
    异步 SSH 服务

    实现 SSHService 接口。Netmiko 本身是同步库，
    通过 run_in_executor 在线程池中运行以保持非阻塞。
    """

    async def execute_command(
        self,
        device: Device,
        credential: Credential,
        command: str,
        timeout: float = 30.0,
    ) -> OperationResult:
        """在设备上执行命令"""
        loop = asyncio.get_running_loop()
        start = datetime.now()

        try:
            output = await loop.run_in_executor(
                None,
                self._sync_execute,
                device,
                credential,
                command,
                timeout,
            )
            end = datetime.now()
            return OperationResult(
                status=ResultStatus.SUCCESS,
                message=f"命令在 {device.name} 上执行成功",
                data={"output": output, "device": str(device)},
                start_time=start,
                end_time=end,
            )
        except (
            DeviceConnectionError,
            DeviceAuthenticationError,
            DeviceTimeoutError,
            DeviceCommandError,
        ) as e:
            end = datetime.now()
            return OperationResult(
                status=ResultStatus.FAILED,
                message=str(e),
                errors=[str(e)],
                start_time=start,
                end_time=end,
                metadata={"device": str(device)},
            )
        except Exception as e:
            end = datetime.now()
            logger.error(f"SSH to {device}: {e}")
            return OperationResult(
                status=ResultStatus.ERROR,
                message=f"意外错误: {e}",
                errors=[str(e)],
                start_time=start,
                end_time=end,
                metadata={"device": str(device)},
            )

    async def execute_batch(
        self,
        devices: list[Device],
        credential: Credential,
        commands: list[str],
        timeout: float = 30.0,
        concurrency: int = 10,
    ) -> list[OperationResult]:
        """
        批量执行命令

        使用 Semaphore 控制并发连接数。
        """
        semaphore = asyncio.Semaphore(concurrency)
        combined_cmd = "\n".join(commands)

        async def _limited(dev: Device) -> OperationResult:
            async with semaphore:
                return await self.execute_command(
                    dev, credential, combined_cmd, timeout
                )

        tasks = [_limited(d) for d in devices]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    # ── 同步内核 ──

    @staticmethod
    def _sync_execute(
        device: Device,
        credential: Credential,
        command: str,
        timeout: float,
    ) -> str:
        """
        同步 SSH 执行 (在 executor 线程中运行)

        Raises:
            DeviceConnectionError
            DeviceAuthenticationError
            DeviceTimeoutError
            DeviceCommandError
        """
        try:
            from netmiko import ConnectHandler
            from netmiko.exceptions import (
                NetmikoAuthenticationException,
                NetmikoTimeoutException,
            )
        except ImportError as e:
            raise DeviceConnectionError(
                device.name, "netmiko 未安装"
            ) from e

        params: Dict[str, Any] = device.get_netmiko_params()
        params["username"] = credential.username
        params["timeout"] = int(timeout)

        # 密码认证
        pw = credential.get_password_value()
        if pw:
            params["password"] = pw

        # SSH Key 认证
        if credential.has_ssh_key():
            params["use_keys"] = True
            params["key_file"] = credential.ssh_key_path

        try:
            with ConnectHandler(**params) as conn:
                # 支持多行命令
                lines = [c.strip() for c in command.split("\n") if c.strip()]
                outputs = []
                for line in lines:
                    out = conn.send_command(line, read_timeout=timeout)
                    outputs.append(out)
                return "\n".join(outputs)

        except NetmikoAuthenticationException as e:
            raise DeviceAuthenticationError(device.name) from e
        except NetmikoTimeoutException as e:
            raise DeviceTimeoutError(device.name, command, timeout) from e
        except Exception as e:
            raise DeviceConnectionError(device.name, str(e)) from e


__all__ = ["AsyncSSHService"]
