"""
NetOps Toolkit CLI 入口

基于Typer构建的CLI框架,支持命令行和交互式两种模式。
"""

import sys
from pathlib import Path
from typing import List, Optional

import questionary
import typer
from rich.console import Console

from netops_toolkit import __version__
from netops_toolkit.config.config_manager import get_config
from netops_toolkit.core.logger import setup_logging, get_logger, log_audit
from netops_toolkit.plugins import (
    Plugin,
    PluginCategory,
    get_registered_plugins,
)
from netops_toolkit.ui.theme import NetOpsTheme, console
from netops_toolkit.ui.components import (
    create_header_panel,
    create_summary_panel,
    print_banner,
    print_separator,
)

# 创建Typer应用
app = typer.Typer(
    name="netops",
    help="NetOps Toolkit - 网络工程实施及测试工具集",
    add_completion=False,
    pretty_exceptions_show_locals=False,
)

logger = get_logger(__name__)


def init_app() -> None:
    """初始化应用程序"""
    config = get_config()
    
    # 初始化日志系统
    log_level = config.get("app.log_level", "INFO")
    log_dir = config.get("output.log_dir", "./logs")
    
    setup_logging(
        log_dir=log_dir,
        log_level=log_level,
        enable_console=True,
        enable_file=True,
    )
    
    logger.debug("NetOps Toolkit 已初始化")


def show_banner() -> None:
    """显示应用横幅"""
    config = get_config()
    
    if config.get("ui.show_banner", True):
        print_banner("NetOps Toolkit", __version__)
        console.print()


def get_plugins_by_category() -> dict:
    """
    按分类获取已注册的插件
    
    Returns:
        {category: [plugin_classes]} 字典
    """
    plugins = get_registered_plugins()
    categorized = {}
    
    for name, plugin_class in plugins.items():
        category = plugin_class.category
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(plugin_class)
    
    return categorized


def build_main_menu() -> List[dict]:
    """
    构建主菜单选项
    
    Returns:
        菜单选项列表
    """
    category_icons = {
        PluginCategory.DIAGNOSTICS: "🔍",
        PluginCategory.DEVICE_MGMT: "🖥️",
        PluginCategory.SCANNING: "📡",
        PluginCategory.PERFORMANCE: "⚡",
        PluginCategory.UTILS: "🛠️",
    }
    
    category_names = {
        PluginCategory.DIAGNOSTICS: "诊断工具",
        PluginCategory.DEVICE_MGMT: "设备管理",
        PluginCategory.SCANNING: "网络扫描",
        PluginCategory.PERFORMANCE: "性能测试",
        PluginCategory.UTILS: "实用工具",
    }
    
    plugins_by_category = get_plugins_by_category()
    
    menu_items = []
    
    for category in PluginCategory:
        plugins = plugins_by_category.get(category, [])
        icon = category_icons.get(category, "•")
        name = category_names.get(category, category.value)
        count = len(plugins)
        
        menu_items.append({
            "name": f"{icon} {name} ({count})",
            "value": category,
            "disabled": "无可用插件" if count == 0 else None,
        })
    
    # 添加其他菜单项
    menu_items.extend([
        questionary.Separator("─" * 30),
        {"name": "⚙️  设置", "value": "settings"},
        {"name": "ℹ️  关于", "value": "about"},
        {"name": "🚪 退出", "value": "exit"},
    ])
    
    return menu_items


def build_plugin_menu(category: PluginCategory) -> List[dict]:
    """
    构建插件子菜单
    
    Args:
        category: 插件分类
        
    Returns:
        菜单选项列表
    """
    plugins_by_category = get_plugins_by_category()
    plugins = plugins_by_category.get(category, [])
    
    menu_items = []
    
    for plugin_class in plugins:
        plugin = plugin_class()
        menu_items.append({
            "name": f"{plugin.get_menu_title()} - {plugin.description}",
            "value": plugin_class,
        })
    
    menu_items.append({"name": "⬅️  返回上级", "value": "back"})
    
    return menu_items


def show_about() -> None:
    """显示关于信息"""
    about_info = {
        "名称": "NetOps Toolkit",
        "版本": __version__,
        "描述": "网络工程实施及测试工具集",
        "作者": "Network Engineering Team",
        "许可证": "MIT License",
    }
    
    panel = create_summary_panel("关于 NetOps Toolkit", about_info)
    console.print(panel)


