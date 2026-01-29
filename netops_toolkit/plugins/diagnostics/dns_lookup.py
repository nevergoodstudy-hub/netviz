"""
DNS查询插件

提供DNS正向/反向查询功能,支持多种记录类型。
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

try:
    import dns.resolver
    import dns.reversename
    import dns.exception
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

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
from netops_toolkit.utils.network_utils import is_valid_ip
from netops_toolkit.utils.export_utils import save_report

logger = get_logger(__name__)


@register_plugin
class DNSLookupPlugin(Plugin):
    """DNS查询插件"""
    
    name = "DNS查询"
    category = PluginCategory.DIAGNOSTICS
    description = "DNS正向/反向查询,支持多种记录类型"
    version = "1.0.0"
    
    # 支持的记录类型
    RECORD_TYPES = ["A", "AAAA", "MX", "CNAME", "NS", "TXT", "SOA", "PTR", "SRV"]
    
    def validate_dependencies(self) -> bool:
        """验证依赖"""
        if not DNS_AVAILABLE:
            logger.error("dnspython库未安装, 请运行: pip install dnspython")
            return False
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="domain",
                param_type=str,
                description="域名或IP地址",
                required=True,
            ),
            ParamSpec(
                name="record_type",
                param_type=str,
                description="记录类型",
                required=False,
                default="A",
                choices=self.RECORD_TYPES,
            ),
            ParamSpec(
                name="dns_server",
                param_type=str,
                description="DNS服务器 (留空使用系统默认)",
                required=False,
                default="",
            ),
        ]
    
    def run(
        self,
        domain: str,
        record_type: str = "A",
        dns_server: Optional[str] = None,
        export_path: Optional[str] = None,
        **kwargs,
    ) -> PluginResult:
        """
        执行DNS查询
        
        Args:
            domain: 域名或IP地址
            record_type: 记录类型
            dns_server: DNS服务器
            export_path: 导出文件路径
            
        Returns:
            PluginResult
        """
        start_time = datetime.now()
        
        # 检查是否为IP地址 (反向查询)
        is_reverse = is_valid_ip(domain)
        if is_reverse:
            record_type = "PTR"
            console.print(f"[cyan]检测到IP地址,将执行PTR反向查询[/cyan]")
        
        # 创建resolver
        resolver = dns.resolver.Resolver()
        
        # 配置DNS服务器
        if dns_server:
            resolver.nameservers = [dns_server]
            console.print(f"[cyan]使用DNS服务器: {dns_server}[/cyan]")
        else:
            console.print(f"[cyan]使用系统默认DNS服务器[/cyan]")
        
        console.print(f"\n[cyan]查询 {domain} 的 {record_type} 记录...[/cyan]\n")
        
        # 执行查询
        query_start = time.time()
        results = []
        errors = []
        
        try:
            if is_reverse:
                # 反向查询
                rev_name = dns.reversename.from_address(domain)
                answers = resolver.resolve(rev_name, "PTR")
            else:
                # 正向查询
                answers = resolver.resolve(domain, record_type)
            
            query_time = (time.time() - query_start) * 1000  # 转换为毫秒
            
            # 解析结果
            for rdata in answers:
                result = self._parse_record(rdata, record_type)
                result["ttl"] = answers.rrset.ttl
                result["query_time"] = query_time
                results.append(result)
            
        except dns.resolver.NXDOMAIN:
            errors.append(f"域名不存在: {domain}")
        except dns.resolver.NoAnswer:
            errors.append(f"无 {record_type} 记录: {domain}")
        except dns.resolver.Timeout:
            errors.append(f"DNS查询超时: {domain}")
        except dns.exception.DNSException as e:
            errors.append(f"DNS查询错误: {e}")
        except Exception as e:
            logger.error(f"DNS查询失败: {e}")
            errors.append(f"查询失败: {e}")
        
        # 显示结果
        if results:
            self._display_results(results, domain, record_type)
            
            # 显示统计
            stats = {
                "域名/IP": domain,
                "记录类型": record_type,
                "记录数量": len(results),
                "查询时间": f"{results[0]['query_time']:.2f} ms",
                "TTL": f"{results[0]['ttl']} 秒",
            }
            
            if dns_server:
                stats["DNS服务器"] = dns_server
            
            console.print(create_summary_panel("查询统计", stats, timestamp=datetime.now()))
        else:
            console.print(f"[yellow]⚠ 未找到记录[/yellow]")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")
        
        # 导出报告
        if export_path:
            export_data = {
                "test_time": start_time.isoformat(),
                "domain": domain,
                "record_type": record_type,
                "dns_server": dns_server or "system_default",
                "results": results,
                "errors": errors,
            }
            save_report(export_data, Path(export_path).parent, Path(export_path).stem, "json")
        
        end_time = datetime.now()
        
        # 确定结果状态
        if results:
            status = ResultStatus.SUCCESS
            message = f"成功查询到 {len(results)} 条 {record_type} 记录"
        elif errors:
            status = ResultStatus.FAILED
            message = f"查询失败: {errors[0] if errors else '未知错误'}"
        else:
            status = ResultStatus.ERROR
            message = "未获取到任何结果"
        
        return PluginResult(
            status=status,
            message=message,
            data=results,
            errors=errors,
            start_time=start_time,
            end_time=end_time,
        )
    
    def _parse_record(self, rdata: Any, record_type: str) -> Dict[str, Any]:
        """
        解析DNS记录
        
        Args:
            rdata: DNS记录数据
            record_type: 记录类型
            
        Returns:
            解析后的记录字典
        """
        result = {"type": record_type}
        
        if record_type == "A":
            result["address"] = str(rdata)
            result["value"] = str(rdata)
        
        elif record_type == "AAAA":
            result["address"] = str(rdata)
            result["value"] = str(rdata)
        
        elif record_type == "MX":
            result["priority"] = rdata.preference
            result["mailserver"] = str(rdata.exchange)
            result["value"] = f"{rdata.preference} {rdata.exchange}"
        
        elif record_type == "CNAME":
            result["target"] = str(rdata.target)
            result["value"] = str(rdata.target)
        
        elif record_type == "NS":
            result["nameserver"] = str(rdata.target)
            result["value"] = str(rdata.target)
        
        elif record_type == "TXT":
            txt_value = b"".join(rdata.strings).decode('utf-8', errors='ignore')
            result["text"] = txt_value
            result["value"] = txt_value
        
        elif record_type == "SOA":
            result["mname"] = str(rdata.mname)
            result["rname"] = str(rdata.rname)
            result["serial"] = rdata.serial
            result["refresh"] = rdata.refresh
            result["retry"] = rdata.retry
            result["expire"] = rdata.expire
            result["minimum"] = rdata.minimum
            result["value"] = f"{rdata.mname} {rdata.rname}"
        
        elif record_type == "PTR":
            result["hostname"] = str(rdata.target)
            result["value"] = str(rdata.target)
        
        elif record_type == "SRV":
            result["priority"] = rdata.priority
            result["weight"] = rdata.weight
            result["port"] = rdata.port
            result["target"] = str(rdata.target)
            result["value"] = f"{rdata.priority} {rdata.weight} {rdata.port} {rdata.target}"
        
        else:
            result["value"] = str(rdata)
        
        return result
    
    def _display_results(
        self,
        results: List[Dict[str, Any]],
        domain: str,
        record_type: str,
    ) -> None:
        """
        显示查询结果
        
        Args:
            results: 结果列表
            domain: 域名
            record_type: 记录类型
        """
        # 根据记录类型选择列
        if record_type == "A" or record_type == "AAAA":
            columns = [
                {"header": "类型", "justify": "center", "width": 8},
                {"header": "IP地址", "style": NetOpsTheme.IP_ADDRESS, "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
                {"header": "查询时间(ms)", "justify": "right"},
            ]
            rows = [
                [r["type"], r["address"], str(r["ttl"]), f"{r['query_time']:.2f}"]
                for r in results
            ]
        
        elif record_type == "MX":
            columns = [
                {"header": "优先级", "justify": "center"},
                {"header": "邮件服务器", "style": NetOpsTheme.HOSTNAME, "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
            ]
            rows = [
                [str(r["priority"]), r["mailserver"], str(r["ttl"])]
                for r in results
            ]
        
        elif record_type == "CNAME":
            columns = [
                {"header": "类型", "justify": "center", "width": 8},
                {"header": "目标", "style": NetOpsTheme.HOSTNAME, "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
            ]
            rows = [
                [r["type"], r["target"], str(r["ttl"])]
                for r in results
            ]
        
        elif record_type == "NS":
            columns = [
                {"header": "类型", "justify": "center", "width": 8},
                {"header": "名称服务器", "style": NetOpsTheme.HOSTNAME, "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
            ]
            rows = [
                [r["type"], r["nameserver"], str(r["ttl"])]
                for r in results
            ]
        
        elif record_type == "TXT":
            columns = [
                {"header": "类型", "justify": "center", "width": 8},
                {"header": "文本内容", "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
            ]
            rows = [
                [r["type"], r["text"][:80] + "..." if len(r["text"]) > 80 else r["text"], str(r["ttl"])]
                for r in results
            ]
        
        elif record_type == "PTR":
            columns = [
                {"header": "类型", "justify": "center", "width": 8},
                {"header": "主机名", "style": NetOpsTheme.HOSTNAME, "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
            ]
            rows = [
                [r["type"], r["hostname"], str(r["ttl"])]
                for r in results
            ]
        
        elif record_type == "SOA":
            columns = [
                {"header": "主服务器", "justify": "left"},
                {"header": "序列号", "justify": "right"},
                {"header": "刷新", "justify": "right"},
                {"header": "重试", "justify": "right"},
                {"header": "过期", "justify": "right"},
            ]
            rows = [
                [r["mname"], str(r["serial"]), str(r["refresh"]), str(r["retry"]), str(r["expire"])]
                for r in results
            ]
        
        else:
            # 通用显示
            columns = [
                {"header": "类型", "justify": "center", "width": 8},
                {"header": "值", "justify": "left"},
                {"header": "TTL(秒)", "justify": "right"},
            ]
            rows = [
                [r["type"], r["value"], str(r["ttl"])]
                for r in results
            ]
        
        table = create_result_table(f"DNS查询结果: {domain}", columns, rows)
        console.print(table)
        console.print()


__all__ = ["DNSLookupPlugin"]
