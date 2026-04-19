from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import func, select

import app.api.ai as ai_api_module
import app.api.pcap as pcap_api_module
import app.core.database as database_module
from app.services.parser.pcap_parser import ParseEvent
from app.core.secret_store import encrypt_setting_value
from app.models.analysis import Alert, Settings as DbSettings
from app.models.pcap import Connection, DnsRecord, HttpTransaction, Packet, PcapFile, ParseStatus


@pytest_asyncio.fixture
async def parsed_pcap(test_db):
    now = datetime.utcnow()
    pcap = PcapFile(
        filename="sample.pcap",
        original_filename="sample.pcap",
        file_path="/tmp/sample.pcap",
        file_size=1024,
        file_hash="a" * 64,
        status=ParseStatus.COMPLETED.value,
        parse_progress=100.0,
        total_packets=3,
        total_bytes=1024,
        start_time=now,
        end_time=now + timedelta(seconds=10),
        duration_seconds=10.0,
    )
    test_db.add(pcap)
    await test_db.commit()
    await test_db.refresh(pcap)

    packets = [
        Packet(
            pcap_file_id=pcap.id,
            packet_number=1,
            timestamp=now,
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            protocol="TCP",
            src_port=12345,
            dst_port=80,
            app_protocol="HTTP",
            length=512,
            payload_length=256,
        ),
        Packet(
            pcap_file_id=pcap.id,
            packet_number=2,
            timestamp=now + timedelta(seconds=1),
            src_ip="10.0.0.2",
            dst_ip="10.0.0.1",
            protocol="TCP",
            src_port=80,
            dst_port=12345,
            app_protocol="HTTP",
            length=256,
            payload_length=128,
        ),
        Packet(
            pcap_file_id=pcap.id,
            packet_number=3,
            timestamp=now + timedelta(seconds=2),
            src_ip="10.0.0.1",
            dst_ip="8.8.8.8",
            protocol="UDP",
            src_port=53000,
            dst_port=53,
            app_protocol="DNS",
            length=256,
            payload_length=128,
        ),
    ]
    test_db.add_all(packets)
    await test_db.flush()

    connection = Connection(
        pcap_file_id=pcap.id,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        src_port=12345,
        dst_port=80,
        protocol="TCP",
        packet_count=2,
        byte_count=768,
        src_to_dst_packets=1,
        dst_to_src_packets=1,
        src_to_dst_bytes=512,
        dst_to_src_bytes=256,
        start_time=now,
        end_time=now + timedelta(seconds=1),
        duration_seconds=1.0,
        app_protocol="HTTP",
        is_encrypted=False,
    )
    test_db.add(connection)
    await test_db.flush()

    test_db.add(
        DnsRecord(
            pcap_file_id=pcap.id,
            packet_id=packets[2].id,
            query_id=100,
            is_response=False,
            domain="example.com",
            query_type="A",
            response_code=None,
            answers=None,
            timestamp=now + timedelta(seconds=2),
        )
    )
    test_db.add_all(
        [
            HttpTransaction(
                pcap_file_id=pcap.id,
                connection_id=connection.id,
                method="GET",
                host="example.com",
                uri="/index.html",
                user_agent="NetVizTest",
                content_type=None,
                request_headers=None,
                status_code=None,
                response_content_type=None,
                response_headers=None,
                request_time=now,
                response_time=None,
                request_size=128,
                response_size=0,
            ),
            HttpTransaction(
                pcap_file_id=pcap.id,
                connection_id=connection.id,
                method="RESPONSE",
                host="",
                uri="/",
                user_agent=None,
                content_type=None,
                request_headers=None,
                status_code=200,
                response_content_type="text/html",
                response_headers=None,
                request_time=now + timedelta(seconds=1),
                response_time=now + timedelta(seconds=1),
                request_size=0,
                response_size=256,
            ),
        ]
    )
    test_db.add(
        Alert(
            pcap_file_id=pcap.id,
            alert_type="port_scan",
            severity="high",
            title="Seeded Alert",
            description="Existing alert for dashboard rendering.",
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            detected_at=now,
        )
    )
    await test_db.commit()

    return pcap


