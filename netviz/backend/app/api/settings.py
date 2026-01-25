"""
NetViz 设置 API 接口
管理用户配置、API密钥等
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import Settings

router = APIRouter()


# ==================== Pydantic 模型 ====================


class SettingsUpdate(BaseModel):
    """设置更新请求"""

    key: str
    value: str


class AIProviderConfig(BaseModel):
    """AI 提供商配置"""

    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class AIProviderStatus(BaseModel):
    """AI 提供商状态"""

    provider: str
    configured: bool
    model: str
    status: str


# ==================== 设置接口 ====================


@router.get("/")
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
):
    """获取所有设置"""
    result = await db.execute(select(Settings))
    settings_list = result.scalars().all()

    # 将设置转换为字典，隐藏敏感信息
    settings_dict = {}
    for s in settings_list:
        value = s.value
        # 隐藏 API 密钥
        if "api_key" in s.key.lower() and value:
            value = value[:8] + "..." if len(value) > 8 else "***"
        settings_dict[s.key] = value

    return settings_dict


@router.put("/")
async def update_setting(
    update: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新设置"""
    result = await db.execute(select(Settings).where(Settings.key == update.key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = update.value
    else:
        setting = Settings(key=update.key, value=update.value)
        db.add(setting)

    await db.commit()
    return {"message": "设置已更新", "key": update.key}


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """删除设置"""
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(status_code=404, detail="设置不存在")

    await db.delete(setting)
    await db.commit()

    return {"message": "设置已删除"}


# ==================== AI 提供商接口 ====================


@router.get("/ai-providers", response_model=list[AIProviderStatus])
async def get_ai_providers(
    db: AsyncSession = Depends(get_db),
):
    """获取 AI 提供商状态"""
    providers = []

    # 从数据库获取配置
    result = await db.execute(select(Settings))
    db_settings = {s.key: s.value for s in result.scalars().all()}

    # OpenAI
    openai_key = db_settings.get("openai_api_key") or settings.openai_api_key
    providers.append(
        AIProviderStatus(
            provider="openai",
            configured=bool(openai_key),
            model=db_settings.get("openai_model") or settings.openai_model,
            status="configured" if openai_key else "not_configured",
        )
    )

    # Anthropic
    anthropic_key = db_settings.get("anthropic_api_key") or settings.anthropic_api_key
    providers.append(
        AIProviderStatus(
            provider="anthropic",
            configured=bool(anthropic_key),
            model=db_settings.get("anthropic_model") or settings.anthropic_model,
            status="configured" if anthropic_key else "not_configured",
        )
    )

    # Ollama
    ollama_url = db_settings.get("ollama_base_url") or settings.ollama_base_url
    providers.append(
        AIProviderStatus(
            provider="ollama",
            configured=True,  # Ollama 不需要 API 密钥
            model=db_settings.get("ollama_model") or settings.ollama_model,
            status="local",
        )
    )

    # DeepSeek
    deepseek_key = db_settings.get("deepseek_api_key") or settings.deepseek_api_key
    providers.append(
        AIProviderStatus(
            provider="deepseek",
            configured=bool(deepseek_key),
            model=db_settings.get("deepseek_model") or settings.deepseek_model,
            status="configured" if deepseek_key else "not_configured",
        )
    )

    return providers


@router.post("/ai-providers")
async def configure_ai_provider(
    config: AIProviderConfig,
    db: AsyncSession = Depends(get_db),
):
    """配置 AI 提供商"""
    updates = []

    if config.provider == "openai":
        if config.api_key:
            updates.append(("openai_api_key", config.api_key))
        if config.base_url:
            updates.append(("openai_base_url", config.base_url))
        if config.model:
            updates.append(("openai_model", config.model))

    elif config.provider == "anthropic":
        if config.api_key:
            updates.append(("anthropic_api_key", config.api_key))
        if config.model:
            updates.append(("anthropic_model", config.model))

    elif config.provider == "ollama":
        if config.base_url:
            updates.append(("ollama_base_url", config.base_url))
        if config.model:
            updates.append(("ollama_model", config.model))

    elif config.provider == "deepseek":
        if config.api_key:
            updates.append(("deepseek_api_key", config.api_key))
        if config.base_url:
            updates.append(("deepseek_base_url", config.base_url))
        if config.model:
            updates.append(("deepseek_model", config.model))

    else:
        raise HTTPException(status_code=400, detail="不支持的 AI 提供商")

    # 保存到数据库
    for key, value in updates:
        result = await db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
        else:
            db.add(Settings(key=key, value=value))

    await db.commit()
    return {"message": "AI 提供商配置已更新"}


@router.post("/ai-providers/{provider}/test")
async def test_ai_provider(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """测试 AI 提供商连接"""
    # 获取配置
    result = await db.execute(select(Settings))
    db_settings = {s.key: s.value for s in result.scalars().all()}

    try:
        if provider == "openai":
            api_key = db_settings.get("openai_api_key") or settings.openai_api_key
            if not api_key:
                raise HTTPException(status_code=400, detail="未配置 OpenAI API Key")

            base_url = db_settings.get("openai_base_url") or settings.openai_base_url or "https://api.openai.com/v1"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "OpenAI 连接成功"}
                else:
                    return {"status": "error", "message": f"OpenAI 连接失败: {response.status_code}"}

        elif provider == "anthropic":
            api_key = db_settings.get("anthropic_api_key") or settings.anthropic_api_key
            if not api_key:
                raise HTTPException(status_code=400, detail="未配置 Anthropic API Key")

            # Anthropic 没有简单的健康检查端点，发送最小请求
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
                    return {"status": "success", "message": "Anthropic 连接成功"}
                else:
                    return {"status": "error", "message": f"Anthropic 连接失败: {response.status_code}"}

        elif provider == "ollama":
            base_url = db_settings.get("ollama_base_url") or settings.ollama_base_url

            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(f"{base_url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return {
                            "status": "success",
                            "message": "Ollama 连接成功",
                            "available_models": models,
                        }
                    else:
                        return {"status": "error", "message": f"Ollama 连接失败: {response.status_code}"}
                except httpx.ConnectError:
                    return {"status": "error", "message": "无法连接到 Ollama 服务"}

        elif provider == "deepseek":
            api_key = db_settings.get("deepseek_api_key") or settings.deepseek_api_key
            if not api_key:
                raise HTTPException(status_code=400, detail="未配置 DeepSeek API Key")

            base_url = db_settings.get("deepseek_base_url") or settings.deepseek_base_url

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "DeepSeek 连接成功"}
                else:
                    return {"status": "error", "message": f"DeepSeek 连接失败: {response.status_code}"}

        else:
            raise HTTPException(status_code=400, detail="不支持的 AI 提供商")

    except httpx.TimeoutException:
        return {"status": "error", "message": "连接超时"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== 系统信息接口 ====================


@router.get("/system-info")
async def get_system_info():
    """获取系统信息"""
    import platform
    import sys

    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "app_name": settings.app_name,
        "debug_mode": settings.debug,
    }
