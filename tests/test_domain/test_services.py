"""领域服务单元测试"""

import pytest

from netops_toolkit.domain.entities.device import Device, DeviceStatus, DeviceVendor
from netops_toolkit.domain.entities.scan_result import PingResult
from netops_toolkit.domain.services.network_diagnostics import (
    calculate_health_score,
    classify_latency,
    summarize_results,
)
from netops_toolkit.domain.services.device_management import (
    derive_device_status,
    filter_devices,
    group_devices_by_vendor,
)


class TestClassifyLatency:
    def test_excellent(self):
        assert classify_latency(5.0) == "excellent"

    def test_good(self):
        assert classify_latency(30.0) == "good"

    def test_fair(self):
        assert classify_latency(80.0) == "fair"

    def test_poor(self):
        assert classify_latency(250.0) == "poor"

    def test_none_unreachable(self):
        assert classify_latency(None) == "unreachable"

    def test_zero(self):
        assert classify_latency(0.0) == "excellent"

    def test_boundary_10(self):
        # 10 is not < 10, so it's "good"
        assert classify_latency(10.0) == "good"

    def test_boundary_50(self):
        # 50 is not < 50, so it's "fair"
        assert classify_latency(50.0) == "fair"


class TestCalculateHealthScore:
    def test_all_alive(self):
        results = [
            PingResult(host="10.0.0.1", is_alive=True, avg_latency=5.0, packet_loss=0),
            PingResult(host="10.0.0.2", is_alive=True, avg_latency=10.0, packet_loss=0),
        ]
        score = calculate_health_score(results)
        assert score > 90.0

    def test_all_dead(self):
        results = [
            PingResult(host="10.0.0.1", is_alive=False, packet_loss=100.0),
            PingResult(host="10.0.0.2", is_alive=False, packet_loss=100.0),
        ]
        score = calculate_health_score(results)
        assert score < 20.0

    def test_mixed(self):
        results = [
            PingResult(host="10.0.0.1", is_alive=True, avg_latency=5.0, packet_loss=0),
            PingResult(host="10.0.0.2", is_alive=False, packet_loss=100.0),
        ]
        score = calculate_health_score(results)
        assert 30.0 < score < 80.0

    def test_empty_results(self):
        score = calculate_health_score([])
        assert score == 0.0


class TestSummarizeResults:
    def test_summarize(self):
        results = [
            PingResult(host="10.0.0.1", is_alive=True, avg_latency=5.0),
            PingResult(host="10.0.0.2", is_alive=True, avg_latency=80.0),
            PingResult(host="10.0.0.3", is_alive=False),
        ]
        summary = summarize_results(results)
        assert summary["total"] == 3
        assert summary["alive"] == 2
        assert summary["dead"] == 1

    def test_summarize_empty(self):
        summary = summarize_results([])
        assert summary["total"] == 0
        assert summary["alive"] == 0
        assert summary["dead"] == 0


class TestDeriveDeviceStatus:
    def test_alive(self):
        device = Device(name="r1", ip="10.0.0.1")
        ping = PingResult(host="10.0.0.1", is_alive=True, avg_latency=5.0, packet_loss=0)
        status = derive_device_status(device, ping)
        assert status == DeviceStatus.ONLINE

    def test_dead(self):
        device = Device(name="r1", ip="10.0.0.1")
        ping = PingResult(host="10.0.0.1", is_alive=False)
        status = derive_device_status(device, ping)
        assert status == DeviceStatus.OFFLINE

    def test_no_ping(self):
        device = Device(name="r1", ip="10.0.0.1")
        status = derive_device_status(device, None)
        assert status == DeviceStatus.UNKNOWN

    def test_maintenance_device_stays_maintenance(self):
        device = Device(name="r1", ip="10.0.0.1", status=DeviceStatus.MAINTENANCE)
        ping = PingResult(host="10.0.0.1", is_alive=True)
        status = derive_device_status(device, ping)
        assert status == DeviceStatus.MAINTENANCE


class TestFilterDevices:
    def setup_method(self):
        self.devices = [
            Device(name="core-01", ip="10.0.0.1", vendor="cisco", status=DeviceStatus.ONLINE),
            Device(name="access-01", ip="10.0.0.2", vendor="huawei", status=DeviceStatus.OFFLINE),
            Device(name="core-02", ip="10.0.0.3", vendor="cisco", status=DeviceStatus.ONLINE),
            Device(name="access-02", ip="10.0.0.4", vendor="h3c", status=DeviceStatus.UNKNOWN),
        ]

    def test_filter_by_status(self):
        online = filter_devices(self.devices, status=DeviceStatus.ONLINE)
        assert len(online) == 2

    def test_filter_by_vendor(self):
        cisco = filter_devices(self.devices, vendor="cisco")
        assert len(cisco) == 2

    def test_filter_combined(self):
        result = filter_devices(
            self.devices, status=DeviceStatus.ONLINE, vendor="cisco"
        )
        assert len(result) == 2

    def test_filter_no_match(self):
        result = filter_devices(self.devices, vendor="juniper")
        assert len(result) == 0

    def test_filter_no_criteria(self):
        result = filter_devices(self.devices)
        assert len(result) == 4


class TestGroupDevicesByVendor:
    def test_group(self):
        devices = [
            Device(name="r1", ip="10.0.0.1", vendor="cisco"),
            Device(name="r2", ip="10.0.0.2", vendor="cisco"),
            Device(name="s1", ip="10.0.0.3", vendor="huawei"),
        ]
        groups = group_devices_by_vendor(devices)
        assert len(groups["cisco"]) == 2
        assert len(groups["huawei"]) == 1

    def test_group_empty(self):
        groups = group_devices_by_vendor([])
        assert len(groups) == 0