def show_settings() -> None:
    """显示设置信息"""
    config = get_config()
    
    settings_info = {
        "日志级别": config.get("app.log_level", "INFO"),
        "日志目录": config.get("output.log_dir", "./logs"),
        "报告目录": config.get("output.reports_dir", "./reports"),
        "SSH超时": f"{config.get('network.ssh_timeout', 30)}秒",
        "重试次数": config.get("network.connect_retry", 3),
        "密码加密": "启用" if config.get("security.encrypt_passwords", True) else "禁用",
    }
    
    panel = create_summary_panel("当前设置", settings_info)
    console.print(panel)


def run_plugin_interactive(plugin_class: type) -> None:
    """
    交互式运行插件
    
    Args:
        plugin_class: 插件类
    """
    plugin = plugin_class()
    
    # 显示插件信息
    console.print(f"\n[bold cyan]>>> {plugin.name}[/bold cyan]")
    console.print(f"[dim]{plugin.description}[/dim]\n")
    
    # 初始化插件
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        return
    
    try:
        # 获取参数规格
        params_spec = plugin.get_required_params()
        params = {}
        
        # 交互式收集参数
        for spec in params_spec:
            if spec.choices:
                # 选择题
                value = questionary.select(
                    f"{spec.description}:",
                    choices=spec.choices,
                    default=spec.default,
                ).ask()
            elif spec.param_type == bool:
                # 布尔值
                value = questionary.confirm(
                    f"{spec.description}",
                    default=spec.default if spec.default is not None else True,
                ).ask()
            elif spec.param_type == list:
                # 列表 (逗号分隔)
                raw = questionary.text(
                    f"{spec.description} (逗号分隔):",
                    default=",".join(spec.default) if spec.default else "",
                ).ask()
                value = [x.strip() for x in raw.split(",") if x.strip()]
            else:
                # 文本输入
                value = questionary.text(
                    f"{spec.description}:",
                    default=str(spec.default) if spec.default is not None else "",
                ).ask()
            
            if value is None:  # 用户取消
                console.print("[yellow]操作已取消[/yellow]")
                return
            
            params[spec.name] = value
        
        # 执行插件
        console.print()
        result = plugin.run(**params)
        
        # 记录审计日志
        log_audit(
            user="interactive",
            action=plugin.name,
            target=str(params),
            result=result.status.value,
        )
        
        # 显示结果
        if result.is_success:
            console.print(f"\n[green]✅ {result.message}[/green]")
        else:
            console.print(f"\n[red]❌ {result.message}[/red]")
            for error in result.errors:
                console.print(f"  [red]• {error}[/red]")
                
    finally:
        plugin.cleanup()


def interactive_mode() -> None:
    """交互式菜单模式"""
    show_banner()
    
    while True:
        try:
            # 主菜单
            menu_items = build_main_menu()
            
            choice = questionary.select(
                "请选择功能:",
                choices=menu_items,
                style=questionary.Style([
                    ("selected", "fg:cyan bold"),
                    ("pointer", "fg:cyan bold"),
                ]),
            ).ask()
            
            if choice is None or choice == "exit":
                console.print("\n[cyan]感谢使用 NetOps Toolkit,再见![/cyan]\n")
                break
            
            if choice == "about":
                show_about()
                continue
            
            if choice == "settings":
                show_settings()
                continue
            
            # 如果是分类,显示插件菜单
            if isinstance(choice, PluginCategory):
                while True:
                    plugin_menu = build_plugin_menu(choice)
                    
                    plugin_choice = questionary.select(
                        f"选择 {choice.value} 插件:",
                        choices=plugin_menu,
                    ).ask()
                    
                    if plugin_choice is None or plugin_choice == "back":
                        break
                    
                    # 运行选中的插件
                    run_plugin_interactive(plugin_choice)
                    
                    # 等待用户按键继续
                    questionary.press_any_key_to_continue(
                        message="\n按任意键继续..."
                    ).ask()
                    
        except KeyboardInterrupt:
            console.print("\n\n[yellow]操作已中断[/yellow]")
            break
        except Exception as e:
            logger.error(f"运行错误: {e}")
            console.print(f"\n[red]错误: {e}[/red]")


