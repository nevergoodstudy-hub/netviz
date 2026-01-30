"""
配置备份插件

支持多厂商网络设备配置备份,包括版本管理和差异对比。
"""

from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
import difflib
import hashlib
import json
import os
import time

from netops_toolkit.plugins.base import Plugin, PluginResult, ResultStatus, ParamSpec, register_plugin
from netops_toolkit.core.logger import get_logger
from netops_toolkit.utils.ssh_utils import SSHConnection, check_netmiko_available
from netops_toolkit.config.device_inventory import DeviceInventory

logger = get_logger(__name__)


# 不同厂商获取配置的命令
VENDOR_CONFIG_COMMANDS = {
    "cisco_ios": "show running-config",
    "cisco_xe": "show running-config",
    "cisco_xr": "show running-config",
    "cisco_nxos": "show running-config",
    "huawei": "display current-configuration",
    "huawei_vrp": "display current-configuration",
    "juniper": "show configuration",
    "juniper_junos": "show configuration",
    "arista_eos": "show running-config",
    "hp_comware": "display current-configuration",
    "linux": "cat /etc/network/interfaces",
    "generic_termserver": "show running-config",
}


@register_plugin
class ConfigBackupPlugin(Plugin):
    """配置备份插件"""
    
    name = "config_backup"
    description = "设备配置备份"
    category = "device_mgmt"
    version = "1.0.0"
    
    def validate_dependencies(self) -> Tuple[bool, Optional[str]]:
        """验证依赖"""
        if not check_netmiko_available():
            return False, "Netmiko库未安装, 请运行: pip install netmiko"
        return True, None
    
    def get_required_params(self) -> List[ParamSpec]:
        """获取参数规格"""
        return [
            ParamSpec(
                name="targets",
                param_type=str,
                description="目标设备列表(逗号分隔)",
                required=False,
                default="",
            ),
            ParamSpec(
                name="group",
                param_type=str,
                description="设备组名称",
                required=False,
                default="",
            ),
            ParamSpec(
                name="username",
                param_type=str,
                description="SSH用户名",
                required=False,
                default="admin",
            ),
            ParamSpec(
                name="password",
                param_type=str,
                description="SSH密码",
                required=False,
                default="",
            ),
            ParamSpec(
                name="device_type",
                param_type=str,
                description="设备类型",
                required=False,
                default="cisco_ios",
            ),
            ParamSpec(
                name="backup_dir",
                param_type=str,
                description="备份目录",
                required=False,
                default="./backups",
            ),
        ]
    
    def run(
        self,
        targets: str = "",
        group: str = "",
        username: str = "admin",
        password: str = "",
        device_type: str = "cisco_ios",
        backup_dir: str = "./backups",
        max_workers: int = 5,
        timeout: int = 60,
        compare_with_last: bool = True,
        **kwargs,
    ) -> PluginResult:
        """
        执行配置备份
        
        参数:
            targets: 目标设备列表 (IP或主机名)
            group: 设备组名称
            username: SSH用户名
            password: SSH密码
            device_type: 设备类型 (默认cisco_ios)
            backup_dir: 备份目录 (默认./backups)
            max_workers: 最大并发数 (默认5)
            timeout: 连接超时 (默认60秒)
            compare_with_last: 是否与上次备份对比 (默认True)
        """
        # 处理targets参数
        target_list = [t.strip() for t in targets.split(",") if t.strip()] if targets else []
        
        # 如果指定了设备组,从设备清单获取设备
        device_info_map = {}
        if group and not target_list:
            inventory = DeviceInventory()
            devices_info = inventory.get_devices_by_group(group)
            if not devices_info:
                return PluginResult(
                    status=ResultStatus.FAILED,
                    message=f"设备组 '{group}' 不存在或为空",
                    data={}
                )
            for d in devices_info:
                if d.get("host"):
                    device_info_map[d["host"]] = d
            target_list = list(device_info_map.keys())
        
        if not target_list:
            return PluginResult(
                status=ResultStatus.FAILED,
                message="未指定目标设备",
                data={}
            )
        
        # 确保备份目录存在
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"开始备份 {len(target_list)} 台设备配置到 {backup_dir}")
        
        # 执行备份
        results = self._backup_devices(
            targets=target_list,
            device_info_map=device_info_map,
            username=username,
            password=password,
            device_type=device_type,
            backup_path=backup_path,
            max_workers=max_workers,
            timeout=timeout,
            compare_with_last=compare_with_last,
        )
        
        # 统计结果
        success_count = sum(1 for r in results.values() if r["success"])
        fail_count = len(results) - success_count
        changed_count = sum(1 for r in results.values() if r.get("changed"))
        
        return PluginResult(
            status=ResultStatus.SUCCESS if fail_count == 0 else ResultStatus.PARTIAL,
            message=f"备份完成: {success_count} 成功, {fail_count} 失败, {changed_count} 有变更",
            data={
                "results": results,
                "summary": {
                    "total": len(target_list),
                    "success": success_count,
                    "failed": fail_count,
                    "changed": changed_count,
                    "backup_dir": str(backup_path.absolute()),
                    "timestamp": datetime.now().isoformat(),
                }
            }
        )
    
    def _backup_devices(
        self,
        targets: List[str],
        device_info_map: Dict[str, Dict],
        username: str,
        password: str,
        device_type: str,
        backup_path: Path,
        max_workers: int,
        timeout: int,
        compare_with_last: bool,
    ) -> Dict[str, Dict[str, Any]]:
        """批量备份设备"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for target in targets:
                # 获取设备特定信息
                info = device_info_map.get(target, {})
                dev_username = info.get("username", username)
                dev_type = info.get("device_type", device_type)
                
                futures[executor.submit(
                    self._backup_single_device,
                    host=target,
                    username=dev_username,
                    password=password,
                    device_type=dev_type,
                    backup_path=backup_path,
                    timeout=timeout,
                    compare_with_last=compare_with_last,
                )] = target
            
            for future in as_completed(futures):
                target = futures[future]
                try:
                    result = future.result()
                    results[target] = result
                except Exception as e:
                    logger.error(f"备份异常 {target}: {e}")
                    results[target] = {
                        "success": False,
                        "error": str(e),
                    }
        
        return results
    
    def _backup_single_device(
        self,
        host: str,
        username: str,
        password: str,
        device_type: str,
        backup_path: Path,
        timeout: int,
        compare_with_last: bool,
    ) -> Dict[str, Any]:
        """备份单个设备"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
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
                        "duration": time.time() - start_time,
                    }
                
                # 获取配置命令
                config_cmd = VENDOR_CONFIG_COMMANDS.get(
                    device_type,
                    "show running-config"
                )
                
                # 执行配置获取
                config = conn.execute_command(config_cmd)
                
                if not config:
                    return {
                        "success": False,
                        "error": "获取配置失败",
                        "duration": time.time() - start_time,
                    }
                
                # 创建设备备份目录
                device_dir = backup_path / self._sanitize_hostname(host)
                device_dir.mkdir(parents=True, exist_ok=True)
                
                # 保存配置文件
                config_file = device_dir / f"config_{timestamp}.txt"
                config_file.write_text(config, encoding="utf-8")
                
                # 更新latest链接/文件
                latest_file = device_dir / "config_latest.txt"
                
                # 检查是否有变更
                changed = False
                diff_summary = None
                
                if compare_with_last and latest_file.exists():
                    last_config = latest_file.read_text(encoding="utf-8")
                    if last_config != config:
                        changed = True
                        diff_summary = self._generate_diff_summary(
                            last_config, config, host
                        )
                else:
                    changed = True  # 首次备份视为变更
                
                # 更新latest文件
                latest_file.write_text(config, encoding="utf-8")
                
                # 保存元数据
                self._save_metadata(
                    device_dir=device_dir,
                    host=host,
                    device_type=device_type,
                    timestamp=timestamp,
                    config_hash=hashlib.md5(config.encode()).hexdigest(),
                    changed=changed,
                )
                
                return {
                    "success": True,
                    "error": None,
                    "file": str(config_file),
                    "changed": changed,
                    "diff_summary": diff_summary,
                    "config_size": len(config),
                    "duration": time.time() - start_time,
                }
                
        except Exception as e:
            logger.error(f"备份失败 {host}: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
            }
    
    def _sanitize_hostname(self, hostname: str) -> str:
        """清理主机名用于文件名"""
        return hostname.replace(".", "_").replace(":", "_")
    
    def _generate_diff_summary(
        self,
        old_config: str,
        new_config: str,
        hostname: str,
    ) -> Dict[str, Any]:
        """生成配置差异摘要"""
        old_lines = old_config.splitlines()
        new_lines = new_config.splitlines()
        
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"{hostname}_old",
            tofile=f"{hostname}_new",
            lineterm="",
        ))
        
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        
        return {
            "added_lines": added,
            "removed_lines": removed,
            "diff_preview": "\n".join(diff[:50]),  # 前50行差异
        }
    
    def _save_metadata(
        self,
        device_dir: Path,
        host: str,
        device_type: str,
        timestamp: str,
        config_hash: str,
        changed: bool,
    ) -> None:
        """保存备份元数据"""
        metadata_file = device_dir / "metadata.json"
        
        # 读取现有元数据
        metadata = {"host": host, "device_type": device_type, "backups": []}
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        # 添加新记录
        metadata["backups"].append({
            "timestamp": timestamp,
            "hash": config_hash,
            "changed": changed,
        })
        
        # 只保留最近100条记录
        metadata["backups"] = metadata["backups"][-100:]
        metadata["last_backup"] = timestamp
        
        # 保存
        metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


