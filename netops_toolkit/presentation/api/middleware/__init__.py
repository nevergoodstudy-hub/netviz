"""
API 中间件
"""

from netops_toolkit.presentation.api.middleware.error_handler import (
    register_error_handlers,
)

__all__ = ["register_error_handlers"]
