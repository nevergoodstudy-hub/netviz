"""
NetOps Toolkit TUI - 结果展示界面

结果界面包含:
- 执行摘要
- 结果数据表格
- 多种导出格式
- 结果过滤和搜索
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any
from datetime import datetime
import json

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static, Input, Select, DataTable
from textual.message import Message

if TYPE_CHECKING:
    from ..app import NetOpsApp


class ResultSummary(Static):
    """执行结果摘要"""
    
    DEFAULT_CSS = """
    ResultSummary {
        height: auto;
        padding: 1 2;
        border-bottom: solid $primary-darken-2;
    }
    
    ResultSummary > .summary-title {
        text-style: bold;
        padding: 0 0 1 0;
    }
    
    ResultSummary > .summary-info {
        height: auto;
    }
    
    ResultSummary > .summary-info > .info-item {
        padding: 0 2 0 0;
    }
    """
    
    def __init__(
        self,
        plugin_name: str,
        status: str,
        duration: float,
        row_count: int,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.plugin_name = plugin_name
        self.status = status
        self.duration = duration
        self.row_count = row_count
    
    def compose(self) -> ComposeResult:
        status_icon = "✅" if self.status == "success" else "❌"
        status_color = "green" if self.status == "success" else "red"
        
        yield Label(f"📊 执行结果: {self.plugin_name}", classes="summary-title")
        with Horizontal(classes="summary-info"):
            yield Label(
                f"状态: [{status_color}]{status_icon} {self.status}[/]",
                classes="info-item"
            )
            yield Label(f"耗时: {self.duration:.2f}s", classes="info-item")
            yield Label(f"记录数: {self.row_count}", classes="info-item")
            yield Label(
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                classes="info-item"
            )


class ResultFilter(Static):
    """结果过滤器"""
    
    DEFAULT_CSS = """
    ResultFilter {
        height: 4;
        padding: 0 2;
        border-bottom: solid $primary-darken-2;
    }
    
    ResultFilter > Horizontal {
        height: 100%;
        align: left middle;
    }
    
    ResultFilter Input {
        width: 30;
        margin: 0 1;
    }
    
    ResultFilter Select {
        width: 20;
        margin: 0 1;
    }
    """
    
    class FilterChanged(Message):
        """过滤条件变更消息"""
        def __init__(self, query: str, column: str):
            super().__init__()
            self.query = query
            self.column = column
    
    def __init__(self, columns: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._columns = columns
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("🔍 过滤: ")
            yield Input(placeholder="搜索...", id="filter-input")
            yield Label(" 列: ")
            options = [("全部", "all")] + [(col, col) for col in self._columns]
            yield Select(options, value="all", id="filter-column")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """搜索框内容变化"""
        if event.input.id == "filter-input":
            column_select = self.query_one("#filter-column", Select)
            self.post_message(self.FilterChanged(
                event.value,
                str(column_select.value)
            ))
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """列选择变化"""
        if event.select.id == "filter-column":
            filter_input = self.query_one("#filter-input", Input)
            self.post_message(self.FilterChanged(
                filter_input.value,
                str(event.value)
            ))


class ExportPanel(Static):
    """导出面板"""
    
    DEFAULT_CSS = """
    ExportPanel {
        height: 4;
        padding: 0 2;
        border-top: solid $primary-darken-2;
    }
    
    ExportPanel > Horizontal {
        height: 100%;
        align: left middle;
    }
    
    ExportPanel Button {
        margin: 0 1;
    }
    """
    
    class ExportRequested(Message):
        """导出请求消息"""
        def __init__(self, format: str):
            super().__init__()
            self.format = format
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("📤 导出: ")
            yield Button("CSV", id="export-csv", variant="default")
            yield Button("JSON", id="export-json", variant="default")
            yield Button("Excel", id="export-excel", variant="default")
            yield Button("Markdown", id="export-md", variant="default")
            yield Button("📋 复制", id="export-clipboard", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        format_map = {
            "export-csv": "csv",
            "export-json": "json",
            "export-excel": "excel",
            "export-md": "markdown",
            "export-clipboard": "clipboard",
        }
        if event.button.id in format_map:
            self.post_message(self.ExportRequested(format_map[event.button.id]))


class ResultScreen(Screen):
    """结果展示屏幕
    
    布局:
    ┌──────────────────────────────────────────────────────────────┐
    │  执行摘要: 插件名、状态、耗时、记录数                          │
    ├──────────────────────────────────────────────────────────────┤
    │  过滤: [搜索框] 列: [下拉选择]                                 │
    ├──────────────────────────────────────────────────────────────┤
    │                                                              │
    │  结果数据表格                                                 │
    │                                                              │
    │                                                              │
    ├──────────────────────────────────────────────────────────────┤
    │  导出: [CSV] [JSON] [Excel] [Markdown] [复制]                │
    ├──────────────────────────────────────────────────────────────┤
    │  [返回] [重新执行] [新建任务]                                  │
    └──────────────────────────────────────────────────────────────┘
    """
    
    TITLE = "执行结果"
    
    BINDINGS = [
        Binding("escape", "go_back", "返回", show=True),
        Binding("ctrl+c", "copy_selected", "复制选中", show=True),
        Binding("ctrl+e", "export_csv", "导出CSV", show=True),
        Binding("ctrl+r", "rerun", "重新执行", show=False),
    ]
    
    def __init__(
        self,
        plugin_id: str,
        plugin_info: dict,
        result: dict,
        duration: float = 0.0,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.plugin_id = plugin_id
        self.plugin_info = plugin_info
        self.result = result
        self.duration = duration
        self._all_data: list[dict] = []
        self._filtered_data: list[dict] = []
        self._columns: list[str] = []
    
    def compose(self) -> ComposeResult:
        """构建界面"""
        # 解析结果数据
        self._parse_result()
        
        display_name = self.plugin_info.get("display_name", self.plugin_id)
        status = self.result.get("status", "unknown")
        
        # 结果摘要
        yield ResultSummary(
            plugin_name=display_name,
            status=status,
            duration=self.duration,
            row_count=len(self._all_data),
        )
        
        # 过滤器
        yield ResultFilter(self._columns)
        
        # 数据表格
        with VerticalScroll(id="table-container"):
            yield DataTable(id="result-table")
        
        # 导出面板
        yield ExportPanel()
        
        # 底部按钮
        with Horizontal(id="action-bar"):
            yield Button("🔙 返回", id="btn-back", variant="default")
            yield Button("🔄 重新执行", id="btn-rerun", variant="primary")
            yield Button("➕ 新建任务", id="btn-new", variant="success")
    
    def on_mount(self) -> None:
        """挂载后初始化表格"""
        self._setup_table()
        self._populate_table(self._all_data)
    
    def _parse_result(self) -> None:
        """解析结果数据"""
        data = self.result.get("data", [])
        
        if isinstance(data, list) and len(data) > 0:
            # 列表数据
            if isinstance(data[0], dict):
                self._columns = list(data[0].keys())
                self._all_data = data
            else:
                # 简单列表，转换为单列
                self._columns = ["value"]
                self._all_data = [{"value": item} for item in data]
        elif isinstance(data, dict):
            # 单个字典，转换为键值对列表
            self._columns = ["key", "value"]
            self._all_data = [{"key": k, "value": v} for k, v in data.items()]
        else:
            # 其他情况
            self._columns = ["result"]
            self._all_data = [{"result": str(data)}]
        
        self._filtered_data = self._all_data.copy()
    
    def _setup_table(self) -> None:
        """设置表格列"""
        table = self.query_one("#result-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        
        # 添加列
        for col in self._columns:
            table.add_column(col, key=col)
    
    def _populate_table(self, data: list[dict]) -> None:
        """填充表格数据"""
        table = self.query_one("#result-table", DataTable)
        table.clear()
        
        for row in data:
            values = [str(row.get(col, "")) for col in self._columns]
            table.add_row(*values)
    
    # ========== 事件处理 ==========
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-back":
            self.action_go_back()
        elif event.button.id == "btn-rerun":
            self.action_rerun()
        elif event.button.id == "btn-new":
            self.action_new_task()
    
    def on_result_filter_filter_changed(self, event: ResultFilter.FilterChanged) -> None:
        """处理过滤条件变化"""
        self._apply_filter(event.query, event.column)
    
    def on_export_panel_export_requested(self, event: ExportPanel.ExportRequested) -> None:
        """处理导出请求"""
        self._export_data(event.format)
    
    # ========== Action方法 ==========
    
    def action_go_back(self) -> None:
        """返回上一界面"""
        self.app.pop_screen()
    
    def action_rerun(self) -> None:
        """重新执行插件"""
        from .plugin_screen import PluginScreen
        # 替换当前屏幕为插件屏幕
        self.app.switch_screen(PluginScreen(self.plugin_id, self.plugin_info))
    
    def action_new_task(self) -> None:
        """新建任务（返回主界面）"""
        # 弹出所有屏幕返回主界面
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
    
    def action_copy_selected(self) -> None:
        """复制选中行"""
        table = self.query_one("#result-table", DataTable)
        if table.cursor_row is not None:
            row_data = self._filtered_data[table.cursor_row]
            text = "\t".join(str(v) for v in row_data.values())
            # 注意：Textual没有直接的剪贴板API，需要通过pyperclip等
            self._copy_to_clipboard(text)
            self.notify("已复制到剪贴板", title="成功")
    
    def action_export_csv(self) -> None:
        """快捷键导出CSV"""
        self._export_data("csv")
    
    # ========== 过滤和导出 ==========
    
    def _apply_filter(self, query: str, column: str) -> None:
        """应用过滤"""
        if not query:
            self._filtered_data = self._all_data.copy()
        else:
            query_lower = query.lower()
            if column == "all":
                # 搜索所有列
                self._filtered_data = [
                    row for row in self._all_data
                    if any(query_lower in str(v).lower() for v in row.values())
                ]
            else:
                # 搜索指定列
                self._filtered_data = [
                    row for row in self._all_data
                    if query_lower in str(row.get(column, "")).lower()
                ]
        
        self._populate_table(self._filtered_data)
    
    def _export_data(self, format: str) -> None:
        """导出数据"""
        if format == "clipboard":
            self._export_clipboard()
        elif format == "csv":
            self._export_csv()
        elif format == "json":
            self._export_json()
        elif format == "excel":
            self._export_excel()
        elif format == "markdown":
            self._export_markdown()
    
    def _export_clipboard(self) -> None:
        """导出到剪贴板"""
        lines = ["\t".join(self._columns)]
        for row in self._filtered_data:
            lines.append("\t".join(str(row.get(col, "")) for col in self._columns))
        text = "\n".join(lines)
        self._copy_to_clipboard(text)
        self.notify(f"已复制 {len(self._filtered_data)} 行到剪贴板", title="成功")
    
    def _export_csv(self) -> None:
        """导出CSV文件"""
        import csv
        from pathlib import Path
        
        filename = f"{self.plugin_id}_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = Path.cwd() / filename
        
        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self._columns)
                writer.writeheader()
                writer.writerows(self._filtered_data)
            self.notify(f"已保存到: {filename}", title="导出成功")
        except Exception as e:
            self.notify(f"导出失败: {e}", title="错误", severity="error")
    
    def _export_json(self) -> None:
        """导出JSON文件"""
        from pathlib import Path
        
        filename = f"{self.plugin_id}_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path.cwd() / filename
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._filtered_data, f, ensure_ascii=False, indent=2)
            self.notify(f"已保存到: {filename}", title="导出成功")
        except Exception as e:
            self.notify(f"导出失败: {e}", title="错误", severity="error")
    
    def _export_excel(self) -> None:
        """导出Excel文件"""
        try:
            import openpyxl
            from pathlib import Path
            
            filename = f"{self.plugin_id}_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = Path.cwd() / filename
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Result"
            
            # 写入表头
            for col_idx, col_name in enumerate(self._columns, 1):
                ws.cell(row=1, column=col_idx, value=col_name)
            
            # 写入数据
            for row_idx, row_data in enumerate(self._filtered_data, 2):
                for col_idx, col_name in enumerate(self._columns, 1):
                    ws.cell(row=row_idx, column=col_idx, value=row_data.get(col_name, ""))
            
            wb.save(filepath)
            self.notify(f"已保存到: {filename}", title="导出成功")
        except ImportError:
            self.notify("需要安装 openpyxl: pip install openpyxl", title="错误", severity="error")
        except Exception as e:
            self.notify(f"导出失败: {e}", title="错误", severity="error")
    
    def _export_markdown(self) -> None:
        """导出Markdown表格"""
        from pathlib import Path
        
        filename = f"{self.plugin_id}_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = Path.cwd() / filename
        
        try:
            lines = []
            # 表头
            lines.append("| " + " | ".join(self._columns) + " |")
            lines.append("| " + " | ".join(["---"] * len(self._columns)) + " |")
            # 数据行
            for row in self._filtered_data:
                values = [str(row.get(col, "")).replace("|", "\\|") for col in self._columns]
                lines.append("| " + " | ".join(values) + " |")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.notify(f"已保存到: {filename}", title="导出成功")
        except Exception as e:
            self.notify(f"导出失败: {e}", title="错误", severity="error")
    
    def _copy_to_clipboard(self, text: str) -> None:
        """复制文本到剪贴板"""
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            # 如果没有pyperclip，尝试使用系统命令
            import subprocess
            import sys
            
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["clip"],
                        input=text.encode("utf-16le"),
                        check=True
                    )
                elif sys.platform == "darwin":
                    subprocess.run(
                        ["pbcopy"],
                        input=text.encode("utf-8"),
                        check=True
                    )
                else:
                    # Linux - 尝试xclip
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text.encode("utf-8"),
                        check=True
                    )
            except Exception:
                self.notify("剪贴板功能不可用，请安装pyperclip", severity="warning")
    
    @property
    def _default_css(self) -> str:
        return """
        ResultScreen {
            layout: vertical;
        }
        
        #table-container {
            height: 1fr;
            border: round $primary-darken-2;
            margin: 0 1;
        }
        
        #result-table {
            height: auto;
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
