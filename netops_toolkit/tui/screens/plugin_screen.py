"""
NetOps Toolkit TUI - 插件执行界面

插件执行界面包含:
- 参数表单
- 执行控制按钮
- 实时进度显示
- 结果预览
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any
from functools import partial
import uuid

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static, RichLog
from textual import work
from textual.worker import Worker

if TYPE_CHECKING:
    from ..app import NetOpsApp

# 导入自定义组件
from ..widgets.param_form import PluginParamForm
from ..widgets.progress_panel import ProgressPanel, TaskProgress, TaskStatus


class Breadcrumb(Static):
    """面包屑导航组件"""
    
    DEFAULT_CSS = """
    Breadcrumb {
        height: 2;
        padding: 0 2;
        background: $surface-darken-1;
    }
    """
    
    def __init__(self, path: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._path = path
    
    def render(self) -> str:
        parts = []
        for i, item in enumerate(self._path):
            if i < len(self._path) - 1:
                parts.append(f"[@click=navigate({i})]{item}[/]")
            else:
                parts.append(f"[bold]{item}[/]")
        return "📍 " + " > ".join(parts)
    
    def action_navigate(self, index: int) -> None:
        """导航到指定层级"""
        # 返回主页
        if index == 0:
            self.app.pop_screen()


class PluginHeader(Static):
    """插件头部信息"""
    
    DEFAULT_CSS = """
    PluginHeader {
        height: auto;
        padding: 1 2;
        border-bottom: solid $primary-darken-2;
    }
    
    PluginHeader > .plugin-title {
        text-style: bold;
        padding: 0 0 1 0;
    }
    
    PluginHeader > .plugin-description {
        color: $text-muted;
    }
    """
    
    def __init__(self, plugin_id: str, plugin_info: dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plugin_id = plugin_id
        self.plugin_info = plugin_info
    
    def compose(self) -> ComposeResult:
        icon = self.plugin_info.get("icon", "🔧")
        name = self.plugin_info.get("display_name", self.plugin_id)
        desc = self.plugin_info.get("description", "")
        
        yield Label(f"{icon} {name}", classes="plugin-title")
        if desc:
            yield Label(f"📝 {desc}", classes="plugin-description")


class ExecutionLog(Static):
    """执行日志面板"""
    
    DEFAULT_CSS = """
    ExecutionLog {
        height: 1fr;
        min-height: 10;
        border: round $primary-darken-2;
        margin: 1;
    }
    
    ExecutionLog > .log-header {
        height: 2;
        padding: 0 1;
        background: $surface-darken-2;
        text-style: bold;
    }
    
    ExecutionLog > RichLog {
        height: 1fr;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Label("📋 执行日志", classes="log-header")
        yield RichLog(id="execution-log", highlight=True, markup=True)
    
    def log(self, message: str, style: str = "") -> None:
        """添加日志"""
        log_widget = self.query_one("#execution-log", RichLog)
        if style:
            log_widget.write(f"[{style}]{message}[/]")
        else:
            log_widget.write(message)
    
    def clear(self) -> None:
        """清空日志"""
        log_widget = self.query_one("#execution-log", RichLog)
        log_widget.clear()


class PluginScreen(Screen):
    """插件执行屏幕
    
    布局:
    ┌──────────────────────────────────────────────────────────────┐
    │  面包屑: 主页 > 分类 > 插件名                                  │
    ├──────────────────────────────────────────────────────────────┤
    │  插件标题和描述                                               │
    ├─────────────────────────┬────────────────────────────────────┤
    │                         │                                    │
    │  参数表单                │  执行进度 / 日志                    │
    │                         │                                    │
    │                         │                                    │
    ├─────────────────────────┴────────────────────────────────────┤
    │  [执行] [重置] [取消] [返回]                                   │
    └──────────────────────────────────────────────────────────────┘
    """
    
    TITLE = "插件执行"
    
    BINDINGS = [
        Binding("ctrl+enter", "execute", "执行", show=True),
        Binding("ctrl+r", "reset", "重置", show=True),
        Binding("escape", "go_back", "返回", show=True),
        Binding("ctrl+c", "cancel_task", "取消执行", show=False),
    ]
    
    def __init__(
        self,
        plugin_id: str,
        plugin_info: dict,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.plugin_id = plugin_id
        self.plugin_info = plugin_info
        self._current_worker: Optional[Worker] = None
        self._current_runner = None  # PluginRunner实例
        self._task_id: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """构建界面"""
        category = self.plugin_info.get("category", "other")
        category_name = self._get_category_name(category)
        display_name = self.plugin_info.get("display_name", self.plugin_id)
        
        # 面包屑导航
        yield Breadcrumb(["主页", category_name, display_name])
        
        # 插件头部
        yield PluginHeader(self.plugin_id, self.plugin_info)
        
        # 主内容区
        with Horizontal(id="plugin-main"):
            # 左侧：参数表单
            with Vertical(id="form-panel"):
                yield PluginParamForm(self.plugin_id, self.plugin_info)
            
            # 右侧：进度和日志
            with Vertical(id="output-panel"):
                yield ProgressPanel(title="执行进度", id="progress-panel")
                yield ExecutionLog(id="log-panel")
        
        # 底部操作按钮
        with Horizontal(id="action-bar"):
            yield Button("▶ 执行", id="btn-execute", variant="primary")
            yield Button("↺ 重置", id="btn-reset", variant="default")
            yield Button("⏹ 取消", id="btn-cancel", variant="error", disabled=True)
            yield Button("🔙 返回", id="btn-back", variant="default")
    
    def _get_category_name(self, category: str) -> str:
        """获取分类显示名称"""
        names = {
            "connectivity": "连通性测试",
            "dns": "DNS工具",
            "remote": "远程管理",
            "performance": "性能测试",
            "security": "安全工具",
            "config": "配置管理",
            "other": "其他工具",
        }
        return names.get(category, category)
    
    # ========== 事件处理 ==========
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-execute":
            self.action_execute()
        elif event.button.id == "btn-reset":
            self.action_reset()
        elif event.button.id == "btn-cancel":
            self.action_cancel_task()
        elif event.button.id == "btn-back":
            self.action_go_back()
    
    def on_plugin_param_form_submitted(self, event: PluginParamForm.Submitted) -> None:
        """处理表单提交"""
        self._run_plugin(event.values)
    
    def on_plugin_param_form_cancelled(self, event: PluginParamForm.Cancelled) -> None:
        """处理表单取消"""
        self.action_go_back()
    
    # ========== Action方法 ==========
    
    def action_execute(self) -> None:
        """执行插件"""
        form = self.query_one(PluginParamForm)
        if form.is_valid:
            self._run_plugin(form.values)
        else:
            self.notify("请填写必填参数", title="验证失败", severity="warning")
    
    def action_reset(self) -> None:
        """重置表单"""
        form = self.query_one(PluginParamForm)
        form.action_reset()
        
        # 清空日志
        log_panel = self.query_one("#log-panel", ExecutionLog)
        log_panel.clear()
    
    def action_go_back(self) -> None:
        """返回上一界面"""
        if self._current_worker and self._current_worker.is_running:
            self.notify("请先取消正在执行的任务", title="提示", severity="warning")
            return
        self.app.pop_screen()
    
    def action_cancel_task(self) -> None:
        """取消当前任务"""
        if self._current_worker and self._current_worker.is_running:
            self._current_worker.cancel()
            # 同时取消PluginRunner
            if self._current_runner:
                self._current_runner.cancel()
            self._update_task_status(TaskStatus.CANCELLED, "任务已取消")
            self._on_task_completed()
    
    # ========== 插件执行 ==========
    
    def _run_plugin(self, params: dict) -> None:
        """运行插件"""
        # 禁用执行按钮，启用取消按钮
        self._set_executing(True)
        
        # 创建任务
        self._task_id = str(uuid.uuid4())[:8]
        display_name = self.plugin_info.get("display_name", self.plugin_id)
        
        # 添加到进度面板
        progress_panel = self.query_one("#progress-panel", ProgressPanel)
        progress_panel.add_task(TaskProgress(
            task_id=self._task_id,
            name=display_name,
            status=TaskStatus.PENDING,
            message="准备执行...",
        ))
        
        # 记录日志
        log_panel = self.query_one("#log-panel", ExecutionLog)
        log_panel.log(f"[bold green]▶ 开始执行: {display_name}[/]")
        log_panel.log(f"参数: {params}")
        
        # 启动后台任务
        self._current_worker = self._execute_plugin(params)
    
    @work(thread=True)
    def _execute_plugin(self, params: dict) -> Any:
        """在后台线程执行插件"""
        import time
        
        # 更新状态为运行中
        self.app.call_from_thread(
            self._update_task_status,
            TaskStatus.RUNNING,
            "正在执行..."
        )
        
        try:
            # 尝试加载并执行真实插件
            result = self._execute_real_plugin(params)
            return result
        except ImportError:
            # 模拟执行（开发用）
            return self._execute_mock_plugin(params)
        except Exception as e:
            self.app.call_from_thread(
                self._update_task_status,
                TaskStatus.FAILED,
                str(e)
            )
            self.app.call_from_thread(self._log_message, f"[red]❌ 执行失败: {e}[/]")
            raise
    
    def _execute_real_plugin(self, params: dict) -> Any:
        """执行真实插件"""
        from ..adapters.plugin_adapter import PluginUIAdapter, PluginRunner, ExecutionProgress
        
        adapter = PluginUIAdapter()
        plugin_info = adapter.get_plugin(self.plugin_id)
        
        if not plugin_info:
            raise ValueError(f"插件未找到: {self.plugin_id}")
        
        if not plugin_info.plugin_class:
            raise ValueError(f"插件类未定义: {self.plugin_id}")
        
        # 进度回调
        def on_progress(progress: ExecutionProgress):
            self._update_task_progress(progress.percentage / 100, progress.message)
        
        # 日志回调
        def on_log(message: str):
            self._log_message(message)
        
        # 完成回调
        def on_complete(result):
            if result.is_success:
                self._update_task_status(TaskStatus.COMPLETED, result.message)
                # 转换为字典格式以保持兼容
                result_dict = {
                    "status": "success" if result.is_success else "failed",
                    "data": result.data,
                    "message": result.message,
                    "duration": result.duration,
                    "metadata": result.metadata,
                }
                self._on_task_completed(result_dict)
            else:
                self._update_task_status(TaskStatus.FAILED, result.message)
                self._on_task_completed(None)
        
        # 创建执行器并执行
        runner = PluginRunner(
            plugin_info=plugin_info,
            app=self.app,
            on_progress=on_progress,
            on_log=on_log,
            on_complete=on_complete,
        )
        
        # 保存runner引用用于取消
        self._current_runner = runner
        
        # 执行插件
        result = runner.execute(params)
        
        return result
    
    def _execute_mock_plugin(self, params: dict) -> dict:
        """模拟插件执行（开发用）"""
        import time
        import random
        
        # 模拟执行过程
        total_steps = 10
        for i in range(total_steps):
            if self._current_worker and self._current_worker.is_cancelled:
                return {"status": "cancelled"}
            
            progress = (i + 1) / total_steps
            self.app.call_from_thread(
                self._update_task_progress,
                progress,
                f"执行步骤 {i+1}/{total_steps}..."
            )
            self.app.call_from_thread(
                self._log_message,
                f"[dim]步骤 {i+1}: 模拟处理中...[/]"
            )
            time.sleep(0.5)
        
        # 模拟结果
        result = {
            "status": "success",
            "plugin": self.plugin_id,
            "params": params,
            "data": [
                {"target": "192.168.1.1", "status": "online", "latency": "1.2ms"},
                {"target": "192.168.1.2", "status": "offline", "latency": "-"},
                {"target": "192.168.1.3", "status": "online", "latency": "2.5ms"},
            ]
        }
        
        # 完成
        self.app.call_from_thread(
            self._update_task_status,
            TaskStatus.COMPLETED,
            "执行完成"
        )
        self.app.call_from_thread(
            self._log_message,
            f"[bold green]✓ 执行完成！[/]"
        )
        self.app.call_from_thread(self._on_task_completed, result)
        
        return result
    
    def _update_task_progress(self, progress: float, message: str) -> None:
        """更新任务进度"""
        if self._task_id:
            progress_panel = self.query_one("#progress-panel", ProgressPanel)
            progress_panel.update_task(
                self._task_id,
                progress=progress,
                message=message
            )
    
    def _update_task_status(self, status: TaskStatus, message: str) -> None:
        """更新任务状态"""
        if self._task_id:
            progress_panel = self.query_one("#progress-panel", ProgressPanel)
            progress_panel.update_task(
                self._task_id,
                status=status,
                message=message
            )
    
    def _log_message(self, message: str) -> None:
        """记录日志消息"""
        log_panel = self.query_one("#log-panel", ExecutionLog)
        log_panel.log(message)
    
    def _on_task_completed(self, result: dict = None) -> None:
        """任务完成回调"""
        self._set_executing(False)
        
        if result and result.get("status") == "success":
            # 可选：跳转到结果界面
            self.notify("执行完成！", title="成功", severity="information")
    
    def _set_executing(self, executing: bool) -> None:
        """设置执行状态"""
        execute_btn = self.query_one("#btn-execute", Button)
        cancel_btn = self.query_one("#btn-cancel", Button)
        back_btn = self.query_one("#btn-back", Button)
        
        execute_btn.disabled = executing
        cancel_btn.disabled = not executing
        back_btn.disabled = executing
    
    @property
    def _default_css(self) -> str:
        return """
        PluginScreen {
            layout: vertical;
        }
        
        #plugin-main {
            height: 1fr;
        }
        
        #form-panel {
            width: 40%;
            min-width: 40;
            border-right: solid $primary-darken-2;
            padding: 1;
        }
        
        #output-panel {
            width: 1fr;
        }
        
        #action-bar {
            height: 4;
            align: center middle;
            padding: 1;
            border-top: solid $primary-darken-2;
        }
        
        #action-bar Button {
            margin: 0 1;
        }
        """
