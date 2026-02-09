"""
NetOps Toolkit - 报表引擎

支持功能:
- PDF报表生成 (ReportLab)
- Excel报表生成 (openpyxl)
- 预置报表模板（巡检摘要、设备明细、异常汇总）
- 动态数据填充
- 图表支持（Excel）
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# 延迟导入可选依赖
REPORTLAB_AVAILABLE = False
OPENPYXL_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm, inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image as RLImage
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    pass

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, PieChart, Reference
    OPENPYXL_AVAILABLE = True
except ImportError:
    pass


class ReportFormat(Enum):
    """报表格式枚举"""
    PDF = "pdf"
    EXCEL = "excel"
    BOTH = "both"


class ReportTemplate(Enum):
    """预置报表模板"""
    INSPECTION_SUMMARY = "inspection_summary"     # 巡检摘要
    DEVICE_DETAIL = "device_detail"               # 设备明细
    ANOMALY_REPORT = "anomaly_report"             # 异常汇总
    MONITORING_STATUS = "monitoring_status"       # 监控状态
    CONFIG_AUDIT = "config_audit"                 # 配置审计
    CUSTOM = "custom"                             # 自定义


@dataclass
class ReportMetadata:
    """报表元数据"""
    title: str
    author: str = "NetOps Toolkit"
    organization: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    description: str = ""
    template: ReportTemplate = ReportTemplate.CUSTOM


@dataclass
class DeviceStatusRecord:
    """设备状态记录"""
    device_name: str
    ip: str
    status: str
    latency_ms: Optional[float] = None
    packet_loss: float = 0.0
    last_check: Optional[datetime] = None
    vendor: str = ""
    group: str = ""
    notes: str = ""


@dataclass
class InspectionResult:
    """巡检结果数据"""
    device_name: str
    ip: str
    command: str
    output: str
    status: str  # success, failed, timeout
    timestamp: datetime = field(default_factory=datetime.now)
    error_msg: str = ""


@dataclass
class AnomalyRecord:
    """异常记录"""
    device_name: str
    ip: str
    anomaly_type: str
    severity: str  # info, warning, critical
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


class ReportEngine:
    """报表生成引擎
    
    支持 PDF 和 Excel 两种格式的报表生成。
    提供预置模板和自定义报表功能。
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """初始化报表引擎
        
        Args:
            output_dir: 报表输出目录，默认为当前目录下的 reports 文件夹
        """
        self.output_dir = output_dir or Path.cwd() / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查依赖可用性
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """检查依赖是否可用"""
        if not REPORTLAB_AVAILABLE:
            print("警告: ReportLab 未安装，PDF 报表功能不可用。请运行: pip install reportlab")
        if not OPENPYXL_AVAILABLE:
            print("警告: openpyxl 未安装，Excel 报表功能不可用。请运行: pip install openpyxl")
    
    def generate_report(
        self,
        template: ReportTemplate,
        data: Dict[str, Any],
        metadata: Optional[ReportMetadata] = None,
        format: ReportFormat = ReportFormat.BOTH,
        filename: Optional[str] = None,
    ) -> Dict[str, Optional[Path]]:
        """生成报表
        
        Args:
            template: 报表模板
            data: 报表数据
            metadata: 报表元数据
            format: 输出格式
            filename: 文件名（不含扩展名）
        
        Returns:
            生成的文件路径字典 {"pdf": Path, "excel": Path}
        """
        if metadata is None:
            metadata = ReportMetadata(
                title=f"NetOps Report - {template.value}",
                template=template,
            )
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"netops_{template.value}_{timestamp}"
        
        results: Dict[str, Optional[Path]] = {"pdf": None, "excel": None}
        
        # 根据模板调用对应的生成方法
        if template == ReportTemplate.INSPECTION_SUMMARY:
            generator = InspectionSummaryGenerator(self.output_dir)
        elif template == ReportTemplate.DEVICE_DETAIL:
            generator = DeviceDetailGenerator(self.output_dir)
        elif template == ReportTemplate.ANOMALY_REPORT:
            generator = AnomalyReportGenerator(self.output_dir)
        elif template == ReportTemplate.MONITORING_STATUS:
            generator = MonitoringStatusGenerator(self.output_dir)
        else:
            generator = CustomReportGenerator(self.output_dir)
        
        if format in (ReportFormat.PDF, ReportFormat.BOTH):
            if REPORTLAB_AVAILABLE:
                results["pdf"] = generator.generate_pdf(data, metadata, filename)
            else:
                print("跳过 PDF 生成：ReportLab 未安装")
        
        if format in (ReportFormat.EXCEL, ReportFormat.BOTH):
            if OPENPYXL_AVAILABLE:
                results["excel"] = generator.generate_excel(data, metadata, filename)
            else:
                print("跳过 Excel 生成：openpyxl 未安装")
        
        return results


