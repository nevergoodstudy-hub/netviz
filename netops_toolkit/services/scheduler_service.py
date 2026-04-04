"""NetOps Toolkit - 调度与计划任务服务

支持功能:
- 定时备份设备配置
- 周期性巡检任务
- 自动报表生成
- 任务持久化 (SQLite)
- 失败重试机制
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

# APScheduler 可选导入
APSCHEDULER_AVAILABLE = False
try:
    from apscheduler.events import (
        EVENT_JOB_ERROR,
        EVENT_JOB_EXECUTED,
        EVENT_JOB_MISSED,
        JobExecutionEvent,
    )
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    pass


class JobType(Enum):
    """任务类型"""

    BACKUP = "backup"           # 配置备份
    INSPECTION = "inspection"   # 设备巡检
    REPORT = "report"           # 报表生成
    PING_CHECK = "ping_check"   # Ping检测
    CUSTOM = "custom"           # 自定义任务


class JobStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    MISSED = "missed"


class TriggerType(Enum):
    """触发器类型"""

    INTERVAL = "interval"   # 间隔触发
    CRON = "cron"           # Cron表达式
    DATE = "date"           # 一次性定时


@dataclass
class ScheduledJob:
    """计划任务定义"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    job_type: JobType = JobType.CUSTOM
    trigger_type: TriggerType = TriggerType.INTERVAL

    # 触发器配置
    interval_seconds: int | None = None
    cron_expression: str | None = None
    run_date: datetime | None = None

    # 任务配置
    target_devices: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    # 重试配置
    max_retries: int = 3
    retry_delay_seconds: int = 60

    # 元信息
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_run: datetime | None = None
    next_run: datetime | None = None
    last_status: JobStatus = JobStatus.PENDING
    last_error: str | None = None
    run_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['job_type'] = self.job_type.value
        data['trigger_type'] = self.trigger_type.value
        data['last_status'] = self.last_status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['last_run'] = self.last_run.isoformat() if self.last_run else None
        data['next_run'] = self.next_run.isoformat() if self.next_run else None
        data['run_date'] = self.run_date.isoformat() if self.run_date else None
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledJob:
        """从字典创建"""
        data = data.copy()
        data['job_type'] = JobType(data.get('job_type', 'custom'))
        data['trigger_type'] = TriggerType(data.get('trigger_type', 'interval'))
        data['last_status'] = JobStatus(data.get('last_status', 'pending'))

        for field_name in ['created_at', 'last_run', 'next_run', 'run_date']:
            if data.get(field_name):
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])

        return cls(**data)


@dataclass
class JobExecutionLog:
    """任务执行日志"""

    id: str = field(default_factory=lambda: str(uuid4())[:12])
    job_id: str = ""
    job_name: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    status: JobStatus = JobStatus.RUNNING
    message: str = ""
    error_trace: str | None = None
    duration_seconds: float = 0.0


