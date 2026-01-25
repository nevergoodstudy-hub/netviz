"""
NetViz 日志配置模块
支持控制台输出和文件持久化，带日志轮转
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Literal

# 日志格式
CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColoredFormatter(logging.Formatter):
    """带颜色的控制台日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    log_dir: Path | str = "./logs",
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True,
    enable_file: bool = True,
    app_name: str = "netviz",
) -> logging.Logger:
    """
    配置日志系统
    
    Args:
        log_dir: 日志目录路径
        log_level: 日志级别
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的历史日志文件数量
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        app_name: 应用名称，用于日志文件命名
    
    Returns:
        配置好的根日志器
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # 清除已有处理器（避免重复）
    root_logger.handlers.clear()

    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level))
        
        # Windows 终端可能不支持 ANSI 颜色，检测并选择格式化器
        if sys.platform == "win32":
            # 尝试启用 Windows ANSI 支持
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                console_formatter = ColoredFormatter(CONSOLE_FORMAT, DATE_FORMAT)
            except Exception:
                console_formatter = logging.Formatter(CONSOLE_FORMAT, DATE_FORMAT)
        else:
            console_formatter = ColoredFormatter(CONSOLE_FORMAT, DATE_FORMAT)
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if enable_file:
        # 主日志文件（按大小轮转）
        main_log_file = log_dir / f"{app_name}.log"
        file_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
        root_logger.addHandler(file_handler)

        # 错误日志文件（单独记录 ERROR 及以上级别）
        error_log_file = log_dir / f"{app_name}_error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
        root_logger.addHandler(error_handler)

    # 设置第三方库的日志级别（避免过多噪音）
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("scapy").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志器"""
    return logging.getLogger(name)
