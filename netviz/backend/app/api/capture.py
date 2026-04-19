"""
NetViz 实时抓包 API
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.core.admin_access import require_admin_access
from app.core.config import settings
from app.services.capture.capture_service import capture_service

router = APIRouter(dependencies=[Depends(require_admin_access)])


# ==================== Pydantic 模型 ====================


class CaptureStartRequest(BaseModel):
    """开始抓包请求"""

    interface: str
    filter: Optional[str] = None
    max_packets: int = 0
    save_to_file: bool = False


class CaptureSessionResponse(BaseModel):
    """抓包会话响应"""

    id: str
    interface: str
    filter: Optional[str]
    start_time: str
    packet_count: int
    byte_count: int
    is_running: bool


class InterfaceInfo(BaseModel):
    """网络接口信息"""

    name: str
    description: str
    friendly_name: Optional[str] = None
    ips: list[str] = []
    mac: Optional[str] = None


class PacketInfo(BaseModel):
    """数据包信息"""

    index: int
    timestamp: str
    length: int
    protocol: str
    src_ip: Optional[str]
    dst_ip: Optional[str]
    src_port: Optional[int]
    dst_port: Optional[int]
    info: str


# ==================== API 接口 ====================


@router.get("/interfaces", response_model=list[InterfaceInfo])
async def list_interfaces():
    """获取可用网络接口列表"""
    try:
        interfaces = capture_service.get_interfaces()
        if not interfaces:
            return [{"name": "无可用接口", "description": "请确保已安装 Npcap 驱动"}]
        return interfaces
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取接口失败: {str(e)}")


@router.post("/start", response_model=CaptureSessionResponse)
async def start_capture(request: CaptureStartRequest):
    """开始抓包"""
    session_id = str(uuid.uuid4())[:8]

    # 准备输出文件
    output_file = None
    if request.save_to_file:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = settings.upload_dir / f"capture_{timestamp}.pcap"

    try:
        session = capture_service.start_capture(
            session_id=session_id,
            interface=request.interface,
            filter_expr=request.filter,
            output_file=output_file,
            max_packets=request.max_packets,
        )

        return CaptureSessionResponse(
            id=session.id,
            interface=session.interface,
            filter=session.filter,
            start_time=session.start_time.isoformat(),
            packet_count=session.packet_count,
            byte_count=session.byte_count,
            is_running=session.is_running,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动抓包失败: {str(e)}")


@router.post("/stop/{session_id}", response_model=CaptureSessionResponse)
async def stop_capture(session_id: str):
    """停止抓包"""
    session = capture_service.stop_capture(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return CaptureSessionResponse(
        id=session.id,
        interface=session.interface,
        filter=session.filter,
        start_time=session.start_time.isoformat(),
        packet_count=session.packet_count,
        byte_count=session.byte_count,
        is_running=session.is_running,
    )


@router.get("/sessions", response_model=list[CaptureSessionResponse])
async def list_sessions():
    """获取所有抓包会话"""
    sessions = []
    for session in capture_service.sessions.values():
        sessions.append(
            CaptureSessionResponse(
                id=session.id,
                interface=session.interface,
                filter=session.filter,
                start_time=session.start_time.isoformat(),
                packet_count=session.packet_count,
                byte_count=session.byte_count,
                is_running=session.is_running,
            )
        )
    return sessions


@router.get("/sessions/{session_id}", response_model=CaptureSessionResponse)
async def get_session(session_id: str):
    """获取抓包会话详情"""
    session = capture_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return CaptureSessionResponse(
        id=session.id,
        interface=session.interface,
        filter=session.filter,
        start_time=session.start_time.isoformat(),
        packet_count=session.packet_count,
        byte_count=session.byte_count,
        is_running=session.is_running,
    )


@router.get("/sessions/{session_id}/packets", response_model=list[PacketInfo])
async def get_session_packets(
    session_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """获取抓包会话中的数据包"""
    session = capture_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    packets = capture_service.get_session_packets(session_id, offset, limit)
    return packets


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除抓包会话"""
    if not capture_service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")

    return {"message": "会话已删除"}


@router.get("/check")
async def check_capture_capability():
    """检查抓包功能是否可用"""
    try:
        interfaces = capture_service.get_interfaces()
        has_npcap = len(interfaces) > 0

        return {
            "available": has_npcap,
            "interface_count": len(interfaces),
            "message": "抓包功能可用" if has_npcap else "请安装 Npcap 驱动以启用抓包功能",
            "npcap_download": "https://npcap.com/#download",
        }
    except Exception as e:
        return {
            "available": False,
            "interface_count": 0,
            "message": f"检查失败: {str(e)}",
            "npcap_download": "https://npcap.com/#download",
        }
