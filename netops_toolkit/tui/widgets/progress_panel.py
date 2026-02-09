"""
ProgressPanel组件 - 响应式进度显示

特性:
- 支持多任务进度追踪
- 实时更新进度条
- 显示任务状态和耗时
- 支持取消任务
- 动画效果
"""

from __future__ import annotations

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Button, Static, ProgressBar


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class TaskProgress:
    """任务进度数据"""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def elapsed_seconds(self) -> float:
        """已用时间（秒）"""
        if not self.start_time:
            return 0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def elapsed_str(self) -> str:
        """格式化的已用时间"""
        seconds = self.elapsed_seconds
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}时{minutes}分"


class TaskProgressItem(Static):
    """单个任务进度项"""
    
    DEFAULT_CSS = """
    TaskProgressItem {
        height: auto;
        padding: 1;
        margin: 0 0 1 0;
        border: round $primary-darken-2;
    }
    
    TaskProgressItem.-running {
        border: round $accent;
    }
    
    TaskProgressItem.-completed {
        border: round $success;
    }
    
    TaskProgressItem.-failed {
        border: round $error;
    }
    
    TaskProgressItem > .task-header {
        layout: horizontal;
        height: 2;
    }
    
    TaskProgressItem > .task-header > .task-icon {
        width: 3;
    }
    
    TaskProgressItem > .task-header > .task-name {
        width: 1fr;
        text-style: bold;
    }
    
    TaskProgressItem > .task-header > .task-time {
        width: auto;
        color: $text-muted;
    }
    
    TaskProgressItem > .task-progress {
        height: auto;
        padding: 1 0;
    }
    
    TaskProgressItem > .task-message {
        color: $text-muted;
    }
    
    TaskProgressItem > .task-error {
        color: $error;
    }
    
    TaskProgressItem > .task-actions {
        layout: horizontal;
        height: auto;
        align: right middle;
    }
    """
    
    class CancelRequested(Message):
        """取消任务请求"""
        def __init__(self, task_id: str) -> None:
            self.task_id = task_id
            super().__init__()
    
    # 响应式属性
    progress: reactive[float] = reactive(0.0)
    status: reactive[TaskStatus] = reactive(TaskStatus.PENDING)
    
    def __init__(self, task: TaskProgress, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._task_data = task  # 重命名以避免与父类属性冲突
        self.progress = task.progress
        self.status = task.status
    
    def compose(self) -> ComposeResult:
        """渲染组件"""
        task = self._task_data
        # 头部：图标、名称、时间
        with Horizontal(classes="task-header"):
            yield Label(self._status_icon, classes="task-icon", id=f"icon-{task.task_id}")
            yield Label(task.name, classes="task-name")
            yield Label(task.elapsed_str, classes="task-time", id=f"time-{task.task_id}")
        
        # 进度条
        with Container(classes="task-progress"):
            yield ProgressBar(
                total=100,
                show_eta=False,
                id=f"progress-{task.task_id}",
            )
        
        # 状态消息
        yield Label(
            task.message or "等待中...",
            classes="task-message",
            id=f"message-{task.task_id}",
        )
        
        # 错误消息（如有）
        if task.error:
            yield Label(f"⚠ {task.error}", classes="task-error")
        
        # 操作按钮
        with Horizontal(classes="task-actions"):
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                yield Button("取消", id=f"btn-cancel-{task.task_id}", variant="error")
    
    @property
    def _status_icon(self) -> str:
        """获取状态图标"""
        icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "▶",
            TaskStatus.COMPLETED: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.CANCELLED: "⊘",
        }
        return icons.get(self._task_data.status, "?")
    
    def watch_progress(self, value: float) -> None:
        """监听进度变化"""
        try:
            progress_bar = self.query_one(f"#progress-{self._task_data.task_id}", ProgressBar)
            progress_bar.update(progress=int(value * 100))
        except Exception:
            pass
    
    def watch_status(self, value: TaskStatus) -> None:
        """监听状态变化"""
        # 更新CSS类
        for status in TaskStatus:
            self.remove_class(f"-{status.value}")
        self.add_class(f"-{value.value}")
        
        # 更新图标
        try:
            icon_label = self.query_one(f"#icon-{self._task_data.task_id}", Label)
            icon_label.update(self._status_icon)
        except Exception:
            pass
    
    def update_task(self, task: TaskProgress) -> None:
        """更新任务数据"""
        self._task_data = task
        self.progress = task.progress
        self.status = task.status
        
        # 更新消息
        try:
            msg_label = self.query_one(f"#message-{self._task_data.task_id}", Label)
            msg_label.update(task.message or "")
            
            time_label = self.query_one(f"#time-{self._task_data.task_id}", Label)
            time_label.update(task.elapsed_str)
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == f"btn-cancel-{self._task_data.task_id}":
            self.post_message(self.CancelRequested(self._task_data.task_id))


