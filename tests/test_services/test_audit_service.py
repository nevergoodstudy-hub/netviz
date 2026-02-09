"""
AuditService 审计服务测试模块

测试覆盖:
- 审计记录创建和存储
- 事件类型验证
- 查询过滤功能
- JSON/CSV 导出
- 统计摘要
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from netops_toolkit.services.audit_service import (
    AuditService,
    AuditStore,
    AuditRecord,
    AuditQuery,
    AuditSummary,
    AuditEventType,
    AuditSeverity,
    AuditResult,
)


class TestAuditEventType:
    """测试审计事件类型枚举"""
    
    def test_event_type_values(self):
        """测试事件类型值"""
        assert AuditEventType.CONFIG_BACKUP.value == "config_backup"
        assert AuditEventType.CONFIG_PUSH.value == "config_push"
        assert AuditEventType.DEVICE_CONNECT.value == "device_connect"
        assert AuditEventType.COMMAND_EXECUTE.value == "command_execute"
        assert AuditEventType.COMPLIANCE_CHECK.value == "compliance_check"
    
    def test_event_type_count(self):
        """测试事件类型数量 (应有 20+ 种)"""
        event_types = list(AuditEventType)
        assert len(event_types) >= 20, f"事件类型数量不足: {len(event_types)}"


class TestAuditSeverity:
    """测试审计严重级别枚举"""
    
    def test_severity_values(self):
        """测试严重级别值"""
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.CRITICAL.value == "critical"
        assert AuditSeverity.ERROR.value == "error"
    
    def test_severity_count(self):
        """测试严重级别数量"""
        severities = list(AuditSeverity)
        assert len(severities) == 4


class TestAuditResult:
    """测试审计结果枚举"""
    
    def test_result_values(self):
        """测试结果值"""
        assert AuditResult.SUCCESS.value == "success"
        assert AuditResult.FAILURE.value == "failure"
        assert AuditResult.PARTIAL.value == "partial"
        assert AuditResult.SKIPPED.value == "skipped"


class TestAuditRecord:
    """测试审计记录数据类"""
    
    def test_record_creation(self):
        """测试记录创建"""
        record = AuditRecord(
            event_type=AuditEventType.CONFIG_PUSH,
            severity=AuditSeverity.INFO,
            operator="admin",
            device_name="router-01",
            device_ip="192.168.1.1",
            description="配置推送测试",
            result=AuditResult.SUCCESS,
        )
        
        assert record.event_type == AuditEventType.CONFIG_PUSH
        assert record.severity == AuditSeverity.INFO
        assert record.operator == "admin"
        assert record.device_name == "router-01"
        assert record.device_ip == "192.168.1.1"
        assert record.description == "配置推送测试"
        assert record.result == AuditResult.SUCCESS
    
    def test_record_default_values(self):
        """测试记录默认值"""
        record = AuditRecord()
        
        assert record.id is None
        assert record.event_type == AuditEventType.COMMAND_EXECUTE
        assert record.severity == AuditSeverity.INFO
        assert record.result == AuditResult.SUCCESS
        assert record.operator == ""
        assert record.device_name == ""
        assert record.duration_ms == 0
        assert record.metadata == {}
    
    def test_record_to_dict(self):
        """测试记录转字典"""
        record = AuditRecord(
            event_type=AuditEventType.CONFIG_BACKUP,
            operator="admin",
            device_name="switch-01",
            description="配置备份",
        )
        
        data = record.to_dict()
        
        assert data["event_type"] == "config_backup"
        assert data["operator"] == "admin"
        assert data["device_name"] == "switch-01"
        assert data["description"] == "配置备份"
        assert "timestamp" in data
    
    def test_record_from_dict(self):
        """测试从字典创建记录"""
        data = {
            "id": 1,
            "timestamp": "2026-02-01T10:00:00",
            "event_type": "config_push",
            "severity": "warning",
            "operator": "admin",
            "device_name": "router-01",
            "device_ip": "192.168.1.1",
            "description": "配置推送",
            "result": "success",
        }
        
        record = AuditRecord.from_dict(data)
        
        assert record.id == 1
        assert record.event_type == AuditEventType.CONFIG_PUSH
        assert record.severity == AuditSeverity.WARNING
        assert record.operator == "admin"
    
    def test_record_with_metadata(self):
        """测试带元数据的记录"""
        metadata = {
            "config_lines": 50,
            "backup_file": "/backups/router-01.cfg",
            "checksum": "abc123",
        }
        
        record = AuditRecord(
            event_type=AuditEventType.CONFIG_BACKUP,
            metadata=metadata,
        )
        
        assert record.metadata == metadata
        assert record.metadata["config_lines"] == 50


class TestAuditQuery:
    """测试审计查询参数"""
    
    def test_query_default_values(self):
        """测试查询默认值"""
        query = AuditQuery()
        
        assert query.start_time is None
        assert query.end_time is None
        assert query.event_types == []
        assert query.limit == 1000
        assert query.offset == 0
    
    def test_query_with_filters(self):
        """测试带过滤条件的查询"""
        query = AuditQuery(
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 2, 1),
            event_types=[AuditEventType.CONFIG_PUSH, AuditEventType.CONFIG_BACKUP],
            severities=[AuditSeverity.WARNING, AuditSeverity.CRITICAL],
            operators=["admin", "netops"],
            keyword="配置",
            limit=100,
        )
        
        assert query.start_time == datetime(2026, 1, 1)
        assert len(query.event_types) == 2
        assert len(query.severities) == 2
        assert "admin" in query.operators
        assert query.keyword == "配置"
        assert query.limit == 100


class TestAuditStore:
    """测试审计存储层"""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """创建临时数据库"""
        db_path = tmp_path / "test_audit.db"
        store = AuditStore(db_path)
        yield store
        # 关闭连接后再清理
        store.close()
        # Windows 上文件可能还被锁定，忽略删除错误
        try:
            if db_path.exists():
                db_path.unlink()
            # 删除 WAL 文件
            wal_path = db_path.with_suffix(".db-wal")
            shm_path = db_path.with_suffix(".db-shm")
            if wal_path.exists():
                wal_path.unlink()
            if shm_path.exists():
                shm_path.unlink()
        except PermissionError:
            pass  # Windows 上文件可能还被锁定
    
    def test_store_initialization(self, temp_db):
        """测试存储初始化"""
        assert temp_db is not None
        assert temp_db._db_path.exists()
    
    def test_insert_record(self, temp_db):
        """测试插入记录"""
        record = AuditRecord(
            event_type=AuditEventType.CONFIG_PUSH,
            operator="admin",
            device_name="router-01",
            device_ip="192.168.1.1",
            description="测试配置推送",
            result=AuditResult.SUCCESS,
        )
        
        record_id = temp_db.insert(record)
        
        assert record_id > 0
    
    def test_insert_multiple_records(self, temp_db):
        """测试插入多条记录"""
        records = [
            AuditRecord(
                event_type=AuditEventType.CONFIG_PUSH,
                device_name=f"device-{i}",
                description=f"测试记录 {i}",
            )
            for i in range(5)
        ]
        
        ids = [temp_db.insert(r) for r in records]
        
        assert len(ids) == 5
        assert all(i > 0 for i in ids)
        # 验证 ID 递增
        assert ids == sorted(ids)
    
    def test_query_all_records(self, temp_db):
        """测试查询所有记录"""
        # 插入测试数据
        for i in range(3):
            temp_db.insert(AuditRecord(
                event_type=AuditEventType.COMMAND_EXECUTE,
                device_name=f"device-{i}",
            ))
        
        # 查询
        query = AuditQuery()
        results = temp_db.query(query)
        
        assert len(results) == 3
    
    def test_query_by_event_type(self, temp_db):
        """测试按事件类型查询"""
        # 插入不同类型的记录
        temp_db.insert(AuditRecord(event_type=AuditEventType.CONFIG_PUSH))
        temp_db.insert(AuditRecord(event_type=AuditEventType.CONFIG_BACKUP))
        temp_db.insert(AuditRecord(event_type=AuditEventType.CONFIG_PUSH))
        temp_db.insert(AuditRecord(event_type=AuditEventType.COMMAND_EXECUTE))
        
        # 查询 CONFIG_PUSH
        query = AuditQuery(event_types=[AuditEventType.CONFIG_PUSH])
        results = temp_db.query(query)
        
        assert len(results) == 2
        assert all(r.event_type == AuditEventType.CONFIG_PUSH for r in results)
    
    def test_query_by_time_range(self, temp_db):
        """测试按时间范围查询"""
        now = datetime.now()
        
        # 插入不同时间的记录
        old_record = AuditRecord(
            event_type=AuditEventType.CONFIG_PUSH,
            timestamp=now - timedelta(days=10),
        )
        recent_record = AuditRecord(
            event_type=AuditEventType.CONFIG_PUSH,
            timestamp=now - timedelta(hours=1),
        )
        
        temp_db.insert(old_record)
        temp_db.insert(recent_record)
        
        # 查询最近7天的记录
        query = AuditQuery(
            start_time=now - timedelta(days=7),
            end_time=now,
        )
        results = temp_db.query(query)
        
        assert len(results) == 1
    
    def test_query_by_operator(self, temp_db):
        """测试按操作人查询"""
        temp_db.insert(AuditRecord(operator="admin"))
        temp_db.insert(AuditRecord(operator="netops"))
        temp_db.insert(AuditRecord(operator="admin"))
        
        query = AuditQuery(operators=["admin"])
        results = temp_db.query(query)
        
        assert len(results) == 2
        assert all(r.operator == "admin" for r in results)
    
    def test_query_by_device(self, temp_db):
        """测试按设备查询"""
        temp_db.insert(AuditRecord(device_name="router-01", device_ip="10.0.0.1"))
        temp_db.insert(AuditRecord(device_name="router-02", device_ip="10.0.0.2"))
        temp_db.insert(AuditRecord(device_name="router-01", device_ip="10.0.0.1"))
        
        # 按设备名查询
        query = AuditQuery(device_names=["router-01"])
        results = temp_db.query(query)
        assert len(results) == 2
        
        # 按 IP 查询
        query = AuditQuery(device_ips=["10.0.0.2"])
        results = temp_db.query(query)
        assert len(results) == 1
    
    def test_query_by_result(self, temp_db):
        """测试按结果查询"""
        temp_db.insert(AuditRecord(result=AuditResult.SUCCESS))
        temp_db.insert(AuditRecord(result=AuditResult.FAILURE))
        temp_db.insert(AuditRecord(result=AuditResult.SUCCESS))
        
        query = AuditQuery(results=[AuditResult.FAILURE])
        results = temp_db.query(query)
        
        assert len(results) == 1
        assert results[0].result == AuditResult.FAILURE
    
    def test_query_by_keyword(self, temp_db):
        """测试按关键字查询"""
        temp_db.insert(AuditRecord(description="配置备份成功"))
        temp_db.insert(AuditRecord(description="命令执行完成"))
        temp_db.insert(AuditRecord(description="配置推送失败"))
        
        query = AuditQuery(keyword="配置")
        results = temp_db.query(query)
        
        assert len(results) == 2
        assert all("配置" in r.description for r in results)
    
    def test_query_with_limit_and_offset(self, temp_db):
        """测试分页查询"""
        # 插入10条记录
        for i in range(10):
            temp_db.insert(AuditRecord(description=f"记录 {i}"))
        
        # 第一页
        query = AuditQuery(limit=3, offset=0)
        page1 = temp_db.query(query)
        assert len(page1) == 3
        
        # 第二页
        query = AuditQuery(limit=3, offset=3)
        page2 = temp_db.query(query)
        assert len(page2) == 3
        
        # 验证不重复
        page1_ids = {r.id for r in page1}
        page2_ids = {r.id for r in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_get_by_id(self, temp_db):
        """测试按 ID 获取记录"""
        record = AuditRecord(
            event_type=AuditEventType.CONFIG_PUSH,
            operator="admin",
            description="测试记录",
        )
        record_id = temp_db.insert(record)
        
        retrieved = temp_db.get_by_id(record_id)
        
        assert retrieved is not None
        assert retrieved.id == record_id
        assert retrieved.operator == "admin"
        assert retrieved.description == "测试记录"
    
    def test_get_by_id_not_found(self, temp_db):
        """测试获取不存在的记录"""
        result = temp_db.get_by_id(99999)
        assert result is None


class TestAuditService:
    """测试审计服务高级功能"""
    
    @pytest.fixture
    def audit_service(self, tmp_path):
        """创建临时审计服务"""
        # 重置单例以便使用新的数据库路径
        AuditService._instance = None
        db_path = tmp_path / "audit_service.db"
        service = AuditService(db_path)
        yield service
        # 关闭内部数据库连接
        service._store.close()
        # 清理单例
        AuditService._instance = None
    
    def test_service_log_event(self, audit_service):
        """测试记录审计事件"""
        record_id = audit_service.log(
            event_type=AuditEventType.CONFIG_PUSH,
            description="配置推送",
            operator="admin",
            device_name="router-01",
        )
        
        assert record_id > 0
    
    def test_service_query_recent_logs(self, audit_service):
        """测试获取最近日志"""
        # 插入测试数据
        for i in range(5):
            audit_service.log(
                event_type=AuditEventType.COMMAND_EXECUTE,
                description=f"命令 {i}",
            )
        
        logs = audit_service.query_recent(hours=1, limit=3)
        
        assert len(logs) == 3
    
    def test_service_get_summary(self, audit_service):
        """测试获取统计摘要"""
        # 插入不同类型的记录
        audit_service.log(event_type=AuditEventType.CONFIG_PUSH, description="测试1", result=AuditResult.SUCCESS)
        audit_service.log(event_type=AuditEventType.CONFIG_PUSH, description="测试2", result=AuditResult.FAILURE)
        audit_service.log(event_type=AuditEventType.CONFIG_BACKUP, description="测试3", result=AuditResult.SUCCESS)
        audit_service.log(event_type=AuditEventType.COMMAND_EXECUTE, description="测试4", result=AuditResult.SUCCESS)
        
        summary = audit_service.get_summary()
        
        assert summary.total_records >= 4
        assert summary.success_count >= 3
        assert summary.failure_count >= 1
    
    def test_service_export_json(self, audit_service, tmp_path):
        """测试 JSON 导出"""
        # 插入测试数据
        audit_service.log(
            event_type=AuditEventType.CONFIG_PUSH,
            description="测试导出",
            operator="admin",
        )
        
        export_path = tmp_path / "subdir" / "audit_export.json"
        audit_service.export_json(export_path)
        
        assert export_path.exists()
        
        # 验证内容
        with open(export_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "records" in data
        assert len(data["records"]) >= 1
    
    def test_service_export_csv(self, audit_service, tmp_path):
        """测试 CSV 导出"""
        # 插入测试数据
        audit_service.log(
            event_type=AuditEventType.CONFIG_PUSH,
            description="测试导出",
            operator="admin",
        )
        
        export_path = tmp_path / "subdir" / "audit_export.csv"
        audit_service.export_csv(export_path)
        
        assert export_path.exists()
        
        # 验证内容
        with open(export_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "event_type" in content
        assert "config_push" in content


class TestAuditServiceIntegration:
    """审计服务集成测试"""
    
    @pytest.fixture
    def audit_service(self, tmp_path):
        """创建临时审计服务"""
        # 重置单例
        AuditService._instance = None
        db_path = tmp_path / "integration_audit.db"
        service = AuditService(db_path)
        yield service
        # 关闭内部数据库连接
        service._store.close()
        AuditService._instance = None
    
    @pytest.mark.integration
    def test_full_audit_workflow(self, audit_service):
        """测试完整审计工作流"""
        # 1. 记录配置备份
        backup_id = audit_service.log(
            event_type=AuditEventType.CONFIG_BACKUP,
            description="每日配置备份",
            operator="admin",
            device_name="core-router-01",
            device_ip="10.0.0.1",
            result=AuditResult.SUCCESS,
            metadata={"backup_size": 1024},
        )
        assert backup_id > 0
        
        # 2. 记录配置推送
        push_id = audit_service.log(
            event_type=AuditEventType.CONFIG_PUSH,
            description="更新 ACL 配置",
            operator="admin",
            device_name="core-router-01",
            device_ip="10.0.0.1",
            old_value="permit any any",
            new_value="deny any any log",
            result=AuditResult.SUCCESS,
        )
        assert push_id > 0
        
        # 3. 记录失败操作
        fail_id = audit_service.log(
            event_type=AuditEventType.DEVICE_CONNECT,
            description="尝试连接设备",
            operator="admin",
            device_name="unreachable-device",
            device_ip="10.0.0.99",
            result=AuditResult.FAILURE,
            error_message="Connection timeout",
        )
        assert fail_id > 0
        
        # 4. 查询统计
        summary = audit_service.get_summary()
        assert summary.total_records >= 3
        assert summary.success_count >= 2
        assert summary.failure_count >= 1
        
        # 5. 按设备查询
        query = AuditQuery(device_names=["core-router-01"])
        device_logs = audit_service.query(query)
        assert len(device_logs) >= 2
        
        # 6. 按结果查询
        query = AuditQuery(results=[AuditResult.FAILURE])
        failed_logs = audit_service.query(query)
        assert len(failed_logs) >= 1
