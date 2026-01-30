"""
带宽测速插件

使用speedtest进行网络带宽测试,测量上传和下载速度。
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
import json
import re

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, ParamSpec, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class BandwidthTestPlugin(Plugin):
    """带宽测速插件"""
    
    name = "bandwidth_test"
    description = "网络带宽测速"
    category = "performance"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证speedtest-cli是否可用"""
        try:
            result = subprocess.run(
                ["speedtest-cli", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True, None
            else:
                return False, "speedtest-cli未安装, 请运行: pip install speedtest-cli"
        except FileNotFoundError:
            return False, "speedtest-cli未安装, 请运行: pip install speedtest-cli"
        except Exception as e:
            return False, f"speedtest-cli检查失败: {e}"
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="server_id",
                param_type=str,
                description="测速服务器ID (可选)",
                required=False,
                default=None,
            ),
            ParamSpec(
                name="timeout",
                param_type=int,
                description="超时时间(秒)",
                required=False,
                default=60,
            ),
            ParamSpec(
                name="simple",
                param_type=bool,
                description="简化输出",
                required=False,
                default=False,
            ),
        ]
    
    def run(
        self,
        server_id: Optional[str] = None,
        timeout: int = 60,
        simple: bool = False,
        **kwargs,
    ) -> PluginResult:
        """
        执行带宽测速
        
        参数:
            server_id: 指定测速服务器ID (可选)
            timeout: 测试超时时间秒 (默认60)
            simple: 简化输出 (默认False)
        """
        
        logger.info("开始带宽测速测试")
        
        # 先检查依赖
        dep_ok, dep_msg = self.validate_dependencies()
        if not dep_ok:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=dep_msg or "speedtest-cli未安装, 请运行: pip install speedtest-cli",
                data={"install_hint": "pip install speedtest-cli"}
            )
        
        from netops_toolkit.ui.theme import console
        console.print("[cyan]正在选择最佳服务器...[/cyan]")
        
        # 执行测速
        start_time = datetime.now()
        results = self._perform_speedtest(
            server_id=server_id,
            timeout=timeout,
        )
        duration = (datetime.now() - start_time).total_seconds()
        
        if not results["success"]:
            return PluginResult(
                status=ResultStatus.FAILED,
                message=results.get("error", "测速失败"),
                data=results
            )
        
        # 显示结果
        self._display_results(results, simple)
        
        return PluginResult(
            status=ResultStatus.SUCCESS,
            message=f"测速完成 - 下载: {results['download_mbps']:.2f} Mbps, 上传: {results['upload_mbps']:.2f} Mbps",
            data={
                "results": results,
                "duration": duration,
                "timestamp": start_time.isoformat(),
            }
        )
    
    def _perform_speedtest(
        self,
        server_id: Optional[str],
        timeout: int,
    ) -> Dict[str, Any]:
        """执行speedtest测试"""
        try:
            # 构建命令
            cmd = ["speedtest-cli", "--json"]
            if server_id:
                cmd.extend(["--server", str(server_id)])
            
            # 执行测试
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"speedtest执行失败: {result.stderr}",
                }
            
            # 解析JSON结果
            data = json.loads(result.stdout)
            
            # 转换单位 (bytes/s -> Mbps)
            download_mbps = data["download"] / 1_000_000
            upload_mbps = data["upload"] / 1_000_000
            
            return {
                "success": True,
                "download_bps": data["download"],
                "upload_bps": data["upload"],
                "download_mbps": download_mbps,
                "upload_mbps": upload_mbps,
                "ping": data["ping"],
                "server": {
                    "host": data["server"]["host"],
                    "name": data["server"]["name"],
                    "country": data["server"]["country"],
                    "sponsor": data["server"]["sponsor"],
                    "id": data["server"]["id"],
                    "distance": data["server"]["d"],
                },
                "client": {
                    "ip": data["client"]["ip"],
                    "isp": data["client"]["isp"],
                    "country": data["client"]["country"],
                },
                "timestamp": data["timestamp"],
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "speedtest-cli未安装, 请运行: pip install speedtest-cli",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"测试超时 (>{timeout}秒)",
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"解析结果失败: {e}",
            }
        except KeyError as e:
            return {
                "success": False,
                "error": f"结果格式错误,缺少字段: {e}",
            }
        except OSError as e:
            # Windows 上可能抛出 OSError 而不是 FileNotFoundError
            if getattr(e, 'winerror', None) == 2 or e.errno == 2:  # ERROR_FILE_NOT_FOUND
                return {
                    "success": False,
                    "error": "speedtest-cli未安装, 请运行: pip install speedtest-cli",
                }
            logger.error(f"测速失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"测速失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _display_results(
        self,
        results: Dict[str, Any],
        simple: bool = False,
    ) -> None:
        """显示测速结果"""
        from netops_toolkit.ui.theme import console
        
        if simple:
            # 简化输出
            console.print(f"\n[green]下载: {results['download_mbps']:.2f} Mbps[/green]")
            console.print(f"[cyan]上传: {results['upload_mbps']:.2f} Mbps[/cyan]")
            console.print(f"[yellow]延迟: {results['ping']:.2f} ms[/yellow]\n")
        else:
            # 详细输出
            stats = {
                "下载速度": f"{results['download_mbps']:.2f} Mbps ({results['download_bps'] / 1_000_000:.2f} MB/s)",
                "上传速度": f"{results['upload_mbps']:.2f} Mbps ({results['upload_bps'] / 1_000_000:.2f} MB/s)",
                "延迟": f"{results['ping']:.2f} ms",
                "ISP": results['client']['isp'],
                "本机IP": results['client']['ip'],
                "测速服务器": results['server']['sponsor'],
                "服务器位置": f"{results['server']['name']}, {results['server']['country']}",
                "服务器距离": f"{results['server']['distance']:.2f} km",
            }
            
            panel = create_summary_panel("带宽测速结果", stats)
            console.print(panel)
            
            # 评估带宽质量
            self._display_quality_assessment(results)
    
    def _display_quality_assessment(self, results: Dict[str, Any]) -> None:
        """显示带宽质量评估"""
        from netops_toolkit.ui.theme import console
        
        download_mbps = results["download_mbps"]
        upload_mbps = results["upload_mbps"]
        
        console.print("\n[bold cyan]带宽质量评估:[/bold cyan]")
        
        # 下载速度评估
        if download_mbps >= 100:
            dl_grade = "优秀"
            dl_color = "green"
        elif download_mbps >= 50:
            dl_grade = "良好"
            dl_color = "cyan"
        elif download_mbps >= 20:
            dl_grade = "一般"
            dl_color = "yellow"
        elif download_mbps >= 10:
            dl_grade = "较慢"
            dl_color = "magenta"
        else:
            dl_grade = "很慢"
            dl_color = "red"
        
        console.print(f"  下载速度: [{dl_color}]{dl_grade}[/{dl_color}]")
        
        # 上传速度评估
        if upload_mbps >= 50:
            ul_grade = "优秀"
            ul_color = "green"
        elif upload_mbps >= 20:
            ul_grade = "良好"
            ul_color = "cyan"
        elif upload_mbps >= 10:
            ul_grade = "一般"
            ul_color = "yellow"
        elif upload_mbps >= 5:
            ul_grade = "较慢"
            ul_color = "magenta"
        else:
            ul_grade = "很慢"
            ul_color = "red"
        
        console.print(f"  上传速度: [{ul_color}]{ul_grade}[/{ul_color}]")
        
        # 使用场景建议
        console.print("\n[bold cyan]适用场景:[/bold cyan]")
        
        scenarios = []
        if download_mbps >= 25 and upload_mbps >= 3:
            scenarios.append("✓ 4K视频流")
        if download_mbps >= 5 and upload_mbps >= 1:
            scenarios.append("✓ 高清视频流")
        if download_mbps >= 3 and upload_mbps >= 0.5:
            scenarios.append("✓ 标清视频流")
        if download_mbps >= 25 and upload_mbps >= 10:
            scenarios.append("✓ 视频会议")
        if download_mbps >= 10 and upload_mbps >= 5:
            scenarios.append("✓ 在线游戏")
        if download_mbps >= 1:
            scenarios.append("✓ 网页浏览")
        
        if scenarios:
            for scenario in scenarios:
                console.print(f"  [green]{scenario}[/green]")
        else:
            console.print("  [red]网速较慢,基本使用可能受限[/red]")
        
        console.print()


def list_servers(timeout: int = 30) -> List[Dict[str, Any]]:
    """
    列出可用的测速服务器
    
    Args:
        timeout: 超时时间
        
    Returns:
        服务器列表
    """
    try:
        result = subprocess.run(
            ["speedtest-cli", "--list"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        if result.returncode != 0:
            logger.error(f"获取服务器列表失败: {result.stderr}")
            return []
        
        # 解析输出
        servers = []
        lines = result.stdout.strip().split("\n")
        
        for line in lines:
            # 格式: "12345) ServerName (Location) [Distance km]"
            match = re.match(r'^\s*(\d+)\)\s+(.+?)\s+\((.+?)\)\s+\[(.+?)\]', line)
            if match:
                servers.append({
                    "id": match.group(1),
                    "name": match.group(2).strip(),
                    "location": match.group(3).strip(),
                    "distance": match.group(4).strip(),
                })
        
        return servers
        
    except Exception as e:
        logger.error(f"获取服务器列表失败: {e}")
        return []


__all__ = ["BandwidthTestPlugin", "list_servers"]
