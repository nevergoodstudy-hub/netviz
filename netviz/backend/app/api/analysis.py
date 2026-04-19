"""
NetViz 分析 API 接口
提供流量分析、异常检测与告警查询
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis import Alert, AlertType
from app.models.pcap import Connection, DnsRecord, HttpTransaction, Packet, PcapFile

router = APIRouter()


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
    """Top 通信者"""

    ip: str
    packets_sent: int
    packets_received: int
    bytes_sent: int
    bytes_received: int
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
    detected_at: str


def _alert_to_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        pcap_id=alert.pcap_file_id,
        type=alert.alert_type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        source_ip=alert.src_ip,
        dest_ip=alert.dst_ip,
        mitre_tactic=alert.mitre_tactic,
        mitre_technique=alert.mitre_technique,
        detected_at=alert.detected_at.isoformat(),
    )


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
        .where(Packet.pcap_file_id == pcap_id)
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
            percentage=round((row.count / total_packets) * 100, 2) if total_packets else 0.0,
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
        select(Packet.timestamp, Packet.length)
        .where(Packet.pcap_file_id == pcap_id)
        .order_by(Packet.timestamp)
    )
    packets = result.all()

    if not packets:
        return []

    time_buckets: dict[int, dict[str, int]] = {}
    for pkt in packets:
        if not pkt.timestamp:
            continue

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
    """获取 Top 通信者"""
    result = await db.execute(
        select(Connection).where(Connection.pcap_file_id == pcap_id)
    )
    connections = result.scalars().all()

    talkers: dict[str, dict[str, int]] = {}

    def ensure_talker(ip: str) -> dict[str, int]:
        if ip not in talkers:
            talkers[ip] = {
                "packets_sent": 0,
                "packets_received": 0,
                "bytes_sent": 0,
                "bytes_received": 0,
                "connections": 0,
            }
        return talkers[ip]

    for conn in connections:
        if direction in ("source", "both"):
            source = ensure_talker(conn.src_ip)
            source["packets_sent"] += conn.src_to_dst_packets
            source["bytes_sent"] += conn.src_to_dst_bytes
            source["connections"] += 1

        if direction in ("dest", "both"):
            dest = ensure_talker(conn.dst_ip)
            dest["packets_received"] += conn.src_to_dst_packets
            dest["bytes_received"] += conn.src_to_dst_bytes
            dest["connections"] += 1

        if direction == "both":
            source = ensure_talker(conn.src_ip)
            source["packets_received"] += conn.dst_to_src_packets
            source["bytes_received"] += conn.dst_to_src_bytes

            dest = ensure_talker(conn.dst_ip)
            dest["packets_sent"] += conn.dst_to_src_packets
            dest["bytes_sent"] += conn.dst_to_src_bytes

    sorted_talkers = sorted(
        talkers.items(),
        key=lambda item: item[1]["bytes_sent"] + item[1]["bytes_received"],
        reverse=True,
    )[:limit]

    return [
        TopTalker(ip=ip, **metrics)
        for ip, metrics in sorted_talkers
    ]


@router.get("/dns-analysis/{pcap_id}")
async def get_dns_analysis(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取 DNS 分析"""
    result = await db.execute(
        select(DnsRecord.query_type, func.count(DnsRecord.id).label("count"))
        .where(DnsRecord.pcap_file_id == pcap_id)
        .group_by(DnsRecord.query_type)
    )
    query_types = {row.query_type: row.count for row in result.all()}

    result = await db.execute(
        select(DnsRecord.domain, func.count(DnsRecord.id).label("count"))
        .where(and_(DnsRecord.pcap_file_id == pcap_id, DnsRecord.domain != ""))
        .group_by(DnsRecord.domain)
        .order_by(func.count(DnsRecord.id).desc())
        .limit(20)
    )
    top_domains = [{"domain": row.domain, "count": row.count} for row in result.all()]

    result = await db.execute(
        select(DnsRecord.response_code, func.count(DnsRecord.id).label("count"))
        .where(
            and_(
                DnsRecord.pcap_file_id == pcap_id,
                DnsRecord.response_code.is_not(None),
            )
        )
        .group_by(DnsRecord.response_code)
    )
    response_codes = {str(row.response_code): row.count for row in result.all()}

    return {
        "query_types": query_types,
        "top_domains": top_domains,
        "response_codes": response_codes,
    }


