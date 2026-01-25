"""
NetViz 分析相关数据模型
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.pcap import PcapFile


class AlertSeverity(str, Enum):
    """告警严重级别"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """告警类型"""

    PORT_SCAN = "port_scan"
    DNS_ANOMALY = "dns_anomaly"
    SUSPICIOUS_UA = "suspicious_user_agent"
    MALICIOUS_IP = "malicious_ip"
    MALICIOUS_DOMAIN = "malicious_domain"
    DATA_EXFIL = "data_exfiltration"
    C2_COMMUNICATION = "c2_communication"
    BRUTE_FORCE = "brute_force"
    LATERAL_MOVEMENT = "lateral_movement"
    PROTOCOL_ANOMALY = "protocol_anomaly"
    TRAFFIC_SPIKE = "traffic_spike"
    ENCRYPTED_TRAFFIC = "encrypted_traffic"
    CUSTOM = "custom"


class Alert(Base):
    """告警模型"""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_pcap_severity", "pcap_file_id", "severity"),
        Index("ix_alerts_type", "alert_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcap_file_id: Mapped[int] = mapped_column(ForeignKey("pcap_files.id"), nullable=False)

    # 告警信息
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # 关联信息
    src_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    src_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dst_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connection_id: Mapped[int | None] = mapped_column(ForeignKey("connections.id"), nullable=True)

    # MITRE ATT&CK 映射
    mitre_tactic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mitre_technique: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mitre_technique_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 证据和上下文
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    context: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 置信度
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # 状态
    is_acknowledged: Mapped[bool] = mapped_column(default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 时间戳
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    pcap_file: Mapped["PcapFile"] = relationship("PcapFile", back_populates="alerts")


class AIConversation(Base):
    """AI 对话记录模型"""

    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pcap_file_id: Mapped[int | None] = mapped_column(ForeignKey("pcap_files.id"), nullable=True)

    # 对话信息
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # openai, anthropic, ollama
    model: Mapped[str] = mapped_column(String(50), nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 关系
    messages: Mapped[list["AIMessage"]] = relationship(
        "AIMessage", back_populates="conversation", cascade="all, delete-orphan"
    )


class AIMessage(Base):
    """AI 消息模型"""

    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id"), nullable=False
    )

    # 消息信息
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Token 使用
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    conversation: Mapped["AIConversation"] = relationship(
        "AIConversation", back_populates="messages"
    )


class Settings(Base):
    """用户设置模型"""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # 加密存储敏感信息
    is_encrypted: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
