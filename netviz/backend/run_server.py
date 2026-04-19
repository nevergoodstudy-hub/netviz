"""
NetViz 后端服务入口
用于 PyInstaller 打包
"""
import sys
import os

# 确保可以找到 app 模块
if getattr(sys, 'frozen', False):
    # 打包后的路径
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    
    # 获取端口参数
    port = int(os.environ.get('NETVIZ_PORT', '8000'))
    host = os.environ.get('NETVIZ_HOST', '127.0.0.1')
    
    print(f"Starting NetViz backend on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
