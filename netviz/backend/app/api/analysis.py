"""
NetViz 分析 API 接口
提供流量分析、异常检测、威胁情报等功能
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.pcap import Packet, Connection, DnsRecord, HttpTransaction
from app.models.analysis import Alert

router = APIRouter()


# ==================== Pydantic 模型 ====================


class ProtocolStats(BaseModel):
    """协议统计"""

    protocol: str
    count: int
    bytes: int
    percentage: float


class TimeSeriesPoint(BaseModel):
    """时间序列数据点"""

    timestamp: str
    packets: int
    bytes: int


class TopTalker(BaseModel):
    """Top通信者"""

    ip: str
    packets: int
    bytes: int
    connections: int


class AnomalyResult(BaseModel):
    """异常检测结果"""

    type: str
    severity: str
    description: str
    details: dict
    timestamp: str


class AlertResponse(BaseModel):
    """告警响应"""

    id: int
    pcap_id: int
    type: str
    severity: str
    title: str
    description: str
    source_ip: Optional[str]
    dest_ip: Optional[str]
    mitre_tactic: Optional[str]
    mitre_technique: Optional[str]
    created_at: str


# ==================== 统计分析接口 ====================


@router.get("/protocol-distribution/{pcap_id}", response_model=list[ProtocolStats])
async def get_protocol_distribution(
    pcap_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取协议分布统计"""
    result = await db.execute(
        select(
            Packet.protocol,
            func.count(Packet.id).label("count"),
            func.sum(Packet.length).label("bytes"),
        )
        .where(Packet.pcap_id == pcap_id)
        .group_by(Packet.protocol)
        .order_by(func.count(Packet.id).desc())
    )

    rows = result.all()
    total_packets = sum(row.count for row in rows)

    return [
        ProtocolStats(
            protocol=row.protocol or "Unknown",
            count=row.count,
            bytes=row.bytes or 0,
            percentage=round(row.count / total_packets * 100, 2) if total_packets > 0 else 0,
        )
        for row in rows
    ]


