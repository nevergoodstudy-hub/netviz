"""Security edge case tests - run as: python tests/_run_security_tests.py"""
import sys
sys.path.insert(0, ".")

issues = []
passed = 0

# === 1. Sanitizer ===
from netops_toolkit.infrastructure.security.sanitizer import sanitize_command, sanitize_hostname, sanitize_ip
from netops_toolkit.domain.exceptions import CommandInjectionError

dangerous = ["ls; rm -rf /", "cat | grep x", "a && b", "echo `whoami`", "x$(id)"]
for payload in dangerous:
    try:
        sanitize_command(payload, strict=True)
        issues.append(f"SEC-MEDIUM: sanitize_command did NOT reject: {repr(payload)}")
    except CommandInjectionError:
        passed += 1

safe_cmds = ["show version", "display interface", "ping 10.0.0.1"]
for safe in safe_cmds:
    try:
        sanitize_command(safe, strict=True)
        passed += 1
    except CommandInjectionError:
        issues.append(f"SEC-LOW: sanitize_command rejected safe: {repr(safe)}")

bad_hosts = ["router;ls", "host$(id)", "192.168.1.1|cat"]
for bh in bad_hosts:
    try:
        sanitize_hostname(bh)
        issues.append(f"SEC-HIGH: sanitize_hostname did NOT reject: {repr(bh)}")
    except CommandInjectionError:
        passed += 1

bad_ips = ["10.0.0.1;ls", "10.0.0.1$(id)"]
for bi in bad_ips:
    try:
        sanitize_ip(bi)
        issues.append(f"SEC-HIGH: sanitize_ip did NOT reject: {repr(bi)}")
    except CommandInjectionError:
        passed += 1

# === 2. Validators edge cases ===
from netops_toolkit.domain.validators import validate_ip, validate_port, validate_cidr
from netops_toolkit.domain.exceptions import InvalidIPAddressError, InvalidPortError, InvalidCIDRError

for bad in ["999.999.999.999", "not-an-ip", "", "   "]:
    try:
        validate_ip(bad)
        issues.append(f"VAL-MEDIUM: validate_ip accepted: {repr(bad)}")
    except (InvalidIPAddressError, ValueError):
        passed += 1

for bad_port in [0, -1, 65536, 99999]:
    try:
        validate_port(bad_port)
        issues.append(f"VAL-MEDIUM: validate_port accepted: {bad_port}")
    except InvalidPortError:
        passed += 1

for good_port in [1, 22, 80, 443, 65535]:
    try:
        validate_port(good_port)
        passed += 1
    except InvalidPortError:
        issues.append(f"VAL-LOW: validate_port rejected valid: {good_port}")

try:
    validate_cidr("192.168.1.0/24")
    passed += 1
except Exception:
    issues.append("VAL-MEDIUM: validate_cidr rejected valid 192.168.1.0/24")

try:
    validate_cidr("not-a-cidr")
    issues.append("VAL-MEDIUM: validate_cidr accepted invalid")
except InvalidCIDRError:
    passed += 1

# === 3. Sensitive data masking ===
from netops_toolkit.infrastructure.security.audit_log_enhancer import SensitiveDataMasker

masker = SensitiveDataMasker()

masked = masker.mask_text("password=admin123 token=abc123")
if "admin123" in masked:
    issues.append("SEC-HIGH: SensitiveDataMasker did NOT mask password in text")
else:
    passed += 1

masked_dict = masker.mask_dict({"host": "10.0.0.1", "password": "secret123", "username": "admin"})
if masked_dict.get("password") == "secret123":
    issues.append("SEC-HIGH: SensitiveDataMasker did NOT mask password in dict")
else:
    passed += 1
if masked_dict.get("host") == "10.0.0.1":
    passed += 1
else:
    issues.append("SEC-LOW: SensitiveDataMasker incorrectly masked host field")

# === 4. Exception hierarchy ===
from netops_toolkit.domain.exceptions import NetOpsError, DeviceError, PluginError, SecurityError

assert issubclass(DeviceError, NetOpsError)
assert issubclass(PluginError, NetOpsError)
assert issubclass(SecurityError, NetOpsError)
passed += 3

err = NetOpsError("test", "TEST_CODE", {"key": "val"})
d = err.to_dict()
assert d["error"] == "TEST_CODE"
assert d["message"] == "test"
passed += 1

# === Summary ===
print(f"Security Tests: {passed} passed, {len(issues)} issues")
for i in issues:
    print(f"  [ISSUE] {i}")
