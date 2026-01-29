"""
配置对比插件

对比两个设备配置文件的差异。
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import difflib
from datetime import datetime

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class ConfigDiffPlugin(Plugin):
    """配置对比插件"""
    
    name = "config_diff"
    description = "配置文件对比"
    category = "device_mgmt"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        return True, None
    
    def get_required_params(self) -> List[str]:
        """获取必需参数"""
        return ["file1", "file2"]
    
    def run(self, params: Dict[str, Any]) -> PluginResult:
        """
        执行配置对比
        
        参数:
            file1: 第一个配置文件路径
            file2: 第二个配置文件路径
            context_lines: 上下文行数 (默认3)
            ignore_whitespace: 忽略空白字符 (默认False)
            ignore_comments: 忽略注释行 (默认False)
        """
        file1 = params.get("file1", "")
        file2 = params.get("file2", "")
        context_lines = params.get("context_lines", 3)
        ignore_whitespace = params.get("ignore_whitespace", False)
        ignore_comments = params.get("ignore_comments", False)
        
        if not file1 or not file2:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定配置文件",
                data={}
            )
        
        # 读取文件
        path1 = Path(file1)
        path2 = Path(file2)
        
        if not path1.exists():
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"文件不存在: {file1}",
                data={}
            )
        
        if not path2.exists():
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"文件不存在: {file2}",
                data={}
            )
        
        logger.info(f"开始对比配置: {file1} <-> {file2}")
        
        try:
            config1 = path1.read_text(encoding="utf-8")
            config2 = path2.read_text(encoding="utf-8")
        except Exception as e:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=f"读取文件失败: {e}",
                data={}
            )
        
        # 预处理
        lines1 = self._preprocess_config(
            config1,
            ignore_whitespace,
            ignore_comments
        )
        lines2 = self._preprocess_config(
            config2,
            ignore_whitespace,
            ignore_comments
        )
        
        # 生成差异
        diff_result = self._generate_diff(
            lines1,
            lines2,
            file1,
            file2,
            context_lines
        )
        
        # 显示结果
        self._display_results(
            file1,
            file2,
            diff_result
        )
        
        identical = diff_result["added"] == 0 and diff_result["removed"] == 0
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message="配置文件相同" if identical else f"发现差异: +{diff_result['added']} -{diff_result['removed']}",
            data={
                "file1": file1,
                "file2": file2,
                "identical": identical,
                "diff": diff_result,
            }
        )
    
    def _preprocess_config(
        self,
        config: str,
        ignore_whitespace: bool,
        ignore_comments: bool,
    ) -> List[str]:
        """预处理配置内容"""
        lines = config.splitlines()
        processed = []
        
        for line in lines:
            # 忽略注释
            if ignore_comments:
                if line.strip().startswith(("#", "!", "/*", "*", "//")):
                    continue
            
            # 忽略空白
            if ignore_whitespace:
                line = line.strip()
                if not line:
                    continue
            
            processed.append(line)
        
        return processed
    
    def _generate_diff(
        self,
        lines1: List[str],
        lines2: List[str],
        file1: str,
        file2: str,
        context_lines: int,
    ) -> Dict[str, Any]:
        """生成差异信息"""
        # 使用unified_diff生成差异
        diff = list(difflib.unified_diff(
            lines1,
            lines2,
            fromfile=file1,
            tofile=file2,
            n=context_lines,
            lineterm="",
        ))
        
        # 统计差异
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        
        # 提取变更块
        changes = []
        current_chunk = []
        
        for line in diff:
            if line.startswith("@@"):
                if current_chunk:
                    changes.append("\n".join(current_chunk))
                current_chunk = [line]
            elif line.startswith(("+", "-", " ")):
                current_chunk.append(line)
        
        if current_chunk:
            changes.append("\n".join(current_chunk))
        
        return {
            "diff_lines": diff,
            "added": added,
            "removed": removed,
            "total_changes": added + removed,
            "change_chunks": changes,
            "change_count": len(changes),
        }
    
    def _display_results(
        self,
        file1: str,
        file2: str,
        diff_result: Dict[str, Any],
    ) -> None:
        """显示对比结果"""
        from netops_toolkit.ui.theme import console
        
        # 摘要信息
        summary = {
            "文件1": file1,
            "文件2": file2,
            "新增行": diff_result["added"],
            "删除行": diff_result["removed"],
            "变更总数": diff_result["total_changes"],
            "变更块数": diff_result["change_count"],
        }
        
        panel = create_summary_panel("配置对比结果", summary)
        console.print(panel)
        
        if diff_result["total_changes"] == 0:
            console.print("[green]✓ 配置文件完全相同[/green]\n")
            return
        
        # 显示差异
        console.print("\n[bold cyan]差异内容:[/bold cyan]")
        
        for i, chunk in enumerate(diff_result["change_chunks"][:10], 1):  # 最多显示10个块
            console.print(f"\n[bold yellow]变更块 #{i}:[/bold yellow]")
            
            for line in chunk.split("\n"):
                if line.startswith("+++") or line.startswith("---"):
                    console.print(f"[bold cyan]{line}[/bold cyan]")
                elif line.startswith("@@"):
                    console.print(f"[bold magenta]{line}[/bold magenta]")
                elif line.startswith("+"):
                    console.print(f"[green]{line}[/green]")
                elif line.startswith("-"):
                    console.print(f"[red]{line}[/red]")
                else:
                    console.print(f"[dim]{line}[/dim]")
        
        if diff_result["change_count"] > 10:
            console.print(f"\n[dim]... 还有 {diff_result['change_count'] - 10} 个变更块未显示[/dim]")
        
        console.print()


def compare_files(
    file1: str,
    file2: str,
    context_lines: int = 3,
) -> Dict[str, Any]:
    """
    便捷函数: 对比两个配置文件
    
    Args:
        file1: 第一个文件路径
        file2: 第二个文件路径
        context_lines: 上下文行数
        
    Returns:
        对比结果
    """
    plugin = ConfigDiffPlugin()
    result = plugin.run({
        "file1": file1,
        "file2": file2,
        "context_lines": context_lines,
    })
    return result.data.get("diff", {})


__all__ = ["ConfigDiffPlugin", "compare_files"]
