"""Administrative settings endpoints for NetViz."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_access import require_admin_access
from app.core.config import settings
from app.core.database import get_db
from app.core.provider_urls import normalize_ai_base_url
from app.core.secret_store import build_settings_map, encrypt_setting_value
from app.models.analysis import Settings

router = APIRouter()
BASE_URL_SETTING_TO_PROVIDER = {
    "openai_base_url": "openai",
    "ollama_base_url": "ollama",
    "deepseek_base_url": "deepseek",
}


class SettingsUpdate(BaseModel):
    key: str
    value: str


class AIProviderConfig(BaseModel):
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class AIProviderStatus(BaseModel):
    provider: str
    configured: bool
    model: str
    status: str


@router.get("/")
async def get_all_settings(
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settings))
    return build_settings_map(result.scalars().all(), mask_sensitive=True)


@router.put("/")
async def update_setting(
    update: SettingsUpdate,
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settings).where(Settings.key == update.key))
    setting = result.scalar_one_or_none()
    value = update.value
    if update.key in BASE_URL_SETTING_TO_PROVIDER:
        provider = BASE_URL_SETTING_TO_PROVIDER[update.key]
        try:
            value = normalize_ai_base_url(
                provider,
                update.value,
                allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        stored_value, is_encrypted = encrypt_setting_value(update.key, value)
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"Unable to secure setting storage: {exc}") from exc

    if setting:
        setting.value = stored_value
        setting.is_encrypted = is_encrypted
    else:
        db.add(Settings(key=update.key, value=stored_value, is_encrypted=is_encrypted))

    await db.commit()
    return {"message": "Settings updated", "key": update.key}


@router.delete("/{key}")
async def delete_setting(
    key: str,
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    await db.delete(setting)
    await db.commit()

    return {"message": "Setting deleted"}


@router.get("/ai-providers", response_model=list[AIProviderStatus])
async def get_ai_providers(
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settings))
    db_settings = build_settings_map(result.scalars().all())

    openai_key = db_settings.get("openai_api_key") or settings.openai_api_key
    anthropic_key = db_settings.get("anthropic_api_key") or settings.anthropic_api_key
    deepseek_key = db_settings.get("deepseek_api_key") or settings.deepseek_api_key

    return [
        AIProviderStatus(
            provider="openai",
            configured=bool(openai_key),
            model=(db_settings.get("openai_model") or settings.openai_model),
            status="configured" if openai_key else "not_configured",
        ),
        AIProviderStatus(
            provider="anthropic",
            configured=bool(anthropic_key),
            model=(db_settings.get("anthropic_model") or settings.anthropic_model),
            status="configured" if anthropic_key else "not_configured",
        ),
        AIProviderStatus(
            provider="ollama",
            configured=True,
            model=(db_settings.get("ollama_model") or settings.ollama_model),
            status="local",
        ),
        AIProviderStatus(
            provider="deepseek",
            configured=bool(deepseek_key),
            model=(db_settings.get("deepseek_model") or settings.deepseek_model),
            status="configured" if deepseek_key else "not_configured",
        ),
    ]


@router.post("/ai-providers")
async def configure_ai_provider(
    config: AIProviderConfig,
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db),
):
    updates: list[tuple[str, str]] = []

    if config.provider == "openai":
        if config.api_key:
            updates.append(("openai_api_key", config.api_key))
        if config.base_url:
            try:
                normalized_base_url = normalize_ai_base_url(
                    "openai",
                    config.base_url,
                    allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            updates.append(("openai_base_url", normalized_base_url))
        if config.model:
            updates.append(("openai_model", config.model))
    elif config.provider == "anthropic":
        if config.api_key:
            updates.append(("anthropic_api_key", config.api_key))
        if config.model:
            updates.append(("anthropic_model", config.model))
    elif config.provider == "ollama":
        if config.base_url:
            try:
                normalized_base_url = normalize_ai_base_url("ollama", config.base_url)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            updates.append(("ollama_base_url", normalized_base_url))
        if config.model:
            updates.append(("ollama_model", config.model))
    elif config.provider == "deepseek":
        if config.api_key:
            updates.append(("deepseek_api_key", config.api_key))
        if config.base_url:
            try:
                normalized_base_url = normalize_ai_base_url(
                    "deepseek",
                    config.base_url,
                    allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            updates.append(("deepseek_base_url", normalized_base_url))
        if config.model:
            updates.append(("deepseek_model", config.model))
    else:
        raise HTTPException(status_code=400, detail="Unsupported AI provider")

    for key, value in updates:
        result = await db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        try:
            stored_value, is_encrypted = encrypt_setting_value(key, value)
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Unable to secure setting storage: {exc}",
            ) from exc

        if setting:
            setting.value = stored_value
            setting.is_encrypted = is_encrypted
        else:
            db.add(Settings(key=key, value=stored_value, is_encrypted=is_encrypted))

    await db.commit()
    return {"message": "AI provider configuration updated"}


@router.post("/ai-providers/{provider}/test")
async def test_ai_provider(
    provider: str,
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Settings))
    db_settings = build_settings_map(result.scalars().all())

    try:
        if provider == "openai":
            api_key = db_settings.get("openai_api_key") or settings.openai_api_key
            if not api_key:
                raise HTTPException(status_code=400, detail="OpenAI API key is not configured")

            base_url = (
                db_settings.get("openai_base_url")
                or settings.openai_base_url
            )
            base_url = normalize_ai_base_url(
                "openai",
                base_url,
                allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "OpenAI connection succeeded"}
                return {
                    "status": "error",
                    "message": f"OpenAI connection failed: {response.status_code}",
                }

        if provider == "anthropic":
            api_key = db_settings.get("anthropic_api_key") or settings.anthropic_api_key
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="Anthropic API key is not configured",
                )

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": db_settings.get("anthropic_model") or settings.anthropic_model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}],
                    },
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "Anthropic connection succeeded"}
                return {
                    "status": "error",
                    "message": f"Anthropic connection failed: {response.status_code}",
                }

        if provider == "ollama":
            base_url = normalize_ai_base_url(
                "ollama",
                db_settings.get("ollama_base_url") or settings.ollama_base_url,
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(f"{base_url}/api/tags")
                except httpx.ConnectError:
                    return {"status": "error", "message": "Unable to reach the Ollama service"}

                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return {
                        "status": "success",
                        "message": "Ollama connection succeeded",
                        "available_models": models,
                    }

                return {
                    "status": "error",
                    "message": f"Ollama connection failed: {response.status_code}",
                }

        if provider == "deepseek":
            api_key = db_settings.get("deepseek_api_key") or settings.deepseek_api_key
            if not api_key:
                raise HTTPException(status_code=400, detail="DeepSeek API key is not configured")

            base_url = normalize_ai_base_url(
                "deepseek",
                db_settings.get("deepseek_base_url") or settings.deepseek_base_url,
                allow_unsafe_cloud_urls=settings.allow_unsafe_ai_base_urls,
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "DeepSeek connection succeeded"}
                return {
                    "status": "error",
                    "message": f"DeepSeek connection failed: {response.status_code}",
                }

        raise HTTPException(status_code=400, detail="Unsupported AI provider")
    except httpx.TimeoutException:
        return {"status": "error", "message": "Connection timed out"}
    except HTTPException:
        raise
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.get("/system-info")
async def get_system_info(_: None = Depends(require_admin_access)):
    import platform
    import sys

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "app_name": settings.app_name,
        "debug_mode": settings.debug,
    }
