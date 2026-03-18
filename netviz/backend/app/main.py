"""
NetViz - PCAP 可视化分析平台
主应用入口
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import pcap, analysis, ai, settings as settings_api, websocket, capture, threat_intel
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.logging import setup_logging, get_logger
from app.middleware import RateLimitMiddleware

# 配置日志系统
setup_logging(
    log_dir=settings.log_dir,
    log_level="DEBUG" if settings.debug else settings.log_level,
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count,
    enable_console=True,
    enable_file=True,
    app_name="netviz",
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    settings.ensure_directories()
    await init_db()
    logger.info("Database initialized")

    yield

    # 关闭时
    logger.info("Shutting down...")
    await close_db()


# 创建应用
app = FastAPI(
    title=settings.app_name,
    description="PCAP 可视化分析平台 - 个人全功能版",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# 添加速率限制中间件（每分钟60个请求）
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(pcap.router, prefix="/api/pcap", tags=["PCAP"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(capture.router, prefix="/api/capture", tags=["Capture"])
app.include_router(threat_intel.router, prefix="/api/threat-intel", tags=["Threat Intel"])


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/api/info")
async def app_info():
    """应用信息"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "ai_providers": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "deepseek": bool(settings.deepseek_api_key),
            "ollama": True,  # Ollama 总是可用（如果本地运行）
        },
        "features": {
            "geoip": Path(settings.geoip_db_path).exists(),
            "threat_intel": bool(settings.virustotal_api_key or settings.abuseipdb_api_key),
        },
    }


def run():
    """运行应用"""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    run()
