"""
参数预设管理模块

提供插件参数预设的保存、加载和管理功能。
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from netops_toolkit.core.logger import get_logger

logger = get_logger(__name__)

# 默认预设目录
DEFAULT_PRESETS_DIR = Path.home() / ".netops-toolkit" / "presets"


def get_presets_dir() -> Path:
    """获取预设目录"""
    presets_dir = DEFAULT_PRESETS_DIR
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir


def get_preset_file(plugin_name: str) -> Path:
    """
    获取指定插件的预设文件路径
    
    Args:
        plugin_name: 插件名称
        
    Returns:
        预设文件路径
    """
    # 规范化插件名称作为文件名
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in plugin_name)
    return get_presets_dir() / f"{safe_name}.yaml"


def load_presets(plugin_name: str) -> Dict[str, Dict[str, Any]]:
    """
    加载指定插件的所有预设
    
    Args:
        plugin_name: 插件名称
        
    Returns:
        预设字典 {预设名称: {参数名: 参数值, ...}, ...}
    """
    preset_file = get_preset_file(plugin_name)
    
    if not preset_file.exists():
        return {}
    
    try:
        with open(preset_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("presets", {}) if data else {}
    except Exception as e:
        logger.error(f"加载预设失败: {e}")
        return {}


def save_preset(
    plugin_name: str,
    preset_name: str,
    params: Dict[str, Any],
    description: str = ""
) -> bool:
    """
    保存预设
    
    Args:
        plugin_name: 插件名称
        preset_name: 预设名称
        params: 参数字典
        description: 预设描述
        
    Returns:
        是否保存成功
    """
    # 验证预设名称
    if not preset_name or not preset_name.strip():
        logger.error("预设名称不能为空")
        return False
    
    preset_name = preset_name.strip()
    
    # 验证预设名称安全性
    if not _validate_preset_name(preset_name):
        logger.error(f"无效的预设名称: {preset_name}")
        return False
    
    preset_file = get_preset_file(plugin_name)
    
    try:
        # 加载现有预设
        existing_presets = load_presets(plugin_name)
        
        # 添加/更新预设
        existing_presets[preset_name] = {
            "params": params,
            "description": description,
            "created_at": datetime.now().isoformat(),
        }
        
        # 保存到文件
        data = {
            "plugin_name": plugin_name,
            "presets": existing_presets,
        }
        
        with open(preset_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"预设已保存: {plugin_name}/{preset_name}")
        return True
        
    except Exception as e:
        logger.error(f"保存预设失败: {e}")
        return False


def delete_preset(plugin_name: str, preset_name: str) -> bool:
    """
    删除预设
    
    Args:
        plugin_name: 插件名称
        preset_name: 预设名称
        
    Returns:
        是否删除成功
    """
    preset_file = get_preset_file(plugin_name)
    
    if not preset_file.exists():
        return False
    
    try:
        existing_presets = load_presets(plugin_name)
        
        if preset_name not in existing_presets:
            return False
        
        del existing_presets[preset_name]
        
        # 保存更新后的预设
        data = {
            "plugin_name": plugin_name,
            "presets": existing_presets,
        }
        
        with open(preset_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"预设已删除: {plugin_name}/{preset_name}")
        return True
        
    except Exception as e:
        logger.error(f"删除预设失败: {e}")
        return False


def get_preset(plugin_name: str, preset_name: str) -> Optional[Dict[str, Any]]:
    """
    获取指定预设的参数
    
    Args:
        plugin_name: 插件名称
        preset_name: 预设名称
        
    Returns:
        预设参数字典，如果不存在返回 None
    """
    presets = load_presets(plugin_name)
    preset_data = presets.get(preset_name)
    
    if preset_data:
        return preset_data.get("params", {})
    return None


def list_preset_names(plugin_name: str) -> List[str]:
    """
    列出指定插件的所有预设名称
    
    Args:
        plugin_name: 插件名称
        
    Returns:
        预设名称列表
    """
    return list(load_presets(plugin_name).keys())


def _validate_preset_name(name: str) -> bool:
    """
    验证预设名称安全性
    
    Args:
        name: 预设名称
        
    Returns:
        是否安全
    """
    if not name or len(name) > 100:
        return False
    
    # 只允许字母、数字、中文、空格、连字符、下划线
    import re
    if not re.match(r'^[\w\u4e00-\u9fff\s\-]+$', name):
        return False
    
    # 不能以点开头（防止隐藏文件）
    if name.startswith('.'):
        return False
    
    return True


def export_presets(plugin_name: str, output_path: Path) -> bool:
    """
    导出预设到文件
    
    Args:
        plugin_name: 插件名称
        output_path: 输出路径
        
    Returns:
        是否成功
    """
    presets = load_presets(plugin_name)
    
    if not presets:
        logger.warning(f"没有可导出的预设: {plugin_name}")
        return False
    
    try:
        data = {
            "plugin_name": plugin_name,
            "exported_at": datetime.now().isoformat(),
            "presets": presets,
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"预设已导出到: {output_path}")
        return True
    except Exception as e:
        logger.error(f"导出预设失败: {e}")
        return False


def import_presets(plugin_name: str, input_path: Path, overwrite: bool = False) -> int:
    """
    从文件导入预设
    
    Args:
        plugin_name: 插件名称
        input_path: 输入路径
        overwrite: 是否覆盖已存在的预设
        
    Returns:
        导入的预设数量
    """
    if not input_path.exists():
        logger.error(f"导入文件不存在: {input_path}")
        return 0
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data or "presets" not in data:
            logger.error("无效的预设文件格式")
            return 0
        
        import_presets_data = data["presets"]
        existing_presets = load_presets(plugin_name)
        
        imported_count = 0
        for name, preset_data in import_presets_data.items():
            if name in existing_presets and not overwrite:
                logger.info(f"跳过已存在的预设: {name}")
                continue
            
            params = preset_data.get("params", {})
            description = preset_data.get("description", "")
            
            if save_preset(plugin_name, name, params, description):
                imported_count += 1
        
        logger.info(f"成功导入 {imported_count} 个预设")
        return imported_count
        
    except Exception as e:
        logger.error(f"导入预设失败: {e}")
        return 0


__all__ = [
    "load_presets",
    "save_preset",
    "delete_preset",
    "get_preset",
    "list_preset_names",
    "get_presets_dir",
    "export_presets",
    "import_presets",
]
