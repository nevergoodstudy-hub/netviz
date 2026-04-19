"""
NetViz 威胁情报 API
提供 IP 威胁情报查询接口
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_access import require_admin_access
from app.core.config import settings
from app.core.database import get_db
from app.core.secret_store import build_settings_map, encrypt_setting_value
from app.models.analysis import Settings as DbSettings
from app.services.threat.threat_intel import threat_intel_service, ThreatIntelResult

router = APIRouter()


# ==================== Pydantic 模型 ====================


class ThreatIntelResponse(BaseModel):
    """威胁情报响应"""
    
    ip: str
    is_malicious: bool
    confidence_score: float
    threat_types: list[str]
    sources: list[str]
    details: dict
    cached: bool
    queried_at: str | None


class ThreatIntelBatchRequest(BaseModel):
    """批量查询请求"""
    
    ips: list[str]


class ThreatIntelConfigRequest(BaseModel):
    """威胁情报配置请求"""
    
    virustotal_api_key: str | None = None
    abuseipdb_api_key: str | None = None


class ThreatIntelStatus(BaseModel):
    """威胁情报服务状态"""
    
    configured: bool
    providers: list[str]


# ==================== Helper 函数 ====================


async def _configure_threat_intel(db: AsyncSession) -> None:
    """从数据库配置威胁情报服务"""
    result = await db.execute(select(DbSettings))
    db_settings = build_settings_map(result.scalars().all())
    
    vt_key = db_settings.get("virustotal_api_key") or settings.virustotal_api_key
    abuseipdb_key = db_settings.get("abuseipdb_api_key") or settings.abuseipdb_api_key
    
    threat_intel_service.configure(
        virustotal_key=vt_key,
        abuseipdb_key=abuseipdb_key
    )


def _result_to_response(result: ThreatIntelResult) -> ThreatIntelResponse:
    """转换结果为响应模型"""
    return ThreatIntelResponse(
        ip=result.ip,
        is_malicious=result.is_malicious,
        confidence_score=result.confidence_score,
        threat_types=result.threat_types,
        sources=result.sources,
        details=result.details,
        cached=result.cached,
        queried_at=result.queried_at.isoformat() if result.queried_at else None
    )


# ==================== API 端点 ====================


@router.get("/status", response_model=ThreatIntelStatus)
async def get_threat_intel_status(
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """获取威胁情报服务状态"""
    await _configure_threat_intel(db)
    
    providers = []
    if threat_intel_service._vt_provider:
        providers.append("virustotal")
    if threat_intel_service._abuseipdb_provider:
        providers.append("abuseipdb")
    
    return ThreatIntelStatus(
        configured=threat_intel_service.is_configured(),
        providers=providers
    )


@router.post("/configure")
async def configure_threat_intel(
    config: ThreatIntelConfigRequest,
    _: None = Depends(require_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """配置威胁情报 API 密钥"""
    updates = []
    
    if config.virustotal_api_key:
        updates.append(("virustotal_api_key", config.virustotal_api_key))
    if config.abuseipdb_api_key:
        updates.append(("abuseipdb_api_key", config.abuseipdb_api_key))
    
    # 保存到数据库
    for key, value in updates:
        result = await db.execute(
            select(DbSettings).where(DbSettings.key == key)
        )
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
            setting = DbSettings(key=key, value=stored_value, is_encrypted=is_encrypted)
            db.add(setting)
    
    await db.commit()
    
    # 重新配置服务
    await _configure_threat_intel(db)
    
    return {"message": "威胁情报配置已更新"}


@router.get("/check/{ip}", response_model=ThreatIntelResponse)
async def check_ip_threat_intel(
    ip: str,
    use_cache: bool = Query(default=True, description="是否使用缓存"),
    db: AsyncSession = Depends(get_db)
):
    """查询单个 IP 的威胁情报"""
    await _configure_threat_intel(db)
    
    if not threat_intel_service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="威胁情报服务未配置，请先配置 API 密钥"
        )
    
    result = await threat_intel_service.check_ip(ip, use_cache=use_cache)
    return _result_to_response(result)


@router.post("/check/batch")
async def check_ips_batch_threat_intel(
    request: ThreatIntelBatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """批量查询 IP 的威胁情报"""
    await _configure_threat_intel(db)
    
    if not threat_intel_service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="威胁情报服务未配置，请先配置 API 密钥"
        )
    
    if len(request.ips) > 100:
        raise HTTPException(
            status_code=400,
            detail="单次最多查询 100 个 IP"
        )
    
    results = await threat_intel_service.check_ips_batch(request.ips)
    
    return {
        "results": {
            ip: _result_to_response(result)
            for ip, result in results.items()
        },
        "total": len(results),
        "malicious_count": sum(1 for r in results.values() if r.is_malicious)
    }


@router.post("/cache/clear")
async def clear_threat_intel_cache(_: None = Depends(require_admin_access)):
    """清除威胁情报缓存"""
    threat_intel_service.clear_cache()
    return {"message": "缓存已清除"}


@router.get("/enrich/pcap/{pcap_id}")
async def enrich_pcap_with_threat_intel(
    pcap_id: int,
    limit: int = Query(default=50, description="最多查询的 IP 数量"),
    db: AsyncSession = Depends(get_db)
):
    """为 PCAP 文件中的 IP 添加威胁情报"""
    from app.models.pcap import Connection
    
    await _configure_threat_intel(db)
    
    if not threat_intel_service.is_configured():
        raise HTTPException(
            status_code=400,
            detail="威胁情报服务未配置"
        )
    
    # 获取 PCAP 中的唯一 IP
    result = await db.execute(
        select(Connection.src_ip, Connection.dst_ip)
        .where(Connection.pcap_file_id == pcap_id)
    )
    
    ips = set()
    for row in result.all():
        if row.src_ip:
            ips.add(row.src_ip)
        if row.dst_ip:
            ips.add(row.dst_ip)
    
    # 过滤私有 IP
    public_ips = [
        ip for ip in ips
        if not _is_private_ip(ip)
    ][:limit]
    
    if not public_ips:
        return {
            "message": "没有公网 IP 需要查询",
            "results": {},
            "total": 0,
            "malicious_count": 0
        }
    
    # 批量查询
    results = await threat_intel_service.check_ips_batch(public_ips)
    
    return {
        "pcap_id": pcap_id,
        "results": {
            ip: _result_to_response(result)
            for ip, result in results.items()
        },
        "total": len(results),
        "malicious_count": sum(1 for r in results.values() if r.is_malicious),
        "suspicious_count": sum(1 for r in results.values() if 0.2 < r.confidence_score <= 0.5)
    }


def _is_private_ip(ip: str) -> bool:
    """检查是否为私有 IP"""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_reserved
    except ValueError:
        return True
