"""
凭证领域值对象

安全的凭证表示，敏感字段使用 SecretStr 防止意外泄露。
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, SecretStr


class CredentialType(str, Enum):
    """凭证类型"""

    PASSWORD = "password"
    SSH_KEY = "ssh_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"


class Credential(BaseModel):
    """
    凭证值对象

    敏感字段使用 SecretStr，repr/str 时自动隐藏。
    """

    name: str = Field(..., min_length=1, description="凭证标识名称")
    username: str = Field(default="", description="用户名")
    password: Optional[SecretStr] = Field(default=None, description="密码")
    ssh_key_path: Optional[str] = Field(default=None, description="SSH 密钥路径")
    ssh_key_passphrase: Optional[SecretStr] = Field(default=None, description="SSH 密钥密码")
    credential_type: CredentialType = Field(
        default=CredentialType.PASSWORD,
        description="凭证类型",
    )
    description: str = Field(default="", description="描述")

    def get_password_value(self) -> str:
        """安全获取密码明文值"""
        if self.password is None:
            return ""
        return self.password.get_secret_value()

    def has_ssh_key(self) -> bool:
        """是否配置了 SSH 密钥"""
        return self.ssh_key_path is not None and self.ssh_key_path != ""


__all__ = ["Credential", "CredentialType"]
