"""
NetOps Toolkit 交互式主程序

基于数字选择和快捷键的交互式界面。
"""

import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from netops_toolkit import __version__
from netops_toolkit.config.config_manager import get_config
from netops_toolkit.core.logger import setup_logging, get_logger, log_audit
from netops_toolkit.ui.theme import console
from netops_toolkit.ui.menu import Menu, MenuItem, MenuSystem, ParameterCollector
from netops_toolkit.plugins import PluginCategory, ResultStatus

logger = get_logger(__name__)


# ==================== 参数收集器 ====================

collector = ParameterCollector(console)


# ==================== 插件执行函数 ====================

def run_ping() -> bool:
    """Ping测试"""
    from netops_toolkit.plugins.diagnostics.ping import PingPlugin
    
    target = collector.collect_text("目标IP/主机名 (支持逗号分隔或CIDR)")
    if not target:
        return None
        
    count = collector.collect_number("Ping次数", default=4, min_val=1, max_val=100)
    if count is None:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=2.0)
    if timeout is None:
        return None
        
    export = collector.collect_text("导出文件路径 (留空跳过)", default="", required=False)
    
    plugin = PingPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            targets=target,
            count=count,
            timeout=timeout,
            export_path=export if export else None,
        )
        log_audit("interactive", "ping", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_traceroute() -> bool:
    """路由追踪"""
    from netops_toolkit.plugins.diagnostics.traceroute import TraceroutePlugin
    
    target = collector.collect_text("目标IP/主机名")
    if not target:
        return None
        
    max_hops = collector.collect_number("最大跳数", default=30, min_val=1, max_val=64)
    if max_hops is None:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=3.0)
    if timeout is None:
        return None
    
    plugin = TraceroutePlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            target=target,
            max_hops=max_hops,
            timeout=timeout,
        )
        log_audit("interactive", "traceroute", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_dns() -> bool:
    """DNS查询"""
    from netops_toolkit.plugins.diagnostics.dns_lookup import DNSLookupPlugin as DnsLookupPlugin
    
    domain = collector.collect_text("域名或IP地址")
    if not domain:
        return None
        
    record_types = ["A", "AAAA", "MX", "CNAME", "NS", "TXT", "SOA", "PTR"]
    record_type = collector.collect_choice("记录类型", record_types, default="A")
    if not record_type:
        return None
        
    server = collector.collect_text("DNS服务器 (留空使用系统默认)", default="", required=False)
    
    plugin = DnsLookupPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            domain=domain,
            record_type=record_type,
            dns_server=server if server else None,
        )
        log_audit("interactive", "dns_lookup", domain, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_port_scan() -> bool:
    """端口扫描"""
    from netops_toolkit.plugins.scanning.port_scan import PortScanPlugin
    
    target = collector.collect_text("目标IP/主机名")
    if not target:
        return None
        
    ports = collector.collect_text("端口范围 (如: 80,443 或 1-1000)", default="1-1024")
    if not ports:
        return None
        
    threads = collector.collect_number("并发线程数", default=50, min_val=1, max_val=200)
    if threads is None:
        return None
    
    plugin = PortScanPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            target=target,
            ports=ports,
            threads=threads,
        )
        log_audit("interactive", "port_scan", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_arp_scan() -> bool:
    """ARP扫描"""
    from netops_toolkit.plugins.scanning.arp_scan import ArpScanPlugin
    
    target = collector.collect_text("目标网段 (如: 192.168.1.0/24)")
    if not target:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=1.0)
    if timeout is None:
        return None
        
    workers = collector.collect_number("并发数", default=50, min_val=1, max_val=200)
    if workers is None:
        return None
    
    plugin = ArpScanPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            network=target,
            timeout=timeout,
            workers=workers,
        )
        log_audit("interactive", "arp_scan", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_ssh_batch() -> bool:
    """SSH批量执行"""
    from netops_toolkit.plugins.device_mgmt.ssh_batch import SshBatchPlugin
    
    targets = collector.collect_text("目标设备IP (逗号分隔)")
    if not targets:
        return None
        
    commands = collector.collect_text("执行命令 (多条用分号分隔)")
    if not commands:
        return None
        
    username = collector.collect_text("SSH用户名")
    if not username:
        return None
        
    password = collector.collect_text("SSH密码")
    if not password:
        return None
        
    device_types = ["cisco_ios", "cisco_xe", "cisco_nxos", "huawei_vrp", "juniper_junos", "arista_eos"]
    device_type = collector.collect_choice("设备类型", device_types, default="cisco_ios")
    if not device_type:
        return None
        
    config_mode = collector.collect_bool("配置模式执行", default=False)
    if config_mode is None:
        return None
    
    plugin = SshBatchPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    target_list = [t.strip() for t in targets.split(",")]
    command_list = [c.strip() for c in commands.split(";")]
    
    try:
        result = plugin.run(
            targets=target_list,
            commands=command_list,
            username=username,
            password=password,
            device_type=device_type,
            config_mode=config_mode,
        )
        log_audit("interactive", "ssh_batch", targets, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_config_backup() -> bool:
    """配置备份"""
    from netops_toolkit.plugins.device_mgmt.config_backup import ConfigBackupPlugin
    
    targets = collector.collect_text("目标设备IP (逗号分隔)")
    if not targets:
        return None
        
    username = collector.collect_text("SSH用户名")
    if not username:
        return None
        
    password = collector.collect_text("SSH密码")
    if not password:
        return None
        
    backup_dir = collector.collect_text("备份目录", default="./backups")
    if not backup_dir:
        return None
        
    device_types = ["cisco_ios", "cisco_xe", "cisco_nxos", "huawei_vrp", "juniper_junos", "arista_eos"]
    device_type = collector.collect_choice("设备类型", device_types, default="cisco_ios")
    if not device_type:
        return None
    
    plugin = ConfigBackupPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    target_list = [t.strip() for t in targets.split(",")]
    
    try:
        result = plugin.run(
            targets=target_list,
            username=username,
            password=password,
            backup_dir=backup_dir,
            device_type=device_type,
        )
        log_audit("interactive", "config_backup", targets, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_config_diff() -> bool:
    """配置对比"""
    from netops_toolkit.plugins.device_mgmt.config_diff import ConfigDiffPlugin
    
    file1 = collector.collect_text("第一个配置文件路径")
    if not file1:
        return None
        
    file2 = collector.collect_text("第二个配置文件路径")
    if not file2:
        return None
        
    context = collector.collect_number("上下文行数", default=3, min_val=0, max_val=10)
    if context is None:
        return None
        
    ignore_whitespace = collector.collect_bool("忽略空白字符", default=False)
    if ignore_whitespace is None:
        return None
        
    ignore_comments = collector.collect_bool("忽略注释行", default=False)
    if ignore_comments is None:
        return None
    
    plugin = ConfigDiffPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            file1=file1,
            file2=file2,
            context_lines=context,
            ignore_whitespace=ignore_whitespace,
            ignore_comments=ignore_comments,
        )
        log_audit("interactive", "config_diff", f"{file1} vs {file2}", result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_network_quality() -> bool:
    """网络质量测试"""
    from netops_toolkit.plugins.performance.network_quality import NetworkQualityPlugin
    
    target = collector.collect_text("目标IP/主机名")
    if not target:
        return None
        
    count = collector.collect_number("测试次数", default=50, min_val=10, max_val=500)
    if count is None:
        return None
        
    interval = collector.collect_float("测试间隔(秒)", default=0.2)
    if interval is None:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=3.0)
    if timeout is None:
        return None
    
    plugin = NetworkQualityPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            target=target,
            count=count,
            interval=interval,
            timeout=timeout,
        )
        log_audit("interactive", "network_quality", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_speedtest() -> bool:
    """带宽测速"""
    from netops_toolkit.plugins.performance.bandwidth_test import BandwidthTestPlugin
    
    server_id = collector.collect_text("测速服务器ID (留空自动选择)", default="", required=False)
    timeout = collector.collect_number("超时时间(秒)", default=60, min_val=30, max_val=300)
    if timeout is None:
        return None
        
    simple = collector.collect_bool("简化输出", default=False)
    if simple is None:
        return None
    
    plugin = BandwidthTestPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            server_id=server_id if server_id else None,
            timeout=timeout,
            simple=simple,
        )
        log_audit("interactive", "speedtest", "bandwidth_test", result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_subnet_calc() -> bool:
    """子网计算"""
    from netops_toolkit.plugins.utils.subnet_calc import SubnetCalcPlugin
    
    network = collector.collect_text("网络地址 (如: 192.168.1.0/24)")
    if not network:
        return None
    
    plugin = SubnetCalcPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(network=network)
        log_audit("interactive", "subnet_calc", network, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_ip_convert() -> bool:
    """IP格式转换"""
    from netops_toolkit.plugins.utils.ip_converter import IPConverterPlugin
    
    ip = collector.collect_text("IP地址 (支持多种格式)")
    if not ip:
        return None
    
    plugin = IPConverterPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        # 该插件使用params字典传参
        result = plugin.run({"ip": ip})
        log_audit("interactive", "ip_convert", ip, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_mac_lookup() -> bool:
    """MAC地址查询"""
    from netops_toolkit.plugins.utils.mac_lookup import MacLookupPlugin
    
    mac = collector.collect_text("MAC地址")
    if not mac:
        return None
    
    plugin = MacLookupPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(mac_address=mac)
        log_audit("interactive", "mac_lookup", mac, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_http_debug() -> bool:
    """HTTP调试"""
    from netops_toolkit.plugins.utils.http_debug import HttpDebugPlugin
    
    url = collector.collect_text("URL地址")
    if not url:
        return None
        
    methods = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]
    method = collector.collect_choice("HTTP方法", methods, default="GET")
    if not method:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=10.0)
    if timeout is None:
        return None
    
    plugin = HttpDebugPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            url=url,
            method=method,
            timeout=timeout,
        )
        log_audit("interactive", "http_debug", url, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_whois() -> bool:
    """WHOIS查询"""
    from netops_toolkit.plugins.utils.whois_lookup import WhoisLookupPlugin
    
    target = collector.collect_text("域名或IP地址")
    if not target:
        return None
        
    timeout = collector.collect_number("超时时间(秒)", default=30, min_val=10, max_val=120)
    if timeout is None:
        return None
    
    plugin = WhoisLookupPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            target=target,
            timeout=timeout,
        )
        log_audit("interactive", "whois", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


# ==================== 新增插件函数 ====================

def run_mtr() -> bool:
    """MTR路由追踪"""
    from netops_toolkit.plugins.diagnostics.mtr import MtrPlugin
    
    target = collector.collect_text("目标IP/主机名")
    if not target:
        return None
        
    count = collector.collect_number("测试次数", default=10, min_val=1, max_val=100)
    if count is None:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=1.0)
    if timeout is None:
        return None
    
    plugin = MtrPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            target=target,
            count=count,
            timeout=timeout,
        )
        log_audit("interactive", "mtr", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_tcp_connect() -> bool:
    """TCP端口连通性测试"""
    from netops_toolkit.plugins.diagnostics.tcp_connect import TcpConnectPlugin
    
    host = collector.collect_text("目标主机")
    if not host:
        return None
        
    ports = collector.collect_text("端口 (多个用逗号分隔)", default="80,443")
    if not ports:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=3.0)
    if timeout is None:
        return None
    
    plugin = TcpConnectPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            host=host,
            ports=ports,
            timeout=timeout,
        )
        log_audit("interactive", "tcp_connect", f"{host}:{ports}", result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_ssl_checker() -> bool:
    """SSL证书检查"""
    from netops_toolkit.plugins.utils.ssl_checker import SslCheckerPlugin
    
    host = collector.collect_text("目标主机")
    if not host:
        return None
        
    port = collector.collect_number("端口", default=443, min_val=1, max_val=65535)
    if port is None:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=10.0)
    if timeout is None:
        return None
    
    plugin = SslCheckerPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            host=host,
            port=port,
            timeout=timeout,
        )
        log_audit("interactive", "ssl_checker", host, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_netinfo() -> bool:
    """网络接口信息"""
    from netops_toolkit.plugins.utils.netinfo import NetInfoPlugin
    
    show_all = collector.collect_bool("显示所有接口 (包括禁用的)", default=False)
    if show_all is None:
        return None
    
    plugin = NetInfoPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(show_all=show_all)
        log_audit("interactive", "netinfo", "local", result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_wake_on_lan() -> bool:
    """Wake-on-LAN"""
    from netops_toolkit.plugins.utils.wake_on_lan import WakeOnLanPlugin
    
    mac = collector.collect_text("目标MAC地址")
    if not mac:
        return None
        
    broadcast = collector.collect_text("广播地址", default="255.255.255.255")
    if not broadcast:
        return None
        
    port = collector.collect_number("端口", default=9, min_val=1, max_val=65535)
    if port is None:
        return None
    
    plugin = WakeOnLanPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            mac=mac,
            broadcast=broadcast,
            port=port,
        )
        log_audit("interactive", "wol", mac, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_snmp_query() -> bool:
    """SNMP查询"""
    from netops_toolkit.plugins.diagnostics.snmp_query import SnmpQueryPlugin
    
    host = collector.collect_text("目标主机")
    if not host:
        return None
        
    oid = collector.collect_text("OID (或名称如 sysDescr)", default="sysDescr")
    if not oid:
        return None
        
    community = collector.collect_text("Community字符串", default="public")
    if not community:
        return None
        
    operations = ["get", "walk"]
    operation = collector.collect_choice("操作类型", operations, default="get")
    if not operation:
        return None
    
    plugin = SnmpQueryPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            host=host,
            oid=oid,
            community=community,
            operation=operation,
        )
        log_audit("interactive", "snmp", host, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_route_table() -> bool:
    """路由表查看"""
    from netops_toolkit.plugins.diagnostics.route_table import RouteTablePlugin
    
    ipv6 = collector.collect_bool("显示IPv6路由", default=False)
    if ipv6 is None:
        return None
    
    plugin = RouteTablePlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(ipv6=ipv6)
        log_audit("interactive", "route_table", "local", result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_netstat() -> bool:
    """网络连接查看"""
    from netops_toolkit.plugins.diagnostics.netstat import NetstatPlugin
    
    modes = ["listen", "established", "all"]
    mode = collector.collect_choice("模式", modes, default="listen")
    if not mode:
        return None
        
    protocols = ["all", "tcp", "udp"]
    protocol = collector.collect_choice("协议", protocols, default="all")
    if not protocol:
        return None
    
    plugin = NetstatPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            mode=mode,
            protocol=protocol,
        )
        log_audit("interactive", "netstat", mode, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_host_discovery() -> bool:
    """主机发现"""
    from netops_toolkit.plugins.diagnostics.host_discovery import HostDiscoveryPlugin
    
    target = collector.collect_text("目标网段 (如: 192.168.1.0/24)")
    if not target:
        return None
        
    methods = ["tcp", "ping", "both"]
    method = collector.collect_choice("探测方式", methods, default="tcp")
    if not method:
        return None
        
    ports = collector.collect_text("TCP探测端口", default="22,80,443,3389")
    if not ports:
        return None
        
    timeout = collector.collect_float("超时时间(秒)", default=1.0)
    if timeout is None:
        return None
        
    workers = collector.collect_number("并发数", default=50, min_val=1, max_val=200)
    if workers is None:
        return None
    
    plugin = HostDiscoveryPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            target=target,
            method=method,
            ports=ports,
            timeout=timeout,
            workers=workers,
        )
        log_audit("interactive", "host_discovery", target, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_config_validator() -> bool:
    """配置文件验证"""
    from netops_toolkit.plugins.utils.config_validator import ConfigValidatorPlugin
    
    file_path = collector.collect_text("配置文件路径")
    if not file_path:
        return None
        
    formats = ["auto", "json", "yaml"]
    format_type = collector.collect_choice("格式", formats, default="auto")
    if not format_type:
        return None
        
    show_content = collector.collect_bool("显示文件内容", default=True)
    if show_content is None:
        return None
    
    plugin = ConfigValidatorPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            file_path=file_path,
            format=format_type,
            show_content=show_content,
        )
        log_audit("interactive", "config_validator", file_path, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_base64_tool() -> bool:
    """Base64编解码"""
    from netops_toolkit.plugins.utils.base64_tool import Base64ToolPlugin
    
    actions = ["encode", "decode"]
    action = collector.collect_choice("操作", actions, default="encode")
    if not action:
        return None
        
    input_text = collector.collect_text("输入内容 (文件用 file: 前缀)")
    if not input_text:
        return None
        
    output_file = collector.collect_text("输出文件 (留空不保存)", default="", required=False)
    
    url_safe = collector.collect_bool("URL安全模式", default=False)
    if url_safe is None:
        return None
    
    plugin = Base64ToolPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            action=action,
            input_text=input_text,
            output_file=output_file if output_file else "",
            url_safe=url_safe,
        )
        log_audit("interactive", "base64", action, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


def run_password_generator() -> bool:
    """密码生成器"""
    from netops_toolkit.plugins.utils.password_generator import PasswordGeneratorPlugin
    
    modes = ["random", "memorable", "pin"]
    mode = collector.collect_choice("模式", modes, default="random")
    if not mode:
        return None
        
    length = collector.collect_number("密码长度", default=16, min_val=4, max_val=128)
    if length is None:
        return None
        
    count = collector.collect_number("生成数量", default=5, min_val=1, max_val=100)
    if count is None:
        return None
    
    plugin = PasswordGeneratorPlugin()
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return False
        
    try:
        result = plugin.run(
            mode=mode,
            length=length,
            count=count,
        )
        log_audit("interactive", "password_gen", mode, result.status.value)
        return result.status == ResultStatus.SUCCESS
    finally:
        plugin.cleanup()


# ==================== 系统功能 ====================

def show_about():
    """显示关于信息"""
    about_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
    about_table.add_column("项目", style="cyan")
    about_table.add_column("信息", style="white")
    
    about_table.add_row("名称", "NetOps Toolkit")
    about_table.add_row("版本", __version__)
    about_table.add_row("描述", "网络工程实施及测试工具集")
    about_table.add_row("作者", "Network Engineering Team")
    about_table.add_row("许可证", "MIT License")
    about_table.add_row("插件数", "27")
    about_table.add_row("命令数", "29")
    
    panel = Panel(about_table, title="[bold cyan]关于 NetOps Toolkit[/bold cyan]", border_style="cyan")
    console.print(panel)
    return None


def show_settings():
    """显示设置信息"""
    config = get_config()
    
    settings_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
    settings_table.add_column("配置项", style="cyan")
    settings_table.add_column("当前值", style="white")
    
    settings_table.add_row("日志级别", config.get("app.log_level", "INFO"))
    settings_table.add_row("日志目录", config.get("output.log_dir", "./logs"))
    settings_table.add_row("报告目录", config.get("output.reports_dir", "./reports"))
    settings_table.add_row("SSH超时", f"{config.get('network.ssh_timeout', 30)}秒")
    settings_table.add_row("重试次数", str(config.get("network.connect_retry", 3)))
    settings_table.add_row("密码加密", "启用" if config.get("security.encrypt_passwords", True) else "禁用")
    
    panel = Panel(settings_table, title="[bold cyan]当前设置[/bold cyan]", border_style="cyan")
    console.print(panel)
    return None


# ==================== 构建菜单 ====================

def build_menus() -> Menu:
    """构建菜单结构"""
    
    # 诊断工具子菜单
    diagnostics_menu = Menu(
        title="🔍 诊断工具",
        items=[
            MenuItem("1", "Ping测试", "检测网络连通性", run_ping, icon="🏓"),
            MenuItem("2", "路由追踪", "追踪数据包路径", run_traceroute, icon="🗺️"),
            MenuItem("3", "DNS查询", "域名解析查询", run_dns, icon="🌐"),
            MenuItem("4", "MTR追踪", "综合Ping+Traceroute", run_mtr, icon="📊"),
            MenuItem("5", "TCP连接测试", "测试TCP端口连通性", run_tcp_connect, icon="🔌"),
            MenuItem("6", "SNMP查询", "查询网络设备SNMP", run_snmp_query, icon="📡"),
            MenuItem("7", "路由表", "查看系统路由表", run_route_table, icon="🛏️"),
            MenuItem("8", "网络连接", "查看网络连接状态", run_netstat, icon="📈"),
        ]
    )
    
    # 网络扫描子菜单
    scanning_menu = Menu(
        title="📡 网络扫描",
        items=[
            MenuItem("1", "端口扫描", "扫描目标开放端口", run_port_scan, icon="🔌"),
            MenuItem("2", "ARP扫描", "局域网主机发现", run_arp_scan, icon="📶"),
            MenuItem("3", "主机发现", "批量检测存活主机", run_host_discovery, icon="🔎"),
        ]
    )
    
    # 设备管理子菜单
    device_mgmt_menu = Menu(
        title="🖥️ 设备管理",
        items=[
            MenuItem("1", "SSH批量执行", "批量执行SSH命令", run_ssh_batch, icon="💻"),
            MenuItem("2", "配置备份", "备份设备配置", run_config_backup, icon="💾"),
            MenuItem("3", "配置对比", "对比配置文件差异", run_config_diff, icon="📊"),
            MenuItem("4", "Wake-on-LAN", "远程唤醒设备", run_wake_on_lan, icon="💡"),
        ]
    )
    
    # 性能测试子菜单
    performance_menu = Menu(
        title="⚡ 性能测试",
        items=[
            MenuItem("1", "网络质量", "测试延迟/抖动/丢包", run_network_quality, icon="📈"),
            MenuItem("2", "带宽测速", "测试上下行带宽", run_speedtest, icon="🚀"),
        ]
    )
    
    # 实用工具子菜单
    utils_menu = Menu(
        title="🛠️ 实用工具",
        items=[
            MenuItem("1", "子网计算器", "计算子网信息", run_subnet_calc, icon="🔢"),
            MenuItem("2", "IP格式转换", "IP地址格式转换", run_ip_convert, icon="🔄"),
            MenuItem("3", "MAC地址查询", "查询MAC厂商信息", run_mac_lookup, icon="🏭"),
            MenuItem("4", "HTTP调试", "测试HTTP请求", run_http_debug, icon="🌍"),
            MenuItem("5", "WHOIS查询", "查询域名/IP注册信息", run_whois, icon="📋"),
            MenuItem("6", "SSL证书检查", "检查HTTPS证书信息", run_ssl_checker, icon="🔐"),
            MenuItem("7", "网络接口信息", "查看本机网络配置", run_netinfo, icon="🌐"),
            MenuItem("8", "配置验证器", "验证JSON/YAML格式", run_config_validator, icon="✅"),
            MenuItem("9", "Base64工具", "Base64编解码", run_base64_tool, icon="🔤"),
            MenuItem("P", "密码生成器", "生成安全密码", run_password_generator, icon="🔑", shortcut="P"),
        ]
    )
    
    # 主菜单
    main_menu = Menu(
        title="NetOps Toolkit v" + __version__,
        items=[
            MenuItem("1", "诊断工具", "Ping/Traceroute/DNS/MTR等", submenu=diagnostics_menu, icon="🔍"),
            MenuItem("2", "网络扫描", "端口扫描/主机发现", submenu=scanning_menu, icon="📡"),
            MenuItem("3", "设备管理", "SSH批量/配置备份/WOL", submenu=device_mgmt_menu, icon="🖥️"),
            MenuItem("4", "性能测试", "网络质量/带宽测速", submenu=performance_menu, icon="⚡"),
            MenuItem("5", "实用工具", "子网计算/SSL/密码等", submenu=utils_menu, icon="🛠️"),
            MenuItem("S", "系统设置", "查看当前配置", show_settings, icon="⚙️", shortcut="S"),
            MenuItem("A", "关于", "关于本程序", show_about, icon="ℹ️", shortcut="A"),
        ],
        footer="提示: 输入数字选择功能,输入 Q 退出程序",
    )
    
    return main_menu


def init_app():
    """初始化应用"""
    config = get_config()
    
    log_level = config.get("app.log_level", "INFO")
    log_dir = config.get("output.log_dir", "./logs")
    
    setup_logging(
        log_dir=log_dir,
        log_level=log_level,
        enable_console=False,  # 交互模式禁用控制台日志
        enable_file=True,
    )


def main():
    """主入口"""
    init_app()
    
    main_menu = build_menus()
    menu_system = MenuSystem(console)
    menu_system.run(main_menu)


if __name__ == "__main__":
    main()