# ==================== CLI 命令 ====================

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="显示版本号"),
):
    """
    NetOps Toolkit - 网络工程实施及测试工具集
    
    无参数运行进入交互式模式,或使用子命令执行特定功能。
    """
    init_app()
    
    if version:
        console.print(f"NetOps Toolkit v{__version__}")
        raise typer.Exit()
    
    # 如果没有子命令,进入交互模式
    if ctx.invoked_subcommand is None:
        interactive_mode()


@app.command()
def ping(
    targets: str = typer.Argument(..., help="目标IP或主机名 (支持逗号分隔或CIDR)"),
    count: int = typer.Option(4, "-c", "--count", help="Ping次数"),
    timeout: float = typer.Option(2.0, "-t", "--timeout", help="超时时间(秒)"),
    export: Optional[str] = typer.Option(None, "-o", "--output", help="导出文件路径"),
):
    """
    Ping测试 - 检测网络连通性
    
    示例:
        netops ping 192.168.1.1
        netops ping 192.168.1.1,192.168.1.2 -c 10
        netops ping 192.168.1.0/24 -o result.json
    """
    # 动态导入插件
    try:
        from netops_toolkit.plugins.diagnostics.ping import PingPlugin
    except ImportError as e:
        console.print(f"[red]无法加载Ping插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = PingPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run(
            targets=targets,
            count=count,
            timeout=timeout,
            export_path=export,
        )
        
        log_audit(
            user="cli",
            action="ping",
            target=targets,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command()
def scan(
    target: str = typer.Argument(..., help="目标IP或网段"),
    ports: str = typer.Option("1-1024", "-p", "--ports", help="端口范围"),
    threads: int = typer.Option(50, "-T", "--threads", help="线程数"),
):
    """
    端口扫描 - 检测开放端口
    
    示例:
        netops scan 192.168.1.1
        netops scan 192.168.1.1 -p 22,80,443
        netops scan 192.168.1.0/24 -p 1-1000 -T 100
    """
    try:
        from netops_toolkit.plugins.scanning.port_scan import PortScanPlugin
    except ImportError as e:
        console.print(f"[red]无法加载端口扫描插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = PortScanPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run(
            target=target,
            ports=ports,
            threads=threads,
        )
        
        log_audit(
            user="cli",
            action="port_scan",
            target=target,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command()
def dns(
    domain: str = typer.Argument(..., help="域名或IP地址"),
    record_type: str = typer.Option("A", "-t", "--type", help="记录类型 (A, AAAA, MX, CNAME, NS, TXT)"),
    server: Optional[str] = typer.Option(None, "-s", "--server", help="DNS服务器"),
):
    """
    DNS查询 - 域名解析
    
    示例:
        netops dns www.baidu.com
        netops dns baidu.com -t MX
        netops dns 8.8.8.8
    """
    try:
        from netops_toolkit.plugins.diagnostics.dns_lookup import DNSLookupPlugin
    except ImportError as e:
        console.print(f"[red]无法加载DNS查询插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = DNSLookupPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run(
            domain=domain,
            record_type=record_type,
            dns_server=server,
        )
        
        log_audit(
            user="cli",
            action="dns_lookup",
            target=domain,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="ssh-batch")
def ssh_batch(
    targets: Optional[List[str]] = typer.Option(None, "-t", "--target", help="目标设备IP列表"),
    group: Optional[str] = typer.Option(None, "-g", "--group", help="设备组名称"),
    commands: List[str] = typer.Option(..., "-c", "--command", help="要执行的命令(可多次指定)"),
    username: str = typer.Option("admin", "-u", "--username", help="SSH用户名"),
    password: str = typer.Option("", "-p", "--password", help="SSH密码"),
    device_type: str = typer.Option("cisco_ios", "--device-type", help="设备类型"),
    max_workers: int = typer.Option(5, "-w", "--workers", help="最大并发数"),
    timeout: int = typer.Option(30, "--timeout", help="连接超时(秒)"),
    config_mode: bool = typer.Option(False, "--config", help="配置模式执行"),
):
    """
    SSH批量执行 - 在多台设备上执行命令
    
    示例:
        netops ssh-batch -t 192.168.1.1 -t 192.168.1.2 -c "show version" -u admin -p password
        netops ssh-batch -g core_switches -c "show ip int brief" -c "show running-config"
    """
    try:
        from netops_toolkit.plugins.device_mgmt.ssh_batch import SSHBatchPlugin
    except ImportError as e:
        console.print(f"[red]无法加载SSH批量执行插件: {e}[/red]")
        raise typer.Exit(1)
    
    if not targets and not group:
        console.print("[red]请指定设备 (-t) 或设备组 (-g)[/red]")
        raise typer.Exit(1)
    
    plugin = SSHBatchPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        params = {
            "commands": commands,
            "username": username,
            "password": password,
            "device_type": device_type,
            "max_workers": max_workers,
            "timeout": timeout,
            "config_mode": config_mode,
        }
        
        if targets:
            params["targets"] = targets
        if group:
            params["group"] = group
        
        result = plugin.run(params)
        
        log_audit(
            user="cli",
            action="ssh_batch",
            target=group or ",".join(targets) if targets else "unknown",
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="config-backup")
def config_backup(
    targets: Optional[List[str]] = typer.Option(None, "-t", "--target", help="目标设备IP列表"),
    group: Optional[str] = typer.Option(None, "-g", "--group", help="设备组名称"),
    username: str = typer.Option("admin", "-u", "--username", help="SSH用户名"),
    password: str = typer.Option("", "-p", "--password", help="SSH密码"),
    device_type: str = typer.Option("cisco_ios", "--device-type", help="设备类型"),
    backup_dir: str = typer.Option("./backups", "-d", "--dir", help="备份目录"),
    max_workers: int = typer.Option(5, "-w", "--workers", help="最大并发数"),
    timeout: int = typer.Option(60, "--timeout", help="连接超时(秒)"),
):
    """
    配置备份 - 备份设备配置
    
    示例:
        netops config-backup -t 192.168.1.1 -u admin -p password
        netops config-backup -g core_switches -d ./backups/core
    """
    try:
        from netops_toolkit.plugins.device_mgmt.config_backup import ConfigBackupPlugin
    except ImportError as e:
        console.print(f"[red]无法加载配置备份插件: {e}[/red]")
        raise typer.Exit(1)
    
    if not targets and not group:
        console.print("[red]请指定设备 (-t) 或设备组 (-g)[/red]")
        raise typer.Exit(1)
    
    plugin = ConfigBackupPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        params = {
            "username": username,
            "password": password,
            "device_type": device_type,
            "backup_dir": backup_dir,
            "max_workers": max_workers,
            "timeout": timeout,
        }
        
        if targets:
            params["targets"] = targets
        if group:
            params["group"] = group
        
        result = plugin.run(params)
        
        log_audit(
            user="cli",
            action="config_backup",
            target=group or ",".join(targets) if targets else "unknown",
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command()
def traceroute(
    target: str = typer.Argument(..., help="目标IP或主机名"),
    max_hops: int = typer.Option(30, "-m", "--max-hops", help="最大跳数"),
    timeout: float = typer.Option(3.0, "-t", "--timeout", help="超时时间(秒)"),
    export: Optional[str] = typer.Option(None, "-o", "--output", help="导出文件路径"),
):
    """
    路由追踪 - 追踪到目标的网络路径
    
    示例:
        netops traceroute www.baidu.com
        netops traceroute 8.8.8.8 -m 15
    """
    try:
        from netops_toolkit.plugins.diagnostics.traceroute import TraceroutePlugin
    except ImportError as e:
        console.print(f"[red]无法加载Traceroute插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = TraceroutePlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run(
            target=target,
            max_hops=max_hops,
            timeout=timeout,
            export_path=export,
        )
        
        log_audit(
            user="cli",
            action="traceroute",
            target=target,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command()
def http(
    url: str = typer.Argument(..., help="目标URL"),
    method: str = typer.Option("GET", "-m", "--method", help="HTTP方法"),
    timeout: float = typer.Option(10.0, "-t", "--timeout", help="超时时间(秒)"),
    export: Optional[str] = typer.Option(None, "-o", "--output", help="导出文件路径"),
):
    """
    HTTP调试 - 测试HTTP/HTTPS请求
    
    示例:
        netops http https://www.baidu.com
        netops http https://api.github.com -m POST
    """
    try:
        from netops_toolkit.plugins.utils.http_debug import HTTPDebugPlugin
    except ImportError as e:
        console.print(f"[red]无法加载HTTP调试插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = HTTPDebugPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run(
            url=url,
            method=method,
            timeout=timeout,
            export_path=export,
        )
        
        log_audit(
            user="cli",
            action="http_debug",
            target=url,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command()
def subnet(
    cidr: str = typer.Argument(..., help="CIDR格式的网络地址 (e.g., 192.168.1.0/24)"),
):
    """
    子网计算器 - 计算网络信息
    
    示例:
        netops subnet 192.168.1.0/24
        netops subnet 10.0.0.0/8
    """
    from netops_toolkit.utils.network_utils import get_network_info, is_valid_network
    
    if not is_valid_network(cidr):
        console.print(f"[red]无效的CIDR格式: {cidr}[/red]")
        raise typer.Exit(1)
    
    info = get_network_info(cidr)
    
    if info:
        panel = create_summary_panel(f"子网信息: {cidr}", {
            "网络地址": info["network"],
            "广播地址": info["broadcast"],
            "子网掩码": info["netmask"],
            "前缀长度": f"/{info['prefix_length']}",
            "总地址数": info["num_addresses"],
            "可用主机数": info["num_hosts"],
            "第一个主机": info["first_host"],
            "最后一个主机": info["last_host"],
        })
        console.print(panel)


@app.command(name="quality")
def network_quality(
    target: str = typer.Argument(..., help="目标IP或主机名"),
    count: int = typer.Option(50, "-c", "--count", help="测试次数"),
    interval: float = typer.Option(0.2, "-i", "--interval", help="测试间隔(秒)"),
    timeout: float = typer.Option(3.0, "-t", "--timeout", help="超时时间(秒)"),
):
    """
    网络质量测试 - 综合评估延迟、抖动、丢包率
    
    示例:
        netops quality 8.8.8.8
        netops quality www.baidu.com -c 100
        netops quality 192.168.1.1 -c 30 -i 0.5
    """
    try:
        from netops_toolkit.plugins.performance.network_quality import NetworkQualityPlugin
    except ImportError as e:
        console.print(f"[red]无法加载网络质量测试插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = NetworkQualityPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({
            "target": target,
            "count": count,
            "interval": interval,
            "timeout": timeout,
        })
        
        log_audit(
            user="cli",
            action="network_quality",
            target=target,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="speedtest")
def bandwidth_test(
    server_id: Optional[str] = typer.Option(None, "-s", "--server", help="测速服务器ID"),
    timeout: int = typer.Option(60, "-t", "--timeout", help="超时时间(秒)"),
    simple: bool = typer.Option(False, "--simple", help="简化输出"),
):
    """
    带宽测速 - 测试网络上下行带宽
    
    示例:
        netops speedtest
        netops speedtest --simple
        netops speedtest -s 12345
    """
    try:
        from netops_toolkit.plugins.performance.bandwidth_test import BandwidthTestPlugin
    except ImportError as e:
        console.print(f"[red]无法加载带宽测速插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = BandwidthTestPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({
            "server_id": server_id,
            "timeout": timeout,
            "simple": simple,
        })
        
        log_audit(
            user="cli",
            action="bandwidth_test",
            target="speedtest",
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="ip-convert")
def ip_convert(
    ip: str = typer.Argument(..., help="IP地址(支持多种格式)"),
):
    """
    IP格式转换 - 十进制/二进制/十六进制/整数
    
    示例:
        netops ip-convert 192.168.1.1
        netops ip-convert 3232235777
        netops ip-convert 0xC0A80101
    """
    try:
        from netops_toolkit.plugins.utils.ip_converter import IPConverterPlugin
    except ImportError as e:
        console.print(f"[red]无法加载IP转换插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = IPConverterPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({"ip": ip})
        
        log_audit(
            user="cli",
            action="ip_convert",
            target=ip,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="mac-lookup")
def mac_lookup(
    mac: str = typer.Argument(..., help="MAC地址"),
):
    """
    MAC地址查询 - 厂商识别和格式转换
    
    示例:
        netops mac-lookup 00:0C:29:12:34:56
        netops mac-lookup 00-0C-29-12-34-56
        netops mac-lookup 000C29123456
    """
    try:
        from netops_toolkit.plugins.utils.mac_lookup import MACLookupPlugin
    except ImportError as e:
        console.print(f"[red]无法加载MAC查询插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = MACLookupPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({"mac": mac})
        
        log_audit(
            user="cli",
            action="mac_lookup",
            target=mac,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="arp-scan")
def arp_scan(
    network: str = typer.Argument(..., help="网络地址(CIDR格式)"),
    timeout: int = typer.Option(1, "-t", "--timeout", help="超时时间(秒)"),
    workers: int = typer.Option(50, "-w", "--workers", help="并发数"),
):
    """
    ARP扫描 - 局域网主机发现
    
    示例:
        netops arp-scan 192.168.1.0/24
        netops arp-scan 10.0.0.0/24 -w 100
    """
    try:
        from netops_toolkit.plugins.scanning.arp_scan import ARPScanPlugin
    except ImportError as e:
        console.print(f"[red]无法加载ARP扫描插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = ARPScanPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({
            "network": network,
            "timeout": timeout,
            "max_workers": workers,
        })
        
        log_audit(
            user="cli",
            action="arp_scan",
            target=network,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="config-diff")
def config_diff(
    file1: str = typer.Argument(..., help="第一个配置文件"),
    file2: str = typer.Argument(..., help="第二个配置文件"),
    context: int = typer.Option(3, "-c", "--context", help="上下文行数"),
    ignore_whitespace: bool = typer.Option(False, "--ignore-ws", help="忽略空白"),
    ignore_comments: bool = typer.Option(False, "--ignore-comments", help="忽略注释"),
):
    """
    配置对比 - 对比两个配置文件的差异
    
    示例:
        netops config-diff config1.txt config2.txt
        netops config-diff old.cfg new.cfg --ignore-ws
    """
    try:
        from netops_toolkit.plugins.device_mgmt.config_diff import ConfigDiffPlugin
    except ImportError as e:
        console.print(f"[red]无法加载配置对比插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = ConfigDiffPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({
            "file1": file1,
            "file2": file2,
            "context_lines": context,
            "ignore_whitespace": ignore_whitespace,
            "ignore_comments": ignore_comments,
        })
        
        log_audit(
            user="cli",
            action="config_diff",
            target=f"{file1} <-> {file2}",
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


@app.command(name="tui")
def launch_tui():
    """
    启动现代TUI界面
    
    全屏终端用户界面，支持：
    - 鼠标/键盘双模式交互
    - 实时进度显示
    - 主题切换 (T键)
    - 命令面板 (Ctrl+P)
    
    示例:
        netops tui
    """
    try:
        from netops_toolkit.tui.app import run_tui
        run_tui()
    except ImportError as e:
        console.print(f"[red]无法加载TUI模块: {e}[/red]")
        console.print("[yellow]请确保已安装textual依赖: pip install textual[/yellow]")
        raise typer.Exit(1)


@app.command(name="whois")
def whois_query(
    target: str = typer.Argument(..., help="域名或IP地址"),
    timeout: int = typer.Option(30, "-t", "--timeout", help="查询超时(秒)"),
):
    """
    WHOIS查询 - 域名/IP注册信息查询
    
    示例:
        netops whois baidu.com
        netops whois 8.8.8.8
    """
    try:
        from netops_toolkit.plugins.utils.whois_lookup import WhoisLookupPlugin
    except ImportError as e:
        console.print(f"[red]无法加载WHOIS查询插件: {e}[/red]")
        raise typer.Exit(1)
    
    plugin = WhoisLookupPlugin()
    
    if not plugin.initialize():
        console.print("[red]插件初始化失败[/red]")
        raise typer.Exit(1)
    
    try:
        result = plugin.run({
            "target": target,
            "timeout": timeout,
        })
        
        log_audit(
            user="cli",
            action="whois",
            target=target,
            result=result.status.value,
        )
        
        if not result.is_success:
            raise typer.Exit(1)
            
    finally:
        plugin.cleanup()


if __name__ == "__main__":
    app()
