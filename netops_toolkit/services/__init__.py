"""
NetOps Toolkit 服务模块

提供后端服务功能:
- ReportEngine: 报表生成引擎 (PDF/Excel)
- SchedulerService: 任务调度服务 (APScheduler)
- TopologyService: 网络拓扑可视化服务
- ComplianceService: 配置合规检查服务
"""

from .report_engine import ReportEngine, ReportTemplate, ReportFormat
from .scheduler_service import (
    SchedulerService, ScheduledJob, JobType, JobStatus, TriggerType,
    get_scheduler, start_scheduler, stop_scheduler,
)
from .topology_service import (
    TopologyService, TopologyBuilder, ASCIITopologyRenderer,
    TopologyNode, TopologyLink, NodeType, NETWORKX_AVAILABLE,
)
from .compliance_service import (
    ComplianceService, ComplianceChecker, ComplianceRule, ComplianceResult,
    DeviceComplianceReport, ComplianceLevel, RuleType, BUILTIN_RULES,
)
from .audit_service import (
    AuditService, AuditStore, AuditRecord, AuditQuery, AuditSummary,
    AuditEventType, AuditSeverity, AuditResult,
    get_audit_service, audit_log,
)

__all__ = [
    # 报表引擎
    "ReportEngine",
    "ReportTemplate",
    "ReportFormat",
    # 调度服务
    "SchedulerService",
    "ScheduledJob",
    "JobType",
    "JobStatus",
    "TriggerType",
    "get_scheduler",
    "start_scheduler",
    "stop_scheduler",
    # 拓扑服务
    "TopologyService",
    "TopologyBuilder",
    "ASCIITopologyRenderer",
    "TopologyNode",
    "TopologyLink",
    "NodeType",
    "NETWORKX_AVAILABLE",
    # 合规服务
    "ComplianceService",
    "ComplianceChecker",
    "ComplianceRule",
    "ComplianceResult",
    "DeviceComplianceReport",
    "ComplianceLevel",
    "RuleType",
    "BUILTIN_RULES",
    # 审计服务
    "AuditService",
    "AuditStore",
    "AuditRecord",
    "AuditQuery",
    "AuditSummary",
    "AuditEventType",
    "AuditSeverity",
    "AuditResult",
    "get_audit_service",
    "audit_log",
]
