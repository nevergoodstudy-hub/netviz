"""
统一错误处理中间件

将领域异常自动映射为标准 HTTP 错误响应。
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from netops_toolkit.domain.exceptions import (
    CommandInjectionError,
    ConfigurationError,
    CredentialError,
    DeviceAuthenticationError,
    DeviceConnectionError,
    DeviceNotFoundError,
    DeviceTimeoutError,
    NetOpsError,
    PluginNotFoundError,
    SecurityError,
    ValidationError,
)

# 异常类 → HTTP 状态码映射
_STATUS_MAP: dict[type, int] = {
    ValidationError: 422,
    DeviceNotFoundError: 404,
    PluginNotFoundError: 404,
    DeviceAuthenticationError: 401,
    CredentialError: 401,
    CommandInjectionError: 403,
    SecurityError: 403,
    DeviceConnectionError: 502,
    DeviceTimeoutError: 504,
    ConfigurationError: 500,
}


def register_error_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器

    在 FastAPI 应用工厂中调用:
        register_error_handlers(app)
    """

    @app.exception_handler(NetOpsError)
    async def netops_error_handler(
        request: Request, exc: NetOpsError
    ) -> JSONResponse:
        """处理所有 NetOpsError 子类"""
        status_code = 500
        for exc_type, code in _STATUS_MAP.items():
            if isinstance(exc, exc_type):
                status_code = code
                break

        # 仅在服务端错误时记录完整堆栈
        if status_code >= 500:
            logger.error(f"[{exc.code}] {exc.message}", exc_info=True)
        else:
            logger.warning(f"[{exc.code}] {exc.message}")

        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """处理未预期的异常"""
        logger.exception(f"未处理异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "内部服务器错误",
                "details": {},
            },
        )


__all__ = ["register_error_handlers"]
