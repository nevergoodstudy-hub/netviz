"""
设备管理 API 路由

从 web/app.py 提取的设备相关端点，使用 APIRouter 模块化。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def list_devices(
    group: Optional[str] = Query(None, description="按组名过滤"),
    vendor: Optional[str] = Query(None, description="按厂商过滤"),
) -> dict:
    """获取设备列表 API"""
    try:
        from netops_toolkit.config.device_inventory import DeviceInventory

        config_paths = [
            Path("config/devices.yaml"),
            Path.cwd() / "config" / "devices.yaml",
        ]
        for path in config_paths:
            if path.exists():
                inventory = DeviceInventory(path)
                devices = [
                    {
                        "name": d.name,
                        "ip": d.ip,
                        "vendor": getattr(d, "vendor", ""),
                        "description": getattr(d, "description", ""),
                        "group": getattr(d, "group", ""),
                    }
                    for d in inventory
                ]

                # 应用过滤
                if group:
                    devices = [d for d in devices if d.get("group") == group]
                if vendor:
                    devices = [d for d in devices if d.get("vendor") == vendor]

                return {"status": "ok", "devices": devices, "count": len(devices)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "ok", "devices": [], "count": 0}


@router.get("/{device_name}")
async def get_device(device_name: str) -> dict:
    """获取单个设备详情"""
    try:
        from netops_toolkit.config.device_inventory import DeviceInventory

        config_paths = [
            Path("config/devices.yaml"),
            Path.cwd() / "config" / "devices.yaml",
        ]
        for path in config_paths:
            if path.exists():
                inventory = DeviceInventory(path)
                for d in inventory:
                    if d.name == device_name:
                        return {
                            "status": "ok",
                            "device": {
                                "name": d.name,
                                "ip": d.ip,
                                "vendor": getattr(d, "vendor", ""),
                                "description": getattr(d, "description", ""),
                            },
                        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "error", "message": f"Device '{device_name}' not found"}


__all__ = ["router"]
