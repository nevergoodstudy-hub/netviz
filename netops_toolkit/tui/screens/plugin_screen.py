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
from netops_toolkit.utils.export_utils import save_report
from netops_toolkit.utils.dependency_utils import (
    get_dependency_info, install_dependency, DependencyInfo
)
from netops_toolkit.utils.preset_utils import (
    list_preset_names, get_preset, save_preset
)
from pathlib import Path

logger = get_logger(__name__)


class PluginScreen(Screen):
    """插件执行屏幕 - 参数表单 + 执行 + 结果显示"""
    
    BINDINGS = [
        ("escape", "go_back", "返回"),
        ("ctrl+r", "run_plugin", "执行"),
        ("ctrl+e", "show_export_menu", "导出"),
        ("ctrl+i", "install_deps", "安装依赖"),
        ("ctrl+s", "save_current_preset", "保存预设"),
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
        self._last_result: Optional[PluginResult] = None  # 保存最后执行结果
        self._last_params: Dict[str, Any] = {}  # 保存最后执行参数
    
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
        
        # 预设选择
        preset_names = list_preset_names(self.plugin.name)
        if preset_names:
            with Horizontal(id="preset-row", classes="param-row"):
                yield Label("预设配置:", classes="param-label")
                preset_options = [("选择预设...", "")] + [(n, n) for n in preset_names]
                yield Select(preset_options, id="preset-select", classes="param-input")
        
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
            yield Button("💾 导出", id="export-button", variant="primary")
            yield Button("📂 保存预设", id="save-preset-btn", variant="default")
            yield Button("⬅️ 返回", id="cancel-button", variant="warning")
        
        # 导出格式选择 (默认隐藏)
        with Horizontal(id="export-options", classes="hidden"):
            yield Button("JSON", id="export-json", variant="default")
            yield Button("CSV", id="export-csv", variant="default")
            yield Button("HTML", id="export-html", variant="default")
            yield Button("Markdown", id="export-md", variant="default")
        
        # 依赖安装按钮 (默认隐藏)
        with Horizontal(id="install-deps-container", classes="hidden"):
            yield Button("📦 安装缺少的依赖", id="install-deps-btn", variant="warning")
        
        # 进度条
        yield ProgressBar(id="progress-bar", show_eta=False)
        
        # 日志输出区域
        yield LogView(id="log-view")
    
    def on_mount(self) -> None:
        """屏幕挂载时"""
        # 初始化插件并检查依赖
        if not self.plugin.initialize():
            log_view = self.query_one("#log-view", LogView)
            missing_deps = self.plugin.get_missing_dependencies()
            if missing_deps:
                log_view.log_warning(f"缺少依赖: {', '.join(missing_deps)}")
                log_view.log_info("📦 点击'安装依赖'按钮或按 Ctrl+I 安装缺少的依赖")
                self._show_install_button()
            else:
                log_view.log_error("插件初始化失败")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "run-button":
            self.action_run_plugin()
        elif event.button.id == "cancel-button":
            self.action_go_back()
        elif event.button.id == "export-button":
            self.action_show_export_menu()
        elif event.button.id.startswith("export-"):
            fmt = event.button.id.replace("export-", "")
            self._do_export(fmt)
        elif event.button.id == "install-deps-btn":
            self.action_install_deps()
        elif event.button.id == "save-preset-btn":
            self.action_save_current_preset()
    
    def action_go_back(self) -> None:
        """返回上一屏幕"""
        self.plugin.cleanup()
        self.app.pop_screen()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """处理预设选择变更"""
        if event.select.id == "preset-select" and event.value:
            self._load_preset(str(event.value))
    
    def action_show_export_menu(self) -> None:
        """显示/隐藏导出格式选项"""
        export_options = self.query_one("#export-options")
        if "hidden" in export_options.classes:
            export_options.remove_class("hidden")
        else:
            export_options.add_class("hidden")
    
    def _do_export(self, fmt: str) -> None:
        """执行导出操作"""
        if self._last_result is None:
            self.app.notify("请先执行插件获取结果", title="提示")
            return
        
        # 隐藏导出选项
        self.query_one("#export-options").add_class("hidden")
        
        # 准备导出数据
        export_data = self._last_result.data if self._last_result.data else {
            "status": self._last_result.status.value,
            "message": self._last_result.message,
            "params": self._last_params,
        }
        
        # 确定导出目录
        reports_dir = Path.cwd() / "reports"
        
        try:
            output_path = save_report(
                data=export_data,
                report_dir=reports_dir,
                prefix=self.plugin_name.replace(" ", "_"),
                format=fmt,
                title=f"{self.plugin.name} 执行报告",
                plugin_name=self.plugin.name,
                status=self._last_result.status.value,
                errors=self._last_result.errors,
            )
            
            if output_path:
                log_view = self.query_one("#log-view", LogView)
                log_view.log_success(f"已导出到: {output_path}")
                self.app.notify(f"已导出到 {output_path.name}", title="导出成功")
            else:
                self.app.notify("导出失败", title="错误")
        except Exception as e:
            logger.error(f"导出失败: {e}")
            self.app.notify(f"导出失败: {e}", title="错误")
    
    def _load_preset(self, preset_name: str) -> None:
        """加载预设参数到表单"""
        params = get_preset(self.plugin.name, preset_name)
        if not params:
            self.app.notify(f"预设 '{preset_name}' 不存在", title="错误")
            return
        
        log_view = self.query_one("#log-view", LogView)
        log_view.log_info(f"加载预设: {preset_name}")
        
        # 填充表单
        for param_name, value in params.items():
            widget = self.param_inputs.get(param_name)
            if widget is None:
                continue
            
            try:
                if isinstance(widget, Input):
                    widget.value = str(value) if value is not None else ""
                elif isinstance(widget, Switch):
                    widget.value = bool(value)
                elif isinstance(widget, Select):
                    widget.value = str(value)
            except Exception as e:
                logger.warning(f"设置参数 {param_name} 失败: {e}")
        
        self.app.notify(f"已加载预设: {preset_name}", title="预设")
    
    def action_save_current_preset(self) -> None:
        """保存当前参数为预设"""
        # 收集当前参数
        params = self._collect_params()
        if params is None:
            return
        
        # 使用时间戳生成默认预设名称
        from datetime import datetime
        default_name = datetime.now().strftime("预设_%Y%m%d_%H%M%S")
        
        # 保存预设
        if save_preset(self.plugin.name, default_name, params):
            log_view = self.query_one("#log-view", LogView)
            log_view.log_success(f"预设已保存: {default_name}")
            self.app.notify(f"预设已保存: {default_name}", title="成功")
            
            # 刷新预设列表 (如果存在)
            try:
                preset_select = self.query_one("#preset-select", Select)
                preset_names = list_preset_names(self.plugin.name)
                preset_options = [("选择预设...", "")] + [(n, n) for n in preset_names]
                preset_select.set_options(preset_options)
            except Exception:
                pass
        else:
            self.app.notify("保存预设失败", title="错误")
    
    def _show_install_button(self) -> None:
        """显示依赖安装按钮"""
        try:
            container = self.query_one("#install-deps-container")
            container.remove_class("hidden")
        except Exception:
            pass
    
    def _hide_install_button(self) -> None:
        """隐藏依赖安装按钮"""
        try:
            container = self.query_one("#install-deps-container")
            container.add_class("hidden")
        except Exception:
            pass
    
    def action_install_deps(self) -> None:
        """安装缺少的依赖"""
        missing_deps = self.plugin.get_missing_dependencies()
        if not missing_deps:
            self.app.notify("没有缺少的依赖", title="提示")
            return
        
        # 异步安装
        self.run_worker(self._install_missing_deps(missing_deps), exclusive=True)
    
    async def _install_missing_deps(self, deps: List[str]) -> None:
        """异步安装缺少的依赖"""
        log_view = self.query_one("#log-view", LogView)
        progress = self.query_one("#progress-bar", ProgressBar)
        
        log_view.log_info(f"开始安装依赖: {', '.join(deps)}")
        progress.update(total=len(deps) * 100, progress=0)
        
        import concurrent.futures
        loop = asyncio.get_event_loop()
        
        success_count = 0
        failed_count = 0
        
        for i, dep_name in enumerate(deps):
            dep_info = get_dependency_info(dep_name)
            log_view.log_info(f"正在安装: {dep_info.package_name}...")
            
            try:
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    ok, msg = await loop.run_in_executor(
                        pool,
                        lambda d=dep_info: install_dependency(d)
                    )
                
                if ok:
                    log_view.log_success(f"✅ {dep_info.package_name} 安装成功")
                    success_count += 1
                else:
                    log_view.log_error(f"❌ {dep_info.package_name} 安装失败: {msg}")
                    failed_count += 1
            except Exception as e:
                log_view.log_error(f"❌ {dep_info.package_name} 安装异常: {e}")
                failed_count += 1
            
            progress.update(progress=(i + 1) * 100)
        
        # 安装完成后重新初始化插件
        if success_count > 0:
            log_view.log_info("尝试重新初始化插件...")
            if self.plugin.initialize():
                log_view.log_success("插件初始化成功！现在可以执行插件。")
                self._hide_install_button()
                self.app.notify("依赖安装完成", title="成功")
            else:
                remaining = self.plugin.get_missing_dependencies()
                if remaining:
                    log_view.log_warning(f"仍缺少依赖: {', '.join(remaining)}")
                else:
                    log_view.log_warning("插件初始化仍然失败")
        else:
            log_view.log_error("所有依赖安装失败")
            self.app.notify("依赖安装失败", title="错误")
    
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
        self._last_params = params.copy()  # 保存参数
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
            
            # 保存执行结果
            self._last_result = result
            
            progress.update(progress=90)
            
            # 处理结果
            if result.is_success:
                log_view.log_success(f"执行成功: {result.message}")
                log_view.log_info("💾 可使用 Ctrl+E 或点击'导出'按钮保存结果")
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
