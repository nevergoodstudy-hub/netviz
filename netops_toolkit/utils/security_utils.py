"""
安全工具模块

提供密码加密、凭证管理等安全相关功能。
"""

import base64
import hashlib
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)

# 默认密钥文件位置
DEFAULT_KEY_FILE = Path.home() / ".netops" / ".key"


def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple:
    """
    从密码生成加密密钥
    
    Args:
        password: 用户密码
        salt: 盐值 (None表示生成新盐值)
        
    Returns:
        (key, salt) 元组
    """
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def generate_encryption_key() -> bytes:
    """
    生成随机加密密钥
    
    Returns:
        Fernet密钥
    """
    return Fernet.generate_key()


def save_encryption_key(key: bytes, key_file: Path = DEFAULT_KEY_FILE) -> bool:
    """
    保存加密密钥到文件
    
    Args:
        key: 加密密钥
        key_file: 密钥文件路径
        
    Returns:
        True表示成功
    """
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置文件权限为仅用户可读写 (仅Unix系统)
        with open(key_file, "wb") as f:
            f.write(key)
        
        # 尝试设置文件权限 (仅Unix)
        try:
            os.chmod(key_file, 0o600)
        except (OSError, AttributeError):
            pass  # Windows系统忽略
        
        logger.info(f"加密密钥已保存: {key_file}")
        return True
    except Exception as e:
        logger.error(f"保存密钥失败: {e}")
        return False


def load_encryption_key(key_file: Path = DEFAULT_KEY_FILE) -> Optional[bytes]:
    """
    从文件加载加密密钥
    
    Args:
        key_file: 密钥文件路径
        
    Returns:
        加密密钥, 不存在返回None
    """
    if not key_file.exists():
        return None
    
    try:
        with open(key_file, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"加载密钥失败: {e}")
        return None


def get_or_create_key(key_file: Path = DEFAULT_KEY_FILE) -> bytes:
    """
    获取或创建加密密钥
    
    Args:
        key_file: 密钥文件路径
        
    Returns:
        加密密钥
    """
    key = load_encryption_key(key_file)
    
    if key is None:
        key = generate_encryption_key()
        save_encryption_key(key, key_file)
        logger.info("已生成新的加密密钥")
    
    return key


def encrypt_string(plaintext: str, key: Optional[bytes] = None) -> str:
    """
    加密字符串
    
    Args:
        plaintext: 明文字符串
        key: 加密密钥 (None表示使用默认密钥)
        
    Returns:
        加密后的base64字符串
    """
    if key is None:
        key = get_or_create_key()
    
    fernet = Fernet(key)
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode()


def decrypt_string(ciphertext: str, key: Optional[bytes] = None) -> Optional[str]:
    """
    解密字符串
    
    Args:
        ciphertext: 加密后的base64字符串
        key: 加密密钥 (None表示使用默认密钥)
        
    Returns:
        解密后的明文字符串, 失败返回None
    """
    if key is None:
        key = get_or_create_key()
    
    try:
        fernet = Fernet(key)
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"解密失败: {e}")
        return None


def hash_password(password: str) -> str:
    """
    对密码进行哈希 (单向)
    
    使用 PBKDF2-SHA256 进行密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        哈希后的字符串
    """
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        iterations=100000,
    )
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """
    验证密码
    
    Args:
        password: 明文密码
        hashed: 哈希后的密码字符串
        
    Returns:
        True表示匹配
    """
    try:
        salt, expected_hash = hashed.split("$")
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            iterations=100000,
        )
        return pwd_hash.hex() == expected_hash
    except Exception:
        return False


class CredentialManager:
    """凭证管理器类"""
    
    def __init__(self, secrets_file: Optional[Path] = None):
        """
        初始化凭证管理器
        
        Args:
            secrets_file: 密钥文件路径
        """
        self.secrets_file = secrets_file or Path("config") / "secrets.yaml"
        self._credentials: Dict[str, Dict[str, str]] = {}
        self._key = get_or_create_key()
    
    def load(self) -> bool:
        """
        加载凭证文件
        
        Returns:
            True表示成功
        """
        if not self.secrets_file.exists():
            logger.debug(f"凭证文件不存在: {self.secrets_file}")
            return False
        
        try:
            with open(self.secrets_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            self._credentials = data.get("credentials", {})
            logger.info(f"已加载 {len(self._credentials)} 个凭证")
            return True
        except Exception as e:
            logger.error(f"加载凭证文件失败: {e}")
            return False
    
    def get_credential(self, name: str, decrypt: bool = True) -> Optional[Dict[str, str]]:
        """
        获取凭证
        
        Args:
            name: 凭证名称
            decrypt: 是否解密密码
            
        Returns:
            凭证字典 {username, password}, 不存在返回None
        """
        cred = self._credentials.get(name)
        
        if cred is None:
            return None
        
        result = {
            "username": cred.get("username", ""),
            "password": cred.get("password", ""),
        }
        
        # 尝试解密密码
        if decrypt and result["password"].startswith("ENC:"):
            encrypted_pwd = result["password"][4:]
            decrypted = decrypt_string(encrypted_pwd, self._key)
            if decrypted:
                result["password"] = decrypted
            else:
                logger.warning(f"凭证 {name} 的密码解密失败")
        
        return result
    
    def set_credential(
        self,
        name: str,
        username: str,
        password: str,
        encrypt: bool = True,
    ) -> None:
        """
        设置凭证
        
        Args:
            name: 凭证名称
            username: 用户名
            password: 密码
            encrypt: 是否加密密码
        """
        if encrypt:
            encrypted_pwd = encrypt_string(password, self._key)
            password = f"ENC:{encrypted_pwd}"
        
        self._credentials[name] = {
            "username": username,
            "password": password,
        }
    
    def save(self) -> bool:
        """
        保存凭证到文件
        
        Returns:
            True表示成功
        """
        try:
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {"credentials": self._credentials}
            
            with open(self.secrets_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"凭证已保存: {self.secrets_file}")
            return True
        except Exception as e:
            logger.error(f"保存凭证文件失败: {e}")
            return False
    
    def list_credentials(self) -> list:
        """
        列出所有凭证名称
        
        Returns:
            凭证名称列表
        """
        return list(self._credentials.keys())


def mask_password(password: str, visible_chars: int = 2) -> str:
    """
    掩码显示密码
    
    Args:
        password: 密码字符串
        visible_chars: 显示的字符数
        
    Returns:
        掩码后的字符串
    """
    if len(password) <= visible_chars * 2:
        return "*" * len(password)
    
    return password[:visible_chars] + "*" * (len(password) - visible_chars * 2) + password[-visible_chars:]


__all__ = [
    "generate_key_from_password",
    "generate_encryption_key",
    "save_encryption_key",
    "load_encryption_key",
    "get_or_create_key",
    "encrypt_string",
    "decrypt_string",
    "hash_password",
    "verify_password",
    "CredentialManager",
    "mask_password",
]
