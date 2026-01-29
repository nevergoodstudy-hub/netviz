"""
密码生成器插件

生成安全的随机密码,支持多种配置选项。
"""

import secrets
import string
import math
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
from rich.table import Table
from rich.panel import Panel

logger = get_logger(__name__)


@register_plugin
class PasswordGeneratorPlugin(Plugin):
    """密码生成器插件"""
    
    name = "密码生成器"
    category = PluginCategory.UTILS
    description = "生成安全的随机密码"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="length",
                param_type=int,
                description="密码长度",
                required=False,
                default=16,
            ),
            ParamSpec(
                name="count",
                param_type=int,
                description="生成数量",
                required=False,
                default=5,
            ),
            ParamSpec(
                name="uppercase",
                param_type=bool,
                description="包含大写字母",
                required=False,
                default=True,
            ),
            ParamSpec(
                name="lowercase",
                param_type=bool,
                description="包含小写字母",
                required=False,
                default=True,
            ),
            ParamSpec(
                name="digits",
                param_type=bool,
                description="包含数字",
                required=False,
                default=True,
            ),
            ParamSpec(
                name="symbols",
                param_type=bool,
                description="包含特殊符号",
                required=False,
                default=True,
            ),
            ParamSpec(
                name="exclude",
                param_type=str,
                description="排除的字符",
                required=False,
                default="",
            ),
            ParamSpec(
                name="mode",
                param_type=str,
                description="模式: random(随机), memorable(易记), pin(纯数字)",
                required=False,
                default="random",
            ),
        ]
    
    def run(
        self,
        length: int = 16,
        count: int = 5,
        uppercase: bool = True,
        lowercase: bool = True,
        digits: bool = True,
        symbols: bool = True,
        exclude: str = "",
        mode: str = "random",
        **kwargs,
    ) -> PluginResult:
        """生成密码"""
        start_time = datetime.now()
        
        # 验证参数
        if length < 4:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="密码长度至少为4",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        if count < 1 or count > 100:
            return PluginResult(
                status=ResultStatus.ERROR,
                message="生成数量必须在1-100之间",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        console.print(f"[cyan]生成安全密码...[/cyan]")
        console.print(f"[cyan]模式: {mode}[/cyan]")
        console.print(f"[cyan]长度: {length}, 数量: {count}[/cyan]\n")
        
        # 生成密码
        passwords = []
        
        if mode == "pin":
            # 纯数字PIN码
            for _ in range(count):
                pin = ''.join(secrets.choice(string.digits) for _ in range(length))
                passwords.append(pin)
            charset_desc = "数字"
            charset_size = 10
            
        elif mode == "memorable":
            # 易记密码 (词+数字+词)
            words = self._get_word_list()
            for _ in range(count):
                pwd = self._generate_memorable(words, length)
                passwords.append(pwd)
            charset_desc = "易记单词组合"
            charset_size = 26  # 近似
            
        else:
            # 随机密码
            charset = ""
            charset_parts = []
            
            if uppercase:
                charset += string.ascii_uppercase
                charset_parts.append("大写")
            if lowercase:
                charset += string.ascii_lowercase
                charset_parts.append("小写")
            if digits:
                charset += string.digits
                charset_parts.append("数字")
            if symbols:
                charset += "!@#$%^&*()_+-=[]{}|;:,.<>?"
                charset_parts.append("符号")
            
            if not charset:
                return PluginResult(
                    status=ResultStatus.ERROR,
                    message="至少需要选择一种字符类型",
                    start_time=start_time,
                    end_time=datetime.now(),
                )
            
            # 排除字符
            if exclude:
                charset = ''.join(c for c in charset if c not in exclude)
            
            charset_desc = "+".join(charset_parts)
            charset_size = len(charset)
            
            for _ in range(count):
                pwd = ''.join(secrets.choice(charset) for _ in range(length))
                passwords.append(pwd)
        
        # 计算熵
        entropy = length * math.log2(charset_size) if charset_size > 0 else 0
        
        console.print("[green]✅ 密码生成成功![/green]\n")
        
        # 显示密码
        table = Table(title="生成的密码")
        table.add_column("#", style="dim", width=4)
        table.add_column("密码", style="green")
        table.add_column("强度", style="yellow")
        
        for i, pwd in enumerate(passwords, 1):
            strength = self._get_strength(pwd)
            strength_color = {
                "弱": "red",
                "中等": "yellow",
                "强": "green",
                "非常强": "cyan",
            }.get(strength, "white")
            
            table.add_row(
                str(i),
                pwd,
                f"[{strength_color}]{strength}[/{strength_color}]",
            )
        
        console.print(table)
        
        # 密码强度分析
        console.print(f"\n[yellow]密码分析:[/yellow]")
        console.print(f"  • 字符集: {charset_desc}")
        console.print(f"  • 字符集大小: {charset_size}")
        console.print(f"  • 熵: {entropy:.1f} bits")
        console.print(f"  • 可能组合: {charset_size ** length:.2e}")
        
        # 破解时间估算
        crack_time = self._estimate_crack_time(entropy)
        console.print(f"\n[yellow]暴力破解时间估算:[/yellow]")
        console.print(f"  • 在线攻击 (100/秒): {crack_time['online']}")
        console.print(f"  • 离线攻击 (10B/秒): {crack_time['offline']}")
        
        # 安全建议
        console.print(f"\n[yellow]安全建议:[/yellow]")
        if entropy < 40:
            console.print("  • [red]密码强度较弱,建议增加长度或字符类型[/red]")
        elif entropy < 60:
            console.print("  • [yellow]密码强度中等,适合一般用途[/yellow]")
        else:
            console.print("  • [green]密码强度足够,适合高安全需求[/green]")
        console.print("  • 不要在多个网站使用相同密码")
        console.print("  • 建议使用密码管理器存储")
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"生成了 {count} 个密码",
            data={
                "passwords": passwords,
                "length": length,
                "entropy": entropy,
                "charset_size": charset_size,
            },
            start_time=start_time,
            end_time=datetime.now(),
        )
    
    def _get_strength(self, password: str) -> str:
        """评估密码强度"""
        score = 0
        
        # 长度
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        
        # 字符类型
        if any(c.isupper() for c in password):
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        
        if score <= 3:
            return "弱"
        elif score <= 5:
            return "中等"
        elif score <= 6:
            return "强"
        else:
            return "非常强"
    
    def _estimate_crack_time(self, entropy: float) -> Dict[str, str]:
        """估算破解时间"""
        combinations = 2 ** entropy
        
        # 在线攻击: 100次/秒
        online_seconds = combinations / 100 / 2
        online_str = self._format_time(online_seconds)
        
        # 离线攻击: 10亿次/秒
        offline_seconds = combinations / 10_000_000_000 / 2
        offline_str = self._format_time(offline_seconds)
        
        return {
            "online": online_str,
            "offline": offline_str,
        }
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 1:
            return "瞬间"
        elif seconds < 60:
            return f"{seconds:.0f} 秒"
        elif seconds < 3600:
            return f"{seconds/60:.0f} 分钟"
        elif seconds < 86400:
            return f"{seconds/3600:.0f} 小时"
        elif seconds < 86400 * 365:
            return f"{seconds/86400:.0f} 天"
        elif seconds < 86400 * 365 * 1000:
            return f"{seconds/86400/365:.0f} 年"
        elif seconds < 86400 * 365 * 1000000:
            return f"{seconds/86400/365/1000:.0f} 千年"
        elif seconds < 86400 * 365 * 1000000000:
            return f"{seconds/86400/365/1000000:.0f} 百万年"
        else:
            return "宇宙寿命以上"
    
    def _get_word_list(self) -> List[str]:
        """获取常用词列表"""
        # 简单的英文单词列表
        return [
            "apple", "banana", "cherry", "dragon", "eagle",
            "forest", "garden", "harbor", "island", "jungle",
            "knight", "lemon", "mango", "noble", "ocean",
            "piano", "queen", "river", "storm", "tiger",
            "ultra", "valley", "winter", "yellow", "zebra",
            "alpha", "brave", "cloud", "delta", "ember",
            "flame", "ghost", "happy", "ivory", "joker",
            "karma", "laser", "magic", "neon", "orbit",
            "pixel", "quest", "radar", "solar", "turbo",
        ]
    
    def _generate_memorable(self, words: List[str], target_length: int) -> str:
        """生成易记密码"""
        result = []
        current_length = 0
        
        while current_length < target_length:
            word = secrets.choice(words)
            # 随机大小写
            if secrets.randbelow(2):
                word = word.capitalize()
            result.append(word)
            current_length += len(word)
            
            # 添加数字或符号
            if current_length < target_length:
                separator = secrets.choice(['', str(secrets.randbelow(100)), '-', '_'])
                result.append(separator)
                current_length += len(separator)
        
        password = ''.join(result)[:target_length]
        return password
