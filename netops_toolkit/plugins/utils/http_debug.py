"""
HTTP调试插件

提供HTTP/HTTPS请求测试功能,支持请求头管理和响应分析。
"""

import json
import ssl
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from http.client import HTTPResponse

from netops_toolkit.core.logger import get_logger
from netops_toolkit.plugins import (
    Plugin,
    PluginCategory,
    PluginResult,
    ResultStatus,
    ParamSpec,
    register_plugin,
)
from netops_toolkit.ui.theme import NetOpsTheme, console
from netops_toolkit.ui.components import (
    create_result_table,
    create_summary_panel,
    create_info_panel,
)
from netops_toolkit.utils.export_utils import save_report

logger = get_logger(__name__)


@register_plugin
class HTTPDebugPlugin(Plugin):
    """HTTP调试插件"""
    
    name = "HTTP调试"
    category = PluginCategory.UTILS
    description = "HTTP/HTTPS请求测试,响应分析"
    version = "1.0.0"
    
    # 支持的HTTP方法
    HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]
    
    def validate_dependencies(self) -> bool:
        """验证依赖"""
        # 使用内置的urllib,无需额外依赖
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="url",
                param_type=str,
                description="目标URL",
                required=True,
            ),
            ParamSpec(
                name="method",
                param_type=str,
                description="HTTP方法",
                required=False,
                default="GET",
                choices=self.HTTP_METHODS,
            ),
            ParamSpec(
                name="timeout",
                param_type=float,
                description="超时时间(秒)",
                required=False,
                default=10.0,
            ),
        ]
    
    def run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[str] = None,
        timeout: float = 10.0,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
        export_path: Optional[str] = None,
        **kwargs,
    ) -> PluginResult:
        """
        执行HTTP请求
        
        Args:
            url: 目标URL
            method: HTTP方法
            headers: 自定义请求头
            data: 请求体数据
            timeout: 超时时间
            verify_ssl: 是否验证SSL证书
            follow_redirects: 是否跟随重定向
            export_path: 导出文件路径
            
        Returns:
            PluginResult
        """
        start_time = datetime.now()
        
        # 验证URL
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        console.print(f"\n[cyan]{method} {url}[/cyan]\n")
        
        # 准备请求头
        default_headers = {
            "User-Agent": "NetOps-Toolkit/1.0",
            "Accept": "*/*",
        }
        
        if headers:
            default_headers.update(headers)
        
        # 执行请求
        request_start = time.time()
        response_data = {}
        errors = []
        
        try:
            # 创建请求
            req = urllib.request.Request(
                url,
                method=method,
                headers=default_headers,
                data=data.encode() if data else None,
            )
            
            # SSL配置
            context = None
            if url.startswith('https://'):
                context = ssl.create_default_context()
                if not verify_ssl:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
            
            # 发送请求
            with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
                response_time = (time.time() - request_start) * 1000  # 毫秒
                
                response_data = self._parse_response(response, response_time)
                
        except urllib.error.HTTPError as e:
            response_time = (time.time() - request_start) * 1000
            response_data = {
                "status_code": e.code,
                "reason": e.reason,
                "headers": dict(e.headers) if e.headers else {},
                "body": "",
                "body_size": 0,
                "response_time": response_time,
                "error": str(e),
            }
            
        except urllib.error.URLError as e:
            errors.append(f"URL错误: {e.reason}")
            
        except ssl.SSLError as e:
            errors.append(f"SSL错误: {e}")
            
        except TimeoutError:
            errors.append(f"请求超时 (>{timeout}秒)")
            
        except Exception as e:
            logger.error(f"HTTP请求失败: {e}")
            errors.append(f"请求失败: {e}")
        
        # 显示结果
        if response_data:
            self._display_results(response_data, url, method)
            
            # 显示统计
            stats = {
                "URL": url,
                "方法": method,
                "状态码": f"{response_data.get('status_code', '-')} {response_data.get('reason', '')}",
                "响应时间": f"{response_data.get('response_time', 0):.2f} ms",
                "响应大小": self._format_size(response_data.get('body_size', 0)),
                "SSL验证": "是" if verify_ssl else "否",
            }
            
            console.print(create_summary_panel("请求统计", stats, timestamp=datetime.now()))
        else:
            console.print(f"[red]❌ 请求失败[/red]")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")
        
        # 导出报告
        if export_path:
            export_data = {
                "test_time": start_time.isoformat(),
                "url": url,
                "method": method,
                "headers": default_headers,
                "data": data,
                "timeout": timeout,
                "verify_ssl": verify_ssl,
                "response": response_data,
                "errors": errors,
            }
            save_report(export_data, Path(export_path).parent, Path(export_path).stem, "json")
        
        end_time = datetime.now()
        
        # 确定结果状态
        if response_data and not errors:
            status_code = response_data.get('status_code', 0)
            if 200 <= status_code < 300:
                status = ResultStatus.SUCCESS
                message = f"请求成功 - {status_code} {response_data.get('reason', '')}"
            elif 300 <= status_code < 400:
                status = ResultStatus.PARTIAL
                message = f"重定向 - {status_code} {response_data.get('reason', '')}"
            else:
                status = ResultStatus.FAILED
                message = f"请求失败 - {status_code} {response_data.get('reason', '')}"
        else:
            status = ResultStatus.ERROR
            message = f"请求错误: {errors[0] if errors else '未知错误'}"
        
        return PluginResult(
            status=status,
            message=message,
            data=response_data,
            errors=errors,
            start_time=start_time,
            end_time=end_time,
        )
    
    def _parse_response(self, response: HTTPResponse, response_time: float) -> Dict[str, Any]:
        """
        解析HTTP响应
        
        Args:
            response: HTTP响应对象
            response_time: 响应时间(毫秒)
            
        Returns:
            响应数据字典
        """
        # 读取响应体
        try:
            body = response.read()
            body_text = body.decode('utf-8', errors='ignore')
        except Exception:
            body = b""
            body_text = ""
        
        return {
            "status_code": response.status,
            "reason": response.reason,
            "headers": dict(response.headers),
            "body": body_text[:5000],  # 限制响应体大小
            "body_size": len(body),
            "response_time": response_time,
            "url": response.url if hasattr(response, 'url') else "",
            "error": None,
        }
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"
    
    def _display_results(
        self,
        response: Dict[str, Any],
        url: str,
        method: str,
    ) -> None:
        """
        显示响应结果
        
        Args:
            response: 响应数据
            url: URL
            method: HTTP方法
        """
        status_code = response.get('status_code', 0)
        
        # 状态码颜色
        if 200 <= status_code < 300:
            status_style = NetOpsTheme.SUCCESS
            status_icon = "✓"
        elif 300 <= status_code < 400:
            status_style = NetOpsTheme.WARNING
            status_icon = "→"
        else:
            status_style = NetOpsTheme.ERROR
            status_icon = "✕"
        
        # 显示状态行
        console.print(f"[{status_style}]{status_icon} HTTP {status_code} {response.get('reason', '')}[/]")
        console.print(f"[dim]响应时间: {response.get('response_time', 0):.2f} ms | 大小: {self._format_size(response.get('body_size', 0))}[/dim]")
        console.print()
        
        # 显示响应头
        headers = response.get('headers', {})
        if headers:
            console.print("[bold]响应头:[/bold]")
            
            # 选择重要的头显示
            important_headers = [
                'Content-Type', 'Content-Length', 'Server', 'Date',
                'Cache-Control', 'Set-Cookie', 'Location', 'X-Powered-By',
            ]
            
            for header in important_headers:
                if header in headers:
                    value = headers[header]
                    if len(value) > 80:
                        value = value[:77] + "..."
                    console.print(f"  [cyan]{header}:[/cyan] {value}")
            
            # 显示其他头的数量
            other_count = len(headers) - len([h for h in important_headers if h in headers])
            if other_count > 0:
                console.print(f"  [dim]... 及其他 {other_count} 个头[/dim]")
            
            console.print()
        
        # 显示响应体预览
        body = response.get('body', '')
        if body:
            console.print("[bold]响应体预览:[/bold]")
            
            # 尝试格式化JSON
            try:
                parsed = json.loads(body)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                # 限制显示行数
                lines = formatted.split('\n')
                if len(lines) > 20:
                    preview = '\n'.join(lines[:20]) + f"\n... (共 {len(lines)} 行)"
                else:
                    preview = formatted
                console.print(f"[dim]{preview}[/dim]")
            except json.JSONDecodeError:
                # 非JSON内容
                if len(body) > 500:
                    preview = body[:500] + "..."
                else:
                    preview = body
                console.print(f"[dim]{preview}[/dim]")
            
            console.print()


__all__ = ["HTTPDebugPlugin"]
