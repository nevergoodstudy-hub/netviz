"""
SSH批量执行插件

支持对多台网络设备并发执行SSH命令。
"""

from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.utils.ssh_utils import SSHConnection, check_netmiko_available
from netops_toolkit.config.device_inventory import DeviceInventory

logger = get_logger(__name__)


@register_plugin
class SSHBatchPlugin(Plugin):
    """SSH批量执行插件"""
    
    name = "ssh_batch"
    description = "SSH批量命令执行"
    category = "device_mgmt"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        if not check_netmiko_available():
            return False, "Netmiko库未安装, 请运行: pip install netmiko"
        return True, None
    
    def get_required_params(self) -> List[str]:
        """获取必需参数"""
        return ["commands"]
    
    def run(self, params: Dict[str, Any]) -> PluginResult:
        """
        执行SSH批量命令
        
        参数:
            commands: 命令列表 (str或List[str])
            targets: 目标设备列表 (IP或主机名)
            group: 设备组名称
            username: SSH用户名
            password: SSH密码
            device_type: 设备类型 (默认cisco_ios)
            max_workers: 最大并发数 (默认5)
            timeout: 连接超时 (默认30秒)
            config_mode: 是否使用配置模式执行 (默认False)
        """
        # 获取参数
        commands = params.get("commands", [])
        if isinstance(commands, str):
            commands = [commands]
        
        targets = params.get("targets", [])
        group = params.get("group")
        username = params.get("username", "admin")
        password = params.get("password", "")
        device_type = params.get("device_type", "cisco_ios")
        max_workers = params.get("max_workers", 5)
        timeout = params.get("timeout", 30)
        config_mode = params.get("config_mode", False)
        
        # 如果指定了设备组,从设备清单获取设备
        if group and not targets:
            inventory = DeviceInventory()
            devices_info = inventory.get_devices_by_group(group)
            if not devices_info:
                return PluginResult(
                    status=ResultStatus.FAILED,
                    message=f"设备组 '{group}' 不存在或为空",
                    data={}
                )
            targets = [d.get("host") for d in devices_info if d.get("host")]
            # 尝试从设备清单获取凭据
            if devices_info and not password:
                first_device = devices_info[0]
                username = first_device.get("username", username)
                device_type = first_device.get("device_type", device_type)
        
        if not targets:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定目标设备",
                data={}
            )
        
        if not commands:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定命令",
                data={}
            )
        
        logger.info(f"开始对 {len(targets)} 台设备执行 {len(commands)} 条命令")
        
        # 执行批量操作
        results = self._execute_batch(
            targets=targets,
            commands=commands,
            username=username,
            password=password,
            device_type=device_type,
            max_workers=max_workers,
            timeout=timeout,
            config_mode=config_mode,
        )
        
        # 统计结果
        success_count = sum(1 for r in results.values() if r["success"])
        fail_count = len(results) - success_count
        
        return PluginResult(
            status=ResultStatus.SUCCESS if fail_count == 0 else ResultStatus.PARTIAL,
            message=f"执行完成: {success_count} 成功, {fail_count} 失败",
            data={
                "results": results,
                "summary": {
                    "total": len(targets),
                    "success": success_count,
                    "failed": fail_count,
                    "commands": commands,
                    "timestamp": datetime.now().isoformat(),
                }
            }
        )
    
    def _execute_batch(
        self,
        targets: List[str],
        commands: List[str],
        username: str,
        password: str,
        device_type: str,
        max_workers: int,
        timeout: int,
        config_mode: bool,
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量执行命令
        
        Returns:
            {设备: 执行结果} 字典
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._execute_on_device,
                    host=target,
                    commands=commands,
                    username=username,
                    password=password,
                    device_type=device_type,
                    timeout=timeout,
                    config_mode=config_mode,
                ): target
                for target in targets
            }
            
            for future in as_completed(futures):
                target = futures[future]
                try:
                    result = future.result()
                    results[target] = result
                except Exception as e:
                    logger.error(f"执行异常 {target}: {e}")
                    results[target] = {
                        "success": False,
                        "error": str(e),
                        "outputs": {},
                    }
        
        return results
    
    def _execute_on_device(
        self,
        host: str,
        commands: List[str],
        username: str,
        password: str,
        device_type: str,
        timeout: int,
        config_mode: bool,
    ) -> Dict[str, Any]:
        """
        在单个设备上执行命令
        
        Returns:
            执行结果字典
        """
        start_time = time.time()
        
        try:
            with SSHConnection(
                host=host,
                username=username,
                password=password,
                device_type=device_type,
                timeout=timeout,
            ) as conn:
                if not conn.is_connected():
                    return {
                        "success": False,
                        "error": "连接失败",
                        "outputs": {},
                        "duration": time.time() - start_time,
                    }
                
                if config_mode:
                    # 配置模式执行
                    output = conn.execute_config_commands(commands)
                    outputs = {"config_output": output or ""}
                else:
                    # 普通模式执行
                    outputs = conn.execute_commands(commands)
                
                return {
                    "success": True,
                    "error": None,
                    "outputs": outputs,
                    "duration": time.time() - start_time,
                }
                
        except Exception as e:
            logger.error(f"设备执行失败 {host}: {e}")
            return {
                "success": False,
                "error": str(e),
                "outputs": {},
                "duration": time.time() - start_time,
            }


def execute_batch_commands(
    targets: List[str],
    commands: List[str],
    username: str,
    password: str,
    device_type: str = "cisco_ios",
    max_workers: int = 5,
    timeout: int = 30,
    config_mode: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    便捷函数: 批量执行SSH命令
    
    Args:
        targets: 目标设备列表
        commands: 命令列表
        username: 用户名
        password: 密码
        device_type: 设备类型
        max_workers: 最大并发数
        timeout: 超时时间
        config_mode: 配置模式
        
    Returns:
        执行结果
    """
    plugin = SSHBatchPlugin()
    result = plugin.run({
        "targets": targets,
        "commands": commands,
        "username": username,
        "password": password,
        "device_type": device_type,
        "max_workers": max_workers,
        "timeout": timeout,
        "config_mode": config_mode,
    })
    return result.data.get("results", {})


__all__ = ["SSHBatchPlugin", "execute_batch_commands"]