def compare_configs(
    config1_path: str,
    config2_path: str,
) -> Dict[str, Any]:
    """
    对比两个配置文件
    
    Args:
        config1_path: 第一个配置文件路径
        config2_path: 第二个配置文件路径
        
    Returns:
        差异信息
    """
    try:
        config1 = Path(config1_path).read_text(encoding="utf-8")
        config2 = Path(config2_path).read_text(encoding="utf-8")
        
        diff = list(difflib.unified_diff(
            config1.splitlines(),
            config2.splitlines(),
            fromfile=config1_path,
            tofile=config2_path,
            lineterm="",
        ))
        
        return {
            "identical": len(diff) == 0,
            "diff": "\n".join(diff),
            "added": sum(1 for l in diff if l.startswith("+") and not l.startswith("+++")),
            "removed": sum(1 for l in diff if l.startswith("-") and not l.startswith("---")),
        }
    except Exception as e:
        return {
            "error": str(e),
            "identical": False,
        }


def list_backups(backup_dir: str, host: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出备份记录
    
    Args:
        backup_dir: 备份目录
        host: 可选的主机过滤
        
    Returns:
        备份记录列表
    """
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return []
    
    backups = []
    
    for device_dir in backup_path.iterdir():
        if not device_dir.is_dir():
            continue
        
        # 过滤主机
        if host and host.replace(".", "_") != device_dir.name:
            continue
        
        metadata_file = device_dir / "metadata.json"
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                backups.append({
                    "host": metadata.get("host", device_dir.name),
                    "device_type": metadata.get("device_type"),
                    "last_backup": metadata.get("last_backup"),
                    "backup_count": len(metadata.get("backups", [])),
                    "path": str(device_dir),
                })
            except Exception:
                pass
    
    return backups


__all__ = ["ConfigBackupPlugin", "compare_configs", "list_backups"]
