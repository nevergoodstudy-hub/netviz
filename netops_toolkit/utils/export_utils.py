"""数据导出工具模块

提供JSON、CSV、HTML、Markdown等格式的数据导出功能。
"""

import csv
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)

# HTML 报告模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.8; }}
        .content {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status-success {{ color: #28a745; }}
        .status-failed {{ color: #dc3545; }}
        .status-partial {{ color: #ffc107; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{ background-color: #f8f9fa; }}
        .metadata {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        .error {{ color: #dc3545; margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>生成时间: {timestamp}</p>
    </div>
    <div class="content">
        {content}
    </div>
    <div class="metadata">
        <p>由 NetOps Toolkit 生成</p>
    </div>
</body>
</html>
"""


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


def export_to_html(
    data: Any,
    output_path: Path,
    title: str = "NetOps 报告",
    plugin_name: str = "",
    status: str = "success",
    errors: Optional[List[str]] = None,
) -> bool:
    """
    导出数据为HTML格式报告
    
    Args:
        data: 要导出的数据
        output_path: 输出文件路径
        title: 报告标题
        plugin_name: 插件名称
        status: 执行状态
        errors: 错误列表
        
    Returns:
        True表示成功, False表示失败
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建内容
        content_parts = []
        
        # 状态信息
        status_class = f"status-{status.lower()}"
        status_text = {"success": "成功", "failed": "失败", "partial": "部分成功"}.get(status.lower(), status)
        content_parts.append(f'<p><strong>执行状态:</strong> <span class="{status_class}">{status_text}</span></p>')
        
        if plugin_name:
            content_parts.append(f'<p><strong>插件:</strong> {html.escape(plugin_name)}</p>')
        
        # 错误信息
        if errors:
            content_parts.append('<div class="errors"><strong>错误信息:</strong>')
            for err in errors:
                content_parts.append(f'<p class="error">• {html.escape(str(err))}</p>')
            content_parts.append('</div>')
        
        # 数据内容
        content_parts.append('<h2>结果数据</h2>')
        
        if isinstance(data, list) and data and isinstance(data[0], dict):
            # 列表数据渲染为表格
            content_parts.append(_render_html_table(data))
        elif isinstance(data, dict):
            # 字典数据渲染为键值对
            content_parts.append(_render_html_dict(data))
        else:
            # 其他数据渲染为 JSON
            content_parts.append(f'<pre>{html.escape(json.dumps(data, indent=2, ensure_ascii=False, default=str))}</pre>')
        
        # 生成完整 HTML
        html_content = HTML_TEMPLATE.format(
            title=html.escape(title),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            content="\n".join(content_parts)
        )
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"数据已导出为HTML: {output_path}")
        return True
    except Exception as e:
        logger.error(f"导出HTML失败: {e}")
        return False


def _render_html_table(data: List[Dict[str, Any]]) -> str:
    """渲染 HTML 表格"""
    if not data:
        return "<p>无数据</p>"
    
    headers = list(data[0].keys())
    
    table_html = ['<table>']
    # 表头
    table_html.append('<thead><tr>')
    for h in headers:
        table_html.append(f'<th>{html.escape(str(h))}</th>')
    table_html.append('</tr></thead>')
    # 表体
    table_html.append('<tbody>')
    for row in data:
        table_html.append('<tr>')
        for h in headers:
            val = row.get(h, "")
            table_html.append(f'<td>{html.escape(str(val))}</td>')
        table_html.append('</tr>')
    table_html.append('</tbody></table>')
    
    return "\n".join(table_html)


def _render_html_dict(data: Dict[str, Any]) -> str:
    """渲染字典为 HTML"""
    items = ['<table>']
    items.append('<thead><tr><th>键</th><th>值</th></tr></thead><tbody>')
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value, ensure_ascii=False, default=str)
        else:
            val_str = str(value)
        items.append(f'<tr><td>{html.escape(str(key))}</td><td>{html.escape(val_str)}</td></tr>')
    items.append('</tbody></table>')
    return "\n".join(items)


def export_to_markdown(
    data: Any,
    output_path: Path,
    title: str = "NetOps 报告",
    plugin_name: str = "",
    status: str = "success",
    errors: Optional[List[str]] = None,
) -> bool:
    """
    导出数据为Markdown格式报告
    
    Args:
        data: 要导出的数据
        output_path: 输出文件路径
        title: 报告标题
        plugin_name: 插件名称
        status: 执行状态
        errors: 错误列表
        
    Returns:
        True表示成功, False表示失败
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        md_lines = [f"# {title}", ""]
        md_lines.append(f"**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        
        # 状态信息
        status_emoji = {"success": "✅", "failed": "❌", "partial": "⚠️"}.get(status.lower(), "ℹ️")
        status_text = {"success": "成功", "failed": "失败", "partial": "部分成功"}.get(status.lower(), status)
        md_lines.append(f"**执行状态:** {status_emoji} {status_text}")
        
        if plugin_name:
            md_lines.append(f"**插件名称:** {plugin_name}")
        md_lines.append("")
        
        # 错误信息
        if errors:
            md_lines.append("## 错误信息")
            for err in errors:
                md_lines.append(f"- {err}")
            md_lines.append("")
        
        # 数据内容
        md_lines.append("## 结果数据")
        md_lines.append("")
        
        if isinstance(data, list) and data and isinstance(data[0], dict):
            md_lines.append(_render_md_table(data))
        elif isinstance(data, dict):
            md_lines.append(_render_md_dict(data))
        else:
            md_lines.append("```json")
            md_lines.append(json.dumps(data, indent=2, ensure_ascii=False, default=str))
            md_lines.append("```")
        
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("*由 NetOps Toolkit 生成*")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        
        logger.info(f"数据已导出为Markdown: {output_path}")
        return True
    except Exception as e:
        logger.error(f"导出Markdown失败: {e}")
        return False


def _render_md_table(data: List[Dict[str, Any]]) -> str:
    """渲染 Markdown 表格"""
    if not data:
        return "*无数据*"
    
    headers = list(data[0].keys())
    
    # 表头
    header_line = "| " + " | ".join(str(h) for h in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    
    # 数据行
    rows = []
    for row in data:
        vals = []
        for h in headers:
            v = row.get(h, "")
            # 处理换行和管道符
            v_str = str(v).replace("\n", " ").replace("|", "\\|")
            vals.append(v_str)
        rows.append("| " + " | ".join(vals) + " |")
    
    return "\n".join([header_line, separator] + rows)


def _render_md_dict(data: Dict[str, Any]) -> str:
    """渲染字典为 Markdown"""
    lines = ["| 键 | 值 |", "| --- | --- |"]
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value, ensure_ascii=False, default=str)
        else:
            val_str = str(value)
        # 处理换行和管道符
        val_str = val_str.replace("\n", " ").replace("|", "\\|")
        lines.append(f"| {key} | {val_str} |")
    return "\n".join(lines)


def validate_export_path(path: Union[str, Path]) -> Path:
    """
    验证并规范化导出路径（安全检查）
    
    Args:
        path: 输入路径
        
    Returns:
        规范化后的 Path 对象
        
    Raises:
        ValueError: 路径不安全或无效
    """
    path = Path(path).resolve()
    
    # 检查路径遍历攻击
    try:
        path.relative_to(Path.cwd())
    except ValueError:
        # 允许绝对路径，但检查是否包含危险模式
        path_str = str(path).lower()
        dangerous_patterns = ["/etc/", "/root/", "/system32/", "\\windows\\"]
        for pattern in dangerous_patterns:
            if pattern in path_str:
                raise ValueError(f"不安全的导出路径: {path}")
    
    return path


def save_report(
    data: Any,
    report_dir: Path,
    prefix: str = "report",
    format: str = "json",
    title: str = "NetOps 报告",
    plugin_name: str = "",
    status: str = "success",
    errors: Optional[List[str]] = None,
) -> Optional[Path]:
    """
    保存报告文件
    
    Args:
        data: 报告数据
        report_dir: 报告目录
        prefix: 文件名前缀
        format: 导出格式 (json/csv/html/md)
        title: 报告标题 (用于 HTML/Markdown)
        plugin_name: 插件名称
        status: 执行状态
        errors: 错误列表
        
    Returns:
        保存的文件路径, 失败返回None
    """
    try:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 规范化格式
        fmt = format.lower()
        ext_map = {"json": "json", "csv": "csv", "html": "html", "md": "md", "markdown": "md"}
        extension = ext_map.get(fmt, "json")
        
        filename = generate_report_filename(prefix, extension=extension)
        output_path = report_dir / filename
        
        # 验证路径安全性
        output_path = validate_export_path(output_path)
        
        if fmt == "json":
            success = export_to_json(data, output_path)
        elif fmt == "csv":
            if not isinstance(data, list):
                # 尝试将字典转换为单元素列表
                if isinstance(data, dict):
                    data = [data]
                else:
                    logger.error("CSV格式要求数据为列表或字典类型")
                    return None
            success = export_to_csv(data, output_path)
        elif fmt == "html":
            success = export_to_html(data, output_path, title, plugin_name, status, errors)
        elif fmt in ("md", "markdown"):
            success = export_to_markdown(data, output_path, title, plugin_name, status, errors)
        else:
            logger.error(f"不支持的导出格式: {format}")
            return None
        
        return output_path if success else None
    except ValueError as e:
        logger.error(f"路径验证失败: {e}")
        return None
    except Exception as e:
        logger.error(f"保存报告失败: {e}")
        return None


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
    "export_to_html",
    "export_to_markdown",
    "format_table_data",
    "generate_report_filename",
    "save_report",
    "dict_to_pretty_string",
    "flatten_dict",
    "validate_export_path",
]
