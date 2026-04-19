"""
NetViz PCAP 解析器
使用 Scapy 实现纯 Python PCAP 解析，无需安装 Wireshark
"""

import hashlib
import json
import logging
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from scapy.all import DNS, IP, TCP, UDP, Ether, Raw
from scapy.layers.http import HTTP, HTTPRequest, HTTPResponse
from scapy.layers.inet6 import IPv6
from scapy.layers.tls.record import TLS
from scapy.utils import PcapReader

logger = logging.getLogger(__name__)


@dataclass
class PacketInfo:
    """解析后的数据包信息"""

    packet_number: int
    timestamp: datetime
    timestamp_micro: int = 0

    # 链路层
    src_mac: str | None = None
    dst_mac: str | None = None
    eth_type: int | None = None

    # 网络层
    src_ip: str | None = None
    dst_ip: str | None = None
    ip_version: int | None = None
    ttl: int | None = None

    # 传输层
    protocol: str | None = None
    src_port: int | None = None
    dst_port: int | None = None
    tcp_flags: str | None = None
    tcp_seq: int | None = None
    tcp_ack: int | None = None

    # 应用层
    app_protocol: str | None = None
    app_data: dict[str, Any] | None = None

    # 包信息
    length: int = 0
    payload_length: int = 0


@dataclass
class ConnectionKey:
    """连接标识"""

    src_ip: str
    dst_ip: str
    src_port: int | None
    dst_port: int | None
    protocol: str

    def __hash__(self) -> int:
        # 使用有序的元组确保双向连接被识别为同一连接
        ips = tuple(sorted([self.src_ip, self.dst_ip]))
        ports = tuple(sorted([self.src_port or 0, self.dst_port or 0]))
        return hash((ips, ports, self.protocol))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConnectionKey):
            return False
        ips1 = tuple(sorted([self.src_ip, self.dst_ip]))
        ips2 = tuple(sorted([other.src_ip, other.dst_ip]))
        ports1 = tuple(sorted([self.src_port or 0, self.dst_port or 0]))
        ports2 = tuple(sorted([other.src_port or 0, other.dst_port or 0]))
        return ips1 == ips2 and ports1 == ports2 and self.protocol == other.protocol


@dataclass
class ConnectionInfo:
    """连接统计信息"""

    src_ip: str
    dst_ip: str
    src_port: int | None
    dst_port: int | None
    protocol: str
    packet_count: int = 0
    byte_count: int = 0
    src_to_dst_packets: int = 0
    dst_to_src_packets: int = 0
    src_to_dst_bytes: int = 0
    dst_to_src_bytes: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None
    app_protocol: str | None = None
    is_encrypted: bool = False


@dataclass
class ParseResult:
    """解析结果"""

    file_hash: str
    total_packets: int
    total_bytes: int
    start_time: datetime | None
    end_time: datetime | None
    duration_seconds: float
    packets: list[PacketInfo] = field(default_factory=list)
    connections: dict[ConnectionKey, ConnectionInfo] = field(default_factory=dict)
    dns_records: list[dict] = field(default_factory=list)
    http_transactions: list[dict] = field(default_factory=list)
    protocol_stats: dict[str, int] = field(default_factory=dict)


@dataclass
class ParseEvent:
    """Single parsed packet event emitted during streaming parsing."""

    packet: PacketInfo
    dns_record: dict | None = None
    http_transaction: dict | None = None


