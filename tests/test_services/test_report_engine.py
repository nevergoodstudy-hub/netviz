"""
ReportEngine 测试模块

测试覆盖:
- ReportFormat
- ReportTemplate
- ReportMetadata
- DeviceStatusRecord
- ReportEngine
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
from pathlib import Path


class TestReportEnums:
    """测试报表枚举"""
    
    def test_report_format_import(self):
        """测试 ReportFormat 导入"""
        from netops_toolkit.services.report_engine import ReportFormat
        
        assert ReportFormat is not None
    
    def test_report_format_values(self):
        """测试 ReportFormat 值"""
        from netops_toolkit.services.report_engine import ReportFormat
        
        assert hasattr(ReportFormat, 'PDF')
        assert hasattr(ReportFormat, 'EXCEL')
    
    def test_report_template_import(self):
        """测试 ReportTemplate 导入"""
        from netops_toolkit.services.report_engine import ReportTemplate
        
        assert ReportTemplate is not None
    
    def test_report_template_values(self):
        """测试 ReportTemplate 值"""
        from netops_toolkit.services.report_engine import ReportTemplate
        
        assert hasattr(ReportTemplate, 'INSPECTION_SUMMARY')
        assert hasattr(ReportTemplate, 'DEVICE_DETAIL')


class TestReportMetadata:
    """测试报表元数据"""
    
    def test_report_metadata_import(self):
        """测试导入"""
        from netops_toolkit.services.report_engine import ReportMetadata
        
        assert ReportMetadata is not None
    
    def test_report_metadata_creation(self):
        """测试创建元数据"""
        from netops_toolkit.services.report_engine import ReportMetadata
        
        metadata = ReportMetadata(
            title="Network Status Report",
            author="Admin"
        )
        
        assert metadata.title == "Network Status Report"
        assert metadata.author == "Admin"


class TestDeviceStatusRecord:
    """测试设备状态记录"""
    
    def test_device_status_record_import(self):
        """测试导入"""
        from netops_toolkit.services.report_engine import DeviceStatusRecord
        
        assert DeviceStatusRecord is not None
    
    def test_device_status_record_creation(self):
        """测试创建记录"""
        from netops_toolkit.services.report_engine import DeviceStatusRecord
        
        record = DeviceStatusRecord(
            device_name="Router1",
            ip="192.168.1.1",
            status="online"
        )
        
        assert record.device_name == "Router1"
        assert record.status == "online"


class TestInspectionResult:
    """测试巡检结果"""
    
    def test_inspection_result_import(self):
        """测试导入"""
        from netops_toolkit.services.report_engine import InspectionResult
        
        assert InspectionResult is not None
    
    def test_inspection_result_creation(self):
        """测试创建"""
        from netops_toolkit.services.report_engine import InspectionResult
        
        result = InspectionResult(
            device_name="Router1",
            ip="192.168.1.1",
            command="show version",
            output="...",
            status="success"
        )
        
        assert result.device_name == "Router1"
        assert result.command == "show version"


class TestAnomalyRecord:
    """测试异常记录"""
    
    def test_anomaly_record_import(self):
        """测试导入"""
        from netops_toolkit.services.report_engine import AnomalyRecord
        
        assert AnomalyRecord is not None
    
    def test_anomaly_record_creation(self):
        """测试创建"""
        from netops_toolkit.services.report_engine import AnomalyRecord
        
        record = AnomalyRecord(
            device_name="Router1",
            ip="192.168.1.1",
            anomaly_type="high_cpu",
            severity="warning",
            description="CPU usage > 90%"
        )
        
        assert record.device_name == "Router1"
        assert record.severity == "warning"


class TestReportEngine:
    """测试报表引擎"""
    
    def test_report_engine_import(self):
        """测试导入"""
        from netops_toolkit.services.report_engine import ReportEngine
        
        assert ReportEngine is not None
    
    def test_report_engine_creation(self):
        """测试创建"""
        from netops_toolkit.services.report_engine import ReportEngine
        
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ReportEngine(output_dir=Path(tmpdir))
            assert engine is not None
    
    def test_report_engine_output_dir(self):
        """测试输出目录"""
        from netops_toolkit.services.report_engine import ReportEngine
        
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ReportEngine(output_dir=Path(tmpdir))
            assert engine.output_dir.exists()
