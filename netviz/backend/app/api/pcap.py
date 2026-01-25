"""
NetViz PCAP 文件操作 API
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.pcap import Connection, DnsRecord, HttpTransaction, Packet, ParseStatus, PcapFile
from app.services.parser.pcap_parser import parse_pcap_async

router = APIRouter()


# ============== Schemas ==============

class PcapFileResponse(BaseModel):
    """PCAP 文件响应"""

    id: int
    filename: str
    original_filename: str
    file_size: int
    file_hash: str
    status: str
    parse_progress: float
    total_packets: int
    total_bytes: int
    start_time: datetime | None
    end_time: datetime | None
    duration_seconds: float
    created_at: datetime

    class Config:
        from_attributes = True


class PcapListResponse(BaseModel):
    """PCAP 列表响应"""

    items: list[PcapFileResponse]
    total: int


class PacketResponse(BaseModel):
    """数据包响应"""

    id: int
    packet_number: int
    timestamp: datetime
    src_mac: str | None
    dst_mac: str | None
    src_ip: str | None
    dst_ip: str | None
    protocol: str | None
    src_port: int | None
    dst_port: int | None
    tcp_flags: str | None
    app_protocol: str | None
    length: int
    payload_length: int

    class Config:
        from_attributes = True


class ConnectionResponse(BaseModel):
    """连接响应"""

    id: int
    src_ip: str
    dst_ip: str
    src_port: int | None
    dst_port: int | None
    protocol: str
    packet_count: int
    byte_count: int
    src_to_dst_packets: int
    dst_to_src_packets: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    app_protocol: str | None
    is_encrypted: bool
    risk_score: float
    src_country: str | None
    dst_country: str | None
    src_lat: float | None
    src_lon: float | None
    dst_lat: float | None
    dst_lon: float | None

    class Config:
        from_attributes = True


class ProtocolStatsResponse(BaseModel):
    """协议统计响应"""

    protocol: str
    count: int
    bytes: int
    percentage: float


class TopTalkersResponse(BaseModel):
    """Top 通信者响应"""

    ip: str
    packets_sent: int
    packets_received: int
    bytes_sent: int
    bytes_received: int
    connections: int


# ============== 进度管理 ==============

# 使用内存存储解析进度（单机版足够）
parse_progress: dict[int, float] = {}


def update_progress(pcap_id: int, progress: float) -> None:
    """更新解析进度"""
    parse_progress[pcap_id] = progress


# ============== API Endpoints ==============

@router.post("/upload", response_model=PcapFileResponse)
async def upload_pcap(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """上传 PCAP 文件"""
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    allowed_extensions = {".pcap", ".pcapng", ".cap"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")

    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = settings.upload_dir / unique_filename
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件并计算哈希
    sha256_hash = hashlib.sha256()
    file_size = 0

    with open(file_path, "wb") as f:
        while chunk := await file.read(8192):
            f.write(chunk)
            sha256_hash.update(chunk)
            file_size += len(chunk)

    file_hash = sha256_hash.hexdigest()

    # 检查文件大小
    if file_size > settings.max_upload_size:
        file_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大允许 {settings.max_upload_size // (1024*1024)} MB",
        )

    # 创建数据库记录
    pcap_file = PcapFile(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_hash=file_hash,
        status=ParseStatus.PENDING.value,
    )
    db.add(pcap_file)
    await db.commit()
    await db.refresh(pcap_file)

    # 后台解析
    background_tasks.add_task(parse_pcap_task, pcap_file.id, str(file_path))

    return pcap_file


async def parse_pcap_task(pcap_id: int, file_path: str) -> None:
    """后台解析 PCAP 文件"""
    from app.core.database import get_db_context

    async with get_db_context() as db:
        # 更新状态为解析中
        pcap_file = await db.get(PcapFile, pcap_id)
        if not pcap_file:
            return

        pcap_file.status = ParseStatus.PARSING.value
        await db.commit()

        try:
            # 解析文件
            result = await parse_pcap_async(
                file_path,
                progress_callback=lambda p: update_progress(pcap_id, p),
                store_packets=True,
            )

            # 更新 PCAP 文件信息
            pcap_file.status = ParseStatus.COMPLETED.value
            pcap_file.parse_progress = 100.0
            pcap_file.total_packets = result.total_packets
            pcap_file.total_bytes = result.total_bytes
            pcap_file.start_time = result.start_time
            pcap_file.end_time = result.end_time
            pcap_file.duration_seconds = result.duration_seconds

            # 批量插入数据包
            for pkt_info in result.packets:
                packet = Packet(
                    pcap_file_id=pcap_id,
                    packet_number=pkt_info.packet_number,
                    timestamp=pkt_info.timestamp,
                    timestamp_micro=pkt_info.timestamp_micro,
                    src_mac=pkt_info.src_mac,
                    dst_mac=pkt_info.dst_mac,
                    eth_type=pkt_info.eth_type,
                    src_ip=pkt_info.src_ip,
                    dst_ip=pkt_info.dst_ip,
                    ip_version=pkt_info.ip_version,
                    ttl=pkt_info.ttl,
                    protocol=pkt_info.protocol,
                    src_port=pkt_info.src_port,
                    dst_port=pkt_info.dst_port,
                    tcp_flags=pkt_info.tcp_flags,
                    tcp_seq=pkt_info.tcp_seq,
                    tcp_ack=pkt_info.tcp_ack,
                    app_protocol=pkt_info.app_protocol,
                    length=pkt_info.length,
                    payload_length=pkt_info.payload_length,
                )
                db.add(packet)

            # 批量插入连接
            for conn_info in result.connections.values():
                if conn_info.src_ip:
                    conn = Connection(
                        pcap_file_id=pcap_id,
                        src_ip=conn_info.src_ip,
                        dst_ip=conn_info.dst_ip,
                        src_port=conn_info.src_port,
                        dst_port=conn_info.dst_port,
                        protocol=conn_info.protocol,
                        packet_count=conn_info.packet_count,
                        byte_count=conn_info.byte_count,
                        src_to_dst_packets=conn_info.src_to_dst_packets,
                        dst_to_src_packets=conn_info.dst_to_src_packets,
                        src_to_dst_bytes=conn_info.src_to_dst_bytes,
                        dst_to_src_bytes=conn_info.dst_to_src_bytes,
                        start_time=conn_info.start_time,
                        end_time=conn_info.end_time,
                        duration_seconds=(conn_info.end_time - conn_info.start_time).total_seconds()
                        if conn_info.start_time and conn_info.end_time
                        else 0,
                        app_protocol=conn_info.app_protocol,
                        is_encrypted=conn_info.is_encrypted,
                    )
                    db.add(conn)

            await db.commit()

        except Exception as e:
            pcap_file.status = ParseStatus.FAILED.value
            pcap_file.error_message = str(e)
            await db.commit()
            raise


@router.get("/list", response_model=PcapListResponse)
async def list_pcap_files(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取 PCAP 文件列表"""
    # 获取总数
    count_result = await db.execute(select(func.count(PcapFile.id)))
    total = count_result.scalar() or 0

    # 获取列表
    result = await db.execute(
        select(PcapFile).order_by(PcapFile.created_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return PcapListResponse(items=list(items), total=total)


@router.get("/{pcap_id}", response_model=PcapFileResponse)
async def get_pcap_file(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取 PCAP 文件详情"""
    pcap_file = await db.get(PcapFile, pcap_id)
    if not pcap_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    return pcap_file


@router.get("/{pcap_id}/progress")
async def get_parse_progress(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取解析进度"""
    pcap_file = await db.get(PcapFile, pcap_id)
    if not pcap_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    progress = parse_progress.get(pcap_id, pcap_file.parse_progress)

    return {
        "status": pcap_file.status,
        "progress": progress,
        "error_message": pcap_file.error_message,
    }


@router.get("/{pcap_id}/packets")
async def get_packets(
    pcap_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    protocol: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """获取数据包列表"""
    query = select(Packet).where(Packet.pcap_file_id == pcap_id)

    if protocol:
        query = query.where(Packet.protocol == protocol)
    if src_ip:
        query = query.where(Packet.src_ip == src_ip)
    if dst_ip:
        query = query.where(Packet.dst_ip == dst_ip)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # 获取数据
    query = query.order_by(Packet.packet_number).offset(skip).limit(limit)
    result = await db.execute(query)
    packets = result.scalars().all()

    return {"items": packets, "total": total}


@router.get("/{pcap_id}/connections")
async def get_connections(
    pcap_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取连接列表"""
    query = (
        select(Connection)
        .where(Connection.pcap_file_id == pcap_id)
        .order_by(Connection.byte_count.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    connections = result.scalars().all()

    # 获取总数
    count_result = await db.execute(
        select(func.count(Connection.id)).where(Connection.pcap_file_id == pcap_id)
    )
    total = count_result.scalar() or 0

    return {"items": connections, "total": total}


@router.get("/{pcap_id}/stats/protocols")
async def get_protocol_stats(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取协议统计"""
    result = await db.execute(
        select(Packet.protocol, func.count(Packet.id), func.sum(Packet.length))
        .where(Packet.pcap_file_id == pcap_id)
        .where(Packet.protocol.isnot(None))
        .group_by(Packet.protocol)
    )
    stats = result.all()

    total_count = sum(s[1] for s in stats)

    return [
        {
            "protocol": s[0],
            "count": s[1],
            "bytes": s[2] or 0,
            "percentage": round((s[1] / total_count * 100) if total_count > 0 else 0, 2),
        }
        for s in stats
    ]


@router.get("/{pcap_id}/stats/timeline")
async def get_timeline_stats(
    pcap_id: int,
    interval: int = Query(60, description="时间间隔(秒)"),
    db: AsyncSession = Depends(get_db),
):
    """获取时间线统计"""
    # 获取 PCAP 文件信息
    pcap_file = await db.get(PcapFile, pcap_id)
    if not pcap_file or not pcap_file.start_time:
        raise HTTPException(status_code=404, detail="文件不存在或未解析完成")

    # 简化实现：获取所有包的时间戳并在 Python 中聚合
    result = await db.execute(
        select(Packet.timestamp, Packet.length)
        .where(Packet.pcap_file_id == pcap_id)
        .order_by(Packet.timestamp)
    )
    packets = result.all()

    if not packets:
        return []

    # 按时间间隔聚合
    from collections import defaultdict

    timeline: dict[int, dict] = defaultdict(lambda: {"packets": 0, "bytes": 0})
    base_time = packets[0][0].timestamp()

    for timestamp, length in packets:
        bucket = int((timestamp.timestamp() - base_time) // interval)
        timeline[bucket]["packets"] += 1
        timeline[bucket]["bytes"] += length

    return [
        {
            "time_offset": bucket * interval,
            "timestamp": datetime.fromtimestamp(base_time + bucket * interval).isoformat(),
            "packets": data["packets"],
            "bytes": data["bytes"],
        }
        for bucket, data in sorted(timeline.items())
    ]


@router.get("/{pcap_id}/topology")
async def get_network_topology(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取网络拓扑数据（用于力导向图）"""
    result = await db.execute(
        select(Connection).where(Connection.pcap_file_id == pcap_id)
    )
    connections = result.scalars().all()

    # 构建节点和边
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for conn in connections:
        # 添加源节点
        if conn.src_ip not in nodes:
            nodes[conn.src_ip] = {
                "id": conn.src_ip,
                "packets_out": 0,
                "packets_in": 0,
                "bytes_out": 0,
                "bytes_in": 0,
                "country": conn.src_country,
                "lat": conn.src_lat,
                "lon": conn.src_lon,
            }
        nodes[conn.src_ip]["packets_out"] += conn.src_to_dst_packets
        nodes[conn.src_ip]["bytes_out"] += conn.src_to_dst_bytes

        # 添加目标节点
        if conn.dst_ip not in nodes:
            nodes[conn.dst_ip] = {
                "id": conn.dst_ip,
                "packets_out": 0,
                "packets_in": 0,
                "bytes_out": 0,
                "bytes_in": 0,
                "country": conn.dst_country,
                "lat": conn.dst_lat,
                "lon": conn.dst_lon,
            }
        nodes[conn.dst_ip]["packets_in"] += conn.dst_to_src_packets
        nodes[conn.dst_ip]["bytes_in"] += conn.dst_to_src_bytes

        # 添加边
        edges.append(
            {
                "source": conn.src_ip,
                "target": conn.dst_ip,
                "protocol": conn.protocol,
                "app_protocol": conn.app_protocol,
                "packets": conn.packet_count,
                "bytes": conn.byte_count,
                "is_encrypted": conn.is_encrypted,
                "risk_score": conn.risk_score,
            }
        )

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }


@router.delete("/{pcap_id}")
async def delete_pcap_file(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """删除 PCAP 文件"""
    pcap_file = await db.get(PcapFile, pcap_id)
    if not pcap_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 删除文件
    file_path = Path(pcap_file.file_path)
    if file_path.exists():
        file_path.unlink()

    # 删除数据库记录（级联删除相关数据）
    await db.delete(pcap_file)
    await db.commit()

    return {"message": "删除成功"}
