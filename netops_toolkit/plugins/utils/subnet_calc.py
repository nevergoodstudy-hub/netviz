"""
子网计算器插件

提供CIDR计算、VLSM子网划分、IP范围计算等网络计算功能。
"""

import ipaddress
from datetime import datetime
from pathlib import Path
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
from netops_toolkit.ui.theme import NetOpsTheme, console
from netops_toolkit.ui.components import (
    create_result_table,
    create_summary_panel,
    create_info_panel,
)
from netops_toolkit.utils.export_utils import save_report

logger = get_logger(__name__)


@register_plugin
class SubnetCalcPlugin(Plugin):
    """子网计算器插件"""
    
    name = "子网计算器"
    category = PluginCategory.UTILS
    description = "CIDR计算、子网划分、IP范围计算"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        """验证依赖"""
        # 使用标准库ipaddress,无需额外依赖
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="network",
                param_type=str,
                description="网络地址 (CIDR格式,如 192.168.1.0/24)",
                required=True,
            ),
            ParamSpec(
                name="action",
                param_type=str,
                description="操作类型",
                required=False,
                default="info",
                choices=["info", "split", "supernet"],
            ),
        ]
    
    def run(
        self,
        network: str,
        action: str = "info",
        split_prefix: int = 0,
        split_count: int = 0,
        export_path: Optional[str] = None,
        **kwargs,
    ) -> PluginResult:
        """
        执行子网计算
        
        Args:
            network: 网络地址 (CIDR格式)
            action: 操作类型 (info, split, supernet)
            split_prefix: 子网前缀长度 (用于split)
            split_count: 划分数量 (用于split)
            export_path: 导出文件路径
            
        Returns:
            PluginResult
        """
        start_time = datetime.now()
        
        # 解析网络地址
        try:
            net = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"无效的网络地址: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        results = {}
        
        if action == "info":
            results = self._get_network_info(net)
            self._display_network_info(results, network)
            
        elif action == "split":
            if split_prefix > 0:
                results = self._split_by_prefix(net, split_prefix)
            elif split_count > 0:
                results = self._split_by_count(net, split_count)
            else:
                # 默认二分
                results = self._split_by_count(net, 2)
            
            if "error" in results:
                return PluginResult(
                    status=ResultStatus.ERROR,
                    message=results["error"],
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            
            self._display_subnets(results, network)
            
        elif action == "supernet":
            results = self._get_supernet_info(net)
            self._display_supernet_info(results, network)
        
        # 导出报告
        if export_path:
            export_data = {
                "test_time": start_time.isoformat(),
                "network": network,
                "action": action,
                "results": results,
            }
            save_report(export_data, Path(export_path).parent, Path(export_path).stem, "json")
        
        end_time = datetime.now()
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"子网计算完成: {network}",
            data=results,
            start_time=start_time,
            end_time=end_time,
        )
    
    def _get_network_info(self, net: ipaddress.IPv4Network) -> Dict[str, Any]:
        """
        获取网络详细信息
        
        Args:
            net: 网络对象
            
        Returns:
            网络信息字典
        """
        hosts = list(net.hosts())
        
        info = {
            "network": str(net.network_address),
            "broadcast": str(net.broadcast_address),
            "netmask": str(net.netmask),
            "hostmask": str(net.hostmask),
            "prefix_length": net.prefixlen,
            "total_addresses": net.num_addresses,
            "usable_hosts": len(hosts),
            "first_host": str(hosts[0]) if hosts else str(net.network_address),
            "last_host": str(hosts[-1]) if hosts else str(net.broadcast_address),
            "is_private": net.is_private,
            "is_global": net.is_global,
            "is_multicast": net.is_multicast,
            "is_loopback": net.is_loopback,
            "version": net.version,
            # 二进制表示
            "network_binary": self._ip_to_binary(net.network_address),
            "netmask_binary": self._ip_to_binary(net.netmask),
        }
        
        # 计算通配符掩码
        info["wildcard_mask"] = str(net.hostmask)
        
        return info
    
    def _ip_to_binary(self, ip: ipaddress.IPv4Address) -> str:
        """将IP地址转换为二进制字符串"""
        octets = str(ip).split('.')
        binary = '.'.join(format(int(o), '08b') for o in octets)
        return binary
    
    def _split_by_prefix(
        self,
        net: ipaddress.IPv4Network,
        new_prefix: int,
    ) -> Dict[str, Any]:
        """
        按前缀长度划分子网
        
        Args:
            net: 原始网络
            new_prefix: 新的前缀长度
            
        Returns:
            划分结果
        """
        if new_prefix <= net.prefixlen:
            return {"error": f"新前缀长度必须大于原前缀长度 {net.prefixlen}"}
        
        if new_prefix > 32:
            return {"error": "前缀长度不能超过32"}
        
        try:
            subnets = list(net.subnets(new_prefix=new_prefix))
            
            subnet_info = []
            for i, subnet in enumerate(subnets):
                hosts = list(subnet.hosts())
                subnet_info.append({
                    "index": i + 1,
                    "network": str(subnet.network_address),
                    "cidr": str(subnet),
                    "broadcast": str(subnet.broadcast_address),
                    "netmask": str(subnet.netmask),
                    "first_host": str(hosts[0]) if hosts else "-",
                    "last_host": str(hosts[-1]) if hosts else "-",
                    "usable_hosts": len(hosts),
                })
            
            return {
                "original_network": str(net),
                "new_prefix": new_prefix,
                "subnet_count": len(subnets),
                "hosts_per_subnet": subnet_info[0]["usable_hosts"] if subnet_info else 0,
                "subnets": subnet_info,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _split_by_count(
        self,
        net: ipaddress.IPv4Network,
        count: int,
    ) -> Dict[str, Any]:
        """
        按数量划分子网
        
        Args:
            net: 原始网络
            count: 需要的子网数量
            
        Returns:
            划分结果
        """
        import math
        
        # 计算需要的额外位数
        extra_bits = math.ceil(math.log2(count))
        new_prefix = net.prefixlen + extra_bits
        
        if new_prefix > 32:
            return {"error": f"无法划分{count}个子网,原网络太小"}
        
        return self._split_by_prefix(net, new_prefix)
    
    def _get_supernet_info(self, net: ipaddress.IPv4Network) -> Dict[str, Any]:
        """
        获取超网(聚合)信息
        
        Args:
            net: 网络对象
            
        Returns:
            超网信息
        """
        supernets = []
        
        current = net
        while current.prefixlen > 0:
            try:
                current = current.supernet()
                supernets.append({
                    "cidr": str(current),
                    "prefix": current.prefixlen,
                    "addresses": current.num_addresses,
                })
                
                # 限制只显示8级
                if len(supernets) >= 8:
                    break
            except Exception:
                break
        
        return {
            "original_network": str(net),
            "supernets": supernets,
        }
    
    def _display_network_info(self, info: Dict[str, Any], network: str) -> None:
        """显示网络信息"""
        console.print(f"\n[bold cyan]网络详细信息: {network}[/bold cyan]\n")
        
        # 基本信息
        basic_info = {
            "网络地址": info["network"],
            "广播地址": info["broadcast"],
            "子网掩码": info["netmask"],
            "通配符掩码": info["wildcard_mask"],
            "前缀长度": f"/{info['prefix_length']}",
            "总地址数": info["total_addresses"],
            "可用主机数": info["usable_hosts"],
            "第一个主机": info["first_host"],
            "最后一个主机": info["last_host"],
        }
        
        console.print(create_summary_panel("基本信息", basic_info))
        
        # 属性信息
        attr_info = {
            "IP版本": f"IPv{info['version']}",
            "私有网络": "是" if info["is_private"] else "否",
            "公网地址": "是" if info["is_global"] else "否",
            "组播地址": "是" if info["is_multicast"] else "否",
            "环回地址": "是" if info["is_loopback"] else "否",
        }
        
        console.print(create_summary_panel("网络属性", attr_info))
        
        # 二进制表示
        console.print("[bold]二进制表示:[/bold]")
        console.print(f"  网络地址: [cyan]{info['network_binary']}[/cyan]")
        console.print(f"  子网掩码: [cyan]{info['netmask_binary']}[/cyan]")
        console.print()
    
    def _display_subnets(self, results: Dict[str, Any], network: str) -> None:
        """显示子网划分结果"""
        console.print(f"\n[bold cyan]子网划分: {network}[/bold cyan]\n")
        
        # 统计信息
        stats = {
            "原始网络": results["original_network"],
            "新前缀长度": f"/{results['new_prefix']}",
            "子网数量": results["subnet_count"],
            "每子网主机数": results["hosts_per_subnet"],
        }
        
        console.print(create_summary_panel("划分统计", stats))
        
        # 子网列表
        subnets = results.get("subnets", [])
        
        if subnets:
            columns = [
                {"header": "#", "justify": "center", "width": 4},
                {"header": "子网", "style": NetOpsTheme.IP_ADDRESS, "justify": "left"},
                {"header": "网络地址", "justify": "left"},
                {"header": "广播地址", "justify": "left"},
                {"header": "可用范围", "justify": "left"},
                {"header": "主机数", "justify": "right"},
            ]
            
            # 最多显示20个子网
            display_subnets = subnets[:20]
            
            rows = []
            for s in display_subnets:
                host_range = f"{s['first_host']} - {s['last_host']}" if s['first_host'] != "-" else "-"
                rows.append([
                    str(s["index"]),
                    s["cidr"],
                    s["network"],
                    s["broadcast"],
                    host_range,
                    str(s["usable_hosts"]),
                ])
            
            table = create_result_table("子网列表", columns, rows)
            console.print(table)
            
            if len(subnets) > 20:
                console.print(f"[dim]... 还有 {len(subnets) - 20} 个子网未显示[/dim]")
            
            console.print()
    
    def _display_supernet_info(self, results: Dict[str, Any], network: str) -> None:
        """显示超网信息"""
        console.print(f"\n[bold cyan]超网(聚合)信息: {network}[/bold cyan]\n")
        
        supernets = results.get("supernets", [])
        
        if supernets:
            columns = [
                {"header": "CIDR", "style": NetOpsTheme.IP_ADDRESS, "justify": "left"},
                {"header": "前缀", "justify": "center"},
                {"header": "地址数量", "justify": "right"},
            ]
            
            rows = [
                [s["cidr"], f"/{s['prefix']}", str(s["addresses"])]
                for s in supernets
            ]
            
            table = create_result_table("超网层级", columns, rows)
            console.print(table)
            console.print()


__all__ = ["SubnetCalcPlugin"]
