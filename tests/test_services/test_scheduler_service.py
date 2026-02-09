"""
SchedulerService 测试模块

测试覆盖:
- ScheduledJob
- JobType
- JobStatus
- TriggerType
- JobLogStore
- JobExecutionLog
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
from pathlib import Path


class TestSchedulerEnums:
    """测试调度器枚举"""
    
    def test_job_type_import(self):
        """测试 JobType 导入"""
        from netops_toolkit.services.scheduler_service import JobType
        
        assert JobType is not None
    
    def test_job_type_values(self):
        """测试 JobType 值"""
        from netops_toolkit.services.scheduler_service import JobType
        
        assert hasattr(JobType, 'BACKUP')
        assert hasattr(JobType, 'INSPECTION')
    
    def test_job_status_import(self):
        """测试 JobStatus 导入"""
        from netops_toolkit.services.scheduler_service import JobStatus
        
        assert JobStatus is not None
    
    def test_job_status_values(self):
        """测试 JobStatus 值"""
        from netops_toolkit.services.scheduler_service import JobStatus
        
        assert hasattr(JobStatus, 'PENDING')
        assert hasattr(JobStatus, 'SUCCESS')
    
    def test_trigger_type_import(self):
        """测试 TriggerType 导入"""
        from netops_toolkit.services.scheduler_service import TriggerType
        
        assert TriggerType is not None
    
    def test_trigger_type_values(self):
        """测试 TriggerType 值"""
        from netops_toolkit.services.scheduler_service import TriggerType
        
        assert hasattr(TriggerType, 'INTERVAL')
        assert hasattr(TriggerType, 'CRON')


class TestScheduledJob:
    """测试计划作业"""
    
    def test_scheduled_job_import(self):
        """测试导入"""
        from netops_toolkit.services.scheduler_service import ScheduledJob
        
        assert ScheduledJob is not None
    
    def test_scheduled_job_creation(self):
        """测试创建作业"""
        from netops_toolkit.services.scheduler_service import ScheduledJob, JobType, TriggerType
        
        job = ScheduledJob(
            name="Test Job",
            job_type=JobType.BACKUP,
            trigger_type=TriggerType.INTERVAL
        )
        
        assert job.name == "Test Job"
        assert job.job_type == JobType.BACKUP
    
    def test_scheduled_job_to_dict(self):
        """测试转换为字典"""
        from netops_toolkit.services.scheduler_service import ScheduledJob, JobType, TriggerType
        
        job = ScheduledJob(
            name="Test Job",
            job_type=JobType.BACKUP,
            trigger_type=TriggerType.INTERVAL
        )
        
        data = job.to_dict()
        assert isinstance(data, dict)
        assert data['name'] == "Test Job"


class TestJobExecutionLog:
    """测试作业执行日志"""
    
    def test_job_execution_log_import(self):
        """测试导入"""
        from netops_toolkit.services.scheduler_service import JobExecutionLog
        
        assert JobExecutionLog is not None
    
    def test_job_execution_log_creation(self):
        """测试创建日志"""
        from netops_toolkit.services.scheduler_service import JobExecutionLog, JobStatus
        
        log = JobExecutionLog(
            job_id="job1",
            job_name="Test Job",
            status=JobStatus.SUCCESS
        )
        
        assert log.job_id == "job1"
        assert log.status == JobStatus.SUCCESS


class TestJobLogStore:
    """测试作业日志存储"""
    
    def test_job_log_store_import(self):
        """测试导入"""
        from netops_toolkit.services.scheduler_service import JobLogStore
        
        assert JobLogStore is not None
    
    def test_job_log_store_creation(self):
        """测试创建"""
        from netops_toolkit.services.scheduler_service import JobLogStore
        import gc
        
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = Path(tmpdir) / "test.db"
            store = JobLogStore(db_path)
            assert store is not None
            del store
            gc.collect()
        finally:
            import shutil
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass
    
    def test_save_and_get_log(self):
        """测试保存和获取日志"""
        from netops_toolkit.services.scheduler_service import JobLogStore, JobExecutionLog, JobStatus
        import gc
        
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = Path(tmpdir) / "test.db"
            store = JobLogStore(db_path)
            
            # 保存日志
            log = JobExecutionLog(
                job_id="job1",
                job_name="Test Job",
                status=JobStatus.SUCCESS
            )
            store.save_log(log)
            
            # 获取日志
            logs = store.get_logs(job_id="job1")
            assert len(logs) >= 1
            
            del store
            gc.collect()
        finally:
            import shutil
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass


class TestSchedulerService:
    """测试调度服务"""
    
    def test_scheduler_service_import(self):
        """测试导入"""
        from netops_toolkit.services.scheduler_service import SchedulerService
        
        assert SchedulerService is not None
    
    def test_scheduler_service_creation(self):
        """测试创建"""
        from netops_toolkit.services.scheduler_service import SchedulerService
        import gc
        
        tmpdir = tempfile.mkdtemp()
        try:
            service = SchedulerService(data_dir=Path(tmpdir))
            assert service is not None
            del service
            gc.collect()
        finally:
            import shutil
            import time
            time.sleep(0.1)
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass
