"""
NetOps Toolkit TUI 插件执行屏幕

显示插件参数表单并执行插件。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import (
    Static, Button, Input, Switch, Select,
    ProgressBar, Label, RichLog
)
from textual.worker import Worker, get_current_worker

from netops_toolkit.plugins import Plugin, PluginResult, ResultStatus, ParamSpec
from netops_toolkit.core.logger import get_logger, log_audit
from netops_toolkit.tui.widgets.result_view import LogView

logger = get_logger(__name__)


class PluginScreen(Screen):
    """插件执行屏幕 - 参数表单 + 执行 + 结果显示"""
    
    BINDINGS = [
        ("escape", "go_back", "返回"),
        ("ctrl+r", "run_plugin", "执行"),
    ]
    
    def __init__(self, plugin_name: str, plugin_class: Type[Plugin]) -> None:
        """
        初始化插件屏幕
        
        Args:
            plugin_name: 插件名称
            plugin_class: 插件类
        """
        super().__init__()
        self.plugin_name = plugin_name
        self.plugin_class = plugin_class
        self.plugin = plugin_class()
        self.param_inputs: Dict[str, Any] = {}
        self._plugin_running = False
    
    def compose(self) -> ComposeResult:
        """组合界面组件"""
        # 插件信息头部
        yield Container(
            Static(
                f"[bold cyan]{self.plugin.name}[/bold cyan]",
                id="plugin-title"
            ),
            Static(
                f"[dim]{self.plugin.description}[/dim]",
                id="plugin-description"
            ),
            id="plugin-header"
        )
        
        # 参数表单
        with Container(id="param-form"):
            yield Static("[bold]参数配置[/bold]", classes="form-title")
            
            # 动态生成参数输入
            params = self.plugin.get_required_params()
            for param in params:
                with Horizontal(classes="param-row"):
                    # 参数标签
                    required_mark = "[red]*[/red]" if param.required else ""
                    yield Label(
                        f"{param.description}{required_mark}:",
                        classes="param-label"
                    )
                    
                    # 根据参数类型生成输入组件
                    if param.choices:
                        # 选择框
                        options = [(str(c), c) for c in param.choices]
                        default_val = str(param.default) if param.default else options[0][0]
                        widget = Select(
                            options,
                            value=default_val,
                            id=f"param-{param.name}",
                            classes="param-input"
                        )
                    elif param.param_type == bool:
                        # 开关
                        widget = Switch(
                            value=param.default if param.default is not None else False,
                            id=f"param-{param.name}",
                            classes="param-input"
                        )
                    else:
                        # 文本输入
                        default_str = str(param.default) if param.default is not None else ""
                        placeholder = f"请输入{param.description}"
                        widget = Input(
                            value=default_str,
                            placeholder=placeholder,
                            id=f"param-{param.name}",
                            classes="param-input"
                        )
                    
                    self.param_inputs[param.name] = widget
                    yield widget
        
        # 操作按钮
        with Horizontal(id="action-buttons"):
            yield Button("▶️ 执行", id="run-button", variant="success")
            yield Button("⬅️ 返回", id="cancel-button", variant="warning")
        
        # 进度条
        yield ProgressBar(id="progress-bar", show_eta=False)
        
        # 日志输出区域
        yield LogView(id="log-view")
    
    def on_mount(self) -> None:
        """屏幕挂载时"""
        # 初始化插件
        if not self.plugin.initialize():
            self.query_one("#log-view", LogView).log_error("插件初始化失败")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "run-button":
            self.action_run_plugin()
        elif event.button.id == "cancel-button":
            self.action_go_back()
    
    def action_go_back(self) -> None:
        """返回上一屏幕"""
        self.plugin.cleanup()
        self.app.pop_screen()
    
    def action_run_plugin(self) -> None:
        """执行插件"""
        if self._plugin_running:
            self.app.notify("插件正在执行中...", title="提示")
            return
        
        # 收集参数
        params = self._collect_params()
        if params is None:
            return
        
        # 启动异步执行
        self.run_worker(self._execute_plugin(params), exclusive=True)
    
    def _collect_params(self) -> Optional[Dict[str, Any]]:
        """收集表单参数"""
        params = {}
        param_specs = self.plugin.get_required_params()
        
        for spec in param_specs:
            widget = self.param_inputs.get(spec.name)
            if widget is None:
                continue
            
            # 获取值
            if isinstance(widget, Input):
                value = widget.value.strip()
            elif isinstance(widget, Switch):
                value = widget.value
            elif isinstance(widget, Select):
                value = widget.value
            else:
                value = None
            
            # 类型转换
            if spec.param_type == int and isinstance(value, str):
                try:
                    value = int(value) if value else spec.default
                except ValueError:
                    self.app.notify(f"参数 {spec.description} 必须是整数", title="错误")
                    return None
            elif spec.param_type == float and isinstance(value, str):
                try:
                    value = float(value) if value else spec.default
                except ValueError:
                    self.app.notify(f"参数 {spec.description} 必须是数字", title="错误")
                    return None
            
            # 必填检查
            if spec.required and not value and value != 0 and value is not False:
                self.app.notify(f"请填写必填参数: {spec.description}", title="错误")
                return None
            
            params[spec.name] = value
        
        return params
    
    async def _execute_plugin(self, params: Dict[str, Any]) -> None:
        """异步执行插件"""
        self._plugin_running = True
        log_view = self.query_one("#log-view", LogView)
        progress = self.query_one("#progress-bar", ProgressBar)
        run_button = self.query_one("#run-button", Button)
        
        # 禁用执行按钮
        run_button.disabled = True
        
        # 开始进度
        progress.update(total=100, progress=10)
        log_view.log_info(f"开始执行 {self.plugin.name}...")
        log_view.log_info(f"参数: {params}")
        
        try:
            # 模拟进度
            progress.update(progress=30)
            
            # 执行插件
            # 注意：由于插件可能是同步的，这里使用 run_in_executor
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(
                    pool,
                    lambda: self.plugin.run(**params)
                )
            
            progress.update(progress=90)
            
            # 处理结果
            if result.is_success:
                log_view.log_success(f"执行成功: {result.message}")
                self.app.notify(result.message, title="成功", timeout=5)
            else:
                log_view.log_error(f"执行失败: {result.message}")
                for error in result.errors:
                    log_view.log_error(f"  - {error}")
                self.app.notify(result.message, title="失败", timeout=5)
            
            # 显示结果数据
            if result.data:
                log_view.log_info("结果数据:")
                if isinstance(result.data, list):
                    for item in result.data[:10]:  # 限制显示数量
                        log_view.write(f"  {item}")
                elif isinstance(result.data, dict):
                    for key, value in list(result.data.items())[:10]:
                        log_view.write(f"  {key}: {value}")
            
            # 记录审计日志
            log_audit(
                user="tui",
                action=self.plugin.name,
                target=str(params),
                result=result.status.value,
            )
            
            progress.update(progress=100)
            
        except Exception as e:
            logger.error(f"插件执行异常: {e}")
            log_view.log_error(f"执行异常: {e}")
            self.app.notify(f"执行异常: {e}", title="错误", timeout=5)
            
        finally:
            self._plugin_running = False
            run_button.disabled = False


__all__ = ["PluginScreen"]
