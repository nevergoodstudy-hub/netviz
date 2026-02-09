"""
NetOps Toolkit - 变更审计服务

支持功能:
- SQLite 持久化审计日志
- 多种事件类型追踪（配置变更、设备访问、命令执行等）
- 变更前后值记录
- 灵活查询接口
- JSON/CSV 导出

符合 ITIL 变更管理标准:
- 完整审计追踪
- 时间戳和操作人记录
- 变更影响评估
"""

from __future__ import annotations

import csv
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union


class AuditEventType(Enum):
    """审计事件类型
    
    基于 ITIL 变更管理分类:
    - CONFIG_*: 配置变更相关
    - DEVICE_*: 设备访问相关
    - COMMAND_*: 命令执行相关
    - REPORT_*: 报表生成相关
    - SYSTEM_*: 系统操作相关
    - COMPLIANCE_*: 合规检查相关
    """
    # 配置变更
    CONFIG_BACKUP = "config_backup"           # 配置备份
    CONFIG_PUSH = "config_push"               # 配置推送
    CONFIG_RESTORE = "config_restore"         # 配置恢复
    CONFIG_COMPARE = "config_compare"         # 配置对比
    
    # 设备访问
    DEVICE_CONNECT = "device_connect"         # 设备连接
    DEVICE_DISCONNECT = "device_disconnect"   # 设备断开
    DEVICE_ADD = "device_add"                 # 添加设备
    DEVICE_REMOVE = "device_remove"           # 移除设备
    DEVICE_UPDATE = "device_update"           # 更新设备信息
    
    # 命令执行
    COMMAND_EXECUTE = "command_execute"       # 执行命令
    COMMAND_BATCH = "command_batch"           # 批量命令
    
    # 报表相关
    REPORT_GENERATE = "report_generate"       # 生成报表
    REPORT_EXPORT = "report_export"           # 导出报表
    
    # 系统操作
    SYSTEM_LOGIN = "system_login"             # 系统登录
    SYSTEM_LOGOUT = "system_logout"           # 系统登出
    SYSTEM_SETTINGS = "system_settings"       # 系统设置变更
    SCHEDULER_JOB = "scheduler_job"           # 调度任务
    
    # 合规相关
    COMPLIANCE_CHECK = "compliance_check"     # 合规检查
    COMPLIANCE_REPORT = "compliance_report"   # 合规报告
    
    # 拓扑相关
    TOPOLOGY_VIEW = "topology_view"           # 拓扑查看
    TOPOLOGY_EXPORT = "topology_export"       # 拓扑导出


class AuditSeverity(Enum):
    """审计严重级别"""
    INFO = "info"           # 信息
    WARNING = "warning"     # 警告
    CRITICAL = "critical"   # 关键
    ERROR = "error"         # 错误


class AuditResult(Enum):
    """审计操作结果"""
    SUCCESS = "success"     # 成功
    FAILURE = "failure"     # 失败
    PARTIAL = "partial"     # 部分成功
    SKIPPED = "skipped"     # 跳过


