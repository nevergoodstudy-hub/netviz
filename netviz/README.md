# NetViz - PCAP 可视化分析平台

[![CI/CD](https://github.com/nevergoodstudy-hub/netviz/actions/workflows/ci.yml/badge.svg)](https://github.com/nevergoodstudy-hub/netviz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)

NetViz 是一个功能完整的 PCAP 网络数据包可视化分析平台，支持桌面应用和 Web 两种运行模式。

![NetViz Screenshot](docs/screenshot.png)

## 功能特性

- 📊 **PCAP 文件分析** - 上传并解析 PCAP/PCAPNG 文件，支持多种协议
- 📈 **可视化图表** - 协议分布、时间序列、流量拓扑、Top 通信者
- 🔍 **实时抓包** - 直接捕获网络流量（需要 Npcap）
- 🤖 **AI 分析助手** - 支持 OpenAI、Anthropic、DeepSeek、Ollama
- 🚨 **异常检测** - 自动检测端口扫描、可疑 DNS、大数据传输等
- 🔒 **威胁情报** - 集成 VirusTotal、AbuseIPDB API
- 🖥️ **桌面应用** - 基于 Tauri 2.0 的原生桌面体验

## 项目结构

```
netviz/
├── src/                 # React 前端源码
├── src-tauri/           # Tauri 桌面应用配置
├── backend/             # Python FastAPI 后端
├── public/              # 静态资源
├── scripts/             # 构建脚本
└── package.json
```

## 快速开始

### 1. 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖
cd backend
python -m venv .venv
.\.venv\Scripts\pip install fastapi uvicorn sqlalchemy aiosqlite scapy python-multipart aiofiles httpx psutil pydantic-settings
```

### 2. 运行方式

#### 方式 A：桌面应用模式（推荐）

1. 先启动后端：
```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

2. 启动 Tauri 应用：
```bash
npm run tauri:dev
```

或运行已构建的应用：
```powershell
.\src-tauri\target\debug\netviz.exe
```

#### 方式 B：Web 开发模式

```bash
# 终端 1 - 后端
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2 - 前端
npm run dev
```

访问 http://localhost:3000

## 构建发布版本

### 构建桌面应用

```bash
npm run tauri:build
```

输出位置：`src-tauri/target/release/`

### 打包后端（可选，用于独立分发）

```powershell
.\scripts\build-backend.ps1
```

## 配置

### 环境变量（后端 .env）

```ini
# AI 提供商
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
OLLAMA_BASE_URL=http://localhost:11434

# 日志
LOG_LEVEL=INFO
LOG_DIR=./logs
```

### 实时抓包

Windows 系统需要安装 [Npcap](https://npcap.com/) 驱动。

## 技术栈

- **前端**: React 18, TypeScript, Vite, TailwindCSS, ECharts, D3.js
- **后端**: Python 3.11+, FastAPI, SQLAlchemy, Scapy
- **桌面**: Tauri 2, Rust
- **AI**: OpenAI, Anthropic, DeepSeek, Ollama 支持

## 贡献

欢迎贡献代码！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 致谢

- [Scapy](https://scapy.net/) - Python 网络数据包处理库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [Tauri](https://tauri.app/) - 构建桌面应用的工具
- [ECharts](https://echarts.apache.org/) - 可视化图表库

## Star History

如果这个项目对你有帮助，请给个 Star ⭐️
