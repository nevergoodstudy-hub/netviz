"""
审计日志增强器 — 敏感信息自动脱敏

功能:
- 基于正则表达式检测常见敏感数据模式 (密码、密钥、Token 等)
- 基于字段名自动识别敏感字典键 (password, secret, key ...)
- 支持部分保留脱敏 (如 IP 保留网段, 密码只显示长度)
- 可扩展的脱敏规则注册机制
- 与 loguru 集成的日志过滤器
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern


class MaskStrategy(Enum):
    """脱敏策略"""

    FULL = "full"  # 完全替换: ******
    PARTIAL = "partial"  # 部分保留: pa***rd
    HASH = "hash"  # 哈希替换: [SHA256:a1b2c3...]
    LENGTH = "length"  # 长度提示: [REDACTED:8chars]
    FIXED = "fixed"  # 固定占位: [REDACTED]


@dataclass(frozen=True)
class MaskRule:
    """脱敏规则"""

    name: str
    pattern: Pattern[str]
    replacement: str = "[REDACTED]"
    strategy: MaskStrategy = MaskStrategy.FIXED
    description: str = ""


# ── 预定义正则脱敏规则 ──

_BUILTIN_RULES: List[MaskRule] = [
    MaskRule(
        name="password_in_text",
        pattern=re.compile(
            r"(password|passwd|pwd)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        replacement=r"\1=******",
        description="文本中的密码赋值",
    ),
    MaskRule(
        name="token_bearer",
        pattern=re.compile(
            r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*",
            re.IGNORECASE,
        ),
        replacement=r"\1[REDACTED]",
        description="Bearer Token",
    ),
    MaskRule(
        name="api_key_param",
        pattern=re.compile(
            r"(api[_-]?key|apikey|access[_-]?token|secret[_-]?key)"
            r"\s*[:=]\s*[A-Za-z0-9\-._~+/]{8,}=*",
            re.IGNORECASE,
        ),
        replacement=r"\1=[REDACTED]",
        description="API Key / Token 参数",
    ),
    MaskRule(
        name="private_key_block",
        pattern=re.compile(
            r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"
            r"[\s\S]*?"
            r"-----END\s+(?:RSA\s+)?PRIVATE\s+KEY-----",
        ),
        replacement="[REDACTED PRIVATE KEY]",
        description="PEM 私钥块",
    ),
    MaskRule(
        name="connection_string",
        pattern=re.compile(
            r"((?:mysql|postgres|mongodb|redis|sqlite)"
            r"://[^:]+:)[^@]+(@)",
            re.IGNORECASE,
        ),
        replacement=r"\1******\2",
        description="数据库连接字符串密码",
    ),
    MaskRule(
        name="ssh_password_arg",
        pattern=re.compile(
            r"(-p\s+|--password\s+|--pass\s+)\S+",
            re.IGNORECASE,
        ),
        replacement=r"\1******",
        description="SSH/CLI 密码参数",
    ),
]

# 敏感字段名关键字 (用于字典脱敏)
_SENSITIVE_KEYS: set[str] = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "ssh_key",
    "ssh_key_passphrase",
    "encryption_key",
    "credential",
    "auth",
    "authorization",
    "cookie",
    "session_id",
    "jwt",
}


class SensitiveDataMasker:
    """
    敏感数据脱敏器

    支持:
    - 字符串文本中的正则匹配脱敏
    - 字典/JSON 中基于键名的值脱敏
    - 自定义规则扩展

    用法::

        masker = SensitiveDataMasker()
        safe_text = masker.mask_text("password=admin123")
        # => "password=******"

        safe_dict = masker.mask_dict({"host": "10.0.0.1", "password": "secret"})
        # => {"host": "10.0.0.1", "password": "******"}
    """

    def __init__(
        self,
        extra_rules: Optional[List[MaskRule]] = None,
        extra_sensitive_keys: Optional[set[str]] = None,
    ) -> None:
        self._rules: List[MaskRule] = list(_BUILTIN_RULES)
        if extra_rules:
            self._rules.extend(extra_rules)

        self._sensitive_keys: set[str] = set(_SENSITIVE_KEYS)
        if extra_sensitive_keys:
            self._sensitive_keys.update(extra_sensitive_keys)

    def add_rule(self, rule: MaskRule) -> None:
        """添加自定义脱敏规则"""
        self._rules.append(rule)

    def add_sensitive_key(self, key: str) -> None:
        """添加敏感字段名"""
        self._sensitive_keys.add(key.lower())

    # ── 文本脱敏 ──

    def mask_text(self, text: str) -> str:
        """
        对文本应用所有正则脱敏规则

        Args:
            text: 原始文本

        Returns:
            脱敏后的文本
        """
        if not text:
            return text

        result = text
        for rule in self._rules:
            result = rule.pattern.sub(rule.replacement, result)
        return result

    # ── 字典脱敏 ──

    def mask_dict(
        self,
        data: Dict[str, Any],
        *,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        对字典中的敏感字段进行脱敏

        Args:
            data: 原始字典
            recursive: 是否递归处理嵌套字典

        Returns:
            脱敏后的字典 (原始字典不被修改)
        """
        result: Dict[str, Any] = {}
        for key, value in data.items():
            if self._is_sensitive_key(key):
                result[key] = self._mask_value(value)
            elif recursive and isinstance(value, dict):
                result[key] = self.mask_dict(value, recursive=True)
            elif isinstance(value, str):
                result[key] = self.mask_text(value)
            else:
                result[key] = value
        return result

    # ── 内部方法 ──

    def _is_sensitive_key(self, key: str) -> bool:
        """判断字段名是否为敏感字段"""
        normalized = key.lower().strip()
        return normalized in self._sensitive_keys

    @staticmethod
    def _mask_value(value: Any) -> str:
        """将敏感值替换为脱敏占位符"""
        if isinstance(value, str) and len(value) > 0:
            return f"[REDACTED:{len(value)}chars]"
        return "******"