@router.get("/http-analysis/{pcap_id}")
async def get_http_analysis(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """获取 HTTP 分析"""
    result = await db.execute(
        select(HttpTransaction.method, func.count(HttpTransaction.id).label("count"))
        .where(
            and_(
                HttpTransaction.pcap_file_id == pcap_id,
                HttpTransaction.method != "",
                HttpTransaction.method != "RESPONSE",
            )
        )
        .group_by(HttpTransaction.method)
    )
    methods = {row.method: row.count for row in result.all()}

    result = await db.execute(
        select(HttpTransaction.status_code, func.count(HttpTransaction.id).label("count"))
        .where(
            and_(
                HttpTransaction.pcap_file_id == pcap_id,
                HttpTransaction.status_code.is_not(None),
            )
        )
        .group_by(HttpTransaction.status_code)
    )
    status_codes = {str(row.status_code): row.count for row in result.all()}

    result = await db.execute(
        select(HttpTransaction.host, func.count(HttpTransaction.id).label("count"))
        .where(
            and_(
                HttpTransaction.pcap_file_id == pcap_id,
                HttpTransaction.host.is_not(None),
                HttpTransaction.host != "",
            )
        )
        .group_by(HttpTransaction.host)
        .order_by(func.count(HttpTransaction.id).desc())
        .limit(20)
    )
    top_hosts = [{"host": row.host, "count": row.count} for row in result.all()]

    result = await db.execute(
        select(HttpTransaction.user_agent, func.count(HttpTransaction.id).label("count"))
        .where(
            and_(
                HttpTransaction.pcap_file_id == pcap_id,
                HttpTransaction.user_agent.is_not(None),
                HttpTransaction.user_agent != "",
            )
        )
        .group_by(HttpTransaction.user_agent)
        .order_by(func.count(HttpTransaction.id).desc())
        .limit(10)
    )
    top_user_agents = [{"user_agent": row.user_agent, "count": row.count} for row in result.all()]

    return {
        "methods": methods,
        "status_codes": status_codes,
        "top_hosts": top_hosts,
        "top_user_agents": top_user_agents,
    }


@router.post("/detect-anomalies/{pcap_id}", response_model=list[AnomalyResult])
async def detect_anomalies(pcap_id: int, db: AsyncSession = Depends(get_db)):
    """运行异常检测并持久化告警"""
    pcap_file = await db.get(PcapFile, pcap_id)
    if not pcap_file:
        raise HTTPException(status_code=404, detail="PCAP 文件不存在")

    anomalies: list[AnomalyResult] = []
    generated_alerts: list[Alert] = []
    now = datetime.utcnow()
    now_iso = now.replace(tzinfo=timezone.utc).isoformat()

    await db.execute(
        delete(Alert).where(
            and_(
                Alert.pcap_file_id == pcap_id,
                Alert.alert_type.in_(
                    [
                        AlertType.PORT_SCAN.value,
                        AlertType.DNS_ANOMALY.value,
                        AlertType.DATA_EXFIL.value,
                    ]
                ),
            )
        )
    )

    result = await db.execute(
        select(
            Connection.src_ip,
            func.count(func.distinct(Connection.dst_port)).label("port_count"),
        )
        .where(Connection.pcap_file_id == pcap_id)
        .group_by(Connection.src_ip)
        .having(func.count(func.distinct(Connection.dst_port)) > 50)
    )
    for row in result.all():
        details = {"source_ip": row.src_ip, "unique_ports": row.port_count}
        anomalies.append(
            AnomalyResult(
                type=AlertType.PORT_SCAN.value,
                severity="high",
                description="检测到可能的端口扫描行为",
                details=details,
                timestamp=now_iso,
            )
        )
        generated_alerts.append(
            Alert(
                pcap_file_id=pcap_id,
                alert_type=AlertType.PORT_SCAN.value,
                severity="high",
                title="疑似端口扫描",
                description="同一源地址短时间内访问了大量不同目标端口。",
                src_ip=row.src_ip,
                evidence=str(details),
                detected_at=now,
                recommendation="检查该主机是否在进行横向探测或资产扫描。",
                confidence=0.85,
            )
        )

    result = await db.execute(
        select(DnsRecord.domain, func.count(DnsRecord.id).label("count"))
        .where(and_(DnsRecord.pcap_file_id == pcap_id, func.length(DnsRecord.domain) > 50))
        .group_by(DnsRecord.domain)
    )
    for row in result.all():
        details = {"domain": row.domain, "count": row.count}
        anomalies.append(
            AnomalyResult(
                type=AlertType.DNS_ANOMALY.value,
                severity="medium",
                description="检测到可疑的长 DNS 域名，可能存在 DNS 隧道行为",
                details=details,
                timestamp=now_iso,
            )
        )
        generated_alerts.append(
            Alert(
                pcap_file_id=pcap_id,
                alert_type=AlertType.DNS_ANOMALY.value,
                severity="medium",
                title="疑似 DNS 隧道",
                description="发现异常偏长的 DNS 查询域名。",
                evidence=str(details),
                detected_at=now,
                recommendation="核查相关域名和主机是否存在数据外传行为。",
                confidence=0.65,
            )
        )

    result = await db.execute(
        select(Connection)
        .where(
            and_(
                Connection.pcap_file_id == pcap_id,
                Connection.byte_count > 100 * 1024 * 1024,
            )
        )
        .limit(10)
    )
    for conn in result.scalars().all():
        details = {
            "source": f"{conn.src_ip}:{conn.src_port}",
            "dest": f"{conn.dst_ip}:{conn.dst_port}",
            "bytes": conn.byte_count,
        }
        anomalies.append(
            AnomalyResult(
                type=AlertType.DATA_EXFIL.value,
                severity="low",
                description="检测到大数据量传输",
                details=details,
                timestamp=now_iso,
            )
        )
        generated_alerts.append(
            Alert(
                pcap_file_id=pcap_id,
                alert_type=AlertType.DATA_EXFIL.value,
                severity="low",
                title="大流量传输",
                description="检测到高字节数连接，建议确认是否为预期业务流量。",
                src_ip=conn.src_ip,
                dst_ip=conn.dst_ip,
                src_port=conn.src_port,
                dst_port=conn.dst_port,
                evidence=str(details),
                detected_at=now,
                recommendation="结合业务上下文确认是否存在大文件外传。",
                confidence=0.5,
            )
        )

    if generated_alerts:
        db.add_all(generated_alerts)

    await db.commit()
    return anomalies


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
        query = query.where(Alert.pcap_file_id == pcap_id)
    if severity:
        query = query.where(Alert.severity == severity)

    result = await db.execute(query.offset(offset).limit(limit))
    return [_alert_to_response(alert) for alert in result.scalars().all()]


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
