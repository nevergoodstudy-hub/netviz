"""
JSON/YAML 配置验证器插件

验证配置文件格式并提供详细的错误信息。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from netops_toolkit.core.logger import get_logger
from netops_toolkit.plugins import (
    Plugin,
    PluginCategory,
    PluginResult,
    ResultStatus,
    ParamSpec,
    register_plugin,
)
from netops_toolkit.ui.theme import console
from rich.syntax import Syntax
from rich.panel import Panel

logger = get_logger(__name__)


@register_plugin
class ConfigValidatorPlugin(Plugin):
    """JSON/YAML配置验证器插件"""
    
    name = "配置验证器"
    category = PluginCategory.UTILS
    description = "验证JSON/YAML配置文件格式"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="file_path",
                param_type=str,
                description="配置文件路径",
                required=True,
            ),
            ParamSpec(
                name="format",
                param_type=str,
                description="格式: auto, json, yaml",
                required=False,
                default="auto",
            ),
            ParamSpec(
                name="show_content",
                param_type=bool,
                description="显示文件内容",
                required=False,
                default=True,
            ),
        ]
    
    def run(
        self,
        file_path: str,
        format: str = "auto",
        show_content: bool = True,
        **kwargs,
    ) -> PluginResult:
        """验证配置文件"""
        start_time = datetime.now()
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"文件不存在: {file_path}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"读取文件失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 自动检测格式
        if format == "auto":
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ('.json',):
                format = "json"
            elif ext in ('.yaml', '.yml'):
                format = "yaml"
            else:
                # 尝试检测内容
                content_stripped = content.strip()
                if content_stripped.startswith('{') or content_stripped.startswith('['):
                    format = "json"
                else:
                    format = "yaml"
        
        console.print(f"[cyan]验证配置文件...[/cyan]")
        console.print(f"[cyan]文件: {file_path}[/cyan]")
        console.print(f"[cyan]格式: {format.upper()}[/cyan]")
        console.print(f"[cyan]大小: {len(content)} 字节, {len(content.splitlines())} 行[/cyan]\n")
        
        # 验证
        if format == "json":
            result = self._validate_json(content, file_path, show_content)
        else:
            result = self._validate_yaml(content, file_path, show_content)
        
        result.start_time = start_time
        result.end_time = datetime.now()
        return result
    
    def _validate_json(
        self, content: str, file_path: str, show_content: bool
    ) -> PluginResult:
        """验证JSON格式"""
        try:
            data = json.loads(content)
            
            console.print("[green]✅ JSON格式正确![/green]\n")
            
            # 统计信息
            stats = self._get_data_stats(data)
            console.print("[yellow]结构分析:[/yellow]")
            for key, value in stats.items():
                console.print(f"  • {key}: {value}")
            
            # 显示内容预览
            if show_content:
                console.print()
                # 格式化JSON
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                if len(formatted) > 2000:
                    formatted = formatted[:2000] + "\n... (内容已截断)"
                
                syntax = Syntax(formatted, "json", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="JSON内容预览", border_style="green"))
            
            return PluginResult(
                status=ResultStatus.SUCCESS,
                message="JSON格式验证通过",
                data={"format": "json", "valid": True, "stats": stats},
            )
            
        except json.JSONDecodeError as e:
            console.print("[red]❌ JSON格式错误![/red]\n")
            
            # 详细错误信息
            console.print("[yellow]错误详情:[/yellow]")
            console.print(f"  • 错误: {e.msg}")
            console.print(f"  • 行号: {e.lineno}")
            console.print(f"  • 列号: {e.colno}")
            console.print(f"  • 位置: 字符 {e.pos}")
            
            # 显示错误位置
            lines = content.splitlines()
            if 0 < e.lineno <= len(lines):
                console.print("\n[yellow]错误位置:[/yellow]")
                
                # 显示上下文
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                
                for i in range(start, end):
                    line_num = i + 1
                    line = lines[i]
                    if line_num == e.lineno:
                        console.print(f"  [red]>{line_num:4d}| {line}[/red]")
                        console.print(f"  [red]     {' ' * (e.colno - 1)}^[/red]")
                    else:
                        console.print(f"  [dim] {line_num:4d}| {line}[/dim]")
            
            # 常见错误提示
            console.print("\n[yellow]可能的原因:[/yellow]")
            self._suggest_json_fix(e.msg, content, e.lineno, e.colno)
            
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"JSON格式错误: {e.msg} (行 {e.lineno}, 列 {e.colno})",
                data={"format": "json", "valid": False, "error": str(e)},
            )
    
    def _validate_yaml(
        self, content: str, file_path: str, show_content: bool
    ) -> PluginResult:
        """验证YAML格式"""
        try:
            import yaml
        except ImportError:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="需要安装 PyYAML: pip install pyyaml",
            )
        
        try:
            # 使用safe_load避免安全问题
            data = yaml.safe_load(content)
            
            console.print("[green]✅ YAML格式正确![/green]\n")
            
            # 统计信息
            stats = self._get_data_stats(data)
            console.print("[yellow]结构分析:[/yellow]")
            for key, value in stats.items():
                console.print(f"  • {key}: {value}")
            
            # 显示内容预览
            if show_content:
                console.print()
                preview = content[:2000] + "\n... (内容已截断)" if len(content) > 2000 else content
                syntax = Syntax(preview, "yaml", theme="monokai", line_numbers=True)
                console.print(Panel(syntax, title="YAML内容预览", border_style="green"))
            
            return PluginResult(
                status=ResultStatus.SUCCESS,
                message="YAML格式验证通过",
                data={"format": "yaml", "valid": True, "stats": stats},
            )
            
        except yaml.YAMLError as e:
            console.print("[red]❌ YAML格式错误![/red]\n")
            
            console.print("[yellow]错误详情:[/yellow]")
            console.print(f"  • {e}")
            
            # 如果有位置信息
            if hasattr(e, 'problem_mark') and e.problem_mark:
                mark = e.problem_mark
                console.print(f"\n[yellow]错误位置:[/yellow]")
                console.print(f"  • 行号: {mark.line + 1}")
                console.print(f"  • 列号: {mark.column + 1}")
                
                # 显示上下文
                lines = content.splitlines()
                if 0 <= mark.line < len(lines):
                    start = max(0, mark.line - 2)
                    end = min(len(lines), mark.line + 3)
                    
                    for i in range(start, end):
                        line_num = i + 1
                        line = lines[i]
                        if i == mark.line:
                            console.print(f"  [red]>{line_num:4d}| {line}[/red]")
                            console.print(f"  [red]     {' ' * mark.column}^[/red]")
                        else:
                            console.print(f"  [dim] {line_num:4d}| {line}[/dim]")
            
            # 常见YAML错误提示
            console.print("\n[yellow]常见YAML问题:[/yellow]")
            console.print("  • 缩进必须使用空格,不能使用Tab")
            console.print("  • 冒号后需要空格 (key: value)")
            console.print("  • 特殊字符需要引号包围")
            console.print("  • 列表项需要正确缩进")
            
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"YAML格式错误: {e}",
                data={"format": "yaml", "valid": False, "error": str(e)},
            )
    
    def _get_data_stats(self, data: Any) -> Dict[str, Any]:
        """获取数据结构统计"""
        stats = {}
        
        if data is None:
            stats["类型"] = "空"
        elif isinstance(data, dict):
            stats["类型"] = "对象(字典)"
            stats["键数量"] = len(data)
            stats["顶级键"] = ", ".join(list(data.keys())[:5])
            if len(data) > 5:
                stats["顶级键"] += f" ... (+{len(data)-5})"
        elif isinstance(data, list):
            stats["类型"] = "数组(列表)"
            stats["元素数量"] = len(data)
            if data and isinstance(data[0], dict):
                stats["元素类型"] = "对象"
            elif data:
                stats["元素类型"] = type(data[0]).__name__
        else:
            stats["类型"] = type(data).__name__
            stats["值"] = str(data)[:50]
        
        # 计算嵌套深度
        stats["嵌套深度"] = self._get_depth(data)
        
        return stats
    
    def _get_depth(self, data: Any, current: int = 0) -> int:
        """计算嵌套深度"""
        if isinstance(data, dict):
            if not data:
                return current + 1
            return max(self._get_depth(v, current + 1) for v in data.values())
        elif isinstance(data, list):
            if not data:
                return current + 1
            return max(self._get_depth(v, current + 1) for v in data)
        return current
    
    def _suggest_json_fix(self, error_msg: str, content: str, line: int, col: int):
        """根据错误提供JSON修复建议"""
        error_lower = error_msg.lower()
        
        if "expecting" in error_lower and "delimiter" in error_lower:
            console.print("  • 可能缺少逗号或括号")
        if "unterminated string" in error_lower:
            console.print("  • 字符串未闭合,检查引号是否配对")
        if "invalid escape" in error_lower:
            console.print("  • 无效的转义字符,使用 \\\\ 而不是 \\")
        if "extra data" in error_lower:
            console.print("  • JSON后有多余内容,确保只有一个根对象")
        if "expecting value" in error_lower:
            console.print("  • 期望值但未找到,可能有多余的逗号")
        if "expecting property name" in error_lower:
            console.print("  • 对象键必须是双引号字符串")
            console.print("  • 检查是否使用了单引号 (应使用双引号)")
        
        # 通用建议
        console.print("  • JSON键和字符串必须使用双引号")
        console.print("  • 最后一个元素后不能有逗号")
        console.print("  • 布尔值是 true/false (小写)")
        console.print("  • 空值是 null (小写)")
