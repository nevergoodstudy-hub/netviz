"""
ResultTable组件 - 实时结果展示表格

特性:
- 支持实时数据更新
- 可点击行查看详情
- 支持排序和过滤
- 分页显示
- 导出功能
"""

from __future__ import annotations

from typing import Any, Optional, Callable
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Label, Button, Static


@dataclass
class TableColumn:
    """表格列定义"""
    key: str
    label: str
    width: Optional[int] = None
    sortable: bool = True
    formatter: Optional[Callable[[Any], str]] = None


class ResultTable(Widget):
    """实时结果表格组件
    
    支持:
    - 动态添加/更新行
    - 行点击事件
    - 列排序
    - 分页显示
    - 数据导出
    """
    
    DEFAULT_CSS = """
    ResultTable {
        width: 100%;
        height: 100%;
    }
    
    ResultTable > .table-header {
        height: 3;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-bottom: solid $primary-darken-2;
    }
    
    ResultTable > .table-header > .table-title {
        width: 1fr;
        text-style: bold;
    }
    
    ResultTable > .table-header > .table-info {
        width: auto;
        color: $text-muted;
    }
    
    ResultTable > .table-container {
        height: 1fr;
    }
    
    ResultTable > .table-footer {
        height: 3;
        layout: horizontal;
        align: center middle;
        padding: 0 1;
        border-top: solid $primary-darken-2;
    }
    
    ResultTable > .table-footer > .pagination {
        layout: horizontal;
        width: auto;
    }
    
    ResultTable > .table-footer > .export-buttons {
        layout: horizontal;
        width: auto;
    }
    """
    
    BINDINGS = [
        Binding("up", "cursor_up", "上移", show=False),
        Binding("down", "cursor_down", "下移", show=False),
        Binding("enter", "select_row", "查看详情", show=False),
        Binding("e", "export", "导出", show=True),
        Binding("r", "refresh", "刷新", show=True),
    ]
    
    class RowSelected(Message):
        """行选中消息"""
        def __init__(self, row_key: str, row_data: dict) -> None:
            self.row_key = row_key
            self.row_data = row_data
            super().__init__()
    
    class ExportRequested(Message):
        """导出请求消息"""
        def __init__(self, format: str) -> None:
            self.format = format
            super().__init__()
    
    # 当前页码
    current_page: reactive[int] = reactive(1)
    
    # 每页行数
    page_size: reactive[int] = reactive(50)
    
    # 总行数
    total_rows: reactive[int] = reactive(0)
    
    def __init__(
        self,
        columns: list[TableColumn] = None,
        title: str = "结果",
        show_pagination: bool = True,
        show_export: bool = True,
        *args,
        **kwargs,
    ) -> None:
        """初始化表格
        
        Args:
            columns: 列定义列表
            title: 表格标题
            show_pagination: 是否显示分页
            show_export: 是否显示导出按钮
        """
        super().__init__(*args, **kwargs)
        self._columns = columns or []
        self._title = title
        self._show_pagination = show_pagination
        self._show_export = show_export
        self._data: dict[str, dict] = {}  # {row_key: row_data}
        self._sort_column: Optional[str] = None
        self._sort_ascending: bool = True
    
    def compose(self) -> ComposeResult:
        """渲染组件"""
        # 头部
        with Horizontal(classes="table-header"):
            yield Label(f"📊 {self._title}", classes="table-title")
            yield Label("0 条记录", classes="table-info", id="row-count")
        
        # 表格容器
        with Container(classes="table-container"):
            table = DataTable(id="data-table", cursor_type="row")
            yield table
        
        # 底部
        with Horizontal(classes="table-footer"):
            # 分页控件
            if self._show_pagination:
                with Horizontal(classes="pagination"):
                    yield Button("◀ 上一页", id="btn-prev", disabled=True)
                    yield Label("1 / 1", id="page-info")
                    yield Button("下一页 ▶", id="btn-next", disabled=True)
            
            # 导出按钮
            if self._show_export:
                with Horizontal(classes="export-buttons"):
                    yield Button("📄 CSV", id="btn-export-csv")
                    yield Button("📊 Excel", id="btn-export-excel")
    
    def on_mount(self) -> None:
        """挂载后初始化"""
        self._setup_columns()
    
    def _setup_columns(self) -> None:
        """设置表格列"""
        table = self.query_one("#data-table", DataTable)
        
        for col in self._columns:
            table.add_column(col.label, key=col.key, width=col.width)
    
    def add_row(self, key: str, data: dict) -> None:
        """添加一行数据
        
        Args:
            key: 行唯一标识
            data: 行数据字典
        """
        self._data[key] = data
        self._render_row(key, data)
        self._update_info()
    
    def update_row(self, key: str, data: dict) -> None:
        """更新一行数据
        
        Args:
            key: 行唯一标识
            data: 新的行数据
        """
        if key in self._data:
            self._data[key].update(data)
            self._render_row(key, self._data[key], update=True)
    
    def remove_row(self, key: str) -> None:
        """移除一行数据"""
        if key in self._data:
            del self._data[key]
            table = self.query_one("#data-table", DataTable)
            try:
                table.remove_row(key)
            except Exception:
                pass
            self._update_info()
    
    def clear(self) -> None:
        """清空所有数据"""
        self._data.clear()
        table = self.query_one("#data-table", DataTable)
        table.clear()
        self._update_info()
    
    def _render_row(self, key: str, data: dict, update: bool = False) -> None:
        """渲染一行数据"""
        table = self.query_one("#data-table", DataTable)
        
        # 构建行数据
        row_values = []
        for col in self._columns:
            value = data.get(col.key, "")
            if col.formatter:
                value = col.formatter(value)
            row_values.append(str(value))
        
        if update:
            # 更新现有行
            try:
                for i, col in enumerate(self._columns):
                    table.update_cell(key, col.key, row_values[i])
            except Exception:
                pass
        else:
            # 添加新行
            table.add_row(*row_values, key=key)
    
    def _update_info(self) -> None:
        """更新统计信息"""
        self.total_rows = len(self._data)
        count_label = self.query_one("#row-count", Label)
        count_label.update(f"{self.total_rows} 条记录")
        
        # 更新分页
        if self._show_pagination:
            self._update_pagination()
    
    def _update_pagination(self) -> None:
        """更新分页状态"""
        total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
        
        page_label = self.query_one("#page-info", Label)
        page_label.update(f"{self.current_page} / {total_pages}")
        
        prev_btn = self.query_one("#btn-prev", Button)
        next_btn = self.query_one("#btn-next", Button)
        
        prev_btn.disabled = self.current_page <= 1
        next_btn.disabled = self.current_page >= total_pages
    
    # ========== 事件处理 ==========
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理行选中"""
        row_key = str(event.row_key.value)
        if row_key in self._data:
            self.post_message(self.RowSelected(row_key, self._data[row_key]))
    
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """处理列头点击（排序）"""
        column_key = str(event.column_key.value)
        
        # 找到对应的列定义
        col_def = next((c for c in self._columns if c.key == column_key), None)
        if col_def and col_def.sortable:
            if self._sort_column == column_key:
                self._sort_ascending = not self._sort_ascending
            else:
                self._sort_column = column_key
                self._sort_ascending = True
            
            self._sort_data()
    
    def _sort_data(self) -> None:
        """对数据进行排序"""
        if not self._sort_column:
            return
        
        table = self.query_one("#data-table", DataTable)
        table.sort(self._sort_column, reverse=not self._sort_ascending)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-prev":
            self.current_page = max(1, self.current_page - 1)
            self._update_pagination()
        elif event.button.id == "btn-next":
            total_pages = max(1, (self.total_rows + self.page_size - 1) // self.page_size)
            self.current_page = min(total_pages, self.current_page + 1)
            self._update_pagination()
        elif event.button.id == "btn-export-csv":
            self.post_message(self.ExportRequested("csv"))
        elif event.button.id == "btn-export-excel":
            self.post_message(self.ExportRequested("excel"))
    
    # ========== Action方法 ==========
    
    def action_cursor_up(self) -> None:
        """向上移动光标"""
        table = self.query_one("#data-table", DataTable)
        table.action_cursor_up()
    
    def action_cursor_down(self) -> None:
        """向下移动光标"""
        table = self.query_one("#data-table", DataTable)
        table.action_cursor_down()
    
    def action_select_row(self) -> None:
        """选择当前行"""
        table = self.query_one("#data-table", DataTable)
        table.action_select_cursor()
    
    def action_export(self) -> None:
        """导出数据"""
        self.post_message(self.ExportRequested("csv"))
    
    def action_refresh(self) -> None:
        """刷新表格"""
        self._update_info()
    
    # ========== 公共方法 ==========
    
    def set_data(self, data: list[dict], key_field: str = "id") -> None:
        """批量设置数据
        
        Args:
            data: 数据列表
            key_field: 作为行key的字段名
        """
        self.clear()
        for row in data:
            key = str(row.get(key_field, id(row)))
            self.add_row(key, row)
    
    def get_data(self) -> list[dict]:
        """获取所有数据"""
        return list(self._data.values())
    
    def get_selected_row(self) -> Optional[dict]:
        """获取当前选中的行数据"""
        table = self.query_one("#data-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            return self._data.get(str(row_key))
        return None
