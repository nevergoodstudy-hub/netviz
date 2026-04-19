"""
NetViz 威胁情报服务
集成 VirusTotal、AbuseIPDB 等威胁情报源
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ThreatIntelResult:
    """威胁情报查询结果"""
    
    ip: str
    is_malicious: bool
    confidence_score: float  # 0.0 - 1.0
    threat_types: list[str]
    sources: list[str]
    details: dict[str, Any]
    cached: bool = False
    queried_at: datetime | None = None


class ThreatIntelCache:
    """简单的内存缓存"""
    
    def __init__(self, ttl_hours: int = 24):
        self._cache: dict[str, tuple[ThreatIntelResult, datetime]] = {}
        self._ttl = timedelta(hours=ttl_hours)
    
    def get(self, ip: str) -> ThreatIntelResult | None:
        if ip in self._cache:
            result, timestamp = self._cache[ip]
            if datetime.now() - timestamp < self._ttl:
                result.cached = True
                return result
            else:
                del self._cache[ip]
        return None
    
    def set(self, ip: str, result: ThreatIntelResult) -> None:
        self._cache[ip] = (result, datetime.now())
    
    def clear(self) -> None:
        self._cache.clear()


class VirusTotalProvider:
    """VirusTotal 威胁情报提供商"""
    
    BASE_URL = "https://www.virustotal.com/api/v3"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def check_ip(self, ip: str) -> dict[str, Any] | None:
        """查询 IP 的威胁情报"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/ip_addresses/{ip}",
                    headers={"x-apikey": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    attrs = data.get("data", {}).get("attributes", {})
                    stats = attrs.get("last_analysis_stats", {})
                    
                    malicious_count = stats.get("malicious", 0)
                    suspicious_count = stats.get("suspicious", 0)
                    total_engines = sum(stats.values()) if stats else 1
                    
                    return {
                        "source": "virustotal",
                        "malicious_count": malicious_count,
                        "suspicious_count": suspicious_count,
                        "total_engines": total_engines,
                        "score": (malicious_count + suspicious_count * 0.5) / total_engines if total_engines > 0 else 0,
                        "country": attrs.get("country"),
                        "as_owner": attrs.get("as_owner"),
                        "reputation": attrs.get("reputation", 0),
                    }
                elif response.status_code == 404:
                    return {"source": "virustotal", "score": 0, "not_found": True}
                else:
                    logger.warning(f"VirusTotal API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"VirusTotal query failed for {ip}: {e}")
            return None
    
    async def check_file_hash(self, file_hash: str) -> dict[str, Any] | None:
        """查询文件哈希的威胁情报"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/files/{file_hash}",
                    headers={"x-apikey": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    attrs = data.get("data", {}).get("attributes", {})
                    stats = attrs.get("last_analysis_stats", {})
                    
                    return {
                        "source": "virustotal",
                        "malicious_count": stats.get("malicious", 0),
                        "suspicious_count": stats.get("suspicious", 0),
                        "total_engines": sum(stats.values()),
                        "file_type": attrs.get("type_description"),
                        "file_name": attrs.get("meaningful_name"),
                    }
                return None
                
        except Exception as e:
            logger.error(f"VirusTotal file query failed: {e}")
            return None


class AbuseIPDBProvider:
    """AbuseIPDB 威胁情报提供商"""
    
    BASE_URL = "https://api.abuseipdb.com/api/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def check_ip(self, ip: str) -> dict[str, Any] | None:
        """查询 IP 的威胁情报"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/check",
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                    headers={
                        "Key": self.api_key,
                        "Accept": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    
                    return {
                        "source": "abuseipdb",
                        "abuse_confidence_score": data.get("abuseConfidenceScore", 0),
                        "total_reports": data.get("totalReports", 0),
                        "is_whitelisted": data.get("isWhitelisted", False),
                        "country_code": data.get("countryCode"),
                        "isp": data.get("isp"),
                        "domain": data.get("domain"),
                        "usage_type": data.get("usageType"),
                        "score": data.get("abuseConfidenceScore", 0) / 100,
                    }
                else:
                    logger.warning(f"AbuseIPDB API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"AbuseIPDB query failed for {ip}: {e}")
            return None


class ThreatIntelService:
    """威胁情报聚合服务"""
    
    def __init__(self):
        self._cache = ThreatIntelCache()
        self._vt_provider: VirusTotalProvider | None = None
        self._abuseipdb_provider: AbuseIPDBProvider | None = None
    
    def configure(
        self,
        virustotal_key: str | None = None,
        abuseipdb_key: str | None = None
    ) -> None:
        """配置威胁情报提供商"""
        self._vt_provider = VirusTotalProvider(virustotal_key) if virustotal_key else None
        self._abuseipdb_provider = (
            AbuseIPDBProvider(abuseipdb_key) if abuseipdb_key else None
        )
    
    def is_configured(self) -> bool:
        """检查是否有提供商已配置"""
        return self._vt_provider is not None or self._abuseipdb_provider is not None
    
    async def check_ip(self, ip: str, use_cache: bool = True) -> ThreatIntelResult:
        """查询 IP 的威胁情报（聚合多个源）"""
        # 检查缓存
        if use_cache:
            cached = self._cache.get(ip)
            if cached:
                return cached
        
        # 并发查询所有提供商
        tasks = []
        if self._vt_provider:
            tasks.append(self._vt_provider.check_ip(ip))
        if self._abuseipdb_provider:
            tasks.append(self._abuseipdb_provider.check_ip(ip))
        
        if not tasks:
            return ThreatIntelResult(
                ip=ip,
                is_malicious=False,
                confidence_score=0.0,
                threat_types=[],
                sources=[],
                details={"error": "No threat intel providers configured"},
                queried_at=datetime.now()
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 聚合结果
        sources = []
        scores = []
        threat_types = []
        details = {}
        
        for result in results:
            if isinstance(result, Exception):
                continue
            if result is None:
                continue
            
            source = result.get("source", "unknown")
            sources.append(source)
            details[source] = result
            
            score = result.get("score", 0)
            scores.append(score)
            
            # 根据分数判断威胁类型
            if score > 0.5:
                threat_types.append(f"malicious_{source}")
            elif score > 0.2:
                threat_types.append(f"suspicious_{source}")
        
        # 计算综合分数（加权平均）
        if scores:
            avg_score = sum(scores) / len(scores)
        else:
            avg_score = 0.0
        
        result = ThreatIntelResult(
            ip=ip,
            is_malicious=avg_score > 0.5,
            confidence_score=avg_score,
            threat_types=list(set(threat_types)),
            sources=sources,
            details=details,
            queried_at=datetime.now()
        )
        
        # 缓存结果
        self._cache.set(ip, result)
        
        return result
    
    async def check_ips_batch(
        self,
        ips: list[str],
        concurrency: int = 5
    ) -> dict[str, ThreatIntelResult]:
        """批量查询 IP 的威胁情报"""
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        
        async def check_with_semaphore(ip: str) -> tuple[str, ThreatIntelResult]:
            async with semaphore:
                result = await self.check_ip(ip)
                return ip, result
        
        tasks = [check_with_semaphore(ip) for ip in ips]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item in completed:
            if isinstance(item, tuple):
                ip, result = item
                results[ip] = result
        
        return results
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()


# 全局服务实例
threat_intel_service = ThreatIntelService()
