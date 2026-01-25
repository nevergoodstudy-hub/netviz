"""
NetViz PCAP 相关数据模型
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.analysis import Alert


class ParseStatus(str, Enum):
    """解析状态枚举"""

    PENDING = "pending"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"


class PcapFile(Base):
    """PCAP 文件模型"""

    __tablename__ = "pcap_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256

    # 解析状态
    status: Mapped[str] = mapped_column(String(20), default=ParseStatus.PENDING.value)
    parse_progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 统计信息
    total_packets: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    packets: Mapped[list["Packet"]] = relationship(
        "Packet", back_populates="pcap_file", cascade="all, delete-orphan"
    )
    connections: Mapped[list["Connection"]] = relationship(
        "Connection", back_populates="pcap_file", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="pcap_file", cascade="all, delete-orphan"
    )


class Packet(Base):
    """数据包模型"""

    __tablename__ = "packets"
    __table_args__ = (
        Index("ix_packets_pcap_timestamp", "pcap_file_id", "timestamp"),
        Index("ix_packets_src_ip", "src_ip"),
        Index("ix_packets_dst_ip", "dst_ip"),
        Index("ix_packets_protocol", "protocol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcap_file_id: Mapped[int] = mapped_column(ForeignKey("pcap_files.id"), nullable=False)
    packet_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # 时间信息
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    timestamp_micro: Mapped[int] = mapped_column(Integer, default=0)  # 微秒部分

    # 链路层
    src_mac: Mapped[str | None] = mapped_column(String(17), nullable=True)
    dst_mac: Mapped[str | None] = mapped_column(String(17), nullable=True)
    eth_type: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 网络层
    src_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # 支持 IPv6
    dst_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    ip_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttl: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 传输层
    protocol: Mapped[str | None] = mapped_column(String(10), nullable=True)  # TCP, UDP, ICMP
    src_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dst_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tcp_flags: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tcp_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tcp_ack: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 应用层
    app_protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)  # HTTP, DNS, etc.
    app_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 格式的应用层数据

    # 包信息
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_length: Mapped[int] = mapped_column(Integer, default=0)

    # 关系
    pcap_file: Mapped["PcapFile"] = relationship("PcapFile", back_populates="packets")


class Connection(Base):
    """连接/会话模型"""

    __tablename__ = "connections"
    __table_args__ = (
        Index("ix_connections_pcap_ips", "pcap_file_id", "src_ip", "dst_ip"),
        Index("ix_connections_protocol", "protocol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcap_file_id: Mapped[int] = mapped_column(ForeignKey("pcap_files.id"), nullable=False)

    # 连接标识
    src_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    dst_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    src_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dst_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str] = mapped_column(String(10), nullable=False)

    # 统计信息
    packet_count: Mapped[int] = mapped_column(Integer, default=0)
    byte_count: Mapped[int] = mapped_column(Integer, default=0)
    src_to_dst_packets: Mapped[int] = mapped_column(Integer, default=0)
    dst_to_src_packets: Mapped[int] = mapped_column(Integer, default=0)
    src_to_dst_bytes: Mapped[int] = mapped_column(Integer, default=0)
    dst_to_src_bytes: Mapped[int] = mapped_column(Integer, default=0)

    # 时间信息
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    # 地理信息
    src_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    src_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    src_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    dst_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    dst_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    dst_lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 应用层信息
    app_protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)

    # 风险标记
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组

    # 关系
    pcap_file: Mapped["PcapFile"] = relationship("PcapFile", back_populates="connections")


class DnsRecord(Base):
    """DNS 记录模型"""

    __tablename__ = "dns_records"
    __table_args__ = (Index("ix_dns_records_domain", "domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcap_file_id: Mapped[int] = mapped_column(ForeignKey("pcap_files.id"), nullable=False)
    packet_id: Mapped[int] = mapped_column(ForeignKey("packets.id"), nullable=False)

    # DNS 信息
    query_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_response: Mapped[bool] = mapped_column(Boolean, default=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    query_type: Mapped[str] = mapped_column(String(10), nullable=False)  # A, AAAA, MX, etc.
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class HttpTransaction(Base):
    """HTTP 事务模型"""

    __tablename__ = "http_transactions"
    __table_args__ = (Index("ix_http_transactions_host", "host"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcap_file_id: Mapped[int] = mapped_column(ForeignKey("pcap_files.id"), nullable=False)
    connection_id: Mapped[int | None] = mapped_column(ForeignKey("connections.id"), nullable=True)

    # 请求信息
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_headers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # 响应信息
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    response_headers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # 时间和大小
    request_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    response_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    request_size: Mapped[int] = mapped_column(Integer, default=0)
    response_size: Mapped[int] = mapped_column(Integer, default=0)
