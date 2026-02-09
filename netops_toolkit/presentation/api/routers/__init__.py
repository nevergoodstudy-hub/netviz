"""
API 路由模块

每个模块包含一组相关 API 端点, 使用 FastAPI APIRouter 模块化。
"""

from netops_toolkit.presentation.api.routers.devices import router as devices_router
from netops_toolkit.presentation.api.routers.monitoring import (
    router as monitoring_router,
)

__all__ = ["devices_router", "monitoring_router"]
