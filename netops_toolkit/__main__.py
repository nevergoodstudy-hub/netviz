"""
NetOps Toolkit 入口点

允许通过 python -m netops_toolkit 运行程序

使用方式:
- python -m netops_toolkit              # 启动 TUI 界面 (默认)
- python -m netops_toolkit --tui        # 启动 TUI 界面
- python -m netops_toolkit --interactive # 启动旧版交互式菜单
- python -m netops_toolkit --cli        # 使用 CLI 模式
- python -m netops_toolkit ping ...     # CLI 子命令
"""

import sys


def main():
    """主入口函数"""
    args = sys.argv[1:]
    
    # 检查模式参数
    if "--tui" in args:
        # TUI 模式
        args.remove("--tui")
        run_tui_mode()
    elif "--interactive" in args:
        # 旧版交互式模式
        args.remove("--interactive")
        run_interactive_mode()
    elif "--cli" in args or len(args) > 0:
        # CLI 模式 (有其他参数时也进入 CLI)
        if "--cli" in args:
            args.remove("--cli")
        run_cli_mode()
    else:
        # 默认启动 TUI 模式
        run_tui_mode()


def run_tui_mode():
    """运行 TUI 模式"""
    try:
        from netops_toolkit.tui.app import run_tui
        run_tui()
    except ImportError as e:
        print(f"TUI 模块加载失败: {e}")
        print("请确保已安装 textual: pip install textual")
        print("正在回退到交互式模式...")
        run_interactive_mode()
    except Exception as e:
        print(f"TUI 启动失败: {e}")
        print("正在回退到交互式模式...")
        run_interactive_mode()


def run_interactive_mode():
    """运行交互式模式 (旧版)"""
    from netops_toolkit.interactive import main as interactive_main
    interactive_main()


def run_cli_mode():
    """运行 CLI 模式"""
    from netops_toolkit.cli import app
    app()


if __name__ == "__main__":
    main()
