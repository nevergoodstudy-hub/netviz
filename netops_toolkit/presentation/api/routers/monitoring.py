"""
监控 API 路由

从 web/app.py 提取的监控相关端点。
使用 asyncio.create_subprocess_exec 替代阻塞 subprocess。
"""

from __future__ import annotations

import asyncio
import platform
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


async def _async_ping(ip: str, timeout: float = 3.0) -> str:
    """异步 Ping 单个主机"""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    cmd = ["ping", param, "1", "-w", "1000", ip]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "unknown"
        return "online" if proc.returncode == 0 else "offline"
    except OSError:
        return "unknown"


@router.get("/status")
async def monitoring_status() -> dict:
    """获取监控状态"""
    # 获取设备列表
    devices: List[dict] = []
    try:
        from netops_toolkit.config.device_inventory import DeviceInventory

        config_paths = [
            Path("config/devices.yaml"),
            Path.cwd() / "config" / "devices.yaml",
        ]
        for path in config_paths:
            if path.exists():
                inventory = DeviceInventory(path)
                devices = [{"name": d.name, "ip": d.ip} for d in inventory]
                break
    except Exception:
        devices = [
            {"name": "SW-CORE-01", "ip": "192.168.1.10"},
            {"name": "SW-CORE-02", "ip": "192.168.1.11"},
        ]

    # 并发异步 Ping
    target_devices = devices[:5]
    statuses = await asyncio.gather(
        *[_async_ping(d["ip"]) for d in target_devices]
    )

    results = [
        {
            "name": device["name"],
            "ip": device["ip"],
            "status": status,
            "latency": "-",
        }
        for device, status in zip(target_devices, statuses)
    ]

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "devices": results,
    }


__all__ = ["router"]
