"""
PluginParamForm组件 - 动态参数表单

根据插件的ParamSpec自动生成表单控件。
支持:
- 多种输入类型（文本、数字、布尔、选择、文件路径等）
- 输入验证
- 必填/可选标识
- 帮助提示
"""

from __future__ import annotations

from typing import Any, Optional, Callable
from enum import Enum

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, Container
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Label,
    Static,
    Input,
    Button,
    Switch,
    Select,
    TextArea,
)


class ParamType(Enum):
    """参数类型枚举"""
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    CHOICE = "choice"
    MULTILINE = "multiline"
    FILE_PATH = "filepath"
    IP_ADDRESS = "ip"
    IP_RANGE = "ip_range"
    PORT = "port"
    PORT_RANGE = "port_range"


class FormField(Static):
    """单个表单字段
    
    包含标签、输入控件、验证状态和帮助提示
    """
    
    DEFAULT_CSS = """
    FormField {
        height: auto;
        margin: 1 0;
    }
    
    FormField > .field-row {
        layout: horizontal;
        height: auto;
    }
    
    FormField > .field-row > .field-label {
        width: 15;
        content-align: right middle;
        padding-right: 1;
    }
    
    FormField > .field-row > .field-input {
        width: 1fr;
    }
    
    FormField > .field-row > .field-required {
        width: 2;
        color: $error;
    }
    
    FormField > .field-hint {
        padding-left: 16;
        color: $text-muted;
        text-style: italic;
    }
    
    FormField > .field-error {
        padding-left: 16;
        color: $error;
    }
    
    FormField.-invalid > .field-row > .field-input Input {
        border: tall $error;
    }
    """
    
    class ValueChanged(Message):
        """字段值变化消息"""
        def __init__(self, field_name: str, value: Any, valid: bool) -> None:
            self.field_name = field_name
            self.value = value
            self.valid = valid
            super().__init__()
    
    # 是否有效
    valid: reactive[bool] = reactive(True)
    
    def __init__(
        self,
        param_spec: dict,
        *args,
        **kwargs,
    ) -> None:
        """初始化表单字段
        
        Args:
            param_spec: 参数规格字典，包含:
                - name: 参数名
                - display_name: 显示名称
                - type: 参数类型
                - required: 是否必填
                - default: 默认值
                - hint: 帮助提示
                - choices: 可选值列表（用于choice类型）
                - validator: 验证函数
        """
        super().__init__(*args, **kwargs)
        self.param_spec = param_spec
        self.field_name = param_spec.get("name", "")
        self._value: Any = param_spec.get("default", "")
        self._error_message = ""
    
    def compose(self) -> ComposeResult:
        """渲染字段"""
        spec = self.param_spec
        # 优先使用 display_name, 其次使用 description, 最后使用 name
        display_name = spec.get("display_name") or spec.get("description") or spec.get("name", "")
        required = spec.get("required", False)
        hint = spec.get("hint", "")
        param_type = spec.get("type", "str")
        
        # 字段行
        with Horizontal(classes="field-row"):
            yield Label(display_name, classes="field-label")
            
            # 根据类型选择输入控件
            with Container(classes="field-input"):
                yield self._create_input_widget(param_type)
            
            # 必填标识
            yield Label("*" if required else " ", classes="field-required")
        
        # 帮助提示
        if hint:
            yield Label(hint, classes="field-hint")
        
        # 错误消息（初始隐藏）
        yield Label("", classes="field-error", id=f"error-{self.field_name}")
    
    def _create_input_widget(self, param_type: str) -> Widget:
        """根据参数类型创建对应的输入控件"""
        spec = self.param_spec
        default = spec.get("default", "")
        
        if param_type in ("bool", "boolean"):
            return Switch(value=bool(default), id=f"input-{self.field_name}")
        
        elif param_type == "choice":
            choices = spec.get("choices", [])
            options = [(str(c), c) for c in choices]
            return Select(
                options,
                value=default if default in choices else (choices[0] if choices else None),
                id=f"input-{self.field_name}",
            )
        
        elif param_type == "multiline":
            return TextArea(
                text=str(default),
                id=f"input-{self.field_name}",
            )
        
        elif param_type in ("int", "integer", "port"):
            return Input(
                value=str(default) if default else "",
                placeholder=spec.get("placeholder", "输入数字..."),
                type="integer",
                id=f"input-{self.field_name}",
            )
        
        elif param_type == "float":
            return Input(
                value=str(default) if default else "",
                placeholder=spec.get("placeholder", "输入数字..."),
                type="number",
                id=f"input-{self.field_name}",
            )
        
        else:  # 默认字符串输入 (str, string, 等)
            return Input(
                value=str(default) if default else "",
                placeholder=spec.get("placeholder", ""),
                id=f"input-{self.field_name}",
            )
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入变化"""
        self._value = event.value
        self._validate_and_notify()
    
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """处理开关变化"""
        self._value = event.value
        self._validate_and_notify()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """处理选择变化"""
        self._value = event.value
        self._validate_and_notify()
    
    def _validate_and_notify(self) -> None:
        """验证值并发送消息"""
        is_valid = self._validate()
        self.valid = is_valid
        self.post_message(self.ValueChanged(self.field_name, self._value, is_valid))
    
    def _validate(self) -> bool:
        """验证字段值"""
        spec = self.param_spec
        required = spec.get("required", False)
        param_type = spec.get("type", "str")
        
        # 必填检查
        if required and not self._value:
            self._set_error("此字段为必填项")
            return False
        
        # 类型检查
        if self._value:
            if param_type in ("int", "integer", "port"):
                try:
                    int(self._value)
                except ValueError:
                    self._set_error("请输入有效的整数")
                    return False
            
            elif param_type == "float":
                try:
                    float(self._value)
                except ValueError:
                    self._set_error("请输入有效的数字")
                    return False
            
            elif param_type == "ip":
                if not self._validate_ip(str(self._value)):
                    self._set_error("请输入有效的IP地址")
                    return False
        
        # 自定义验证器
        validator = spec.get("validator")
        if validator and callable(validator):
            result = validator(self._value)
            if result is not True:
                self._set_error(str(result) if result else "验证失败")
                return False
        
        self._clear_error()
        return True
    
    def _validate_ip(self, value: str) -> bool:
        """验证IP地址格式"""
        parts = value.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False
    
    def _set_error(self, message: str) -> None:
        """设置错误消息"""
        self._error_message = message
        self.add_class("-invalid")
        error_label = self.query_one(f"#error-{self.field_name}", Label)
        error_label.update(f"⚠ {message}")
    
    def _clear_error(self) -> None:
        """清除错误消息"""
        self._error_message = ""
        self.remove_class("-invalid")
        error_label = self.query_one(f"#error-{self.field_name}", Label)
        error_label.update("")
    
    @property
    def value(self) -> Any:
        """获取字段值"""
        return self._value
    
    def set_value(self, value: Any) -> None:
        """设置字段值"""
        self._value = value
        # 更新输入控件
        try:
            input_widget = self.query_one(f"#input-{self.field_name}")
            if isinstance(input_widget, Input):
                input_widget.value = str(value) if value else ""
            elif isinstance(input_widget, Switch):
                input_widget.value = bool(value)
            elif isinstance(input_widget, Select):
                input_widget.value = value
        except Exception:
            pass


class PluginParamForm(Widget):
    """完整的插件参数表单
    
    根据插件的参数规格自动生成表单
    """
    
    DEFAULT_CSS = """
    PluginParamForm {
        width: 100%;
        height: auto;
        padding: 1 2;
    }
    
    PluginParamForm > .form-title {
        text-style: bold;
        padding: 0 0 1 0;
        border-bottom: solid $primary-darken-2;
    }
    
    PluginParamForm > .form-fields {
        height: auto;
        padding: 1 0;
    }
    
    PluginParamForm > .form-actions {
        layout: horizontal;
        align: center middle;
        height: auto;
        padding: 1 0;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+enter", "submit", "提交", show=True),
        Binding("ctrl+r", "reset", "重置", show=True),
    ]
    
    class Submitted(Message):
        """表单提交消息"""
        def __init__(self, plugin_id: str, values: dict) -> None:
            self.plugin_id = plugin_id
            self.values = values
            super().__init__()
    
    class Cancelled(Message):
        """表单取消消息"""
        pass
    
    def __init__(
        self,
        plugin_id: str,
        plugin_info: dict,
        *args,
        **kwargs,
    ) -> None:
        """初始化表单
        
        Args:
            plugin_id: 插件ID
            plugin_info: 插件信息，包含params参数规格列表
        """
        super().__init__(*args, **kwargs)
        self.plugin_id = plugin_id
        self.plugin_info = plugin_info
        self._params = plugin_info.get("params", [])
        self._field_values: dict[str, Any] = {}
        self._field_valid: dict[str, bool] = {}
    
    def compose(self) -> ComposeResult:
        """渲染表单"""
        display_name = self.plugin_info.get("display_name", self.plugin_id)
        
        # 标题
        yield Label(f"⚙ {display_name} - 参数配置", classes="form-title")
        
        # 字段列表
        with Vertical(classes="form-fields"):
            for param in self._params:
                yield FormField(param)
        
        # 操作按钮
        with Horizontal(classes="form-actions"):
            yield Button("▶ 执行", id="btn-submit", variant="primary")
            yield Button("↺ 重置", id="btn-reset", variant="default")
            yield Button("✕ 取消", id="btn-cancel", variant="error")
    
    def on_mount(self) -> None:
        """挂载后初始化"""
        # 初始化字段值
        for param in self._params:
            name = param.get("name", "")
            self._field_values[name] = param.get("default", "")
            self._field_valid[name] = not param.get("required", False)
    
    def on_form_field_value_changed(self, event: FormField.ValueChanged) -> None:
        """处理字段值变化"""
        self._field_values[event.field_name] = event.value
        self._field_valid[event.field_name] = event.valid
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        if event.button.id == "btn-submit":
            self.action_submit()
        elif event.button.id == "btn-reset":
            self.action_reset()
        elif event.button.id == "btn-cancel":
            self.post_message(self.Cancelled())
    
    def action_submit(self) -> None:
        """提交表单"""
        # 验证所有字段
        if not self._validate_all():
            self.app.notify("请检查表单中的错误", title="验证失败", severity="error")
            return
        
        # 发送提交消息
        self.post_message(self.Submitted(self.plugin_id, self._field_values.copy()))
    
    def action_reset(self) -> None:
        """重置表单"""
        for param in self._params:
            name = param.get("name", "")
            default = param.get("default", "")
            self._field_values[name] = default
            
            # 重置字段控件
            try:
                field = self.query_one(f"FormField", FormField)
                if field.field_name == name:
                    field.set_value(default)
            except Exception:
                pass
    
    def _validate_all(self) -> bool:
        """验证所有字段"""
        return all(self._field_valid.values())
    
    @property
    def values(self) -> dict:
        """获取所有字段值"""
        return self._field_values.copy()
    
    @property
    def is_valid(self) -> bool:
        """表单是否有效"""
        return self._validate_all()