@dataclass
class AuditRecord:
    """审计记录数据类
    
    符合 ITIL 审计追踪标准:
    - 谁 (operator): 操作人
    - 什么 (event_type): 操作类型
    - 什么时候 (timestamp): 时间
    - 在哪里 (device): 目标设备
    - 为什么 (description): 原因描述
    - 结果 (result): 操作结果
    """
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: AuditEventType = AuditEventType.COMMAND_EXECUTE
    severity: AuditSeverity = AuditSeverity.INFO
    operator: str = ""              # 操作人
    device_name: str = ""           # 设备名称
    device_ip: str = ""             # 设备IP
    description: str = ""           # 操作描述
    old_value: str = ""             # 变更前的值
    new_value: str = ""             # 变更后的值
    result: AuditResult = AuditResult.SUCCESS
    error_message: str = ""         # 错误信息
    duration_ms: int = 0            # 执行时长(毫秒)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "operator": self.operator,
            "device_name": self.device_name,
            "device_ip": self.device_ip,
            "description": self.description,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "result": self.result.value,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditRecord":
        """从字典创建"""
        return cls(
            id=data.get("id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            event_type=AuditEventType(data.get("event_type", "command_execute")),
            severity=AuditSeverity(data.get("severity", "info")),
            operator=data.get("operator", ""),
            device_name=data.get("device_name", ""),
            device_ip=data.get("device_ip", ""),
            description=data.get("description", ""),
            old_value=data.get("old_value", ""),
            new_value=data.get("new_value", ""),
            result=AuditResult(data.get("result", "success")),
            error_message=data.get("error_message", ""),
            duration_ms=data.get("duration_ms", 0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AuditQuery:
    """审计查询参数"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: List[AuditEventType] = field(default_factory=list)
    severities: List[AuditSeverity] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)
    device_names: List[str] = field(default_factory=list)
    device_ips: List[str] = field(default_factory=list)
    results: List[AuditResult] = field(default_factory=list)
    keyword: str = ""               # 描述关键字搜索
    limit: int = 1000               # 最大返回条数
    offset: int = 0                 # 偏移量


@dataclass
class AuditSummary:
    """审计统计摘要"""
    total_records: int = 0
    success_count: int = 0
    failure_count: int = 0
    partial_count: int = 0
    by_event_type: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    by_device: Dict[str, int] = field(default_factory=dict)
    by_operator: Dict[str, int] = field(default_factory=dict)
    time_range: Tuple[Optional[datetime], Optional[datetime]] = (None, None)


class AuditStore:
    """审计存储层
    
    使用 SQLite 作为后端存储，支持:
    - WAL 模式提高并发性能
    - 自动创建表和索引
    - 线程安全
    """
    
    # 数据库表结构
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'info',
        operator TEXT,
        device_name TEXT,
        device_ip TEXT,
        description TEXT,
        old_value TEXT,
        new_value TEXT,
        result TEXT NOT NULL DEFAULT 'success',
        error_message TEXT,
        duration_ms INTEGER DEFAULT 0,
        metadata TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
    CREATE INDEX IF NOT EXISTS idx_audit_device_name ON audit_log(device_name);
    CREATE INDEX IF NOT EXISTS idx_audit_device_ip ON audit_log(device_ip);
    CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_log(operator);
    CREATE INDEX IF NOT EXISTS idx_audit_result ON audit_log(result);
    """
    
    def __init__(self, db_path: Union[str, Path] = "data/audit.db"):
        """初始化审计存储
        
        Args:
            db_path: 数据库文件路径
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._local = threading.local()
        self._lock = threading.RLock()
        
        # 初始化数据库
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                isolation_level=None,  # 自动提交
            )
            self._local.conn.row_factory = sqlite3.Row
            # 启用 WAL 模式
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn
    
    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """事务上下文管理器"""
        conn = self._get_connection()
        with self._lock:
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN")
                yield cursor
                cursor.execute("COMMIT")
            except Exception:
                cursor.execute("ROLLBACK")
                raise
    
    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = self._get_connection()
        conn.executescript(self.SCHEMA)
    
    def insert(self, record: AuditRecord) -> int:
        """插入审计记录
        
        Returns:
            记录ID
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            INSERT INTO audit_log (
                timestamp, event_type, severity, operator,
                device_name, device_ip, description,
                old_value, new_value, result,
                error_message, duration_ms, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.timestamp.isoformat(),
                record.event_type.value,
                record.severity.value,
                record.operator,
                record.device_name,
                record.device_ip,
                record.description,
                record.old_value,
                record.new_value,
                record.result.value,
                record.error_message,
                record.duration_ms,
                json.dumps(record.metadata, ensure_ascii=False),
            ),
        )
        return cursor.lastrowid
    
    def query(self, query: AuditQuery) -> List[AuditRecord]:
        """查询审计记录"""
        conditions = []
        params = []
        
        if query.start_time:
            conditions.append("timestamp >= ?")
            params.append(query.start_time.isoformat())
        
        if query.end_time:
            conditions.append("timestamp <= ?")
            params.append(query.end_time.isoformat())
        
        if query.event_types:
            placeholders = ",".join("?" * len(query.event_types))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(e.value for e in query.event_types)
        
        if query.severities:
            placeholders = ",".join("?" * len(query.severities))
            conditions.append(f"severity IN ({placeholders})")
            params.extend(s.value for s in query.severities)
        
        if query.operators:
            placeholders = ",".join("?" * len(query.operators))
            conditions.append(f"operator IN ({placeholders})")
            params.extend(query.operators)
        
        if query.device_names:
            placeholders = ",".join("?" * len(query.device_names))
            conditions.append(f"device_name IN ({placeholders})")
            params.extend(query.device_names)
        
        if query.device_ips:
            placeholders = ",".join("?" * len(query.device_ips))
            conditions.append(f"device_ip IN ({placeholders})")
            params.extend(query.device_ips)
        
        if query.results:
            placeholders = ",".join("?" * len(query.results))
            conditions.append(f"result IN ({placeholders})")
            params.extend(r.value for r in query.results)
        
        if query.keyword:
            conditions.append("description LIKE ?")
            params.append(f"%{query.keyword}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT * FROM audit_log
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """
        params.extend([query.limit, query.offset])
        
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        
        records = []
        for row in cursor.fetchall():
            try:
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
            except json.JSONDecodeError:
                metadata = {}
            
            records.append(AuditRecord(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                event_type=AuditEventType(row["event_type"]),
                severity=AuditSeverity(row["severity"]),
                operator=row["operator"] or "",
                device_name=row["device_name"] or "",
                device_ip=row["device_ip"] or "",
                description=row["description"] or "",
                old_value=row["old_value"] or "",
                new_value=row["new_value"] or "",
                result=AuditResult(row["result"]),
                error_message=row["error_message"] or "",
                duration_ms=row["duration_ms"] or 0,
                metadata=metadata,
            ))
        
        return records
    
    def get_by_id(self, record_id: int) -> Optional[AuditRecord]:
        """根据ID获取记录"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM audit_log WHERE id = ?",
            (record_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except json.JSONDecodeError:
            metadata = {}
        
        return AuditRecord(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            event_type=AuditEventType(row["event_type"]),
            severity=AuditSeverity(row["severity"]),
            operator=row["operator"] or "",
            device_name=row["device_name"] or "",
            device_ip=row["device_ip"] or "",
            description=row["description"] or "",
            old_value=row["old_value"] or "",
            new_value=row["new_value"] or "",
            result=AuditResult(row["result"]),
            error_message=row["error_message"] or "",
            duration_ms=row["duration_ms"] or 0,
            metadata=metadata,
        )
    
    def get_summary(self, query: Optional[AuditQuery] = None) -> AuditSummary:
        """获取统计摘要"""
        if query is None:
            query = AuditQuery()
        
        records = self.query(AuditQuery(
            start_time=query.start_time,
            end_time=query.end_time,
            limit=100000,  # 获取所有用于统计
        ))
        
        summary = AuditSummary()
        summary.total_records = len(records)
        
        for record in records:
            # 结果统计
            if record.result == AuditResult.SUCCESS:
                summary.success_count += 1
            elif record.result == AuditResult.FAILURE:
                summary.failure_count += 1
            elif record.result == AuditResult.PARTIAL:
                summary.partial_count += 1
            
            # 事件类型统计
            event_type = record.event_type.value
            summary.by_event_type[event_type] = summary.by_event_type.get(event_type, 0) + 1
            
            # 严重级别统计
            severity = record.severity.value
            summary.by_severity[severity] = summary.by_severity.get(severity, 0) + 1
            
            # 设备统计
            if record.device_name:
                summary.by_device[record.device_name] = summary.by_device.get(record.device_name, 0) + 1
            
            # 操作人统计
            if record.operator:
                summary.by_operator[record.operator] = summary.by_operator.get(record.operator, 0) + 1
        
        # 时间范围
        if records:
            timestamps = [r.timestamp for r in records]
            summary.time_range = (min(timestamps), max(timestamps))
        
        return summary
    
    def delete_old_records(self, days: int = 90) -> int:
        """删除过期记录
        
        Args:
            days: 保留天数
        
        Returns:
            删除的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM audit_log WHERE timestamp < ?",
            (cutoff.isoformat(),),
        )
        return cursor.rowcount
    
    def vacuum(self) -> None:
        """压缩数据库"""
        conn = self._get_connection()
        conn.execute("VACUUM")
    
    def close(self) -> None:
        """关闭连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class AuditService:
    """审计服务
    
    提供审计日志的统一接口，包括:
    - 记录操作日志
    - 查询和筛选
    - 导出报告
    - 统计分析
    """
    
    _instance: Optional["AuditService"] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs) -> "AuditService":
        """单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, db_path: Union[str, Path] = "data/audit.db"):
        """初始化服务
        
        Args:
            db_path: 数据库文件路径
        """
        if self._initialized:
            return
        
        self._store = AuditStore(db_path)
        self._default_operator = os.environ.get("NETOPS_USERNAME", "system")
        self._initialized = True
    
    def log(
        self,
        event_type: AuditEventType,
        description: str,
        *,
        device_name: str = "",
        device_ip: str = "",
        old_value: str = "",
        new_value: str = "",
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str = "",
        duration_ms: int = 0,
        severity: AuditSeverity = AuditSeverity.INFO,
        operator: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """记录审计日志
        
        这是最常用的接口，用于记录各种操作。
        
        Args:
            event_type: 事件类型
            description: 操作描述
            device_name: 设备名称
            device_ip: 设备IP
            old_value: 变更前的值
            new_value: 变更后的值
            result: 操作结果
            error_message: 错误信息
            duration_ms: 执行时长
            severity: 严重级别
            operator: 操作人
            metadata: 附加元数据
        
        Returns:
            记录ID
        """
        record = AuditRecord(
            timestamp=datetime.now(),
            event_type=event_type,
            severity=severity,
            operator=operator or self._default_operator,
            device_name=device_name,
            device_ip=device_ip,
            description=description,
            old_value=old_value,
            new_value=new_value,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        
        return self._store.insert(record)
    
    def log_config_backup(
        self,
        device_name: str,
        device_ip: str,
        *,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str = "",
        backup_path: str = "",
        duration_ms: int = 0,
    ) -> int:
        """记录配置备份操作"""
        return self.log(
            AuditEventType.CONFIG_BACKUP,
            f"备份配置: {device_name}",
            device_name=device_name,
            device_ip=device_ip,
            new_value=backup_path,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata={"backup_path": backup_path},
        )
    
    def log_config_push(
        self,
        device_name: str,
        device_ip: str,
        config: str,
        *,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str = "",
        duration_ms: int = 0,
    ) -> int:
        """记录配置推送操作"""
        # 截断过长配置
        config_preview = config[:500] + "..." if len(config) > 500 else config
        
        return self.log(
            AuditEventType.CONFIG_PUSH,
            f"推送配置到: {device_name}",
            device_name=device_name,
            device_ip=device_ip,
            new_value=config_preview,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            severity=AuditSeverity.WARNING,  # 配置推送是高风险操作
            metadata={"config_length": len(config)},
        )
    
    def log_command_execute(
        self,
        device_name: str,
        device_ip: str,
        command: str,
        output: str = "",
        *,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str = "",
        duration_ms: int = 0,
    ) -> int:
        """记录命令执行操作"""
        # 截断过长输出
        output_preview = output[:500] + "..." if len(output) > 500 else output
        
        return self.log(
            AuditEventType.COMMAND_EXECUTE,
            f"执行命令: {command}",
            device_name=device_name,
            device_ip=device_ip,
            old_value=command,
            new_value=output_preview,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata={"command": command, "output_length": len(output)},
        )
    
    def log_device_connect(
        self,
        device_name: str,
        device_ip: str,
        *,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str = "",
    ) -> int:
        """记录设备连接"""
        return self.log(
            AuditEventType.DEVICE_CONNECT,
            f"连接设备: {device_name} ({device_ip})",
            device_name=device_name,
            device_ip=device_ip,
            result=result,
            error_message=error_message,
        )
    
    def log_report_generate(
        self,
        report_type: str,
        output_path: str,
        *,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str = "",
        duration_ms: int = 0,
    ) -> int:
        """记录报表生成"""
        return self.log(
            AuditEventType.REPORT_GENERATE,
            f"生成报表: {report_type}",
            new_value=output_path,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata={"report_type": report_type, "output_path": output_path},
        )
    
    def log_compliance_check(
        self,
        device_name: str,
        device_ip: str,
        score: float,
        *,
        result: AuditResult = AuditResult.SUCCESS,
        duration_ms: int = 0,
    ) -> int:
        """记录合规检查"""
        return self.log(
            AuditEventType.COMPLIANCE_CHECK,
            f"合规检查: {device_name} 得分 {score:.1f}",
            device_name=device_name,
            device_ip=device_ip,
            new_value=f"{score:.1f}",
            result=result,
            duration_ms=duration_ms,
            metadata={"score": score},
        )
    
    def query(self, query: AuditQuery) -> List[AuditRecord]:
        """查询审计记录"""
        return self._store.query(query)
    
    def query_recent(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """查询最近的审计记录"""
        return self.query(AuditQuery(
            start_time=datetime.now() - timedelta(hours=hours),
            limit=limit,
        ))
    
    def query_by_device(
        self,
        device_name: str,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """查询指定设备的审计记录"""
        return self.query(AuditQuery(
            device_names=[device_name],
            limit=limit,
        ))
    
    def query_by_type(
        self,
        event_type: AuditEventType,
        limit: int = 100,
    ) -> List[AuditRecord]:
        """查询指定类型的审计记录"""
        return self.query(AuditQuery(
            event_types=[event_type],
            limit=limit,
        ))
    
    def query_failures(self, limit: int = 100) -> List[AuditRecord]:
        """查询失败的操作"""
        return self.query(AuditQuery(
            results=[AuditResult.FAILURE, AuditResult.ERROR],
            limit=limit,
        ))
    
    def get_by_id(self, record_id: int) -> Optional[AuditRecord]:
        """根据ID获取记录"""
        return self._store.get_by_id(record_id)
    
    def get_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AuditSummary:
        """获取统计摘要"""
        return self._store.get_summary(AuditQuery(
            start_time=start_time,
            end_time=end_time,
        ))
    
    def export_json(
        self,
        output_path: Path,
        query: Optional[AuditQuery] = None,
    ) -> int:
        """导出为 JSON 格式
        
        Returns:
            导出的记录数
        """
        records = self.query(query or AuditQuery())
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "export_time": datetime.now().isoformat(),
            "total_records": len(records),
            "records": [r.to_dict() for r in records],
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return len(records)
    
    def export_csv(
        self,
        output_path: Path,
        query: Optional[AuditQuery] = None,
    ) -> int:
        """导出为 CSV 格式
        
        Returns:
            导出的记录数
        """
        records = self.query(query or AuditQuery())
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = [
            "id", "timestamp", "event_type", "severity",
            "operator", "device_name", "device_ip",
            "description", "old_value", "new_value",
            "result", "error_message", "duration_ms",
        ]
        
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                row = record.to_dict()
                # 移除 metadata 字段（CSV 不适合存储复杂结构）
                row.pop("metadata", None)
                writer.writerow(row)
        
        return len(records)
    
    def generate_report_text(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """生成文本格式报告"""
        summary = self.get_summary(start_time, end_time)
        records = self.query(AuditQuery(
            start_time=start_time,
            end_time=end_time,
            limit=100,
        ))
        
        lines = []
        
        # 标题
        lines.append("=" * 70)
        lines.append("  审计日志报告")
        lines.append("=" * 70)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if summary.time_range[0] and summary.time_range[1]:
            lines.append(f"时间范围: {summary.time_range[0].strftime('%Y-%m-%d %H:%M')} "
                        f"至 {summary.time_range[1].strftime('%Y-%m-%d %H:%M')}")
        
        lines.append("-" * 70)
        
        # 摘要统计
        lines.append("📊 统计摘要")
        lines.append(f"  总记录数: {summary.total_records}")
        lines.append(f"  成功: {summary.success_count}")
        lines.append(f"  失败: {summary.failure_count}")
        lines.append(f"  部分成功: {summary.partial_count}")
        lines.append("")
        
        # 事件类型分布
        if summary.by_event_type:
            lines.append("📋 事件类型分布")
            for event_type, count in sorted(summary.by_event_type.items(), key=lambda x: -x[1]):
                lines.append(f"  {event_type}: {count}")
            lines.append("")
        
        # 设备分布
        if summary.by_device:
            lines.append("🖥️ 设备操作分布 (Top 10)")
            for device, count in sorted(summary.by_device.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"  {device}: {count}")
            lines.append("")
        
        # 最近记录
        if records:
            lines.append("-" * 70)
            lines.append("📜 最近操作记录")
            lines.append("-" * 70)
            
            result_icons = {
                AuditResult.SUCCESS: "✅",
                AuditResult.FAILURE: "❌",
                AuditResult.PARTIAL: "⚠️",
                AuditResult.SKIPPED: "⏭️",
            }
            
            for record in records[:20]:
                icon = result_icons.get(record.result, "❓")
                time_str = record.timestamp.strftime("%m-%d %H:%M")
                device = record.device_name or "-"
                lines.append(f"  {icon} [{time_str}] {record.event_type.value}")
                lines.append(f"      {record.description}")
                if device != "-":
                    lines.append(f"      设备: {device}")
        
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def cleanup(self, days: int = 90) -> int:
        """清理过期记录
        
        Args:
            days: 保留天数
        
        Returns:
            删除的记录数
        """
        count = self._store.delete_old_records(days)
        if count > 0:
            self._store.vacuum()
        return count
    
    def close(self) -> None:
        """关闭服务"""
        self._store.close()


# 全局便捷函数
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """获取全局审计服务实例"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


def audit_log(
    event_type: AuditEventType,
    description: str,
    **kwargs,
) -> int:
    """便捷的审计日志记录函数"""
    return get_audit_service().log(event_type, description, **kwargs)