class ProgressPanel(Widget):
    """完整的进度面板组件
    
    管理多个任务的进度显示
    """
    
    DEFAULT_CSS = """
    ProgressPanel {
        width: 100%;
        height: auto;
        min-height: 5;
    }
    
    ProgressPanel > .panel-header {
        height: 3;
        layout: horizontal;
        padding: 0 1;
        border-bottom: solid $primary-darken-2;
    }
    
    ProgressPanel > .panel-header > .panel-title {
        width: 1fr;
        text-style: bold;
    }
    
    ProgressPanel > .panel-header > .panel-summary {
        width: auto;
        color: $text-muted;
    }
    
    ProgressPanel > .task-list {
        height: auto;
        padding: 1;
    }
    
    ProgressPanel > .no-tasks {
        height: 5;
        content-align: center middle;
        color: $text-muted;
    }
    """
    
    BINDINGS = [
        Binding("c", "cancel_all", "取消全部", show=True),
    ]
    
    class TaskCancelled(Message):
        """任务取消消息"""
        def __init__(self, task_id: str) -> None:
            self.task_id = task_id
            super().__init__()
    
    class AllTasksCancelled(Message):
        """全部任务取消消息"""
        pass
    
    def __init__(
        self,
        title: str = "任务进度",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._title = title
        self._tasks: dict[str, TaskProgress] = {}
    
    def compose(self) -> ComposeResult:
        """渲染组件"""
        # 头部
        with Horizontal(classes="panel-header"):
            yield Label(f"📋 {self._title}", classes="panel-title")
            yield Label("0 个任务", classes="panel-summary", id="task-summary")
        
        # 任务列表
        with Vertical(classes="task-list", id="task-list"):
            if not self._tasks:
                yield Label("暂无正在执行的任务", classes="no-tasks")
    
    def add_task(self, task: TaskProgress) -> None:
        """添加任务"""
        self._tasks[task.task_id] = task
        self._refresh_list()
    
    def update_task(
        self,
        task_id: str,
        progress: Optional[float] = None,
        status: Optional[TaskStatus] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            progress: 进度(0-1)
            status: 状态
            message: 状态消息
            error: 错误消息
        """
        if task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        
        if progress is not None:
            task.progress = progress
        if status is not None:
            task.status = status
            if status == TaskStatus.RUNNING and not task.start_time:
                task.start_time = datetime.now()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.end_time = datetime.now()
        if message is not None:
            task.message = message
        if error is not None:
            task.error = error
        
        # 更新UI
        try:
            item = self.query_one(f"TaskProgressItem", TaskProgressItem)
            if item.task.task_id == task_id:
                item.update_task(task)
        except Exception:
            pass
        
        self._update_summary()
    
    def remove_task(self, task_id: str) -> None:
        """移除任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._refresh_list()
    
    def clear_completed(self) -> None:
        """清除已完成的任务"""
        completed_ids = [
            tid for tid, task in self._tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
        for tid in completed_ids:
            del self._tasks[tid]
        self._refresh_list()
    
    def _refresh_list(self) -> None:
        """刷新任务列表"""
        task_list = self.query_one("#task-list", Vertical)
        task_list.remove_children()
        
        if self._tasks:
            for task in self._tasks.values():
                task_list.mount(TaskProgressItem(task))
        else:
            task_list.mount(Label("暂无正在执行的任务", classes="no-tasks"))
        
        self._update_summary()
    
    def _update_summary(self) -> None:
        """更新摘要信息"""
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        total = len(self._tasks)
        
        summary = self.query_one("#task-summary", Label)
        if running > 0:
            summary.update(f"{running}/{total} 个任务运行中")
        else:
            summary.update(f"{total} 个任务")
    
    def on_task_progress_item_cancel_requested(
        self, event: TaskProgressItem.CancelRequested
    ) -> None:
        """处理取消请求"""
        self.post_message(self.TaskCancelled(event.task_id))
    
    def action_cancel_all(self) -> None:
        """取消所有任务"""
        self.post_message(self.AllTasksCancelled())
    
    # ========== 公共方法 ==========
    
    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    def get_running_tasks(self) -> list[TaskProgress]:
        """获取正在运行的任务"""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]
    
    @property
    def has_running_tasks(self) -> bool:
        """是否有运行中的任务"""
        return any(t.status == TaskStatus.RUNNING for t in self._tasks.values())