class BaseReportGenerator(ABC):
    """报表生成器基类"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    @abstractmethod
    def generate_pdf(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成 PDF 报表"""
        pass
    
    @abstractmethod
    def generate_excel(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成 Excel 报表"""
        pass
    
    def _get_pdf_styles(self) -> Dict[str, Any]:
        """获取 PDF 样式"""
        styles = getSampleStyleSheet()
        
        # 自定义标题样式
        styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # 居中
        ))
        
        styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            textColor=colors.grey,
            alignment=1,
        ))
        
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2E86AB'),
        ))
        
        return styles
    
    def _create_pdf_table(
        self,
        data: List[List[str]],
        col_widths: Optional[List[float]] = None,
        header_bg: colors.Color = colors.HexColor('#2E86AB'),
    ) -> Table:
        """创建 PDF 表格"""
        table = Table(data, colWidths=col_widths)
        
        style = TableStyle([
            # 表头样式
            ('BACKGROUND', (0, 0), (-1, 0), header_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # 数据行样式
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            
            # 网格线
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # 斑马条纹
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ])
        
        table.setStyle(style)
        return table
    
    def _setup_excel_styles(self, ws) -> Dict[str, Any]:
        """设置 Excel 样式"""
        styles = {
            'title_font': Font(size=18, bold=True, color='2E86AB'),
            'header_font': Font(size=11, bold=True, color='FFFFFF'),
            'header_fill': PatternFill(start_color='2E86AB', end_color='2E86AB', fill_type='solid'),
            'data_font': Font(size=10),
            'center_align': Alignment(horizontal='center', vertical='center'),
            'left_align': Alignment(horizontal='left', vertical='center'),
            'border': Border(
                left=Side(style='thin', color='CCCCCC'),
                right=Side(style='thin', color='CCCCCC'),
                top=Side(style='thin', color='CCCCCC'),
                bottom=Side(style='thin', color='CCCCCC'),
            ),
            'status_good': PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid'),
            'status_warning': PatternFill(start_color='FFF9C4', end_color='FFF9C4', fill_type='solid'),
            'status_bad': PatternFill(start_color='FFCDD2', end_color='FFCDD2', fill_type='solid'),
        }
        return styles


class InspectionSummaryGenerator(BaseReportGenerator):
    """巡检摘要报表生成器"""
    
    def generate_pdf(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成巡检摘要 PDF"""
        if not REPORTLAB_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.pdf"
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        styles = self._get_pdf_styles()
        story = []
        
        # 标题
        story.append(Paragraph(metadata.title, styles['ReportTitle']))
        story.append(Paragraph(
            f"生成时间: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            styles['ReportSubtitle']
        ))
        story.append(Spacer(1, 20))
        
        # 摘要统计
        summary = data.get('summary', {})
        story.append(Paragraph("📊 巡检概况", styles['SectionHeader']))
        
        summary_data = [
            ['指标', '数值'],
            ['巡检设备总数', str(summary.get('total_devices', 0))],
            ['正常设备', str(summary.get('online_devices', 0))],
            ['异常设备', str(summary.get('offline_devices', 0))],
            ['告警数量', str(summary.get('alerts', 0))],
            ['巡检耗时', f"{summary.get('duration_seconds', 0):.1f} 秒"],
        ]
        
        table = self._create_pdf_table(summary_data, col_widths=[80*mm, 60*mm])
        story.append(table)
        story.append(Spacer(1, 20))
        
        # 设备状态列表
        devices = data.get('devices', [])
        if devices:
            story.append(Paragraph("🖥️ 设备状态详情", styles['SectionHeader']))
            
            device_data = [['设备名称', 'IP地址', '状态', '延迟(ms)', '丢包率', '检测时间']]
            for dev in devices:
                if isinstance(dev, DeviceStatusRecord):
                    device_data.append([
                        dev.device_name,
                        dev.ip,
                        dev.status,
                        f"{dev.latency_ms:.1f}" if dev.latency_ms else "-",
                        f"{dev.packet_loss:.0f}%",
                        dev.last_check.strftime('%H:%M:%S') if dev.last_check else "-",
                    ])
                elif isinstance(dev, dict):
                    device_data.append([
                        dev.get('device_name', ''),
                        dev.get('ip', ''),
                        dev.get('status', ''),
                        f"{dev.get('latency_ms', 0):.1f}" if dev.get('latency_ms') else "-",
                        f"{dev.get('packet_loss', 0):.0f}%",
                        dev.get('last_check', '-'),
                    ])
            
            table = self._create_pdf_table(device_data)
            story.append(table)
        
        # 异常汇总
        anomalies = data.get('anomalies', [])
        if anomalies:
            story.append(PageBreak())
            story.append(Paragraph("⚠️ 异常汇总", styles['SectionHeader']))
            
            anomaly_data = [['设备', '异常类型', '严重程度', '描述', '时间']]
            for anomaly in anomalies:
                if isinstance(anomaly, AnomalyRecord):
                    anomaly_data.append([
                        anomaly.device_name,
                        anomaly.anomaly_type,
                        anomaly.severity,
                        anomaly.description[:50],
                        anomaly.timestamp.strftime('%H:%M:%S'),
                    ])
                elif isinstance(anomaly, dict):
                    anomaly_data.append([
                        anomaly.get('device_name', ''),
                        anomaly.get('anomaly_type', ''),
                        anomaly.get('severity', ''),
                        anomaly.get('description', '')[:50],
                        anomaly.get('timestamp', ''),
                    ])
            
            table = self._create_pdf_table(anomaly_data)
            story.append(table)
        
        doc.build(story)
        return output_path
    
    def generate_excel(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成巡检摘要 Excel"""
        if not OPENPYXL_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.xlsx"
        wb = Workbook()
        
        # 摘要工作表
        ws_summary = wb.active
        ws_summary.title = "巡检摘要"
        styles = self._setup_excel_styles(ws_summary)
        
        # 标题
        ws_summary['A1'] = metadata.title
        ws_summary['A1'].font = styles['title_font']
        ws_summary.merge_cells('A1:F1')
        
        ws_summary['A2'] = f"生成时间: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        ws_summary.merge_cells('A2:F2')
        
        # 摘要统计
        summary = data.get('summary', {})
        row = 4
        summary_items = [
            ('巡检设备总数', summary.get('total_devices', 0)),
            ('正常设备', summary.get('online_devices', 0)),
            ('异常设备', summary.get('offline_devices', 0)),
            ('告警数量', summary.get('alerts', 0)),
            ('巡检耗时(秒)', summary.get('duration_seconds', 0)),
        ]
        
        for label, value in summary_items:
            ws_summary.cell(row=row, column=1, value=label).font = styles['data_font']
            ws_summary.cell(row=row, column=2, value=value).font = styles['data_font']
            row += 1
        
        # 设备状态工作表
        devices = data.get('devices', [])
        if devices:
            ws_devices = wb.create_sheet("设备状态")
            headers = ['设备名称', 'IP地址', '状态', '延迟(ms)', '丢包率(%)', '检测时间', '厂商', '分组']
            
            for col, header in enumerate(headers, 1):
                cell = ws_devices.cell(row=1, column=col, value=header)
                cell.font = styles['header_font']
                cell.fill = styles['header_fill']
                cell.alignment = styles['center_align']
            
            for row_idx, dev in enumerate(devices, 2):
                if isinstance(dev, DeviceStatusRecord):
                    values = [
                        dev.device_name, dev.ip, dev.status,
                        dev.latency_ms, dev.packet_loss,
                        dev.last_check.strftime('%H:%M:%S') if dev.last_check else '',
                        dev.vendor, dev.group,
                    ]
                elif isinstance(dev, dict):
                    values = [
                        dev.get('device_name', ''),
                        dev.get('ip', ''),
                        dev.get('status', ''),
                        dev.get('latency_ms'),
                        dev.get('packet_loss', 0),
                        dev.get('last_check', ''),
                        dev.get('vendor', ''),
                        dev.get('group', ''),
                    ]
                else:
                    continue
                
                for col, value in enumerate(values, 1):
                    cell = ws_devices.cell(row=row_idx, column=col, value=value)
                    cell.font = styles['data_font']
                    cell.alignment = styles['center_align']
                    cell.border = styles['border']
                    
                    # 状态着色
                    if col == 3:  # 状态列
                        if value in ('online', '在线', '✅'):
                            cell.fill = styles['status_good']
                        elif value in ('warning', '告警', '⚠️'):
                            cell.fill = styles['status_warning']
                        elif value in ('offline', '离线', '❌'):
                            cell.fill = styles['status_bad']
            
            # 自动调整列宽
            for col in range(1, len(headers) + 1):
                ws_devices.column_dimensions[get_column_letter(col)].width = 15
        
        # 异常汇总工作表
        anomalies = data.get('anomalies', [])
        if anomalies:
            ws_anomalies = wb.create_sheet("异常汇总")
            headers = ['设备名称', 'IP地址', '异常类型', '严重程度', '描述', '时间', '已解决']
            
            for col, header in enumerate(headers, 1):
                cell = ws_anomalies.cell(row=1, column=col, value=header)
                cell.font = styles['header_font']
                cell.fill = styles['header_fill']
                cell.alignment = styles['center_align']
            
            for row_idx, anomaly in enumerate(anomalies, 2):
                if isinstance(anomaly, AnomalyRecord):
                    values = [
                        anomaly.device_name, anomaly.ip, anomaly.anomaly_type,
                        anomaly.severity, anomaly.description,
                        anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        '是' if anomaly.resolved else '否',
                    ]
                elif isinstance(anomaly, dict):
                    values = [
                        anomaly.get('device_name', ''),
                        anomaly.get('ip', ''),
                        anomaly.get('anomaly_type', ''),
                        anomaly.get('severity', ''),
                        anomaly.get('description', ''),
                        anomaly.get('timestamp', ''),
                        '是' if anomaly.get('resolved') else '否',
                    ]
                else:
                    continue
                
                for col, value in enumerate(values, 1):
                    cell = ws_anomalies.cell(row=row_idx, column=col, value=value)
                    cell.font = styles['data_font']
                    cell.border = styles['border']
                    
                    # 严重程度着色
                    if col == 4:
                        if value == 'critical':
                            cell.fill = styles['status_bad']
                        elif value == 'warning':
                            cell.fill = styles['status_warning']
            
            for col in range(1, len(headers) + 1):
                ws_anomalies.column_dimensions[get_column_letter(col)].width = 18
        
        wb.save(output_path)
        return output_path


class DeviceDetailGenerator(BaseReportGenerator):
    """设备明细报表生成器"""
    
    def generate_pdf(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成设备明细 PDF"""
        if not REPORTLAB_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.pdf"
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        
        styles = self._get_pdf_styles()
        story = []
        
        story.append(Paragraph(metadata.title, styles['ReportTitle']))
        story.append(Paragraph(
            f"生成时间: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            styles['ReportSubtitle']
        ))
        story.append(Spacer(1, 20))
        
        # 设备清单
        devices = data.get('devices', [])
        if devices:
            story.append(Paragraph("📋 设备清单", styles['SectionHeader']))
            
            device_data = [['名称', 'IP', '厂商', '型号', '分组', '描述']]
            for dev in devices:
                if isinstance(dev, dict):
                    device_data.append([
                        dev.get('name', ''),
                        dev.get('ip', ''),
                        dev.get('vendor', ''),
                        dev.get('model', ''),
                        dev.get('group', ''),
                        dev.get('description', '')[:30],
                    ])
            
            table = self._create_pdf_table(device_data)
            story.append(table)
        
        doc.build(story)
        return output_path
    
    def generate_excel(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成设备明细 Excel"""
        if not OPENPYXL_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "设备明细"
        styles = self._setup_excel_styles(ws)
        
        # 标题
        ws['A1'] = metadata.title
        ws['A1'].font = styles['title_font']
        ws.merge_cells('A1:F1')
        
        # 表头
        headers = ['设备名称', 'IP地址', '厂商', '型号', '分组', '端口', '描述', '标签']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = styles['header_font']
            cell.fill = styles['header_fill']
            cell.alignment = styles['center_align']
        
        # 数据
        devices = data.get('devices', [])
        for row_idx, dev in enumerate(devices, 4):
            if isinstance(dev, dict):
                values = [
                    dev.get('name', ''),
                    dev.get('ip', ''),
                    dev.get('vendor', ''),
                    dev.get('model', ''),
                    dev.get('group', ''),
                    dev.get('port', 22),
                    dev.get('description', ''),
                    ', '.join(dev.get('tags', [])) if dev.get('tags') else '',
                ]
                
                for col, value in enumerate(values, 1):
                    cell = ws.cell(row=row_idx, column=col, value=value)
                    cell.font = styles['data_font']
                    cell.border = styles['border']
        
        # 调整列宽
        col_widths = [15, 15, 12, 15, 12, 8, 25, 20]
        for col, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width
        
        wb.save(output_path)
        return output_path


class AnomalyReportGenerator(BaseReportGenerator):
    """异常报表生成器"""
    
    def generate_pdf(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成异常报表 PDF"""
        if not REPORTLAB_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.pdf"
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        
        styles = self._get_pdf_styles()
        story = []
        
        story.append(Paragraph("⚠️ " + metadata.title, styles['ReportTitle']))
        story.append(Paragraph(
            f"生成时间: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            styles['ReportSubtitle']
        ))
        story.append(Spacer(1, 20))
        
        # 异常统计
        anomalies = data.get('anomalies', [])
        critical_count = sum(1 for a in anomalies if (isinstance(a, AnomalyRecord) and a.severity == 'critical') or (isinstance(a, dict) and a.get('severity') == 'critical'))
        warning_count = sum(1 for a in anomalies if (isinstance(a, AnomalyRecord) and a.severity == 'warning') or (isinstance(a, dict) and a.get('severity') == 'warning'))
        
        story.append(Paragraph("📊 异常统计", styles['SectionHeader']))
        summary_data = [
            ['统计项', '数量'],
            ['异常总数', str(len(anomalies))],
            ['严重异常', str(critical_count)],
            ['警告', str(warning_count)],
        ]
        table = self._create_pdf_table(summary_data, col_widths=[80*mm, 60*mm])
        story.append(table)
        story.append(Spacer(1, 20))
        
        # 异常详情
        if anomalies:
            story.append(Paragraph("📝 异常详情", styles['SectionHeader']))
            anomaly_data = [['设备', 'IP', '类型', '严重程度', '描述', '时间']]
            
            for anomaly in anomalies:
                if isinstance(anomaly, AnomalyRecord):
                    anomaly_data.append([
                        anomaly.device_name,
                        anomaly.ip,
                        anomaly.anomaly_type,
                        anomaly.severity,
                        anomaly.description[:40],
                        anomaly.timestamp.strftime('%H:%M:%S'),
                    ])
                elif isinstance(anomaly, dict):
                    anomaly_data.append([
                        anomaly.get('device_name', ''),
                        anomaly.get('ip', ''),
                        anomaly.get('anomaly_type', ''),
                        anomaly.get('severity', ''),
                        anomaly.get('description', '')[:40],
                        anomaly.get('timestamp', ''),
                    ])
            
            table = self._create_pdf_table(anomaly_data)
            story.append(table)
        
        doc.build(story)
        return output_path
    
    def generate_excel(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成异常报表 Excel"""
        if not OPENPYXL_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "异常报表"
        styles = self._setup_excel_styles(ws)
        
        ws['A1'] = metadata.title
        ws['A1'].font = styles['title_font']
        ws.merge_cells('A1:G1')
        
        headers = ['设备名称', 'IP地址', '异常类型', '严重程度', '描述', '发生时间', '已解决']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = styles['header_font']
            cell.fill = styles['header_fill']
            cell.alignment = styles['center_align']
        
        anomalies = data.get('anomalies', [])
        for row_idx, anomaly in enumerate(anomalies, 4):
            if isinstance(anomaly, AnomalyRecord):
                values = [
                    anomaly.device_name, anomaly.ip, anomaly.anomaly_type,
                    anomaly.severity, anomaly.description,
                    anomaly.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    '是' if anomaly.resolved else '否',
                ]
            elif isinstance(anomaly, dict):
                values = [
                    anomaly.get('device_name', ''),
                    anomaly.get('ip', ''),
                    anomaly.get('anomaly_type', ''),
                    anomaly.get('severity', ''),
                    anomaly.get('description', ''),
                    anomaly.get('timestamp', ''),
                    '是' if anomaly.get('resolved') else '否',
                ]
            else:
                continue
            
            for col, value in enumerate(values, 1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.font = styles['data_font']
                cell.border = styles['border']
                
                if col == 4:  # 严重程度着色
                    if value == 'critical':
                        cell.fill = styles['status_bad']
                    elif value == 'warning':
                        cell.fill = styles['status_warning']
        
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15
        
        wb.save(output_path)
        return output_path


class MonitoringStatusGenerator(BaseReportGenerator):
    """监控状态报表生成器"""
    
    def generate_pdf(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成监控状态 PDF"""
        if not REPORTLAB_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.pdf"
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        
        styles = self._get_pdf_styles()
        story = []
        
        story.append(Paragraph("📊 " + metadata.title, styles['ReportTitle']))
        story.append(Paragraph(
            f"报表时间: {metadata.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            styles['ReportSubtitle']
        ))
        story.append(Spacer(1, 20))
        
        # 设备状态
        devices = data.get('devices', [])
        if devices:
            story.append(Paragraph("设备监控状态", styles['SectionHeader']))
            
            device_data = [['设备', 'IP', '状态', '延迟', '丢包率', '最后检测']]
            for dev in devices:
                if isinstance(dev, dict):
                    device_data.append([
                        dev.get('device_name', ''),
                        dev.get('ip', ''),
                        dev.get('status', ''),
                        f"{dev.get('latency_ms', '-')}" if dev.get('latency_ms') else '-',
                        f"{dev.get('packet_loss', 0):.0f}%",
                        dev.get('last_check', '-'),
                    ])
            
            table = self._create_pdf_table(device_data)
            story.append(table)
        
        doc.build(story)
        return output_path
    
    def generate_excel(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成监控状态 Excel"""
        if not OPENPYXL_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "监控状态"
        styles = self._setup_excel_styles(ws)
        
        ws['A1'] = metadata.title
        ws['A1'].font = styles['title_font']
        
        headers = ['设备名称', 'IP地址', '状态', '延迟(ms)', '丢包率(%)', '最后检测时间']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = styles['header_font']
            cell.fill = styles['header_fill']
        
        devices = data.get('devices', [])
        for row_idx, dev in enumerate(devices, 4):
            if isinstance(dev, dict):
                values = [
                    dev.get('device_name', ''),
                    dev.get('ip', ''),
                    dev.get('status', ''),
                    dev.get('latency_ms'),
                    dev.get('packet_loss', 0),
                    dev.get('last_check', ''),
                ]
                
                for col, value in enumerate(values, 1):
                    cell = ws.cell(row=row_idx, column=col, value=value)
                    cell.font = styles['data_font']
                    cell.border = styles['border']
        
        wb.save(output_path)
        return output_path


class CustomReportGenerator(BaseReportGenerator):
    """自定义报表生成器"""
    
    def generate_pdf(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成自定义 PDF"""
        if not REPORTLAB_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.pdf"
        doc = SimpleDocTemplate(str(output_path), pagesize=A4)
        
        styles = self._get_pdf_styles()
        story = []
        
        story.append(Paragraph(metadata.title, styles['ReportTitle']))
        story.append(Spacer(1, 20))
        
        # 简单渲染数据
        for key, value in data.items():
            if isinstance(value, list) and value:
                story.append(Paragraph(f"📋 {key}", styles['SectionHeader']))
                if isinstance(value[0], dict):
                    headers = list(value[0].keys())
                    table_data = [headers]
                    for item in value:
                        table_data.append([str(item.get(h, '')) for h in headers])
                    table = self._create_pdf_table(table_data)
                    story.append(table)
                story.append(Spacer(1, 10))
        
        doc.build(story)
        return output_path
    
    def generate_excel(
        self, data: Dict[str, Any], metadata: ReportMetadata, filename: str
    ) -> Optional[Path]:
        """生成自定义 Excel"""
        if not OPENPYXL_AVAILABLE:
            return None
        
        output_path = self.output_dir / f"{filename}.xlsx"
        wb = Workbook()
        
        ws = wb.active
        ws.title = "数据"
        ws['A1'] = metadata.title
        
        row = 3
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                headers = list(value[0].keys())
                for col, header in enumerate(headers, 1):
                    ws.cell(row=row, column=col, value=header)
                row += 1
                
                for item in value:
                    for col, header in enumerate(headers, 1):
                        ws.cell(row=row, column=col, value=str(item.get(header, '')))
                    row += 1
                row += 1
        
        wb.save(output_path)
        return output_path
