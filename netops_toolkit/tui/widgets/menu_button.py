"""
NetOps Toolkit TUI 菜单按钮组件

自定义的大型菜单按钮，用于主界面和分类选择。
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Static
from textual.message import Message


class CategoryButton(Button):
    """分类按钮组件 - 用于主屏幕的功能分类选择"""
    
    class Selected(Message):
        """分类选中消息"""
        def __init__(self, category: str, label: str) -> None:
            self.category = category
            self.label = label
            super().__init__()
    
    def __init__(
        self,
        icon: str,
        label: str,
        category: str,
        count: int = 0,
        description: str = "",
        **kwargs
    ) -> None:
        """
        初始化分类按钮
        
        Args:
            icon: 图标字符
            label: 按钮标签
            category: 分类标识
            count: 该分类下的插件数量
            description: 分类描述
        """
        # 构建按钮显示文本
        display_text = f"{icon}\n{label}\n({count}个功能)"
        
        super().__init__(display_text, **kwargs)
        
        self.icon = icon
        self.label_text = label
        self.category = category
        self.count = count
        self.description = description
        
        # 添加分类特定的CSS类
        self.add_class("category-button")
        self.add_class(f"-{category.replace('_', '-')}")
    
    def on_click(self) -> None:
        """点击事件处理"""
        self.post_message(self.Selected(self.category, self.label_text))


class MenuButton(Button):
    """菜单按钮组件 - 用于插件列表"""
    
    class Selected(Message):
        """按钮选中消息"""
        def __init__(self, plugin_name: str, plugin_class: type) -> None:
            self.plugin_name = plugin_name
            self.plugin_class = plugin_class
            super().__init__()
    
    def __init__(
        self,
        icon: str,
        label: str,
        plugin_name: str,
        plugin_class: type,
        description: str = "",
        **kwargs
    ) -> None:
        """
        初始化菜单按钮
        
        Args:
            icon: 图标字符
            label: 按钮标签
            plugin_name: 插件名称
            plugin_class: 插件类
            description: 插件描述
        """
        display_text = f"{icon}  {label}"
        
        super().__init__(display_text, **kwargs)
        
        self.icon = icon
        self.label_text = label
        self.plugin_name = plugin_name
        self.plugin_class = plugin_class
        self.description = description
        
        self.add_class("plugin-button")
    
    def on_click(self) -> None:
        """点击事件处理"""
        self.post_message(self.Selected(self.plugin_name, self.plugin_class))


class ActionButton(Button):
    """操作按钮组件 - 用于执行/取消等操作"""
    
    def __init__(
        self,
        label: str,
        variant: str = "default",
        **kwargs
    ) -> None:
        """
        初始化操作按钮
        
        Args:
            label: 按钮标签
            variant: 按钮变体 (default, success, warning, error)
        """
        super().__init__(label, **kwargs)
        
        self.variant = variant
        
        # 根据变体添加样式类
        if variant != "default":
            self.add_class(f"-{variant}")


__all__ = ["CategoryButton", "MenuButton", "ActionButton"]
