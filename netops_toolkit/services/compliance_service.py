"""
NetOps Toolkit - 合规检查服务

支持功能:
- 设备配置合规检查
- NAPALM validate 集成
- 自定义合规规则
- 差异报告生成
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple, Union

import yaml


class ComplianceLevel(Enum):
    """合规级别"""
    COMPLIANT = "compliant"           # 完全合规
    WARNING = "warning"               # 警告（非关键问题）
    NON_COMPLIANT = "non_compliant"   # 不合规
    ERROR = "error"                   # 检查错误
    SKIPPED = "skipped"               # 跳过检查


class RuleType(Enum):
    """规则类型"""
    REGEX_MATCH = "regex_match"       # 正则匹配（必须存在）
    REGEX_NO_MATCH = "regex_no_match" # 正则不匹配（必须不存在）
    VALUE_RANGE = "value_range"       # 值范围检查
    VALUE_EQUAL = "value_equal"       # 值相等检查
    VALUE_IN_LIST = "value_in_list"   # 值在列表中
    NAPALM_VALIDATE = "napalm"        # NAPALM validate
    CUSTOM = "custom"                 # 自定义函数


@dataclass
class ComplianceRule:
    """合规规则定义"""
    id: str
    name: str
    description: str
    rule_type: RuleType
    severity: str = "critical"  # critical, warning, info
    vendor: str = "all"         # 适用厂商: all, cisco_ios, huawei, juniper
    
    # 规则参数
    pattern: str = ""           # 正则表达式
    key_path: str = ""          # 数据键路径 (如 interfaces.GigabitEthernet0/1.is_up)
    expected_value: Any = None  # 期望值
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: List[Any] = field(default_factory=list)
    
    # NAPALM 特定
    napalm_getter: str = ""     # NAPALM getter 方法名
    
    # 自定义检查函数
    custom_check: Optional[Callable[[Any], bool]] = None
    
    # 元数据
    category: str = "general"   # 规则分类
    remediation: str = ""       # 修复建议


@dataclass
class ComplianceResult:
    """单项合规检查结果"""
    rule_id: str
    rule_name: str
    level: ComplianceLevel
    message: str
    actual_value: Any = None
    expected_value: Any = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceComplianceReport:
    """设备合规报告"""
    device_name: str
    device_ip: str
    vendor: str
    check_time: datetime
    results: List[ComplianceResult] = field(default_factory=list)
    
    @property
    def compliant_count(self) -> int:
        return sum(1 for r in self.results if r.level == ComplianceLevel.COMPLIANT)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.level == ComplianceLevel.WARNING)
    
    @property
    def non_compliant_count(self) -> int:
        return sum(1 for r in self.results if r.level == ComplianceLevel.NON_COMPLIANT)
    
    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.level == ComplianceLevel.ERROR)
    
    @property
    def overall_level(self) -> ComplianceLevel:
        """计算整体合规级别"""
        if self.error_count > 0:
            return ComplianceLevel.ERROR
        if self.non_compliant_count > 0:
            return ComplianceLevel.NON_COMPLIANT
        if self.warning_count > 0:
            return ComplianceLevel.WARNING
        return ComplianceLevel.COMPLIANT
    
    @property
    def score(self) -> float:
        """计算合规分数 (0-100)"""
        total = len(self.results)
        if total == 0:
            return 100.0
        passed = self.compliant_count + self.warning_count * 0.5
        return (passed / total) * 100


# ============================================================
# 预定义合规规则
# ============================================================

BUILTIN_RULES: List[ComplianceRule] = [
    # === 安全规则 ===
    ComplianceRule(
        id="SEC-001",
        name="SSH版本检查",
        description="确保SSH使用版本2",
        rule_type=RuleType.REGEX_MATCH,
        severity="critical",
        vendor="cisco_ios",
        pattern=r"ip ssh version 2",
        category="security",
        remediation="配置 'ip ssh version 2'",
    ),
    ComplianceRule(
        id="SEC-002",
        name="Telnet禁用检查",
        description="确保Telnet服务已禁用",
        rule_type=RuleType.REGEX_NO_MATCH,
        severity="critical",
        vendor="cisco_ios",
        pattern=r"transport input.*telnet",
        category="security",
        remediation="在VTY线路配置中移除telnet: 'transport input ssh'",
    ),
    ComplianceRule(
        id="SEC-003",
        name="密码加密检查",
        description="确保启用密码加密服务",
        rule_type=RuleType.REGEX_MATCH,
        severity="critical",
        vendor="cisco_ios",
        pattern=r"service password-encryption",
        category="security",
        remediation="配置 'service password-encryption'",
    ),
    ComplianceRule(
        id="SEC-004",
        name="Enable密码强度",
        description="确保使用enable secret而非enable password",
        rule_type=RuleType.REGEX_NO_MATCH,
        severity="critical",
        vendor="cisco_ios",
        pattern=r"^enable password\s+\S+",
        category="security",
        remediation="使用 'enable secret' 替代 'enable password'",
    ),
    ComplianceRule(
        id="SEC-005",
        name="AAA启用检查",
        description="确保启用AAA新模型",
        rule_type=RuleType.REGEX_MATCH,
        severity="warning",
        vendor="cisco_ios",
        pattern=r"aaa new-model",
        category="security",
        remediation="配置 'aaa new-model'",
    ),
    
    # === 网络规则 ===
    ComplianceRule(
        id="NET-001",
        name="IP路由启用",
        description="确保IP路由已启用",
        rule_type=RuleType.REGEX_NO_MATCH,
        severity="warning",
        vendor="cisco_ios",
        pattern=r"no ip routing",
        category="network",
        remediation="确保未配置 'no ip routing'",
    ),
    ComplianceRule(
        id="NET-002",
        name="CDP启用检查",
        description="检查CDP是否全局启用",
        rule_type=RuleType.REGEX_NO_MATCH,
        severity="info",
        vendor="cisco_ios",
        pattern=r"no cdp run",
        category="network",
        remediation="如需CDP发现功能，配置 'cdp run'",
    ),
    ComplianceRule(
        id="NET-003",
        name="域名查找禁用",
        description="建议禁用DNS域名查找以防止CLI延迟",
        rule_type=RuleType.REGEX_MATCH,
        severity="info",
        vendor="cisco_ios",
        pattern=r"no ip domain.lookup|no ip domain lookup",
        category="network",
        remediation="配置 'no ip domain lookup'",
    ),
    
    # === 管理规则 ===
    ComplianceRule(
        id="MGT-001",
        name="日志时间戳",
        description="确保日志包含时间戳",
        rule_type=RuleType.REGEX_MATCH,
        severity="warning",
        vendor="cisco_ios",
        pattern=r"service timestamps (log|debug)",
        category="management",
        remediation="配置 'service timestamps log datetime msec'",
    ),
    ComplianceRule(
        id="MGT-002",
        name="NTP配置检查",
        description="确保配置了NTP服务器",
        rule_type=RuleType.REGEX_MATCH,
        severity="warning",
        vendor="cisco_ios",
        pattern=r"ntp server\s+\S+",
        category="management",
        remediation="配置NTP服务器: 'ntp server <ip>'",
    ),
    ComplianceRule(
        id="MGT-003",
        name="SNMP社区检查",
        description="确保不使用默认SNMP社区名",
        rule_type=RuleType.REGEX_NO_MATCH,
        severity="critical",
        vendor="cisco_ios",
        pattern=r"snmp-server community (public|private)",
        category="management",
        remediation="更改默认SNMP社区名为复杂字符串",
    ),
    ComplianceRule(
        id="MGT-004",
        name="Syslog服务器配置",
        description="确保配置了远程日志服务器",
        rule_type=RuleType.REGEX_MATCH,
        severity="warning",
        vendor="cisco_ios",
        pattern=r"logging host\s+\S+|logging \d+\.\d+\.\d+\.\d+",
        category="management",
        remediation="配置日志服务器: 'logging host <ip>'",
    ),
    
    # === 接口规则 ===
    ComplianceRule(
        id="INT-001",
        name="未使用端口关闭",
        description="检查是否有未配置但开启的端口",
        rule_type=RuleType.CUSTOM,
        severity="warning",
        vendor="cisco_ios",
        category="interface",
        remediation="关闭未使用的端口: 'shutdown'",
    ),
    
    # === 华为规则 ===
    ComplianceRule(
        id="HW-SEC-001",
        name="SSH启用检查(华为)",
        description="确保SSH服务已启用",
        rule_type=RuleType.REGEX_MATCH,
        severity="critical",
        vendor="huawei",
        pattern=r"stelnet server enable|ssh server enable",
        category="security",
        remediation="配置 'stelnet server enable'",
    ),
    ComplianceRule(
        id="HW-SEC-002",
        name="Super密码配置(华为)",
        description="确保配置了Super密码",
        rule_type=RuleType.REGEX_MATCH,
        severity="critical",
        vendor="huawei",
        pattern=r"super password",
        category="security",
        remediation="配置Super密码",
    ),
    
    # === Juniper规则 ===
    ComplianceRule(
        id="JN-SEC-001",
        name="Root登录限制(Juniper)",
        description="确保Root登录受限",
        rule_type=RuleType.REGEX_MATCH,
        severity="critical",
        vendor="juniper",
        pattern=r"root-login deny",
        category="security",
        remediation="配置 'set system root-login deny'",
    ),
]


class ComplianceChecker:
    """合规检查器"""
    
    def __init__(self, rules: Optional[List[ComplianceRule]] = None):
        """初始化检查器
        
        Args:
            rules: 自定义规则列表，如果为None则使用内置规则
        """
        self._rules = rules or BUILTIN_RULES.copy()
        self._compiled_patterns: Dict[str, Pattern] = {}
    
    def add_rule(self, rule: ComplianceRule) -> None:
        """添加规则"""
        self._rules.append(rule)
    
    def add_rules_from_yaml(self, yaml_path: Path) -> int:
        """从YAML文件加载规则
        
        Args:
            yaml_path: YAML文件路径
        
        Returns:
            加载的规则数量
        """
        if not yaml_path.exists():
            return 0
        
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        count = 0
        for rule_data in data.get("rules", []):
            try:
                rule = ComplianceRule(
                    id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    rule_type=RuleType(rule_data["type"]),
                    severity=rule_data.get("severity", "warning"),
                    vendor=rule_data.get("vendor", "all"),
                    pattern=rule_data.get("pattern", ""),
                    category=rule_data.get("category", "custom"),
                    remediation=rule_data.get("remediation", ""),
                    expected_value=rule_data.get("expected_value"),
                    min_value=rule_data.get("min_value"),
                    max_value=rule_data.get("max_value"),
                    allowed_values=rule_data.get("allowed_values", []),
                )
                self._rules.append(rule)
                count += 1
            except Exception:
                pass
        
        return count
    
    def get_rules_for_vendor(self, vendor: str) -> List[ComplianceRule]:
        """获取适用于指定厂商的规则"""
        return [
            r for r in self._rules
            if r.vendor == "all" or r.vendor == vendor or vendor.startswith(r.vendor)
        ]
    
    def _compile_pattern(self, rule_id: str, pattern: str) -> Pattern:
        """编译并缓存正则表达式"""
        if rule_id not in self._compiled_patterns:
            self._compiled_patterns[rule_id] = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
        return self._compiled_patterns[rule_id]
    
    def check_config(
        self,
        config: str,
        device_name: str,
        device_ip: str,
        vendor: str,
    ) -> DeviceComplianceReport:
        """检查设备配置
        
        Args:
            config: 设备配置文本
            device_name: 设备名称
            device_ip: 设备IP
            vendor: 设备厂商
        
        Returns:
            合规检查报告
        """
        report = DeviceComplianceReport(
            device_name=device_name,
            device_ip=device_ip,
            vendor=vendor,
            check_time=datetime.now(),
        )
        
        # 获取适用规则
        rules = self.get_rules_for_vendor(vendor)
        
        for rule in rules:
            result = self._check_rule(rule, config)
            report.results.append(result)
        
        return report
    
    def _check_rule(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """执行单条规则检查"""
        try:
            if rule.rule_type == RuleType.REGEX_MATCH:
                return self._check_regex_match(rule, config)
            elif rule.rule_type == RuleType.REGEX_NO_MATCH:
                return self._check_regex_no_match(rule, config)
            elif rule.rule_type == RuleType.VALUE_EQUAL:
                return self._check_value_equal(rule, config)
            elif rule.rule_type == RuleType.VALUE_RANGE:
                return self._check_value_range(rule, config)
            elif rule.rule_type == RuleType.VALUE_IN_LIST:
                return self._check_value_in_list(rule, config)
            elif rule.rule_type == RuleType.CUSTOM:
                return self._check_custom(rule, config)
            else:
                return ComplianceResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    level=ComplianceLevel.SKIPPED,
                    message=f"不支持的规则类型: {rule.rule_type}",
                )
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.ERROR,
                message=f"检查错误: {e}",
            )
    
    def _check_regex_match(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """正则匹配检查（必须存在）"""
        pattern = self._compile_pattern(rule.id, rule.pattern)
        match = pattern.search(config)
        
        if match:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.COMPLIANT,
                message="配置符合要求",
                actual_value=match.group(0),
                expected_value=rule.pattern,
            )
        else:
            level = (
                ComplianceLevel.NON_COMPLIANT
                if rule.severity == "critical"
                else ComplianceLevel.WARNING
            )
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=level,
                message=f"未找到匹配: {rule.description}",
                actual_value=None,
                expected_value=rule.pattern,
                details={"remediation": rule.remediation},
            )
    
    def _check_regex_no_match(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """正则不匹配检查（必须不存在）"""
        pattern = self._compile_pattern(rule.id, rule.pattern)
        match = pattern.search(config)
        
        if not match:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.COMPLIANT,
                message="配置符合要求（未发现不安全配置）",
                actual_value=None,
                expected_value=f"不应存在: {rule.pattern}",
            )
        else:
            level = (
                ComplianceLevel.NON_COMPLIANT
                if rule.severity == "critical"
                else ComplianceLevel.WARNING
            )
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=level,
                message=f"发现不合规配置: {match.group(0)}",
                actual_value=match.group(0),
                expected_value=f"不应存在: {rule.pattern}",
                details={"remediation": rule.remediation},
            )
    
    def _check_value_equal(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """值相等检查"""
        # 从配置中提取值（使用正则表达式）
        if not rule.pattern:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.SKIPPED,
                message="未配置提取模式",
            )
        
        pattern = self._compile_pattern(rule.id, rule.pattern)
        match = pattern.search(config)
        
        if not match:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.WARNING,
                message="未找到配置项",
                expected_value=rule.expected_value,
            )
        
        actual = match.group(1) if match.groups() else match.group(0)
        
        if str(actual) == str(rule.expected_value):
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.COMPLIANT,
                message="值匹配",
                actual_value=actual,
                expected_value=rule.expected_value,
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.NON_COMPLIANT,
                message=f"值不匹配: 期望 {rule.expected_value}, 实际 {actual}",
                actual_value=actual,
                expected_value=rule.expected_value,
            )
    
    def _check_value_range(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """值范围检查"""
        if not rule.pattern:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.SKIPPED,
                message="未配置提取模式",
            )
        
        pattern = self._compile_pattern(rule.id, rule.pattern)
        match = pattern.search(config)
        
        if not match:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.WARNING,
                message="未找到配置项",
            )
        
        try:
            actual = float(match.group(1) if match.groups() else match.group(0))
        except (ValueError, TypeError):
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.ERROR,
                message="无法解析数值",
            )
        
        in_range = True
        if rule.min_value is not None and actual < rule.min_value:
            in_range = False
        if rule.max_value is not None and actual > rule.max_value:
            in_range = False
        
        if in_range:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.COMPLIANT,
                message="值在允许范围内",
                actual_value=actual,
                expected_value=f"{rule.min_value} - {rule.max_value}",
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.NON_COMPLIANT,
                message=f"值超出范围: {actual} (允许: {rule.min_value}-{rule.max_value})",
                actual_value=actual,
                expected_value=f"{rule.min_value} - {rule.max_value}",
            )
    
    def _check_value_in_list(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """值在列表中检查"""
        if not rule.pattern:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.SKIPPED,
                message="未配置提取模式",
            )
        
        pattern = self._compile_pattern(rule.id, rule.pattern)
        match = pattern.search(config)
        
        if not match:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.WARNING,
                message="未找到配置项",
            )
        
        actual = match.group(1) if match.groups() else match.group(0)
        
        if actual in rule.allowed_values:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.COMPLIANT,
                message="值在允许列表中",
                actual_value=actual,
                expected_value=rule.allowed_values,
            )
        else:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.NON_COMPLIANT,
                message=f"值不在允许列表中: {actual}",
                actual_value=actual,
                expected_value=rule.allowed_values,
            )
    
    def _check_custom(self, rule: ComplianceRule, config: str) -> ComplianceResult:
        """自定义规则检查"""
        if rule.custom_check is None:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.SKIPPED,
                message="自定义检查函数未定义",
            )
        
        try:
            result = rule.custom_check(config)
            if result:
                return ComplianceResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    level=ComplianceLevel.COMPLIANT,
                    message="自定义检查通过",
                )
            else:
                return ComplianceResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    level=ComplianceLevel.NON_COMPLIANT,
                    message="自定义检查未通过",
                    details={"remediation": rule.remediation},
                )
        except Exception as e:
            return ComplianceResult(
                rule_id=rule.id,
                rule_name=rule.name,
                level=ComplianceLevel.ERROR,
                message=f"自定义检查错误: {e}",
            )


class ComplianceService:
    """合规服务
    
    提供合规检查的统一接口
    """
    
    def __init__(self, rules_path: Optional[Path] = None):
        """初始化服务
        
        Args:
            rules_path: 自定义规则YAML文件路径
        """
        self._checker = ComplianceChecker()
        
        # 加载自定义规则
        if rules_path and rules_path.exists():
            self._checker.add_rules_from_yaml(rules_path)
        
        # 尝试加载默认规则文件
        default_rules = Path("config/compliance_rules.yaml")
        if default_rules.exists():
            self._checker.add_rules_from_yaml(default_rules)
    
    def check_device(
        self,
        config: str,
        device_name: str,
        device_ip: str,
        vendor: str,
    ) -> DeviceComplianceReport:
        """检查单个设备
        
        Args:
            config: 设备配置
            device_name: 设备名称
            device_ip: 设备IP
            vendor: 设备厂商
        
        Returns:
            合规报告
        """
        return self._checker.check_config(config, device_name, device_ip, vendor)
    
    def generate_report_text(self, report: DeviceComplianceReport) -> str:
        """生成文本格式报告"""
        lines = []
        
        # 标题
        lines.append("=" * 70)
        lines.append(f"  合规检查报告")
        lines.append("=" * 70)
        lines.append(f"设备名称: {report.device_name}")
        lines.append(f"设备IP:   {report.device_ip}")
        lines.append(f"厂商:     {report.vendor}")
        lines.append(f"检查时间: {report.check_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("-" * 70)
        
        # 摘要
        level_icon = {
            ComplianceLevel.COMPLIANT: "✅",
            ComplianceLevel.WARNING: "⚠️",
            ComplianceLevel.NON_COMPLIANT: "❌",
            ComplianceLevel.ERROR: "🔴",
        }
        
        lines.append(f"整体状态: {level_icon.get(report.overall_level, '❓')} {report.overall_level.value}")
        lines.append(f"合规分数: {report.score:.1f}/100")
        lines.append(f"检查项数: {len(report.results)}")
        lines.append(f"  ✅ 合规: {report.compliant_count}")
        lines.append(f"  ⚠️ 警告: {report.warning_count}")
        lines.append(f"  ❌ 不合规: {report.non_compliant_count}")
        lines.append(f"  🔴 错误: {report.error_count}")
        lines.append("")
        
        # 详细结果
        lines.append("-" * 70)
        lines.append("  详细检查结果")
        lines.append("-" * 70)
        
        # 按级别分组
        non_compliant = [r for r in report.results if r.level == ComplianceLevel.NON_COMPLIANT]
        warnings = [r for r in report.results if r.level == ComplianceLevel.WARNING]
        compliant = [r for r in report.results if r.level == ComplianceLevel.COMPLIANT]
        
        if non_compliant:
            lines.append("\n❌ 不合规项:")
            for r in non_compliant:
                lines.append(f"  [{r.rule_id}] {r.rule_name}")
                lines.append(f"      {r.message}")
                if r.details.get("remediation"):
                    lines.append(f"      修复: {r.details['remediation']}")
        
        if warnings:
            lines.append("\n⚠️ 警告项:")
            for r in warnings:
                lines.append(f"  [{r.rule_id}] {r.rule_name}")
                lines.append(f"      {r.message}")
        
        if compliant:
            lines.append(f"\n✅ 合规项 ({len(compliant)}项):")
            for r in compliant[:5]:  # 只显示前5项
                lines.append(f"  [{r.rule_id}] {r.rule_name}")
            if len(compliant) > 5:
                lines.append(f"  ... 及其他 {len(compliant) - 5} 项")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def export_report_json(self, report: DeviceComplianceReport, output_path: Path) -> None:
        """导出JSON格式报告"""
        data = {
            "device": {
                "name": report.device_name,
                "ip": report.device_ip,
                "vendor": report.vendor,
            },
            "check_time": report.check_time.isoformat(),
            "summary": {
                "overall_level": report.overall_level.value,
                "score": report.score,
                "total_checks": len(report.results),
                "compliant": report.compliant_count,
                "warnings": report.warning_count,
                "non_compliant": report.non_compliant_count,
                "errors": report.error_count,
            },
            "results": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "level": r.level.value,
                    "message": r.message,
                    "actual_value": str(r.actual_value) if r.actual_value else None,
                    "expected_value": str(r.expected_value) if r.expected_value else None,
                    "details": r.details,
                }
                for r in report.results
            ],
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_builtin_rules(self) -> List[ComplianceRule]:
        """获取内置规则列表"""
        return BUILTIN_RULES.copy()
    
    def get_rules_summary(self) -> Dict[str, int]:
        """获取规则统计"""
        rules = self._checker._rules
        summary = {
            "total": len(rules),
            "by_vendor": {},
            "by_category": {},
            "by_severity": {},
        }
        
        for rule in rules:
            # 按厂商
            vendor = rule.vendor
            summary["by_vendor"][vendor] = summary["by_vendor"].get(vendor, 0) + 1
            
            # 按分类
            category = rule.category
            summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
            
            # 按严重程度
            severity = rule.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
        
        return summary
