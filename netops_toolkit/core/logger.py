"""
日志系统模块

基于loguru实现统一的日志管理,支持:
- 控制台彩色输出
- 文件滚动存储
- 操作审计日志
- 结构化日志格式
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from loguru import logger


# 默认日志配置
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
DEFAULT_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
    "{name}:{function}:{line} | {message}"
)
AUDIT_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} | AUDIT | "
    "user={extra[user]} | action={extra[action]} | "
    "target={extra[target]} | result={extra[result]} | {message}"
)


def setup_logging(
    log_dir: Optional[Union[str, Path]] = None,
    log_level: str = "INFO",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_audit: bool = True,
    rotation: str = "10 MB",
    retention: str = "30 days",
    compression: str = "zip",
) -> None:
    """
    配置全局日志系统
    
    Args:
        log_dir: 日志文件存储目录
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        enable_audit: 是否启用审计日志
        rotation: 日志滚动策略 (e.g., "10 MB", "1 day")
        retention: 日志保留时间 (e.g., "30 days")
        compression: 压缩格式 (zip, gz, bz2, xz)
    """
    # 移除默认处理器
    logger.remove()
    
    # 设置日志目录
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 添加控制台处理器
    if enable_console:
        logger.add(
            sys.stderr,
            format=DEFAULT_LOG_FORMAT,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    
    # 添加文件处理器 - 常规日志
    if enable_file:
        logger.add(
            log_dir / "netops_{time:YYYY-MM-DD}.log",
            format=DEFAULT_FILE_FORMAT,
            level=log_level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            enqueue=True,  # 异步写入,提高性能
        )
        
        # 添加错误专用日志文件
        logger.add(
            log_dir / "netops_error_{time:YYYY-MM-DD}.log",
            format=DEFAULT_FILE_FORMAT,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
            enqueue=True,
        )
    
    # 添加审计日志处理器
    if enable_audit:
        logger.add(
            log_dir / "audit_{time:YYYY-MM-DD}.log",
            format=AUDIT_FORMAT,
            level="INFO",
            filter=lambda record: record["extra"].get("audit", False),
            rotation="1 day",
            retention="90 days",  # 审计日志保留更长时间
            compression=compression,
            encoding="utf-8",
            enqueue=True,
        )
    
    logger.info(f"日志系统已初始化 | 目录: {log_dir} | 级别: {log_level}")


def get_logger(name: str = "netops"):
    """
    获取日志记录器实例
    
    Args:
        name: 日志记录器名称 (用于标识日志来源)
        
    Returns:
        配置好的logger实例
    """
    return logger.bind(name=name)


def log_audit(
    user: str,
    action: str,
    target: str,
    result: str = "success",
    message: str = "",
) -> None:
    """
    记录审计日志
    
    Args:
        user: 执行操作的用户
        action: 操作类型 (e.g., "ssh_connect", "config_backup", "ping_test")
        target: 操作目标 (e.g., 设备IP, 文件路径)
        result: 操作结果 (success, failed, partial)
        message: 附加说明
    """
    logger.bind(
        audit=True,
        user=user,
        action=action,
        target=target,
        result=result,
    ).info(message or f"操作: {action} -> {target}")


class LogContext:
    """
    日志上下文管理器
    
    用于为一组操作添加统一的上下文信息
    
    Example:
        with LogContext(task_id="12345", device="192.168.1.1"):
            logger.info("开始执行任务")
            # ... 执行操作
            logger.info("任务完成")
    """
    
    def __init__(self, **context):
        self.context = context
        self._token = None
    
    def __enter__(self):
        self._token = logger.contextualize(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            self._token.__exit__(exc_type, exc_val, exc_tb)
        return False


# 导出便捷函数
__all__ = [
    "setup_logging",
    "get_logger",
    "log_audit",
    "LogContext",
    "logger",
]


# 默认初始化基础日志配置 (仅控制台)
if not logger._core.handlers:
    logger.add(
        sys.stderr,
        format=DEFAULT_LOG_FORMAT,
        level="INFO",
        colorize=True,
    )
