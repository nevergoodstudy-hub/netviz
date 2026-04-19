"""
NetViz 实时抓包服务
使用 Scapy 进行网络数据包捕获
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from scapy.utils import PcapWriter
from scapy.all import (
    sniff,
    get_if_list,
    conf,
    IP,
    TCP,
    UDP,
    ICMP,
    DNS,
    Raw,
)

# Windows 专用接口信息
import platform
if platform.system() == "Windows":
    try:
        from scapy.arch.windows import get_windows_if_list
        HAS_WINDOWS_IF = True
    except ImportError:
        HAS_WINDOWS_IF = False
else:
    HAS_WINDOWS_IF = False

logger = logging.getLogger(__name__)


@dataclass
class CaptureSession:
    """抓包会话"""

    id: str
    interface: str
    filter: str | None
    start_time: datetime
    packet_count: int = 0
    byte_count: int = 0
    is_running: bool = True
    packets: list = field(default_factory=list)
    output_file: Path | None = None
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None


class CaptureService:
    """抓包服务"""

    def __init__(self):
        self.sessions: dict[str, CaptureSession] = {}
        self._lock = threading.Lock()

    def get_interfaces(self) -> list[dict]:
        """获取可用网络接口列表"""
        interfaces = []
        try:
            # Windows: 使用专用函数获取详细信息
            if HAS_WINDOWS_IF:
                win_ifaces = get_windows_if_list()
                seen_guids = set()  # 避免重复
                
                for iface in win_ifaces:
                    guid = iface.get("guid", "")
                    
                    # 跳过重复的接口
                    if guid in seen_guids:
                        continue
                    seen_guids.add(guid)
                    
                    name = iface.get("name", "")
                    description = iface.get("description", name)
                    mac = iface.get("mac", "")
                    ips = iface.get("ips", [])
                    ipv4_addrs = [ip for ip in ips if "." in ip and not ip.startswith("169.254")]
                    
                    # 过滤掉底层驱动接口（名称中包含 Filter, LightWeight, NPCAP, QoS 等）
                    skip_keywords = [
                        "Filter", "LightWeight", "NPCAP", "QoS", "Scheduler",
                        "WFP", "Packet Driver", "Extension"
                    ]
                    should_skip = any(kw in description for kw in skip_keywords)
                    
                    # 保留有 IP 地址的接口，或者是常见的网卡类型
                    is_useful = (
                        len(ipv4_addrs) > 0 or
                        "Wi-Fi" in description or
                        "Wireless" in description or
                        "Ethernet" in description or
                        "WLAN" in name or
                        "VMware" in description or
                        "Hyper-V" in description or
                        "vEthernet" in name or
                        "Loopback" in description or
                        "Bluetooth" in description
                    )
                    
                    if should_skip or not is_useful:
                        continue
                    
                    # 使用 NPF 设备名作为实际接口名（Scapy 需要）
                    npf_name = f"\\\\Device\\\\NPF_{{{guid}}}" if guid else name
                    
                    interfaces.append({
                        "name": npf_name,
                        "description": description,
                        "friendly_name": name,
                        "ips": ipv4_addrs,
                        "mac": mac,
                    })
            else:
                # 其他系统: 使用 conf.ifaces
                for iface_name, iface_obj in conf.ifaces.items():
                    ip = getattr(iface_obj, "ip", None)
                    mac = getattr(iface_obj, "mac", None)
                    desc = getattr(iface_obj, "description", iface_name)
                    
                    interfaces.append({
                        "name": iface_name,
                        "description": desc or iface_name,
                        "friendly_name": iface_name,
                        "ips": [ip] if ip else [],
                        "mac": mac or "",
                    })
                    
        except Exception as e:
            logger.error(f"获取网络接口失败: {e}")
            # 回退到基本方法
            try:
                if_list = get_if_list()
                for iface in if_list:
                    interfaces.append({
                        "name": iface,
                        "description": iface,
                        "friendly_name": iface,
                        "ips": [],
                        "mac": "",
                    })
            except Exception:
                pass

        return interfaces

    def start_capture(
        self,
        session_id: str,
        interface: str,
        filter_expr: str | None = None,
        packet_callback: Callable | None = None,
        output_file: Path | None = None,
        max_packets: int = 0,
    ) -> CaptureSession:
        """
        开始抓包

        Args:
            session_id: 会话ID
            interface: 网络接口名称
            filter_expr: BPF 过滤表达式 (如 "tcp port 80")
            packet_callback: 数据包回调函数
            output_file: 输出文件路径
            max_packets: 最大抓包数量，0表示无限制

        Returns:
            CaptureSession 对象
        """
        with self._lock:
            if session_id in self.sessions:
                raise ValueError(f"会话 {session_id} 已存在")

            session = CaptureSession(
                id=session_id,
                interface=interface,
                filter=filter_expr,
                start_time=datetime.now(),
                output_file=output_file,
            )
            self.sessions[session_id] = session

        def _capture_thread():
            """抓包线程"""
            writer: PcapWriter | None = None
            try:
                logger.info(f"开始抓包: 接口={interface}, 过滤器={filter_expr}")
                if output_file:
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    writer = PcapWriter(str(output_file), append=False, sync=True)

                def packet_handler(pkt):
                    if session._stop_event.is_set():
                        return True  # 停止抓包

                    session.packet_count += 1
                    session.byte_count += len(pkt)

                    if writer:
                        writer.write(pkt)

                    # 解析数据包基本信息
                    pkt_info = self._parse_packet(pkt, session.packet_count)
                    session.packets.append(pkt_info)

                    # 限制内存中保存的数据包数量
                    if len(session.packets) > 10000:
                        session.packets = session.packets[-5000:]

                    # 回调
                    if packet_callback:
                        try:
                            packet_callback(pkt_info)
                        except Exception as e:
                            logger.error(f"数据包回调错误: {e}")

                    # 检查最大数量
                    if max_packets > 0 and session.packet_count >= max_packets:
                        return True

                    return False

                # 使用短超时轮询，确保空闲接口也能及时响应停止事件。
                while not session._stop_event.is_set():
                    sniff(
                        iface=interface,
                        filter=filter_expr,
                        prn=packet_handler,
                        stop_filter=lambda _: (
                            session._stop_event.is_set()
                            or (max_packets > 0 and session.packet_count >= max_packets)
                        ),
                        store=False,
                        timeout=1,
                    )

                    if max_packets > 0 and session.packet_count >= max_packets:
                        break
                if output_file:
                    logger.info(f"数据包已保存到: {output_file}")

            except Exception as e:
                logger.error(f"抓包错误: {e}")
            finally:
                if writer:
                    writer.close()
                session.is_running = False
                logger.info(f"抓包结束: 共 {session.packet_count} 个数据包")

        # 启动抓包线程
        session._thread = threading.Thread(target=_capture_thread, daemon=True)
        session._thread.start()

        return session

    def stop_capture(self, session_id: str) -> CaptureSession | None:
        """停止抓包"""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None

            session._stop_event.set()
            session.is_running = False

            # 等待线程结束
            if session._thread and session._thread.is_alive():
                session._thread.join(timeout=5.0)

            return session

    def get_session(self, session_id: str) -> CaptureSession | None:
        """获取会话信息"""
        return self.sessions.get(session_id)

    def get_session_packets(
        self, session_id: str, offset: int = 0, limit: int = 100
    ) -> list[dict]:
        """获取会话中的数据包"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        return session.packets[offset : offset + limit]

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if session_id not in self.sessions:
                return False

            session = self.sessions[session_id]
            if session.is_running:
                session._stop_event.set()

            del self.sessions[session_id]
            return True

    def _parse_packet(self, pkt, index: int) -> dict:
        """解析数据包信息"""
        info = {
            "index": index,
            "timestamp": datetime.now().isoformat(),
            "length": len(pkt),
            "protocol": "Unknown",
            "src_ip": None,
            "dst_ip": None,
            "src_port": None,
            "dst_port": None,
            "info": "",
        }

        # IP 层
        if IP in pkt:
            info["src_ip"] = pkt[IP].src
            info["dst_ip"] = pkt[IP].dst
            info["protocol"] = "IP"

            # TCP
            if TCP in pkt:
                info["protocol"] = "TCP"
                info["src_port"] = pkt[TCP].sport
                info["dst_port"] = pkt[TCP].dport
                flags = pkt[TCP].flags
                info["info"] = f"{pkt[TCP].sport} → {pkt[TCP].dport} [{flags}]"

            # UDP
            elif UDP in pkt:
                info["protocol"] = "UDP"
                info["src_port"] = pkt[UDP].sport
                info["dst_port"] = pkt[UDP].dport
                info["info"] = f"{pkt[UDP].sport} → {pkt[UDP].dport}"

                # DNS
                if DNS in pkt:
                    info["protocol"] = "DNS"
                    if pkt[DNS].qr == 0:  # Query
                        if pkt[DNS].qd:
                            info["info"] = f"Query: {pkt[DNS].qd.qname.decode()}"
                    else:  # Response
                        info["info"] = "Response"

            # ICMP
            elif ICMP in pkt:
                info["protocol"] = "ICMP"
                icmp_type = pkt[ICMP].type
                if icmp_type == 8:
                    info["info"] = "Echo Request"
                elif icmp_type == 0:
                    info["info"] = "Echo Reply"
                else:
                    info["info"] = f"Type {icmp_type}"

        return info


# 全局抓包服务实例
capture_service = CaptureService()