@pytest.mark.asyncio
async def test_analysis_and_pcap_detail_endpoints_use_current_schema(client, parsed_pcap):
    pcap_id = parsed_pcap.id

    stats_response = await client.get(f"/api/pcap/{pcap_id}/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["unique_ips"] == 3

    protocol_response = await client.get(f"/api/analysis/protocol-distribution/{pcap_id}")
    assert protocol_response.status_code == 200
    assert {item["protocol"] for item in protocol_response.json()} >= {"TCP", "UDP"}

    talker_response = await client.get(f"/api/analysis/top-talkers/{pcap_id}")
    assert talker_response.status_code == 200
    top_talker = talker_response.json()[0]
    assert "packets_sent" in top_talker
    assert "bytes_received" in top_talker

    dns_response = await client.get(f"/api/analysis/dns-analysis/{pcap_id}")
    assert dns_response.status_code == 200
    assert dns_response.json()["top_domains"][0]["domain"] == "example.com"

    http_response = await client.get(f"/api/analysis/http-analysis/{pcap_id}")
    assert http_response.status_code == 200
    assert http_response.json()["methods"]["GET"] == 1
    assert http_response.json()["status_codes"]["200"] == 1

    alerts_response = await client.get("/api/analysis/alerts")
    assert alerts_response.status_code == 200
    alert = alerts_response.json()[0]
    assert "detected_at" in alert
    assert alert["type"] == "port_scan"


@pytest.mark.asyncio
async def test_detect_anomalies_persists_alerts(client, test_db):
    now = datetime.utcnow()
    pcap = PcapFile(
        filename="anomaly.pcap",
        original_filename="anomaly.pcap",
        file_path="/tmp/anomaly.pcap",
        file_size=2048,
        file_hash="b" * 64,
        status=ParseStatus.COMPLETED.value,
        parse_progress=100.0,
        total_packets=200,
        total_bytes=200 * 1024,
        start_time=now,
        end_time=now + timedelta(seconds=30),
        duration_seconds=30.0,
    )
    test_db.add(pcap)
    await test_db.commit()
    await test_db.refresh(pcap)

    packet = Packet(
        pcap_file_id=pcap.id,
        packet_number=1,
        timestamp=now,
        src_ip="10.10.10.10",
        dst_ip="8.8.8.8",
        protocol="UDP",
        src_port=53000,
        dst_port=53,
        app_protocol="DNS",
        length=128,
        payload_length=64,
    )
    test_db.add(packet)
    await test_db.flush()

    long_domain = f"{'a' * 52}.example.com"
    test_db.add(
        DnsRecord(
            pcap_file_id=pcap.id,
            packet_id=packet.id,
            query_id=200,
            is_response=False,
            domain=long_domain,
            query_type="TXT",
            response_code=None,
            answers=None,
            timestamp=now,
        )
    )

    for port in range(1, 53):
        test_db.add(
            Connection(
                pcap_file_id=pcap.id,
                src_ip="10.10.10.10",
                dst_ip="192.168.1.1",
                src_port=40000 + port,
                dst_port=port,
                protocol="TCP",
                packet_count=1,
                byte_count=1024,
                src_to_dst_packets=1,
                dst_to_src_packets=0,
                src_to_dst_bytes=1024,
                dst_to_src_bytes=0,
                start_time=now,
                end_time=now,
                duration_seconds=0.0,
                app_protocol=None,
                is_encrypted=False,
            )
        )

    test_db.add(
        Connection(
            pcap_file_id=pcap.id,
            src_ip="10.10.10.20",
            dst_ip="203.0.113.20",
            src_port=44321,
            dst_port=443,
            protocol="TCP",
            packet_count=100,
            byte_count=101 * 1024 * 1024,
            src_to_dst_packets=80,
            dst_to_src_packets=20,
            src_to_dst_bytes=101 * 1024 * 1024,
            dst_to_src_bytes=1024,
            start_time=now,
            end_time=now + timedelta(seconds=10),
            duration_seconds=10.0,
            app_protocol="HTTPS",
            is_encrypted=True,
        )
    )
    await test_db.commit()

    response = await client.post(f"/api/analysis/detect-anomalies/{pcap.id}")
    assert response.status_code == 200
    anomaly_types = {item["type"] for item in response.json()}
    assert {"port_scan", "dns_anomaly", "data_exfiltration"} <= anomaly_types

    alerts_response = await client.get("/api/analysis/alerts", params={"pcap_id": pcap.id})
    assert alerts_response.status_code == 200
    alert_types = {item["type"] for item in alerts_response.json()}
    assert {"port_scan", "dns_anomaly", "data_exfiltration"} <= alert_types


@pytest.mark.asyncio
async def test_ai_routes_accept_deepseek_and_use_decrypted_db_settings(
    client, test_db, monkeypatch, parsed_pcap
):
    encrypted_value, is_encrypted = encrypt_setting_value(
        "deepseek_api_key",
        "deepseek-secret-1234567890",
    )
    test_db.add(
        DbSettings(
            key="deepseek_api_key",
            value=encrypted_value,
            is_encrypted=is_encrypted,
        )
    )
    await test_db.commit()

    captured: dict[str, object] = {}

    class FakeAIService:
        model = "deepseek-chat"

        async def chat(self, messages):
            captured["messages"] = messages
            return {
                "content": "mocked response",
                "prompt_tokens": 11,
                "completion_tokens": 7,
            }

    def fake_get_ai_service(provider, overrides=None):
        captured["provider"] = provider
        captured["overrides"] = overrides
        return FakeAIService()

    monkeypatch.setattr(ai_api_module, "get_ai_service", fake_get_ai_service)

    chat_response = await client.post(
        "/api/ai/chat",
        json={"message": "请分析", "provider": "deepseek"},
    )
    assert chat_response.status_code == 200
    assert captured["provider"] == "deepseek"
    assert captured["overrides"]["deepseek_api_key"] == "deepseek-secret-1234567890"

    conversation_id = chat_response.json()["conversation_id"]
    conversation_response = await client.get(f"/api/ai/conversations/{conversation_id}")
    assert conversation_response.status_code == 200
    assert len(conversation_response.json()["messages"]) == 2

    analyze_response = await client.post(
        "/api/ai/analyze",
        json={
            "pcap_id": parsed_pcap.id,
            "analysis_type": "请从安全角度分析这个抓包",
            "provider": "deepseek",
        },
    )
    assert analyze_response.status_code == 200
    assert analyze_response.json()["answer"] == "mocked response"


@pytest.mark.asyncio
async def test_parse_pcap_task_persists_dns_and_http_records(test_db, monkeypatch):
    now = datetime.utcnow()
    pcap = PcapFile(
        filename="task.pcap",
        original_filename="task.pcap",
        file_path="/tmp/task.pcap",
        file_size=512,
        file_hash="c" * 64,
        status=ParseStatus.PENDING.value,
        parse_progress=0.0,
        total_packets=0,
        total_bytes=0,
        start_time=None,
        end_time=None,
        duration_seconds=0.0,
    )
    test_db.add(pcap)
    await test_db.commit()
    await test_db.refresh(pcap)

    fake_result = SimpleNamespace(
        total_packets=1,
        total_bytes=512,
        start_time=now,
        end_time=now,
        duration_seconds=0.0,
        connections={
            "primary": SimpleNamespace(
                src_ip="1.1.1.1",
                dst_ip="2.2.2.2",
                src_port=1234,
                dst_port=80,
                protocol="TCP",
                packet_count=1,
                byte_count=512,
                src_to_dst_packets=1,
                dst_to_src_packets=0,
                src_to_dst_bytes=512,
                dst_to_src_bytes=0,
                start_time=now,
                end_time=now,
                app_protocol="HTTP",
                is_encrypted=False,
            )
        },
        protocol_stats={"TCP": 1},
        packets=[],
        dns_records=[],
        http_transactions=[],
    )

    class FakeParser:
        def __init__(self, *_args, **_kwargs):
            self._callback = None

        def set_progress_callback(self, callback):
            self._callback = callback

        def iter_packets(self):
            if self._callback:
                self._callback(100.0)
            yield ParseEvent(
                packet=SimpleNamespace(
                    packet_number=1,
                    timestamp=now,
                    timestamp_micro=0,
                    src_mac=None,
                    dst_mac=None,
                    eth_type=None,
                    src_ip="1.1.1.1",
                    dst_ip="2.2.2.2",
                    ip_version=4,
                    ttl=64,
                    protocol="TCP",
                    src_port=1234,
                    dst_port=80,
                    tcp_flags="S",
                    tcp_seq=None,
                    tcp_ack=None,
                    app_protocol="HTTP",
                    length=512,
                    payload_length=100,
                ),
                dns_record={
                    "packet_number": 1,
                    "timestamp": now,
                    "query_id": 1,
                    "is_response": False,
                    "domain": "example.org",
                    "query_type": "A",
                    "response_code": None,
                    "answers": [],
                },
                http_transaction={
                    "packet_number": 1,
                    "timestamp": now,
                    "type": "request",
                    "method": "GET",
                    "host": "example.org",
                    "uri": "/",
                    "user_agent": "NetVizTest",
                },
            )

        def build_result(self):
            return fake_result

    @asynccontextmanager
    async def fake_get_db_context():
        yield test_db

    monkeypatch.setattr(pcap_api_module, "PcapParser", FakeParser)
    monkeypatch.setattr(database_module, "get_db_context", fake_get_db_context)

    await pcap_api_module.parse_pcap_task(pcap.id, pcap.file_path)

    dns_count = await test_db.scalar(select(func.count(DnsRecord.id)))
    http_count = await test_db.scalar(select(func.count(HttpTransaction.id)))

    assert dns_count == 1
    assert http_count == 1
