"""
WHOIS查询插件

支持域名和IP地址的WHOIS信息查询。
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
import re

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class WhoisLookupPlugin(Plugin):
    """WHOIS查询插件"""
    
    name = "whois_lookup"
    description = "WHOIS信息查询"
    category = "utils"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        # 检查系统是否有whois命令
        try:
            subprocess.run(
                ["whois", "--version"],
                capture_output=True,
                timeout=5,
            )
            return True, None
        except FileNotFoundError:
            return False, "whois命令不可用, Windows系统可能需要安装"
        except Exception:
            # 有些whois实现不支持--version,尝试其他方法
            return True, None
    
    def get_required_params(self) -> List[str]:
        """获取必需参数"""
        return ["target"]
    
    def run(self, params: Dict[str, Any]) -> PluginResult:
        """
        执行WHOIS查询
        
        参数:
            target: 域名或IP地址
            timeout: 查询超时 (默认30秒)
        """
        target = params.get("target", "")
        timeout = params.get("timeout", 30)
        
        if not target:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定查询目标",
                data={}
            )
        
        logger.info(f"开始WHOIS查询: {target}")
        
        # 执行查询
        whois_data = self._perform_whois(target, timeout)
        
        if not whois_data["success"]:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=whois_data.get("error", "查询失败"),
                data=whois_data
            )
        
        # 解析结果
        parsed = self._parse_whois(whois_data["raw_output"])
        
        # 显示结果
        self._display_results(target, parsed, whois_data["raw_output"])
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"WHOIS查询完成: {target}",
            data={
                "target": target,
                "parsed": parsed,
                "raw": whois_data["raw_output"],
            }
        )
    
    def _perform_whois(self, target: str, timeout: int) -> Dict[str, Any]:
        """执行WHOIS查询"""
        try:
            result = subprocess.run(
                ["whois", target],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"查询失败: {result.stderr}",
                }
            
            return {
                "success": True,
                "raw_output": result.stdout,
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"查询超时 (>{timeout}秒)",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "whois命令不可用",
            }
        except Exception as e:
            logger.error(f"WHOIS查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _parse_whois(self, raw_output: str) -> Dict[str, Any]:
        """解析WHOIS输出"""
        parsed = {
            "domain": None,
            "registrar": None,
            "creation_date": None,
            "expiration_date": None,
            "updated_date": None,
            "name_servers": [],
            "status": [],
            "registrant": None,
            "admin_contact": None,
            "tech_contact": None,
        }
        
        lines = raw_output.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue
            
            # 提取键值对
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                
                # 域名
                if "domain name" in key and not parsed["domain"]:
                    parsed["domain"] = value
                
                # 注册商
                elif "registrar" in key and "abuse" not in key and not parsed["registrar"]:
                    parsed["registrar"] = value
                
                # 日期
                elif "creation date" in key or "created" in key:
                    if not parsed["creation_date"]:
                        parsed["creation_date"] = self._parse_date(value)
                
                elif "expir" in key:
                    if not parsed["expiration_date"]:
                        parsed["expiration_date"] = self._parse_date(value)
                
                elif "updated date" in key or "last updated" in key or "modified" in key:
                    if not parsed["updated_date"]:
                        parsed["updated_date"] = self._parse_date(value)
                
                # 名称服务器
                elif "name server" in key or "nserver" in key:
                    if value and value not in parsed["name_servers"]:
                        parsed["name_servers"].append(value.lower())
                
                # 状态
                elif "status" in key or "state" in key:
                    if value and value not in parsed["status"]:
                        parsed["status"].append(value)
        
        return parsed
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """解析日期字符串"""
        if not date_str:
            return None
        
        # 移除多余信息
        date_str = date_str.split("(")[0].strip()
        date_str = date_str.split("[")[0].strip()
        
        # 常见日期格式
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%b-%Y",
            "%d.%m.%Y",
            "%Y.%m.%d",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str[:19], fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return date_str[:10] if len(date_str) >= 10 else date_str
    
    def _display_results(
        self,
        target: str,
        parsed: Dict[str, Any],
        raw_output: str,
    ) -> None:
        """显示查询结果"""
        from netops_toolkit.ui.theme import console
        
        # 基本信息
        info = {}
        
        if parsed["domain"]:
            info["域名"] = parsed["domain"]
        
        if parsed["registrar"]:
            info["注册商"] = parsed["registrar"]
        
        if parsed["creation_date"]:
            info["注册日期"] = parsed["creation_date"]
        
        if parsed["expiration_date"]:
            info["过期日期"] = parsed["expiration_date"]
            # 计算剩余天数
            try:
                exp_date = datetime.strptime(parsed["expiration_date"], "%Y-%m-%d")
                days_left = (exp_date - datetime.now()).days
                if days_left > 0:
                    info["剩余天数"] = f"{days_left} 天"
                else:
                    info["剩余天数"] = "[red]已过期[/red]"
            except Exception:
                pass
        
        if parsed["updated_date"]:
            info["更新日期"] = parsed["updated_date"]
        
        if info:
            panel = create_summary_panel(f"WHOIS查询: {target}", info)
            console.print(panel)
        else:
            console.print(f"\n[yellow]未能解析出结构化信息[/yellow]\n")
        
        # 名称服务器
        if parsed["name_servers"]:
            console.print("[bold cyan]名称服务器:[/bold cyan]")
            for ns in parsed["name_servers"][:5]:  # 只显示前5个
                console.print(f"  [green]• {ns}[/green]")
            if len(parsed["name_servers"]) > 5:
                console.print(f"  [dim]... 及其他 {len(parsed['name_servers']) - 5} 个[/dim]")
            console.print()
        
        # 状态
        if parsed["status"]:
            console.print("[bold cyan]域名状态:[/bold cyan]")
            for status in parsed["status"][:3]:  # 只显示前3个
                console.print(f"  [yellow]• {status}[/yellow]")
            if len(parsed["status"]) > 3:
                console.print(f"  [dim]... 及其他 {len(parsed['status']) - 3} 个[/dim]")
            console.print()
        
        # 提示查看原始输出
        if not info and not parsed["name_servers"]:
            console.print("[dim]提示: 查看原始WHOIS输出获取完整信息[/dim]\n")


def query_whois(target: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数: 查询WHOIS信息
    
    Args:
        target: 域名或IP地址
        
    Returns:
        解析后的WHOIS信息
    """
    plugin = WhoisLookupPlugin()
    result = plugin.run({"target": target})
    if result.is_success:
        return result.data.get("parsed")
    return None


__all__ = ["WhoisLookupPlugin", "query_whois"]
