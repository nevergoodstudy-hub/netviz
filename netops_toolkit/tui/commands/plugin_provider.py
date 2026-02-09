"""
NetOps Toolkit TUI - 命令面板插件Provider

实现Textual命令面板的插件搜索功能：
- 支持模糊搜索插件名称
- 按分类组织搜索结果
- 点击直接打开插件执行界面
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from textual.command import Provider, Hit, Hits, DiscoveryHit

if TYPE_CHECKING:
    from ..app import NetOpsApp


class PluginProvider(Provider):
    """插件命令面板Provider
    
    在命令面板中提供插件搜索功能:
    - 支持模糊匹配插件名称和描述
    - 显示插件分类图标
    - 直接跳转到插件执行界面
    """
    
    @property
    def _app(self) -> "NetOpsApp":
        """获取类型化的App实例"""
        return self.app  # type: ignore
    
    async def discover(self) -> Hits:
        """返回初始发现结果（用户未输入时显示）
        
        显示最常用或最近使用的插件
        """
        plugins = self._get_all_plugins()
        
        # 显示前10个插件作为发现结果
        for plugin_id, info in list(plugins.items())[:10]:
            icon = info.get("icon", "🔧")
            name = info.get("display_name", plugin_id)
            category = info.get("category", "other")
            description = info.get("description", "")
            
            yield DiscoveryHit(
                display=f"{icon} {name}",
                command=self._create_plugin_command(plugin_id, info),
                help=f"[{self._get_category_name(category)}] {description}"
            )
    
    async def search(self, query: str) -> Hits:
        """搜索插件
        
        Args:
            query: 用户输入的搜索词
            
        Yields:
            Hit: 匹配的插件搜索结果
        """
        # 获取matcher用于模糊匹配
        matcher = self.matcher(query)
        
        plugins = self._get_all_plugins()
        
        for plugin_id, info in plugins.items():
            icon = info.get("icon", "🔧")
            name = info.get("display_name", plugin_id)
            category = info.get("category", "other")
            description = info.get("description", "")
            
            # 构建搜索字符串（包含名称、分类、描述）
            search_text = f"{name} {plugin_id} {self._get_category_name(category)} {description}"
            
            # 执行模糊匹配
            match = matcher.match(search_text)
            if match > 0:
                yield Hit(
                    score=match,
                    match_display=f"{icon} {matcher.highlight(name)}",
                    command=self._create_plugin_command(plugin_id, info),
                    help=f"[{self._get_category_name(category)}] {description}"
                )
    
    def _get_all_plugins(self) -> dict:
        """获取所有已注册的插件
        
        Returns:
            插件字典 {plugin_id: plugin_info}
        """
        try:
            from ..adapters.plugin_adapter import PluginUIAdapter
            
            adapter = PluginUIAdapter()
            plugins = adapter.get_all_plugins()
            
            # 转换为原有格式
            result = {}
            for plugin_id, info in plugins.items():
                result[plugin_id] = {
                    "display_name": info.display_name,
                    "icon": info.icon,
                    "category": info.category,
                    "description": info.description,
                    "parameters": info.parameters,
                    "_plugin_info": info,
                }
            
            if result:
                return result
            else:
                return self._get_demo_plugins()
        except ImportError:
            # 使用演示数据
            return self._get_demo_plugins()
    
    def _get_demo_plugins(self) -> dict:
        """获取演示插件数据"""
        return {
            "ping": {
                "display_name": "Ping测试",
                "description": "ICMP连通性测试",
                "category": "connectivity",
                "icon": "📡",
                "parameters": [
                    {"name": "target", "type": "string", "required": True, "label": "目标主机"},
                    {"name": "count", "type": "integer", "default": 4, "label": "次数"},
                ]
            },
            "traceroute": {
                "display_name": "路由追踪",
                "description": "跟踪网络路径",
                "category": "connectivity",
                "icon": "🛤️",
                "parameters": [
                    {"name": "target", "type": "string", "required": True, "label": "目标主机"},
                ]
            },
            "dns_lookup": {
                "display_name": "DNS查询",
                "description": "域名解析查询",
                "category": "dns",
                "icon": "🌐",
                "parameters": [
                    {"name": "domain", "type": "string", "required": True, "label": "域名"},
                    {"name": "record_type", "type": "choice", "choices": ["A", "AAAA", "MX", "NS", "TXT"], "default": "A", "label": "记录类型"},
                ]
            },
            "port_scan": {
                "display_name": "端口扫描",
                "description": "扫描目标端口状态",
                "category": "security",
                "icon": "🔍",
                "parameters": [
                    {"name": "target", "type": "string", "required": True, "label": "目标主机"},
                    {"name": "ports", "type": "string", "default": "22,80,443", "label": "端口列表"},
                ]
            },
            "ssh_exec": {
                "display_name": "SSH远程执行",
                "description": "通过SSH执行远程命令",
                "category": "remote",
                "icon": "🖥️",
                "parameters": [
                    {"name": "host", "type": "string", "required": True, "label": "目标主机"},
                    {"name": "username", "type": "string", "required": True, "label": "用户名"},
                    {"name": "command", "type": "string", "required": True, "label": "命令"},
                ]
            },
            "bandwidth_test": {
                "display_name": "带宽测试",
                "description": "测试网络带宽",
                "category": "performance",
                "icon": "📊",
                "parameters": [
                    {"name": "server", "type": "string", "required": True, "label": "服务器"},
                    {"name": "duration", "type": "integer", "default": 10, "label": "持续时间(秒)"},
                ]
            },
            "config_backup": {
                "display_name": "配置备份",
                "description": "备份设备配置",
                "category": "config",
                "icon": "💾",
                "parameters": [
                    {"name": "device", "type": "string", "required": True, "label": "设备地址"},
                    {"name": "output_dir", "type": "string", "default": "./backups", "label": "输出目录"},
                ]
            },
            "whois": {
                "display_name": "Whois查询",
                "description": "域名/IP注册信息查询",
                "category": "dns",
                "icon": "📋",
                "parameters": [
                    {"name": "target", "type": "string", "required": True, "label": "域名或IP"},
                ]
            },
        }
    
    def _get_category_name(self, category: str) -> str:
        """获取分类显示名称"""
        names = {
            "connectivity": "连通性",
            "dns": "DNS",
            "remote": "远程管理",
            "performance": "性能",
            "security": "安全",
            "config": "配置",
            "other": "其他",
        }
        return names.get(category, category)
    
    def _create_plugin_command(self, plugin_id: str, plugin_info: dict):
        """创建插件执行命令的回调函数
        
        Args:
            plugin_id: 插件ID
            plugin_info: 插件信息字典
            
        Returns:
            异步回调函数
        """
        async def execute_plugin() -> None:
            """打开插件执行界面"""
            from ..screens.plugin_screen import PluginScreen
            self._app.push_screen(PluginScreen(plugin_id, plugin_info))
        
        return execute_plugin
