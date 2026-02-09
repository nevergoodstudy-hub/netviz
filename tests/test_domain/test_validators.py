"""领域验证器单元测试"""

import pytest

from netops_toolkit.domain import validators
from netops_toolkit.domain.exceptions import (
    InvalidCIDRError,
    InvalidHostnameError,
    InvalidIPAddressError,
    InvalidPortError,
)


class TestIPValidation:
    @pytest.mark.parametrize("ip", ["192.168.1.1", "10.0.0.1", "255.255.255.255"])
    def test_valid_ipv4(self, ip):
        assert validators.validate_ip(ip) == ip

    @pytest.mark.parametrize("ip", ["999.999.999.999", "abc", "192.168.1", ""])
    def test_invalid_ipv4(self, ip):
        with pytest.raises(InvalidIPAddressError):
            validators.validate_ip(ip)


class TestCIDRValidation:
    @pytest.mark.parametrize("cidr", ["192.168.1.0/24", "10.0.0.0/8"])
    def test_valid_cidr(self, cidr):
        assert validators.validate_cidr(cidr) == cidr

    @pytest.mark.parametrize("cidr", ["192.168.1.0/33", "abc/24", "not_a_cidr"])
    def test_invalid_cidr(self, cidr):
        with pytest.raises(InvalidCIDRError):
            validators.validate_cidr(cidr)


class TestHostnameValidation:
    @pytest.mark.parametrize("host", ["router-01", "example.com", "sub.domain.org"])
    def test_valid_hostname(self, host):
        assert validators.validate_hostname(host) == host

    @pytest.mark.parametrize("host", ["", "-invalid", "a" * 256])
    def test_invalid_hostname(self, host):
        with pytest.raises(InvalidHostnameError):
            validators.validate_hostname(host)


class TestPortValidation:
    @pytest.mark.parametrize("port", [1, 22, 80, 443, 8080, 65535])
    def test_valid_port(self, port):
        assert validators.validate_port(port) == port

    @pytest.mark.parametrize("port", [0, -1, 65536, 100000])
    def test_invalid_port(self, port):
        with pytest.raises(InvalidPortError):
            validators.validate_port(port)


class TestPortRangeParsing:
    def test_single_port(self):
        assert validators.parse_port_range("80") == [80]

    def test_port_range(self):
        assert validators.parse_port_range("80-83") == [80, 81, 82, 83]

    def test_comma_separated(self):
        result = validators.parse_port_range("22,80,443")
        assert 22 in result
        assert 80 in result
        assert 443 in result

    def test_mixed(self):
        result = validators.parse_port_range("22,80-82,443")
        assert result == [22, 80, 81, 82, 443]
