"""
日志模块测试

测试覆盖:
- 日志配置
- 日志记录器
- 审计日志
- 日志上下文
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from netops_toolkit.core.logger import (
    setup_logging,
    get_logger,
    log_audit,
    LogContext,
    DEFAULT_LOG_FORMAT,
    DEFAULT_FILE_FORMAT,
)


class TestSetupLogging:
    """测试日志配置"""
    
    def test_setup_logging_creates_log_dir(self, tmp_path):
        """测试日志配置创建目录"""
        log_dir = tmp_path / "test_logs"
        
        setup_logging(
            log_dir=log_dir,
            log_level="DEBUG",
            enable_console=False,
            enable_file=True,
            enable_audit=False,
        )
        
        assert log_dir.exists()
    
    def test_setup_logging_with_different_levels(self, tmp_path):
        """测试不同日志级别"""
        log_dir = tmp_path / "logs"
        
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            setup_logging(
                log_dir=log_dir,
                log_level=level,
                enable_console=False,
                enable_file=False,
                enable_audit=False,
            )
    
    def test_setup_logging_console_only(self, tmp_path):
        """测试仅控制台输出"""
        setup_logging(
            log_dir=tmp_path,
            enable_console=True,
            enable_file=False,
            enable_audit=False,
        )
    
    def test_setup_logging_with_audit(self, tmp_path):
        """测试启用审计日志"""
        log_dir = tmp_path / "audit_logs"
        
        setup_logging(
            log_dir=log_dir,
            enable_console=False,
            enable_file=True,
            enable_audit=True,
        )
        
        assert log_dir.exists()


class TestGetLogger:
    """测试日志记录器获取"""
    
    def test_get_logger_default(self):
        """测试获取默认日志记录器"""
        logger = get_logger()
        assert logger is not None
    
    def test_get_logger_with_name(self):
        """测试获取命名日志记录器"""
        logger = get_logger("test_module")
        assert logger is not None
    
    def test_logger_can_log(self, tmp_path, capsys):
        """测试日志记录"""
        setup_logging(
            log_dir=tmp_path,
            enable_console=True,
            enable_file=False,
            enable_audit=False,
        )
        
        logger = get_logger("test")
        logger.info("Test message")
        
        # 日志应该已输出（到 stderr）


class TestLogAudit:
    """测试审计日志"""
    
    def test_log_audit_basic(self, tmp_path):
        """测试基本审计日志"""
        setup_logging(
            log_dir=tmp_path,
            enable_console=False,
            enable_file=False,
            enable_audit=True,
        )
        
        log_audit(
            user="admin",
            action="ssh_connect",
            target="192.168.1.1",
            result="success",
            message="Connected successfully",
        )
    
    def test_log_audit_with_failure(self, tmp_path):
        """测试失败审计日志"""
        setup_logging(
            log_dir=tmp_path,
            enable_console=False,
            enable_file=False,
            enable_audit=True,
        )
        
        log_audit(
            user="admin",
            action="config_push",
            target="router-01",
            result="failed",
            message="Connection timeout",
        )
    
    def test_log_audit_without_message(self, tmp_path):
        """测试无消息审计日志"""
        setup_logging(
            log_dir=tmp_path,
            enable_console=False,
            enable_file=False,
            enable_audit=True,
        )
        
        log_audit(
            user="netops",
            action="backup",
            target="switch-01",
        )


class TestLogContext:
    """测试日志上下文管理器"""
    
    def test_log_context_creation(self):
        """测试创建上下文"""
        ctx = LogContext(task_id="12345", device="192.168.1.1")
        
        assert ctx.context["task_id"] == "12345"
        assert ctx.context["device"] == "192.168.1.1"
    
    def test_log_context_multiple_params(self):
        """测试多参数上下文"""
        ctx = LogContext(
            batch_id="batch-001",
            device="router-01",
            action="backup",
        )
        
        assert len(ctx.context) == 3
        assert ctx.context["batch_id"] == "batch-001"


class TestLogFormats:
    """测试日志格式"""
    
    def test_default_log_format_exists(self):
        """测试默认日志格式"""
        assert DEFAULT_LOG_FORMAT is not None
        assert "{time" in DEFAULT_LOG_FORMAT
        assert "{level" in DEFAULT_LOG_FORMAT
        assert "{message}" in DEFAULT_LOG_FORMAT
    
    def test_default_file_format_exists(self):
        """测试默认文件格式"""
        assert DEFAULT_FILE_FORMAT is not None
        assert "{time" in DEFAULT_FILE_FORMAT
        assert "{level" in DEFAULT_FILE_FORMAT
