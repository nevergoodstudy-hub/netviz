"""
数据导出工具模块

提供JSON、CSV等格式的数据导出功能。
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)


def export_to_json(
    data: Any,
    output_path: Path,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> bool:
    """
    导出数据为JSON格式
    
    Args:
        data: 要导出的数据
        output_path: 输出文件路径
        indent: 缩进空格数
        ensure_ascii: 是否转义非ASCII字符
        
    Returns:
        True表示成功, False表示失败
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii, default=str)
        
        logger.info(f"数据已导出为JSON: {output_path}")
        return True
    except Exception as e:
        logger.error(f"导出JSON失败: {e}")
        return False


def export_to_csv(
    data: List[Dict[str, Any]],
    output_path: Path,
    fieldnames: Optional[List[str]] = None,
) -> bool:
    """
    导出数据为CSV格式
    
    Args:
        data: 要导出的数据列表 (列表中每个元素为字典)
        output_path: 输出文件路径
        fieldnames: CSV字段名列表 (None表示自动从数据中提取)
        
    Returns:
        True表示成功, False表示失败
    """
    if not data:
        logger.warning("数据为空,无法导出CSV")
        return False
    
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 自动提取字段名
        if fieldnames is None:
            fieldnames = list(data[0].keys())
        
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"数据已导出为CSV: {output_path}")
        return True
    except Exception as e:
        logger.error(f"导出CSV失败: {e}")
        return False


def format_table_data(
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
) -> List[List[str]]:
    """
    格式化表格数据
    
    将字典列表转换为二维列表,用于表格展示。
    
    Args:
        data: 数据列表
        columns: 要显示的列 (None表示全部)
        
    Returns:
        二维列表 (包含表头和数据行)
    """
    if not data:
        return []
    
    # 确定列
    if columns is None:
        columns = list(data[0].keys())
    
    # 构建表格数据
    table = [columns]  # 表头
    
    for row in data:
        table.append([str(row.get(col, "")) for col in columns])
    
    return table


def generate_report_filename(
    prefix: str,
    extension: str = "json",
    timestamp: bool = True,
) -> str:
    """
    生成报告文件名
    
    Args:
        prefix: 文件名前缀
        extension: 文件扩展名
        timestamp: 是否添加时间戳
        
    Returns:
        文件名字符串
    """
    if timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{ts}.{extension}"
    else:
        return f"{prefix}.{extension}"


def save_report(
    data: Any,
    report_dir: Path,
    prefix: str = "report",
    format: str = "json",
) -> Optional[Path]:
    """
    保存报告文件
    
    Args:
        data: 报告数据
        report_dir: 报告目录
        prefix: 文件名前缀
        format: 导出格式 (json 或 csv)
        
    Returns:
        保存的文件路径, 失败返回None
    """
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    
    filename = generate_report_filename(prefix, extension=format)
    output_path = report_dir / filename
    
    if format.lower() == "json":
        success = export_to_json(data, output_path)
    elif format.lower() == "csv":
        if not isinstance(data, list):
            logger.error("CSV格式要求数据为列表类型")
            return None
        success = export_to_csv(data, output_path)
    else:
        logger.error(f"不支持的导出格式: {format}")
        return None
    
    return output_path if success else None


def dict_to_pretty_string(data: Dict[str, Any], indent: int = 2) -> str:
    """
    将字典转换为美化的字符串
    
    Args:
        data: 字典数据
        indent: 缩进空格数
        
    Returns:
        格式化后的字符串
    """
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def flatten_dict(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    扁平化嵌套字典
    
    Args:
        data: 嵌套字典
        parent_key: 父键名
        sep: 键分隔符
        
    Returns:
        扁平化后的字典
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


__all__ = [
    "export_to_json",
    "export_to_csv",
    "format_table_data",
    "generate_report_filename",
    "save_report",
    "dict_to_pretty_string",
    "flatten_dict",
]