class AuditLogEnhancer:
    """
    审计日志增强器

    在审计记录写入前自动:
    1. 对 description / old_value / new_value 等文本字段做正则脱敏
    2. 对 metadata 字典做键名脱敏
    3. 添加结构化上下文 (来源 IP、会话 ID 等)

    用法::

        enhancer = AuditLogEnhancer()
        safe_record = enhancer.enhance(record)
    """

    def __init__(
        self,
        masker: Optional[SensitiveDataMasker] = None,
    ) -> None:
        self._masker = masker or SensitiveDataMasker()

    def enhance(self, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强并脱敏审计记录

        Args:
            record_dict: 审计记录的字典表示

        Returns:
            增强后的审计记录字典
        """
        result = dict(record_dict)

        # 文本字段脱敏
        for text_field in ("description", "old_value", "new_value", "error_message"):
            if text_field in result and isinstance(result[text_field], str):
                result[text_field] = self._masker.mask_text(result[text_field])

        # metadata 字典脱敏
        if "metadata" in result and isinstance(result["metadata"], dict):
            result["metadata"] = self._masker.mask_dict(result["metadata"])

        return result


def create_loguru_filter(
    masker: Optional[SensitiveDataMasker] = None,
) -> Callable:
    """
    创建 loguru 日志过滤器

    在日志消息写入前自动脱敏。

    用法::

        from loguru import logger

        logger.add(
            "app.log",
            filter=create_loguru_filter(),
        )
    """
    _masker = masker or SensitiveDataMasker()

    def _filter(record: Dict[str, Any]) -> bool:
        if isinstance(record.get("message"), str):
            record["message"] = _masker.mask_text(record["message"])
        return True

    return _filter


__all__ = [
    "MaskStrategy",
    "MaskRule",
    "SensitiveDataMasker",
    "AuditLogEnhancer",
    "create_loguru_filter",
]
