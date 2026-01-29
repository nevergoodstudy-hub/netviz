"""
Base64 编解码工具插件

支持文本和文件的Base64编解码。
"""

import base64
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
from rich.panel import Panel
from rich.syntax import Syntax

logger = get_logger(__name__)


@register_plugin
class Base64ToolPlugin(Plugin):
    """Base64编解码工具插件"""
    
    name = "Base64工具"
    category = PluginCategory.UTILS
    description = "Base64编码和解码"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="action",
                param_type=str,
                description="操作: encode(编码) 或 decode(解码)",
                required=True,
            ),
            ParamSpec(
                name="input_text",
                param_type=str,
                description="输入文本 (或文件路径,以 file: 开头)",
                required=True,
            ),
            ParamSpec(
                name="output_file",
                param_type=str,
                description="输出到文件 (可选)",
                required=False,
                default="",
            ),
            ParamSpec(
                name="url_safe",
                param_type=bool,
                description="使用URL安全编码",
                required=False,
                default=False,
            ),
        ]
    
    def run(
        self,
        action: str,
        input_text: str,
        output_file: str = "",
        url_safe: bool = False,
        **kwargs,
    ) -> PluginResult:
        """执行Base64编解码"""
        start_time = datetime.now()
        
        action = action.lower()
        if action not in ("encode", "decode", "e", "d"):
            return PluginResult(
                status=ResultStatus.ERROR,
                message="操作必须是 encode 或 decode",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        is_encode = action in ("encode", "e")
        
        # 检查是否是文件输入
        input_data = None
        is_file_input = False
        
        if input_text.startswith("file:"):
            file_path = input_text[5:].strip()
            if not os.path.exists(file_path):
                return PluginResult(
                    status=ResultStatus.ERROR,
                    message=f"文件不存在: {file_path}",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            
            try:
                with open(file_path, 'rb') as f:
                    input_data = f.read()
                is_file_input = True
                console.print(f"[cyan]从文件读取: {file_path}[/cyan]")
                console.print(f"[cyan]文件大小: {len(input_data)} 字节[/cyan]")
            except Exception as e:
                return PluginResult(
                    status=ResultStatus.ERROR,
                    message=f"读取文件失败: {e}",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
        else:
            input_data = input_text.encode('utf-8') if is_encode else input_text
        
        console.print(f"[cyan]操作: {'编码' if is_encode else '解码'}[/cyan]")
        console.print(f"[cyan]URL安全模式: {'是' if url_safe else '否'}[/cyan]\n")
        
        try:
            if is_encode:
                result = self._encode(input_data, url_safe)
            else:
                result = self._decode(input_data, url_safe)
            
            if result is None:
                return PluginResult(
                    status=ResultStatus.ERROR,
                    message="编解码失败",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            
            # 输出结果
            console.print("[green]✅ 操作成功![/green]\n")
            
            # 保存到文件
            if output_file:
                try:
                    if isinstance(result, bytes):
                        with open(output_file, 'wb') as f:
                            f.write(result)
                    else:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(result)
                    console.print(f"[green]已保存到: {output_file}[/green]\n")
                except Exception as e:
                    console.print(f"[yellow]保存文件失败: {e}[/yellow]\n")
            
            # 显示结果
            if isinstance(result, bytes):
                # 尝试解码为文本
                try:
                    result_text = result.decode('utf-8')
                    result_display = result_text
                except UnicodeDecodeError:
                    result_display = f"[二进制数据, {len(result)} 字节]"
                    # 显示十六进制预览
                    hex_preview = result[:64].hex()
                    result_display += f"\n十六进制预览: {hex_preview}..."
            else:
                result_display = result
            
            # 截断长输出
            if len(result_display) > 1000:
                result_preview = result_display[:1000] + "\n... (已截断)"
            else:
                result_preview = result_display
            
            console.print(Panel(
                result_preview,
                title="输出结果",
                border_style="green",
            ))
            
            # 统计
            input_size = len(input_data) if isinstance(input_data, bytes) else len(input_data.encode('utf-8'))
            output_size = len(result) if isinstance(result, bytes) else len(result.encode('utf-8'))
            
            console.print(f"\n[yellow]统计:[/yellow]")
            console.print(f"  • 输入大小: {input_size} 字节")
            console.print(f"  • 输出大小: {output_size} 字节")
            if is_encode:
                ratio = output_size / input_size if input_size > 0 else 0
                console.print(f"  • 膨胀比例: {ratio:.2f}x")
            
            return PluginResult(
                status=ResultStatus.SUCCESS,
                message=f"{'编码' if is_encode else '解码'}成功",
                data={
                    "action": "encode" if is_encode else "decode",
                    "input_size": input_size,
                    "output_size": output_size,
                    "result": result_display[:500] if len(result_display) > 500 else result_display,
                },
                start_time=start_time,
                end_time=datetime.now(),
            )
            
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"操作失败: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
    
    def _encode(self, data: bytes, url_safe: bool = False) -> Optional[str]:
        """Base64编码"""
        try:
            if url_safe:
                encoded = base64.urlsafe_b64encode(data)
            else:
                encoded = base64.b64encode(data)
            return encoded.decode('ascii')
        except Exception as e:
            logger.error(f"编码失败: {e}")
            return None
    
    def _decode(self, data: str, url_safe: bool = False) -> Optional[bytes]:
        """Base64解码"""
        try:
            # 清理输入
            data_clean = data.strip()
            
            # 添加填充
            padding = 4 - (len(data_clean) % 4)
            if padding != 4:
                data_clean += '=' * padding
            
            if url_safe:
                decoded = base64.urlsafe_b64decode(data_clean)
            else:
                decoded = base64.b64decode(data_clean)
            return decoded
        except Exception as e:
            logger.error(f"解码失败: {e}")
            console.print(f"[red]解码失败: {e}[/red]")
            console.print("[yellow]提示: 确保输入是有效的Base64字符串[/yellow]")
            return None
