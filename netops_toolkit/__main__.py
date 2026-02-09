"""
NetOps Toolkit 入口点

允许通过 python -m netops_toolkit 运行程序

使用方式:
- python -m netops_toolkit              # 启动交互式菜单 (默认)
- python -m netops_toolkit --interactive # 启动交互式菜单
- python -m netops_toolkit --tui        # 启动现代TUI界面
- python -m netops_toolkit --web        # 启动Web UI界面 (新!)
- python -m netops_toolkit --cli        # 使用 CLI 模式
- python -m netops_toolkit ping ...     # CLI 子命令
"""

import sys


def main():
    """主入口函数"""
    args = sys.argv[1:]
    
    # 检查模式参数
    if "--tui" in args:
        # TUI模式 - 现代化终端界面
        args.remove("--tui")
        run_tui_mode()
    elif "--web" in args:
        # Web UI 模式 - 基于 FastAPI
        args.remove("--web")
        run_web_mode()
    elif "--interactive" in args:
        # 交互式模式
        args.remove("--interactive")
        run_interactive_mode()
    elif "--cli" in args or len(args) > 0:
        # CLI 模式 (有其他参数时也进入 CLI)
        if "--cli" in args:
            args.remove("--cli")
        run_cli_mode()
    else:
        # 默认启动交互式模式
        run_interactive_mode()


def run_tui_mode():
    """运行 TUI 模式 - 现代化终端用户界面"""
    try:
        from netops_toolkit.tui.app import run_tui
        run_tui()
    except ImportError as e:
        print(f"错误: 无法加载TUI模块 - {e}")
        print("请确保已安装textual依赖: pip install textual")
        sys.exit(1)


def run_web_mode():
    """运行 Web UI 模式 - 基于 FastAPI + HTMX"""
    try:
        from netops_toolkit.web.app import run_web_server
        run_web_server()
    except ImportError as e:
        print(f"错误: 无法加载Web模块 - {e}")
        print("请确保已安装依赖: pip install fastapi uvicorn jinja2")
        sys.exit(1)


def run_interactive_mode():
    """运行交互式模式"""
    from netops_toolkit.interactive import main as interactive_main
    interactive_main()


def run_cli_mode():
    """运行 CLI 模式"""
    from netops_toolkit.cli import app
    app()


if __name__ == "__main__":
    main()