@router.get("/time-series/{pcap_id}", response_model=list[TimeSeriesPoint])
async def get_time_series(
    pcap_id: int,
    interval: int = Query(default=60, description="时间间隔（秒）"),
    db: AsyncSession = Depends(get_db),
):
    """获取时间序列数据"""
    result = await db.execute(
        select(
            func.min(Packet.timestamp).label("min_ts"),
            func.max(Packet.timestamp).label("max_ts"),
        ).where(Packet.pcap_id == pcap_id)
    )
    time_range = result.first()

    if not time_range or not time_range.min_ts:
        return []

    result = await db.execute(
        select(Packet.timestamp, Packet.length).where(Packet.pcap_id == pcap_id)
    )
    packets = result.all()

    time_buckets: dict[int, dict] = {}
    for pkt in packets:
        if pkt.timestamp:
            bucket = int(pkt.timestamp.timestamp() // interval) * interval
            if bucket not in time_buckets:
                time_buckets[bucket] = {"packets": 0, "bytes": 0}
            time_buckets[bucket]["packets"] += 1
            time_buckets[bucket]["bytes"] += pkt.length or 0

    return [
        TimeSeriesPoint(
            timestamp=datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
            packets=data["packets"],
            bytes=data["bytes"],
        )
        for ts, data in sorted(time_buckets.items())
    ]


@router.get("/top-talkers/{pcap_id}", response_model=list[TopTalker])
async def get_top_talkers(
    pcap_id: int,
    limit: int = Query(default=10, le=100),
    direction: str = Query(default="both", description="source, dest, both"),
    db: AsyncSession = Depends(get_db),
):
    """获取Top通信者"""
    talkers: dict[str, dict] = {}

    if direction in ("source", "both"):
        result = await db.execute(
            select(
                Packet.src_ip,
                func.count(Packet.id).label("count"),
                func.sum(Packet.length).label("bytes"),
            )
            .where(and_(Packet.pcap_id == pcap_id, Packet.src_ip.isnot(None)))
            .group_by(Packet.src_ip)
        )
        for row in result.all():
            if row.src_ip:
                if row.src_ip not in talkers:
                    talkers[row.src_ip] = {"packets": 0, "bytes": 0, "connections": 0}
                talkers[row.src_ip]["packets"] += row.count
                talkers[row.src_ip]["bytes"] += row.bytes or 0

    if direction in ("dest", "both"):
        result = await db.execute(
            select(
                Packet.dst_ip,
                func.count(Packet.id).label("count"),
                func.sum(Packet.length).label("bytes"),
            )
            .where(and_(Packet.pcap_id == pcap_id, Packet.dst_ip.isnot(None)))
            .group_by(Packet.dst_ip)
        )
        for row in result.all():
            if row.dst_ip:
                if row.dst_ip not in talkers:
                    talkers[row.dst_ip] = {"packets": 0, "bytes": 0, "connections": 0}
                talkers[row.dst_ip]["packets"] += row.count
                talkers[row.dst_ip]["bytes"] += row.bytes or 0

    result = await db.execute(
        select(Connection.src_ip, func.count(Connection.id).label("conn_count"))
        .where(Connection.pcap_id == pcap_id)
        .group_by(Connection.src_ip)
    )
    for row in result.all():
        if row.src_ip in talkers:
            talkers[row.src_ip]["connections"] = row.conn_count

    sorted_talkers = sorted(talkers.items(), key=lambda x: x[1]["bytes"], reverse=True)[:limit]

    return [
        TopTalker(
            ip=ip,
            packets=data["packets"],
            bytes=data["bytes"],
            connections=data["connections"],
        )
        for ip, data in sorted_talkers
    ]


@router.get("/dns-analysis/{pcap_id}")
async def get_dns_analysis(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取DNS分析"""
    result = await db.execute(
        select(DnsRecord.query_type, func.count(DnsRecord.id).label("count"))
        .where(DnsRecord.pcap_id == pcap_id)
        .group_by(DnsRecord.query_type)
    )
    query_types = {row.query_type: row.count for row in result.all()}

    result = await db.execute(
        select(DnsRecord.query_name, func.count(DnsRecord.id).label("count"))
        .where(DnsRecord.pcap_id == pcap_id)
        .group_by(DnsRecord.query_name)
        .order_by(func.count(DnsRecord.id).desc())
        .limit(20)
    )
    top_domains = [{"domain": row.query_name, "count": row.count} for row in result.all()]

    result = await db.execute(
        select(DnsRecord.response_code, func.count(DnsRecord.id).label("count"))
        .where(and_(DnsRecord.pcap_id == pcap_id, DnsRecord.response_code.isnot(None)))
        .group_by(DnsRecord.response_code)
    )
    response_codes = {row.response_code: row.count for row in result.all()}

    return {"query_types": query_types, "top_domains": top_domains, "response_codes": response_codes}


@router.get("/http-analysis/{pcap_id}")
async def get_http_analysis(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取HTTP分析"""
    result = await db.execute(
        select(HttpTransaction.method, func.count(HttpTransaction.id).label("count"))
        .where(HttpTransaction.pcap_id == pcap_id)
        .group_by(HttpTransaction.method)
    )
    methods = {row.method: row.count for row in result.all()}

    result = await db.execute(
        select(HttpTransaction.status_code, func.count(HttpTransaction.id).label("count"))
        .where(and_(HttpTransaction.pcap_id == pcap_id, HttpTransaction.status_code.isnot(None)))
        .group_by(HttpTransaction.status_code)
    )
    status_codes = {str(row.status_code): row.count for row in result.all()}

    result = await db.execute(
        select(HttpTransaction.host, func.count(HttpTransaction.id).label("count"))
        .where(and_(HttpTransaction.pcap_id == pcap_id, HttpTransaction.host.isnot(None)))
        .group_by(HttpTransaction.host)
        .order_by(func.count(HttpTransaction.id).desc())
        .limit(20)
    )
    top_hosts = [{"host": row.host, "count": row.count} for row in result.all()]

    result = await db.execute(
        select(HttpTransaction.user_agent, func.count(HttpTransaction.id).label("count"))
        .where(and_(HttpTransaction.pcap_id == pcap_id, HttpTransaction.user_agent.isnot(None)))
        .group_by(HttpTransaction.user_agent)
        .order_by(func.count(HttpTransaction.id).desc())
        .limit(10)
    )
    top_user_agents = [{"user_agent": row.user_agent, "count": row.count} for row in result.all()]

    return {"methods": methods, "status_codes": status_codes, "top_hosts": top_hosts, "top_user_agents": top_user_agents}


# ==================== 异常检测接口 ====================


@router.post("/detect-anomalies/{pcap_id}", response_model=list[AnomalyResult])
async def detect_anomalies(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """运行异常检测"""
    anomalies: list[AnomalyResult] = []

    # 端口扫描检测
    result = await db.execute(
        select(Connection.src_ip, func.count(func.distinct(Connection.dst_port)).label("port_count"))
        .where(Connection.pcap_id == pcap_id)
        .group_by(Connection.src_ip)
        .having(func.count(func.distinct(Connection.dst_port)) > 50)
    )
    for row in result.all():
        anomalies.append(
            AnomalyResult(
                type="port_scan",
                severity="high",
                description="检测到可能的端口扫描行为",
                details={"source_ip": row.src_ip, "unique_ports": row.port_count},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    # DNS隧道检测
    result = await db.execute(
        select(DnsRecord.query_name, func.count(DnsRecord.id).label("count"))
        .where(DnsRecord.pcap_id == pcap_id)
        .group_by(DnsRecord.query_name)
        .having(func.length(DnsRecord.query_name) > 50)
    )
    for row in result.all():
        anomalies.append(
            AnomalyResult(
                type="dns_tunnel",
                severity="medium",
                description="检测到可疑的长DNS域名，可能是DNS隧道",
                details={"domain": row.query_name, "length": len(row.query_name)},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    # 大流量连接检测
    result = await db.execute(
        select(Connection)
        .where(and_(Connection.pcap_id == pcap_id, Connection.bytes_sent > 100 * 1024 * 1024))
        .limit(10)
    )
    for conn in result.scalars().all():
        anomalies.append(
            AnomalyResult(
                type="large_transfer",
                severity="low",
                description="检测到大数据量传输",
                details={
                    "source": f"{conn.src_ip}:{conn.src_port}",
                    "dest": f"{conn.dst_ip}:{conn.dst_port}",
                    "bytes": conn.bytes_sent,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    return anomalies


# ==================== 告警接口 ====================


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    pcap_id: Optional[int] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """获取告警列表"""
    query = select(Alert).order_by(Alert.detected_at.desc())

    if pcap_id:
        query = query.where(Alert.pcap_id == pcap_id)
    if severity:
        query = query.where(Alert.severity == severity)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)

    return [
        AlertResponse(
            id=alert.id,
            pcap_id=alert.pcap_id,
            type=alert.type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description or "",
            source_ip=alert.source_ip,
            dest_ip=alert.dest_ip,
            mitre_tactic=alert.mitre_tactic,
            mitre_technique=alert.mitre_technique,
            created_at=alert.detected_at.isoformat() if alert.detected_at else "",
        )
        for alert in result.scalars().all()
    ]


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """删除告警"""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    await db.delete(alert)
    await db.commit()

    return {"message": "告警已删除"}
