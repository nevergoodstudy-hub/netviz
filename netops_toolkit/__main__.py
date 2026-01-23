"""
NetOps Toolkit 入口点

允许通过 python -m netops_toolkit 运行程序
"""

from netops_toolkit.cli import app


def main():
    """主入口函数"""
    app()


if __name__ == "__main__":
    main()
