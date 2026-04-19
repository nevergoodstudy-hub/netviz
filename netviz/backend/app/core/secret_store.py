from __future__ import annotations

import secrets
from base64 import urlsafe_b64encode
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Iterable

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DEFAULT_SECRET_KEY, settings
from app.models.analysis import Settings as DbSettings

SENSITIVE_KEY_MARKERS = ("api_key", "token", "secret", "password")


def is_sensitive_setting_key(key: str) -> bool:
    normalized_key = key.lower()
    return any(marker in normalized_key for marker in SENSITIVE_KEY_MARKERS)


def mask_sensitive_value(value: str | None) -> str | None:
    if not value:
        return value

    return f"{value[:8]}..." if len(value) > 8 else "***"


def _normalize_key_material(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _build_fernet_from_material(key_material: str) -> Fernet:
    digest = sha256(key_material.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


@lru_cache(maxsize=1)
def _generated_install_key() -> str:
    key_file = Path(settings.settings_encryption_key_file)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    if key_file.exists():
        existing = key_file.read_text(encoding="utf-8").strip()
        if existing:
            return existing

    generated = secrets.token_urlsafe(48)
    key_file.write_text(f"{generated}\n", encoding="utf-8")
    try:
        key_file.chmod(0o600)
    except OSError:
        pass
    return generated


def active_settings_key_material() -> str:
    configured_key = _normalize_key_material(settings.settings_encryption_key)
    if configured_key:
        return configured_key

    return _generated_install_key()


def _legacy_key_materials() -> list[str]:
    active_key = active_settings_key_material()
    candidates: list[str] = []

    for candidate in (
        _normalize_key_material(settings.secret_key),
        DEFAULT_SECRET_KEY,
    ):
        if candidate and candidate != active_key and candidate not in candidates:
            candidates.append(candidate)

    return candidates


def _build_fernet() -> Fernet:
    return _build_fernet_from_material(active_settings_key_material())


def encrypt_setting_value(key: str, value: str) -> tuple[str, bool]:
    if not is_sensitive_setting_key(key) or not value:
        return value, False

    encrypted_value = _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    return encrypted_value, True


def decrypt_setting_value(key: str, value: str | None, is_encrypted: bool) -> str | None:
    if not value:
        return value

    if not is_sensitive_setting_key(key) or not is_encrypted:
        return value

    try:
        return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        for key_material in _legacy_key_materials():
            try:
                return _build_fernet_from_material(key_material).decrypt(
                    value.encode("utf-8")
                ).decode("utf-8")
            except InvalidToken:
                continue
        raise


def serialize_setting(record: DbSettings, *, mask_sensitive: bool = False) -> str | None:
    value = decrypt_setting_value(record.key, record.value, record.is_encrypted)
    if mask_sensitive and is_sensitive_setting_key(record.key):
        return mask_sensitive_value(value)
    return value


def build_settings_map(
    records: Iterable[DbSettings],
    *,
    mask_sensitive: bool = False,
) -> dict[str, str | None]:
    return {
        record.key: serialize_setting(record, mask_sensitive=mask_sensitive)
        for record in records
    }


async def rotate_legacy_encrypted_settings(db: AsyncSession) -> int:
    """将旧的共享密钥密文迁移到当前安装级密钥。"""
    legacy_materials = _legacy_key_materials()
    if not legacy_materials:
        return 0

    legacy_fernets = [
        _build_fernet_from_material(key_material)
        for key_material in legacy_materials
    ]
    active_fernet = _build_fernet()
    result = await db.execute(select(DbSettings).where(DbSettings.is_encrypted.is_(True)))
    rotated = 0

    for record in result.scalars():
        if not is_sensitive_setting_key(record.key):
            continue

        try:
            active_fernet.decrypt(record.value.encode("utf-8"))
            continue
        except InvalidToken:
            pass

        for legacy_fernet in legacy_fernets:
            try:
                plaintext = legacy_fernet.decrypt(record.value.encode("utf-8"))
            except InvalidToken:
                continue

            record.value = active_fernet.encrypt(plaintext).decode("utf-8")
            record.is_encrypted = True
            rotated += 1
            break

    return rotated