class PcapParser:
    """PCAP 文件解析器"""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self._progress_callback: Callable[[float], None] | None = None
        self._file_hash = ""
        self._connections: dict[ConnectionKey, ConnectionInfo] = {}
        self._protocol_stats: dict[str, int] = {}
        self._total_packets = 0
        self._total_bytes = 0
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None

    def set_progress_callback(self, callback: Callable[[float], None]) -> None:
        """设置进度回调函数"""
        self._progress_callback = callback

    def _report_progress(self, progress: float) -> None:
        """报告解析进度"""
        if self._progress_callback:
            self._progress_callback(min(progress, 100.0))

    def calculate_file_hash(self) -> str:
        """计算文件 SHA-256 哈希"""
        sha256_hash = hashlib.sha256()
        with open(self.file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_packet_count(self) -> int:
        """快速获取包数量（用于进度计算）"""
        count = 0
        try:
            with PcapReader(str(self.file_path)) as reader:
                for _ in reader:
                    count += 1
        except Exception as e:
            logger.warning(f"Error counting packets: {e}")
        return count

    def _reset_state(self) -> None:
        self._file_hash = ""
        self._connections = defaultdict(lambda: ConnectionInfo("", "", None, None, ""))
        self._protocol_stats = defaultdict(int)
        self._total_packets = 0
        self._total_bytes = 0
        self._start_time = None
        self._end_time = None

    def _parse_tcp_flags(self, tcp_layer: TCP) -> str:
        """解析 TCP 标志位"""
        flags = []
        if tcp_layer.flags.F:
            flags.append("FIN")
        if tcp_layer.flags.S:
            flags.append("SYN")
        if tcp_layer.flags.R:
            flags.append("RST")
        if tcp_layer.flags.P:
            flags.append("PSH")
        if tcp_layer.flags.A:
            flags.append("ACK")
        if tcp_layer.flags.U:
            flags.append("URG")
        return ",".join(flags) if flags else ""

    def _detect_app_protocol(self, packet: Any, src_port: int | None, dst_port: int | None) -> str | None:
        """检测应用层协议"""
        # 基于端口检测
        common_ports = {
            80: "HTTP",
            443: "HTTPS",
            53: "DNS",
            21: "FTP",
            22: "SSH",
            23: "TELNET",
            25: "SMTP",
            110: "POP3",
            143: "IMAP",
            3389: "RDP",
            445: "SMB",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            27017: "MongoDB",
        }

        for port in [src_port, dst_port]:
            if port in common_ports:
                return common_ports[port]

        # 基于包内容检测
        if packet.haslayer(DNS):
            return "DNS"
        if packet.haslayer(HTTP) or packet.haslayer(HTTPRequest) or packet.haslayer(HTTPResponse):
            return "HTTP"
        if packet.haslayer(TLS):
            return "TLS"

        return None

    def _parse_dns(self, packet: Any, packet_number: int, timestamp: datetime) -> dict | None:
        """解析 DNS 数据"""
        if not packet.haslayer(DNS):
            return None

        dns = packet[DNS]
        is_response = dns.qr == 1

        record = {
            "packet_number": packet_number,
            "timestamp": timestamp,
            "query_id": dns.id,
            "is_response": is_response,
            "domain": "",
            "query_type": "",
            "response_code": dns.rcode if is_response else None,
            "answers": [],
        }

        # 解析查询
        if dns.qd:
            record["domain"] = dns.qd.qname.decode() if isinstance(dns.qd.qname, bytes) else str(dns.qd.qname)
            record["query_type"] = self._dns_type_to_str(dns.qd.qtype)

        # 解析响应
        if is_response and dns.an:
            answers = []
            for i in range(dns.ancount):
                try:
                    rr = dns.an[i]
                    answer = {
                        "type": self._dns_type_to_str(rr.type),
                        "data": str(rr.rdata) if hasattr(rr, "rdata") else "",
                        "ttl": rr.ttl,
                    }
                    answers.append(answer)
                except Exception:
                    pass
            record["answers"] = answers

        return record

    def _dns_type_to_str(self, qtype: int) -> str:
        """DNS 类型转字符串"""
        types = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX", 16: "TXT", 28: "AAAA"}
        return types.get(qtype, str(qtype))

    def _parse_http(self, packet: Any, packet_number: int, timestamp: datetime) -> dict | None:
        """解析 HTTP 数据"""
        http_data = None

        if packet.haslayer(HTTPRequest):
            req = packet[HTTPRequest]
            http_data = {
                "packet_number": packet_number,
                "timestamp": timestamp,
                "type": "request",
                "method": req.Method.decode() if req.Method else "",
                "host": req.Host.decode() if req.Host else "",
                "uri": req.Path.decode() if req.Path else "/",
                "user_agent": req.User_Agent.decode() if hasattr(req, "User_Agent") and req.User_Agent else None,
            }
        elif packet.haslayer(HTTPResponse):
            resp = packet[HTTPResponse]
            http_data = {
                "packet_number": packet_number,
                "timestamp": timestamp,
                "type": "response",
                "status_code": int(resp.Status_Code.decode()) if resp.Status_Code else 0,
                "content_type": resp.Content_Type.decode() if hasattr(resp, "Content_Type") and resp.Content_Type else None,
            }

        return http_data

    def parse(self, store_packets: bool = True, max_packets: int | None = None) -> ParseResult:
        """
        解析 PCAP 文件

        Args:
            store_packets: 是否存储每个包的详细信息（大文件时可设为 False）
            max_packets: 最大解析包数（用于采样分析）
        """
        packets: list[PacketInfo] = []
        dns_records: list[dict] = []
        http_transactions: list[dict] = []
        for event in self.iter_packets(max_packets=max_packets):
            if store_packets:
                packets.append(event.packet)
            if event.dns_record:
                dns_records.append(event.dns_record)
            if event.http_transaction:
                http_transactions.append(event.http_transaction)

        return self.build_result(
            packets=packets,
            dns_records=dns_records,
            http_transactions=http_transactions,
        )

    def iter_packets(self, max_packets: int | None = None):
        """Stream parsed packets one by one to keep memory usage bounded."""
        logger.info(f"Starting to parse: {self.file_path}")
        self._reset_state()
        self._file_hash = self.calculate_file_hash()
        total_packet_count = self.get_packet_count() if self._progress_callback else 0

        try:
            with PcapReader(str(self.file_path)) as reader:
                for i, packet in enumerate(reader, start=1):
                    if max_packets and i > max_packets:
                        break

                    self._total_packets = i

                    if total_packet_count > 0 and i % 1000 == 0:
                        self._report_progress((i / total_packet_count) * 100)

                    timestamp = datetime.fromtimestamp(float(packet.time))
                    timestamp_micro = int((float(packet.time) % 1) * 1_000_000)

                    if self._start_time is None or timestamp < self._start_time:
                        self._start_time = timestamp
                    if self._end_time is None or timestamp > self._end_time:
                        self._end_time = timestamp

                    pkt_info = PacketInfo(
                        packet_number=i,
                        timestamp=timestamp,
                        timestamp_micro=timestamp_micro,
                        length=len(packet),
                    )
                    self._total_bytes += len(packet)

                    if packet.haslayer(Ether):
                        eth = packet[Ether]
                        pkt_info.src_mac = eth.src
                        pkt_info.dst_mac = eth.dst
                        pkt_info.eth_type = eth.type

                    if packet.haslayer(IP):
                        ip = packet[IP]
                        pkt_info.src_ip = ip.src
                        pkt_info.dst_ip = ip.dst
                        pkt_info.ip_version = 4
                        pkt_info.ttl = ip.ttl
                    elif packet.haslayer(IPv6):
                        ip = packet[IPv6]
                        pkt_info.src_ip = ip.src
                        pkt_info.dst_ip = ip.dst
                        pkt_info.ip_version = 6
                        pkt_info.ttl = ip.hlim

                    if packet.haslayer(TCP):
                        tcp = packet[TCP]
                        pkt_info.protocol = "TCP"
                        pkt_info.src_port = tcp.sport
                        pkt_info.dst_port = tcp.dport
                        pkt_info.tcp_flags = self._parse_tcp_flags(tcp)
                        pkt_info.tcp_seq = tcp.seq
                        pkt_info.tcp_ack = tcp.ack
                        self._protocol_stats["TCP"] += 1
                    elif packet.haslayer(UDP):
                        udp = packet[UDP]
                        pkt_info.protocol = "UDP"
                        pkt_info.src_port = udp.sport
                        pkt_info.dst_port = udp.dport
                        self._protocol_stats["UDP"] += 1
                    elif pkt_info.src_ip:
                        pkt_info.protocol = "OTHER"
                        self._protocol_stats["OTHER"] += 1

                    if pkt_info.src_ip:
                        pkt_info.app_protocol = self._detect_app_protocol(
                            packet, pkt_info.src_port, pkt_info.dst_port
                        )
                        if pkt_info.app_protocol:
                            self._protocol_stats[pkt_info.app_protocol] += 1

                    dns_record = self._parse_dns(packet, i, timestamp)
                    http_data = self._parse_http(packet, i, timestamp)

                    if packet.haslayer(Raw):
                        pkt_info.payload_length = len(packet[Raw].load)

                    if pkt_info.src_ip and pkt_info.dst_ip and pkt_info.protocol:
                        conn_key = ConnectionKey(
                            src_ip=pkt_info.src_ip,
                            dst_ip=pkt_info.dst_ip,
                            src_port=pkt_info.src_port,
                            dst_port=pkt_info.dst_port,
                            protocol=pkt_info.protocol,
                        )

                        conn = self._connections[conn_key]
                        if not conn.src_ip:
                            conn.src_ip = pkt_info.src_ip
                            conn.dst_ip = pkt_info.dst_ip
                            conn.src_port = pkt_info.src_port
                            conn.dst_port = pkt_info.dst_port
                            conn.protocol = pkt_info.protocol

                        conn.packet_count += 1
                        conn.byte_count += pkt_info.length

                        if pkt_info.src_ip == conn.src_ip:
                            conn.src_to_dst_packets += 1
                            conn.src_to_dst_bytes += pkt_info.length
                        else:
                            conn.dst_to_src_packets += 1
                            conn.dst_to_src_bytes += pkt_info.length

                        if conn.start_time is None or timestamp < conn.start_time:
                            conn.start_time = timestamp
                        if conn.end_time is None or timestamp > conn.end_time:
                            conn.end_time = timestamp

                        if pkt_info.app_protocol:
                            conn.app_protocol = pkt_info.app_protocol
                        if pkt_info.app_protocol in ["HTTPS", "TLS"]:
                            conn.is_encrypted = True

                    yield ParseEvent(
                        packet=pkt_info,
                        dns_record=dns_record,
                        http_transaction=http_data,
                    )
        except Exception as e:
            logger.error(f"Failed to read PCAP file: {e}")
            raise ValueError(f"无法读取 PCAP 文件: {e}") from e

        self._report_progress(100.0)
        logger.info(f"Parsing completed: {self._total_packets} packets, {self._total_bytes} bytes")

    def build_result(
        self,
        *,
        packets: list[PacketInfo] | None = None,
        dns_records: list[dict] | None = None,
        http_transactions: list[dict] | None = None,
    ) -> ParseResult:
        duration = 0.0
        if self._start_time and self._end_time:
            duration = (self._end_time - self._start_time).total_seconds()

        return ParseResult(
            file_hash=self._file_hash,
            total_packets=self._total_packets,
            total_bytes=self._total_bytes,
            start_time=self._start_time,
            end_time=self._end_time,
            duration_seconds=duration,
            packets=packets or [],
            connections=dict(self._connections),
            dns_records=dns_records or [],
            http_transactions=http_transactions or [],
            protocol_stats=dict(self._protocol_stats),
        )


async def parse_pcap_async(
    file_path: str | Path,
    progress_callback: Callable[[float], None] | None = None,
    store_packets: bool = True,
    max_packets: int | None = None,
) -> ParseResult:
    """
    异步解析 PCAP 文件

    Note: Scapy 本身不支持异步，这里只是包装为协程
    """
    import asyncio

    parser = PcapParser(file_path)
    if progress_callback:
        parser.set_progress_callback(progress_callback)

    # 在线程池中运行同步解析
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: parser.parse(store_packets=store_packets, max_packets=max_packets)
    )
    return result
