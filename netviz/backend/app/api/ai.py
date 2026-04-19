"""
NetViz AI 分析 API
支持多个 AI 提供商（OpenAI、Anthropic、Ollama）
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.secret_store import build_settings_map
from app.models.analysis import AIConversation, AIMessage, Settings
from app.models.pcap import Connection, Packet, PcapFile
from app.services.ai.ai_service import AIService, get_ai_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Schemas ==============

class ChatRequest(BaseModel):
    """聊天请求"""

    message: str
    pcap_id: int | None = None
    conversation_id: int | None = None
    provider: Literal["openai", "anthropic", "ollama", "deepseek"] | None = None


class ChatResponse(BaseModel):
    """聊天响应"""

    message: str
    conversation_id: int
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class SummaryRequest(BaseModel):
    """摘要请求"""

    pcap_id: int
    provider: Literal["openai", "anthropic", "ollama", "deepseek"] | None = None


class AnalysisRequest(BaseModel):
    """分析请求"""

    pcap_id: int
    query: str | None = None
    analysis_type: str | None = None
    provider: Literal["openai", "anthropic", "ollama", "deepseek"] | None = None


class ConversationResponse(BaseModel):
    """对话响应"""

    id: int
    title: str
    provider: str
    model: str
    pcap_file_id: int | None
    message_count: int


class MessageResponse(BaseModel):
    """消息响应"""

    id: int
    role: str
    content: str
    created_at: str


async def get_ai_runtime_settings(db: AsyncSession) -> dict[str, str | None]:
    """获取 AI 运行时设置（数据库优先，已解密）"""
    result = await db.execute(select(Settings))
    return build_settings_map(result.scalars().all())


# ============== Helper Functions ==============

async def get_pcap_context(pcap_id: int, db: AsyncSession) -> str:
    """获取 PCAP 文件的上下文信息"""
    pcap_file = await db.get(PcapFile, pcap_id)
    if not pcap_file:
        raise HTTPException(status_code=404, detail="PCAP 文件不存在")

    # 获取基本统计
    context = f"""
## PCAP 文件信息
- 文件名: {pcap_file.original_filename}
- 总包数: {pcap_file.total_packets}
- 总字节数: {pcap_file.total_bytes}
- 开始时间: {pcap_file.start_time}
- 结束时间: {pcap_file.end_time}
- 持续时间: {pcap_file.duration_seconds:.2f} 秒
"""

    # 获取协议统计
    from sqlalchemy import func

    protocol_result = await db.execute(
        select(Packet.protocol, func.count(Packet.id))
        .where(Packet.pcap_file_id == pcap_id)
        .where(Packet.protocol.isnot(None))
        .group_by(Packet.protocol)
    )
    protocols = protocol_result.all()

    if protocols:
        context += "\n## 协议分布\n"
        for proto, count in protocols:
            context += f"- {proto}: {count} 包\n"

    # 获取连接统计
    conn_result = await db.execute(
        select(Connection)
        .where(Connection.pcap_file_id == pcap_id)
        .order_by(Connection.byte_count.desc())
        .limit(10)
    )
    connections = conn_result.scalars().all()

    if connections:
        context += "\n## Top 10 连接 (按流量)\n"
        for conn in connections:
            context += f"- {conn.src_ip}:{conn.src_port} -> {conn.dst_ip}:{conn.dst_port} ({conn.protocol}): {conn.byte_count} 字节, {conn.packet_count} 包\n"

    return context


# ============== API Endpoints ==============

@router.get("/providers")
async def get_available_providers(db: AsyncSession = Depends(get_db)):
    """获取可用的 AI 提供商"""
    db_settings = await get_ai_runtime_settings(db)
    openai_key = db_settings.get("openai_api_key") or settings.openai_api_key
    anthropic_key = db_settings.get("anthropic_api_key") or settings.anthropic_api_key
    deepseek_key = db_settings.get("deepseek_api_key") or settings.deepseek_api_key

    return {
        "providers": [
            {
                "id": "openai",
                "name": "OpenAI",
                "available": bool(openai_key),
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "available": bool(anthropic_key),
                "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            },
            {
                "id": "ollama",
                "name": "Ollama (本地)",
                "available": True,
                "models": ["llama3.2", "mistral", "codellama"],
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "available": bool(deepseek_key),
                "models": ["deepseek-chat", "deepseek-reasoner"],
            },
        ],
        "default": db_settings.get("default_ai_provider") or settings.default_ai_provider,
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """与 AI 进行对话"""
    db_settings = await get_ai_runtime_settings(db)
    provider = request.provider or db_settings.get("default_ai_provider") or settings.default_ai_provider

    if provider == "none":
        raise HTTPException(status_code=400, detail="未配置 AI 提供商，请先在设置中配置 API Key")

    try:
        ai_service = get_ai_service(provider, db_settings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 获取或创建对话
    conversation: AIConversation | None = None
    if request.conversation_id:
        conversation = await db.get(AIConversation, request.conversation_id)

    if not conversation:
        conversation = AIConversation(
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
            provider=provider,
            model=ai_service.model,
            pcap_file_id=request.pcap_id,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # 构建消息历史
    messages: list[dict] = []

    # 添加系统提示
    system_prompt = """你是 NetViz 网络流量分析助手，专门帮助用户分析 PCAP 文件中的网络流量。