class JobLogStore:
    """任务日志存储 (SQLite)"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """获取 SQLite 连接的上下文管理器，确保 commit + close"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """初始化数据库"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_logs (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    job_name TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    message TEXT,
                    error_trace TEXT,
                    duration_seconds REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_logs_job_id 
                ON job_logs(job_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_logs_start_time 
                ON job_logs(start_time DESC)
            """)

            # 任务定义表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def save_log(self, log: JobExecutionLog) -> None:
        """保存执行日志"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO job_logs 
                (id, job_id, job_name, start_time, end_time, status, message, error_trace, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log.id, log.job_id, log.job_name,
                log.start_time.isoformat(),
                log.end_time.isoformat() if log.end_time else None,
                log.status.value,
                log.message,
                log.error_trace,
                log.duration_seconds,
            ))

    def get_logs(
        self,
        job_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobExecutionLog]:
        """获取执行日志"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row

            if job_id:
                rows = conn.execute("""
                    SELECT * FROM job_logs 
                    WHERE job_id = ?
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """, (job_id, limit, offset)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM job_logs 
                    ORDER BY start_time DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset)).fetchall()

            logs = []
            for row in rows:
                logs.append(JobExecutionLog(
                    id=row['id'],
                    job_id=row['job_id'],
                    job_name=row['job_name'],
                    start_time=datetime.fromisoformat(row['start_time']),
                    end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                    status=JobStatus(row['status']),
                    message=row['message'] or "",
                    error_trace=row['error_trace'],
                    duration_seconds=row['duration_seconds'],
                ))
            return logs

    def save_job(self, job: ScheduledJob) -> None:
        """保存任务定义"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO scheduled_jobs 
                (id, name, job_type, trigger_type, config_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id, job.name, job.job_type.value, job.trigger_type.value,
                json.dumps(job.to_dict()),
                1 if job.enabled else 0,
                job.created_at.isoformat(),
                datetime.now().isoformat(),
            ))

    def load_jobs(self) -> list[ScheduledJob]:
        """加载所有任务定义"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT config_json FROM scheduled_jobs WHERE enabled = 1
            """).fetchall()

            jobs = []
            for row in rows:
                try:
                    data = json.loads(row['config_json'])
                    jobs.append(ScheduledJob.from_dict(data))
                except Exception:
                    pass
            return jobs

    def delete_job(self, job_id: str) -> None:
        """删除任务定义"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))


class SchedulerService:
    """调度服务
    
    基于 APScheduler 的任务调度服务，支持:
    - 间隔触发 (Interval)
    - Cron 表达式触发
    - 一次性定时触发
    - SQLite 持久化
    - 失败重试
    """

    def __init__(self, data_dir: Path | None = None):
        """初始化调度服务
        
        Args:
            data_dir: 数据存储目录

        """
        self.data_dir = data_dir or Path.cwd() / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._scheduler: BackgroundScheduler | None = None
        self._jobs: dict[str, ScheduledJob] = {}
        self._job_handlers: dict[JobType, Callable] = {}
        self._log_store = JobLogStore(self.data_dir / "scheduler.db")
        self._lock = threading.Lock()
        self._running = False

        # 注册默认处理器
        self._register_default_handlers()

        # 检查依赖
        if not APSCHEDULER_AVAILABLE:
            print("警告: APScheduler 未安装，调度功能不可用。请运行: pip install apscheduler")

    def _register_default_handlers(self) -> None:
        """注册默认任务处理器"""
        self._job_handlers[JobType.BACKUP] = self._handle_backup_job
        self._job_handlers[JobType.INSPECTION] = self._handle_inspection_job
        self._job_handlers[JobType.REPORT] = self._handle_report_job
        self._job_handlers[JobType.PING_CHECK] = self._handle_ping_check_job

    def start(self) -> bool:
        """启动调度器"""
        if not APSCHEDULER_AVAILABLE:
            return False

        if self._running:
            return True

        with self._lock:
            # 配置调度器
            job_defaults = {
                'coalesce': True,           # 合并错过的任务
                'max_instances': 3,         # 最大并发实例
                'misfire_grace_time': 300,  # 错过容忍时间(秒)
            }

            executors = {
                'default': ThreadPoolExecutor(10),
            }

            self._scheduler = BackgroundScheduler(
                job_defaults=job_defaults,
                executors=executors,
            )

            # 添加事件监听
            self._scheduler.add_listener(
                self._on_job_executed,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
            )

            # 加载已保存的任务
            self._load_saved_jobs()

            # 启动调度器
            self._scheduler.start()
            self._running = True

            return True

    def stop(self) -> None:
        """停止调度器"""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False

    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self._running

    def _load_saved_jobs(self) -> None:
        """加载已保存的任务"""
        saved_jobs = self._log_store.load_jobs()
        for job in saved_jobs:
            try:
                self._add_job_to_scheduler(job)
                self._jobs[job.id] = job
            except Exception as e:
                print(f"加载任务 {job.name} 失败: {e}")

    def add_job(self, job: ScheduledJob) -> str:
        """添加计划任务
        
        Args:
            job: 任务定义
        
        Returns:
            任务ID

        """
        if not APSCHEDULER_AVAILABLE or not self._running:
            raise RuntimeError("调度器未运行")

        with self._lock:
            self._add_job_to_scheduler(job)
            self._jobs[job.id] = job
            self._log_store.save_job(job)

        return job.id

    def _add_job_to_scheduler(self, job: ScheduledJob) -> None:
        """添加任务到调度器"""
        if not self._scheduler:
            return

        # 创建触发器
        trigger = self._create_trigger(job)

        # 添加到调度器
        self._scheduler.add_job(
            func=self._execute_job,
            trigger=trigger,
            id=job.id,
            name=job.name,
            kwargs={'job_id': job.id},
            replace_existing=True,
        )

    def _create_trigger(self, job: ScheduledJob):
        """创建触发器"""
        if job.trigger_type == TriggerType.INTERVAL:
            return IntervalTrigger(seconds=job.interval_seconds or 3600)
        elif job.trigger_type == TriggerType.CRON:
            # 解析 cron 表达式 (分 时 日 月 周)
            parts = (job.cron_expression or "0 * * * *").split()
            if len(parts) >= 5:
                return CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
            return IntervalTrigger(hours=1)  # 默认
        elif job.trigger_type == TriggerType.DATE:
            return DateTrigger(run_date=job.run_date or datetime.now() + timedelta(hours=1))
        else:
            return IntervalTrigger(hours=1)

    def remove_job(self, job_id: str) -> bool:
        """移除计划任务"""
        with self._lock:
            if job_id in self._jobs:
                if self._scheduler:
                    try:
                        self._scheduler.remove_job(job_id)
                    except Exception:
                        pass
                del self._jobs[job_id]
                self._log_store.delete_job(job_id)
                return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        if self._scheduler and job_id in self._jobs:
            try:
                self._scheduler.pause_job(job_id)
                self._jobs[job_id].enabled = False
                self._log_store.save_job(self._jobs[job_id])
                return True
            except Exception:
                pass
        return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        if self._scheduler and job_id in self._jobs:
            try:
                self._scheduler.resume_job(job_id)
                self._jobs[job_id].enabled = True
                self._log_store.save_job(self._jobs[job_id])
                return True
            except Exception:
                pass
        return False

    def run_job_now(self, job_id: str) -> bool:
        """立即执行任务"""
        if job_id in self._jobs:
            # 使用线程执行
            threading.Thread(
                target=self._execute_job,
                kwargs={'job_id': job_id},
                daemon=True,
            ).start()
            return True
        return False

    def get_jobs(self) -> list[ScheduledJob]:
        """获取所有任务"""
        return list(self._jobs.values())

    def get_job(self, job_id: str) -> ScheduledJob | None:
        """获取指定任务"""
        return self._jobs.get(job_id)

    def get_job_logs(
        self,
        job_id: str | None = None,
        limit: int = 100,
    ) -> list[JobExecutionLog]:
        """获取任务执行日志"""
        return self._log_store.get_logs(job_id=job_id, limit=limit)

    def _execute_job(self, job_id: str) -> None:
        """执行任务"""
        job = self._jobs.get(job_id)
        if not job:
            return

        # 创建执行日志
        log = JobExecutionLog(
            job_id=job_id,
            job_name=job.name,
            status=JobStatus.RUNNING,
        )

        start_time = datetime.now()
        retries = 0
        success = False
        error_msg = None

        while retries <= job.max_retries and not success:
            try:
                # 获取处理器
                handler = self._job_handlers.get(job.job_type)
                if handler:
                    handler(job)
                else:
                    # 自定义任务 - 执行参数中的函数
                    func = job.parameters.get('func')
                    if callable(func):
                        func(job)

                success = True
                log.status = JobStatus.SUCCESS
                log.message = f"任务执行成功 (尝试 {retries + 1} 次)"

            except Exception as e:
                retries += 1
                error_msg = str(e)

                if retries <= job.max_retries:
                    import time
                    time.sleep(job.retry_delay_seconds)
                else:
                    log.status = JobStatus.FAILED
                    log.message = f"任务执行失败: {error_msg}"
                    log.error_trace = error_msg

        # 更新任务状态
        end_time = datetime.now()
        log.end_time = end_time
        log.duration_seconds = (end_time - start_time).total_seconds()

        job.last_run = end_time
        job.last_status = log.status
        job.last_error = error_msg if not success else None
        job.run_count += 1

        # 更新下次运行时间
        if self._scheduler:
            apscheduler_job = self._scheduler.get_job(job_id)
            if apscheduler_job:
                job.next_run = apscheduler_job.next_run_time

        # 保存日志和任务状态
        self._log_store.save_log(log)
        self._log_store.save_job(job)

    def _on_job_executed(self, event: JobExecutionEvent) -> None:
        """任务执行事件回调"""
        # 此处可添加额外的事件处理逻辑
        pass

    # ========== 默认任务处理器 ==========

    def _handle_backup_job(self, job: ScheduledJob) -> None:
        """处理备份任务"""
        from pathlib import Path

        backup_dir = Path(job.parameters.get('backup_dir', 'backups'))
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 获取设备列表
        devices = job.target_devices
        if not devices:
            # 从设备清单加载
            try:
                from netops_toolkit.config.device_inventory import DeviceInventory
                inv = DeviceInventory(Path("config/devices.yaml"))
                devices = [d.name for d in inv]
            except Exception:
                devices = []

        if not devices:
            raise ValueError("没有可备份的设备")

        # 模拟备份（实际应调用 SSH 连接获取配置）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for device in devices:
            backup_file = backup_dir / f"{device}_{timestamp}.cfg"
            # 此处应实际连接设备获取配置
            backup_file.write_text(f"# Backup for {device}\n# Generated at {timestamp}\n")

    def _handle_inspection_job(self, job: ScheduledJob) -> None:
        """处理巡检任务"""
        # 触发监控检测
        import platform
        import subprocess

        devices = job.target_devices
        results = []

        for device in devices:
            ip = job.parameters.get(f'ip_{device}', device)

            # Ping 检测
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", "1000", ip]
            else:
                cmd = ["ping", "-c", "1", "-W", "1", ip]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                status = "online" if result.returncode == 0 else "offline"
            except Exception:
                status = "error"

            results.append({"device": device, "ip": ip, "status": status})

        # 保存巡检结果
        output_dir = Path(job.parameters.get('output_dir', 'inspections'))
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"inspection_{timestamp}.json"
        output_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    def _handle_report_job(self, job: ScheduledJob) -> None:
        """处理报表生成任务"""
        try:
            from netops_toolkit.services.report_engine import (
                ReportEngine,
                ReportFormat,
                ReportTemplate,
            )

            template_name = job.parameters.get('template', 'inspection_summary')
            output_format = job.parameters.get('format', 'both')

            template_map = {
                'inspection_summary': ReportTemplate.INSPECTION_SUMMARY,
                'device_detail': ReportTemplate.DEVICE_DETAIL,
                'anomaly_report': ReportTemplate.ANOMALY_REPORT,
                'monitoring_status': ReportTemplate.MONITORING_STATUS,
            }

            format_map = {
                'pdf': ReportFormat.PDF,
                'excel': ReportFormat.EXCEL,
                'both': ReportFormat.BOTH,
            }

            output_dir = Path(job.parameters.get('output_dir', 'reports'))
            engine = ReportEngine(output_dir)

            # 收集数据（简化版）
            data = {
                'devices': [],
                'summary': {
                    'total_devices': 0,
                    'online_devices': 0,
                    'offline_devices': 0,
                    'alerts': 0,
                    'duration_seconds': 0,
                },
                'anomalies': [],
            }

            engine.generate_report(
                template=template_map.get(template_name, ReportTemplate.INSPECTION_SUMMARY),
                data=data,
                format=format_map.get(output_format, ReportFormat.BOTH),
            )

        except ImportError:
            raise RuntimeError("报表引擎不可用")

    def _handle_ping_check_job(self, job: ScheduledJob) -> None:
        """处理 Ping 检测任务"""
        self._handle_inspection_job(job)  # 复用巡检逻辑


# 便捷函数
_scheduler_instance: SchedulerService | None = None


def get_scheduler() -> SchedulerService:
    """获取全局调度器实例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance


def start_scheduler() -> bool:
    """启动全局调度器"""
    return get_scheduler().start()


def stop_scheduler() -> None:
    """停止全局调度器"""
    if _scheduler_instance:
        _scheduler_instance.stop()
