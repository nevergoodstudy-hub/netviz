"""
凭证安全存储

使用 Fernet 对称加密存储凭证。
密钥派生自用户密码或环境变量。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from loguru import logger

from netops_toolkit.application.interfaces.services import CredentialStore
from netops_toolkit.domain.entities.credential import Credential, CredentialType
from netops_toolkit.domain.exceptions import CredentialError, EncryptionError


class FernetCredentialStore(CredentialStore):
    """
    基于 Fernet 的凭证存储

    凭证以加密 JSON 形式存储在本地文件中。
    加密密钥通过以下优先级获取:
    1. 环境变量 NETOPS_CREDENTIAL_KEY
    2. 从主密码派生
    3. 基于机器标识自动生成 (仅用于开发)
    """

    DEFAULT_STORE_PATH = Path.home() / ".netops" / "credentials.enc"

    def __init__(
        self,
        store_path: Optional[Path] = None,
        master_key: Optional[str] = None,
    ) -> None:
        self._store_path = store_path or self.DEFAULT_STORE_PATH
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

        self._fernet = self._init_fernet(master_key)
        self._cache: dict[str, dict] = {}
        self._load()

    def store(self, credential: Credential) -> None:
        """安全存储凭证"""
        data = credential.model_dump(mode="json")
        # SecretStr 需要特殊处理
        if credential.password:
            data["password"] = credential.password.get_secret_value()
        if credential.ssh_key_passphrase:
            data["ssh_key_passphrase"] = (
                credential.ssh_key_passphrase.get_secret_value()
            )
        self._cache[credential.name] = data
        self._save()
        logger.debug(f"凭证已存储: {credential.name}")

    def retrieve(self, name: str) -> Optional[Credential]:
        """检索凭证"""
        data = self._cache.get(name)
        if data is None:
            return None
        return Credential(**data)

    def remove(self, name: str) -> bool:
        """删除凭证"""
        if name in self._cache:
            del self._cache[name]
            self._save()
            logger.debug(f"凭证已删除: {name}")
            return True
        return False

    def list_names(self) -> list[str]:
        """列出所有凭证名称"""
        return list(self._cache.keys())

    # ── 加密 ──

    def _init_fernet(self, master_key: Optional[str]) -> object:
        """初始化 Fernet 实例"""
        from cryptography.fernet import Fernet

        key = self._derive_key(master_key)
        return Fernet(key)

    @staticmethod
    def _derive_key(master_key: Optional[str] = None) -> bytes:
        """
        派生 Fernet 密钥

        优先使用环境变量，其次使用传入的 master_key。
        """
        raw = master_key or os.environ.get("NETOPS_CREDENTIAL_KEY", "")

        if not raw:
            # 开发模式: 基于机器信息生成确定性密钥
            import getpass
            import platform

            raw = f"{platform.node()}-{getpass.getuser()}-netops-dev"
            logger.warning(
                "使用自动生成的凭证密钥 (仅适合开发环境)"
            )

        # 使用 SHA-256 + base64 派生 32 字节密钥
        digest = hashlib.sha256(raw.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    def _load(self) -> None:
        """从文件加载并解密凭证"""
        if not self._store_path.exists():
            self._cache = {}
            return

        try:
            encrypted = self._store_path.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            self._cache = json.loads(decrypted.decode())
        except Exception as e:
            logger.warning(f"加载凭证文件失败: {e}")
            self._cache = {}

    def _save(self) -> None:
        """加密并保存凭证到文件"""
        try:
            plain = json.dumps(self._cache, ensure_ascii=False).encode()
            encrypted = self._fernet.encrypt(plain)
            self._store_path.write_bytes(encrypted)
        except Exception as e:
            raise EncryptionError("encryption") from e


__all__ = ["FernetCredentialStore"]