你的能力包括：
1. 解释网络协议和流量模式
2. 识别可疑的网络活动
3. 提供安全分析建议
4. 解答网络安全相关问题

请用中文回答，保持专业但易于理解。"""

    messages.append({"role": "system", "content": system_prompt})

    # 如果关联了 PCAP 文件，添加上下文
    if request.pcap_id:
        context = await get_pcap_context(request.pcap_id, db)
        messages.append(
            {"role": "system", "content": f"当前分析的 PCAP 文件上下文：\n{context}"}
        )

    # 添加历史消息
    history_result = await db.execute(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at)
        .limit(20)  # 限制历史消息数量
    )
    history = history_result.scalars().all()

    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # 添加用户消息
    messages.append({"role": "user", "content": request.message})

    # 保存用户消息
    user_message = AIMessage(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    # 调用 AI 服务
    try:
        response = await ai_service.chat(messages)
    except Exception as e:
        logger.error(f"AI service error: {e}")
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")

    # 保存助手消息
    assistant_message = AIMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response["content"],
        prompt_tokens=response.get("prompt_tokens", 0),
        completion_tokens=response.get("completion_tokens", 0),
    )
    db.add(assistant_message)
    await db.commit()

    return ChatResponse(
        message=response["content"],
        conversation_id=conversation.id,
        provider=provider,
        model=ai_service.model,
        prompt_tokens=response.get("prompt_tokens", 0),
        completion_tokens=response.get("completion_tokens", 0),
    )


@router.post("/summary")
async def generate_summary(
    request: SummaryRequest,
    db: AsyncSession = Depends(get_db),
):
    """生成 PCAP 文件分析摘要"""
    db_settings = await get_ai_runtime_settings(db)
    provider = request.provider or db_settings.get("default_ai_provider") or settings.default_ai_provider

    if provider == "none":
        raise HTTPException(status_code=400, detail="未配置 AI 提供商")

    try:
        ai_service = get_ai_service(provider, db_settings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    context = await get_pcap_context(request.pcap_id, db)

    prompt = f"""请根据以下 PCAP 文件信息，生成一份简洁的分析摘要：

{context}

请包含以下内容：
1. 流量概览（时间范围、数据量）
2. 主要协议分布
3. 关键通信节点
4. 可能的安全关注点（如果有）
5. 建议的进一步分析方向

请用中文回答，格式清晰。"""

    messages = [
        {"role": "system", "content": "你是专业的网络流量分析师。"},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await ai_service.chat(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")

    return {
        "summary": response["content"],
        "provider": provider,
        "model": ai_service.model,
    }


@router.post("/analyze")
async def analyze_traffic(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """根据自然语言查询分析流量"""
    db_settings = await get_ai_runtime_settings(db)
    provider = request.provider or db_settings.get("default_ai_provider") or settings.default_ai_provider

    if provider == "none":
        raise HTTPException(status_code=400, detail="未配置 AI 提供商")

    try:
        ai_service = get_ai_service(provider, db_settings)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    query = request.query or request.analysis_type
    if not query:
        raise HTTPException(status_code=422, detail="query is required")

    context = await get_pcap_context(request.pcap_id, db)

    prompt = f"""根据以下 PCAP 文件信息，回答用户的问题。

## PCAP 上下文
{context}

## 用户问题
{query}

请基于上下文信息回答，如果信息不足以回答，请说明需要什么额外信息。"""

    messages = [
        {"role": "system", "content": "你是专业的网络流量分析师，擅长从 PCAP 数据中发现问题和模式。"},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await ai_service.chat(messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 服务调用失败: {str(e)}")

    return {
        "answer": response["content"],
        "provider": provider,
        "model": ai_service.model,
    }


@router.get("/conversations")
async def list_conversations(
    pcap_id: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """获取对话列表"""
    query = select(AIConversation).order_by(AIConversation.updated_at.desc()).limit(limit)

    if pcap_id:
        query = query.where(AIConversation.pcap_file_id == pcap_id)

    result = await db.execute(query)
    conversations = result.scalars().all()

    # 获取每个对话的消息数量
    items = []
    for conv in conversations:
        from sqlalchemy import func

        count_result = await db.execute(
            select(func.count(AIMessage.id)).where(AIMessage.conversation_id == conv.id)
        )
        message_count = count_result.scalar() or 0

        items.append(
            {
                "id": conv.id,
                "title": conv.title,
                "provider": conv.provider,
                "model": conv.model,
                "pcap_file_id": conv.pcap_file_id,
                "message_count": message_count,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
            }
        )

    return {"items": items}


@router.get("/conversations/{conversation_id}/messages")
@router.get("/conversations/{conversation_id}")
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取对话消息"""
    conversation = await db.get(AIConversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    result = await db.execute(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.created_at)
    )
    messages = result.scalars().all()

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "provider": conversation.provider,
            "model": conversation.model,
        },
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除对话"""
    conversation = await db.get(AIConversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    await db.delete(conversation)
    await db.commit()

    return {"message": "删除成功"}
