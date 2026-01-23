"""
NetOps Toolkit - 网络工程实施及测试工具集

面向网络工程师的多功能CLI工具箱,集成网络实施、测试、巡检、诊断功能。
"""

__version__ = "1.0.0"
__author__ = "Network Engineering Team"
__license__ = "MIT"

from .core.logger import get_logger

# 导出常用组件
__all__ = ["__version__", "get_logger"]
