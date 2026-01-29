"""
NetOps Toolkit 交互式菜单系统

支持数字选择菜单项,字母/快捷键执行功能操作。
"""

import os
import sys
from typing import List, Dict, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich import box

from netops_toolkit.ui.theme import console, NetOpsTheme


@dataclass
class MenuItem:
    """菜单项"""
    key: str  # 选择键 (数字或字母)
    label: str  # 显示标签
    description: str = ""  # 描述
    action: Optional[Callable] = None  # 执行动作
    submenu: Optional['Menu'] = None  # 子菜单
    icon: str = ""  # 图标
    enabled: bool = True  # 是否启用
    shortcut: str = ""  # 快捷键提示


@dataclass  
class Menu:
    """菜单"""
    title: str
    items: List[MenuItem] = field(default_factory=list)
    parent: Optional['Menu'] = None
    footer: str = ""
    show_back: bool = True
    show_exit: bool = False
    
    def add_item(self, item: MenuItem) -> 'Menu':
        """添加菜单项"""
        self.items.append(item)
        return self
    
    def get_item(self, key: str) -> Optional[MenuItem]:
        """根据键获取菜单项"""
        for item in self.items:
            if item.key and item.key.lower() == key.lower():
                return item
        return None


class MenuSystem:
    """交互式菜单系统"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.current_menu: Optional[Menu] = None
        self.menu_stack: List[Menu] = []
        self.running = True
        self.status_message = ""
        self.status_type = "info"  # info, success, error, warning
        
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def show_header(self, title: str = "NetOps Toolkit"):
        """显示标题栏"""
        header = Panel(
            Text(title, justify="center", style="bold cyan"),
            box=box.DOUBLE,
            style="cyan",
            padding=(0, 2),
        )
        self.console.print(header)
        
    def show_breadcrumb(self):
        """显示导航路径"""
        if not self.menu_stack:
            return
            
        path_parts = [m.title for m in self.menu_stack]
        if self.current_menu:
            path_parts.append(self.current_menu.title)
            
        path = " > ".join(path_parts)
        self.console.print(f"[dim]📍 {path}[/dim]\n")
        
    def show_menu(self, menu: Menu):
        """显示菜单"""
        # 创建菜单表格
        table = Table(
            show_header=False,
            box=box.ROUNDED,
            border_style="cyan",
            padding=(0, 2),
            expand=True,
        )
        
        table.add_column("键", style="bold yellow", width=6, justify="center")
        table.add_column("功能", style="bold white", width=25)
        table.add_column("描述", style="dim")
        table.add_column("快捷键", style="cyan", width=10, justify="right")
        
        for item in menu.items:
            if not item.enabled:
                style = "dim strikethrough"
                key_display = f"[dim]{item.key}[/dim]"
            else:
                style = ""
                key_display = f"[bold yellow]{item.key}[/bold yellow]"
            
            icon_label = f"{item.icon} {item.label}" if item.icon else item.label
            
            table.add_row(
                key_display,
                icon_label,
                item.description,
                f"[cyan]{item.shortcut}[/cyan]" if item.shortcut else "",
            )
        
        # 添加分隔符和返回/退出选项
        if menu.show_back and menu.parent:
            table.add_row("", "", "", "")
            table.add_row(
                "[bold magenta]0[/bold magenta]",
                "⬅️  返回上级",
                "返回上一级菜单",
                "[magenta]Esc[/magenta]",
            )
            
        if menu.show_exit or not menu.parent:
            table.add_row("", "", "", "")
            table.add_row(
                "[bold red]Q[/bold red]",
                "🚪 退出程序",
                "退出 NetOps Toolkit",
                "[red]Ctrl+C[/red]",
            )
        
        # 显示菜单面板
        menu_panel = Panel(
            table,
            title=f"[bold cyan]{menu.title}[/bold cyan]",
            border_style="cyan",
            padding=(1, 1),
        )
        self.console.print(menu_panel)
        
        # 显示底部提示
        if menu.footer:
            self.console.print(f"\n[dim]{menu.footer}[/dim]")
            
    def show_status(self):
        """显示状态消息"""
        if not self.status_message:
            return
            
        style_map = {
            "info": "blue",
            "success": "green", 
            "error": "red",
            "warning": "yellow",
        }
        
        icon_map = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
        }
        
        style = style_map.get(self.status_type, "white")
        icon = icon_map.get(self.status_type, "•")
        
        self.console.print(f"\n[{style}]{icon} {self.status_message}[/{style}]")
        
    def set_status(self, message: str, msg_type: str = "info"):
        """设置状态消息"""
        self.status_message = message
        self.status_type = msg_type
        
    def clear_status(self):
        """清除状态消息"""
        self.status_message = ""
        
    def get_input(self, prompt: str = "请选择") -> str:
        """获取用户输入"""
        self.console.print()
        try:
            # 使用Python原生输入避免Rich的编码问题
            import sys
            sys.stdout.write(f"{prompt} > ")
            sys.stdout.flush()
            user_input = sys.stdin.readline()
            # 清理输入: 去除空白和不可见字符
            cleaned = user_input.strip()
            # 过滤非 ASCII 控制字符
            cleaned = ''.join(c for c in cleaned if c.isprintable() or c.isspace())
            return cleaned.strip()
        except (KeyboardInterrupt, EOFError):
            return "q"
            
    def navigate_to(self, menu: Menu):
        """导航到指定菜单"""
        if self.current_menu:
            self.menu_stack.append(self.current_menu)
        self.current_menu = menu
        self.clear_status()
        
    def navigate_back(self) -> bool:
        """返回上级菜单"""
        if self.menu_stack:
            self.current_menu = self.menu_stack.pop()
            self.clear_status()
            return True
        return False
        
    def render(self):
        """渲染当前界面"""
        self.clear_screen()
        self.show_header()
        self.console.print()
        
        if self.menu_stack:
            self.show_breadcrumb()
            
        if self.current_menu:
            self.show_menu(self.current_menu)
            
        self.show_status()
        
    def handle_input(self, user_input: str) -> bool:
        """
        处理用户输入
        
        Returns:
            True 继续运行, False 退出
        """
        if not user_input:
            return True
            
        key = user_input.lower()
        
        # 退出
        if key in ('q', 'quit', 'exit'):
            return False
            
        # 返回上级
        if key in ('0', 'b', 'back', '\x1b'):  # \x1b 是 Esc
            if self.navigate_back():
                return True
            else:
                # 已在顶级菜单,询问是否退出
                self.set_status("已在主菜单,按 Q 退出程序", "warning")
                return True
                
        # 查找菜单项
        if self.current_menu:
            item = self.current_menu.get_item(key)
            
            if item:
                if not item.enabled:
                    self.set_status(f"功能 [{item.label}] 当前不可用", "warning")
                    return True
                    
                # 有子菜单则导航
                if item.submenu:
                    item.submenu.parent = self.current_menu
                    self.navigate_to(item.submenu)
                    return True
                    
                # 有动作则执行
                if item.action:
                    try:
                        self.clear_screen()
                        self.show_header()
                        self.console.print()
                        self.console.print(f"[bold cyan]>>> {item.label}[/bold cyan]")
                        self.console.print(f"[dim]{item.description}[/dim]\n")
                        
                        result = item.action()
                        
                        if result is True:
                            self.set_status(f"{item.label} 执行成功", "success")
                        elif result is False:
                            self.set_status(f"{item.label} 执行失败", "error")
                        # result 为 None 时不设置状态
                            
                        # 等待用户确认
                        self.console.print()
                        self.console.input("[dim]按 Enter 键继续...[/dim]")
                        
                    except KeyboardInterrupt:
                        self.set_status("操作已取消", "warning")
                    except Exception as e:
                        self.set_status(f"执行出错: {e}", "error")
                        self.console.print()
                        self.console.input("[dim]按 Enter 键继续...[/dim]")
                        
                    return True
            else:
                self.set_status(f"无效选项: {user_input}", "error")
                
        return True
        
    def run(self, start_menu: Menu):
        """运行菜单系统"""
        self.current_menu = start_menu
        self.running = True
        
        while self.running:
            try:
                self.render()
                user_input = self.get_input()
                self.running = self.handle_input(user_input)
            except KeyboardInterrupt:
                self.console.print("\n")
                self.running = False
                
        # 退出消息
        self.clear_screen()
        self.show_header()
        self.console.print()
        self.console.print("[cyan]感谢使用 NetOps Toolkit,再见![/cyan]\n")


class ParameterCollector:
    """参数收集器 - 用于交互式收集插件参数"""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        
    def collect_text(self, prompt: str, default: str = "", required: bool = True) -> Optional[str]:
        """收集文本参数"""
        default_hint = f" [dim](默认: {default})[/dim]" if default else ""
        required_hint = " [red]*[/red]" if required else ""
        
        full_prompt = f"{prompt}{required_hint}{default_hint}: "
        
        try:
            value = self.console.input(full_prompt).strip()
            if not value:
                value = default
            if required and not value:
                self.console.print("[red]此参数为必填项[/red]")
                return self.collect_text(prompt, default, required)
            return value
        except (KeyboardInterrupt, EOFError):
            return None
            
    def collect_number(self, prompt: str, default: int = 0, min_val: int = None, max_val: int = None) -> Optional[int]:
        """收集数字参数"""
        default_hint = f" [dim](默认: {default})[/dim]"
        range_hint = ""
        if min_val is not None and max_val is not None:
            range_hint = f" [dim](范围: {min_val}-{max_val})[/dim]"
            
        full_prompt = f"{prompt}{default_hint}{range_hint}: "
        
        try:
            value = self.console.input(full_prompt).strip()
            if not value:
                return default
            try:
                num = int(value)
                if min_val is not None and num < min_val:
                    self.console.print(f"[red]值不能小于 {min_val}[/red]")
                    return self.collect_number(prompt, default, min_val, max_val)
                if max_val is not None and num > max_val:
                    self.console.print(f"[red]值不能大于 {max_val}[/red]")
                    return self.collect_number(prompt, default, min_val, max_val)
                return num
            except ValueError:
                self.console.print("[red]请输入有效的数字[/red]")
                return self.collect_number(prompt, default, min_val, max_val)
        except (KeyboardInterrupt, EOFError):
            return None
            
    def collect_float(self, prompt: str, default: float = 0.0) -> Optional[float]:
        """收集浮点数参数"""
        default_hint = f" [dim](默认: {default})[/dim]"
        full_prompt = f"{prompt}{default_hint}: "
        
        try:
            value = self.console.input(full_prompt).strip()
            if not value:
                return default
            try:
                return float(value)
            except ValueError:
                self.console.print("[red]请输入有效的数字[/red]")
                return self.collect_float(prompt, default)
        except (KeyboardInterrupt, EOFError):
            return None
            
    def collect_bool(self, prompt: str, default: bool = True) -> Optional[bool]:
        """收集布尔参数"""
        default_hint = "Y/n" if default else "y/N"
        full_prompt = f"{prompt} [{default_hint}]: "
        
        try:
            value = self.console.input(full_prompt).strip().lower()
            if not value:
                return default
            if value in ('y', 'yes', '是', '1', 'true'):
                return True
            if value in ('n', 'no', '否', '0', 'false'):
                return False
            self.console.print("[red]请输入 Y 或 N[/red]")
            return self.collect_bool(prompt, default)
        except (KeyboardInterrupt, EOFError):
            return None
            
    def collect_choice(self, prompt: str, choices: List[str], default: str = None) -> Optional[str]:
        """收集选择参数"""
        self.console.print(f"\n{prompt}:")
        for i, choice in enumerate(choices, 1):
            marker = " [cyan](默认)[/cyan]" if choice == default else ""
            self.console.print(f"  [yellow]{i}[/yellow]. {choice}{marker}")
            
        try:
            value = self.console.input("\n请选择 [数字]: ").strip()
            if not value and default:
                return default
            try:
                idx = int(value) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
                self.console.print(f"[red]请输入 1-{len(choices)} 之间的数字[/red]")
                return self.collect_choice(prompt, choices, default)
            except ValueError:
                # 直接输入了选项值
                if value in choices:
                    return value
                self.console.print("[red]无效选择[/red]")
                return self.collect_choice(prompt, choices, default)
        except (KeyboardInterrupt, EOFError):
            return None


def create_separator_item() -> MenuItem:
    """创建分隔符菜单项"""
    return MenuItem(
        key="",
        label="─" * 30,
        enabled=False,
    )
