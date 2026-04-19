# NetViz - PCAP 可视化分析平台

[![CI/CD](https://github.com/nevergoodstudy-hub/netviz/actions/workflows/ci.yml/badge.svg)](https://github.com/nevergoodstudy-hub/netviz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 20.19+](https://img.shields.io/badge/node-20.19%2B-green.svg)](https://nodejs.org/)

NetViz 是一个功能完整的 PCAP 网络数据包可视化分析平台，支持桌面应用和 Web 两种运行模式。

## 功能特性

- 📊 **PCAP 文件分析** - 上传并解析 `.pcap` / `.pcapng` / `.cap` 文件，支持多种协议
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
npm ci

# 后端依赖
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -e .[dev]
```

### 2. 运行方式

#### 方式 A：桌面应用模式（推荐）

1. 启动 Tauri 应用：
```bash
npm run tauri:dev
```

Tauri 桌面壳会自动拉起 `netviz-backend` sidecar，并按 [`config/backend-endpoint.json`](config/backend-endpoint.json) 中的地址轮询健康检查。

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

### 3. GitHub Actions 多系统构建

仓库根目录下的 [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) 会针对 `netviz/` 子项目执行：

- Ubuntu 后端测试与依赖审计
- Ubuntu 前端 lint / type-check / 生产依赖审计
- Windows、Linux、macOS 的 Tauri 桌面构建
- 相关 Pull Request 也会执行桌面构建矩阵，尽早发现 sidecar / 打包回归

## 构建发布版本

### 构建桌面应用

```bash
npm run tauri:build
```

输出位置：`src-tauri/target/release/`

默认会为当前系统生成原生安装包；如需调试前端 sourcemap，可临时设置 `NETVIZ_BUILD_SOURCEMAPS=1`。

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

# 桌面管理设置加固（可选）
ADMIN_ACCESS_TOKEN=your_admin_token
SETTINGS_ENCRYPTION_KEY=your_32_plus_char_secret

# 日志
LOG_LEVEL=INFO
LOG_DIR=./logs
```

### 实时抓包

Windows 系统需要安装 [Npcap](https://npcap.com/) 驱动。

### 敏感设置加密

- 推荐通过 `SETTINGS_ENCRYPTION_KEY` 提供专用加密密钥。
- 如果没有设置该环境变量，NetViz 会在数据目录中自动生成一个安装级密钥文件，而不会再回退到共享默认密钥。
- 桌面打包环境下，数据库、上传目录、日志和自动生成密钥会写入当前用户可写的应用数据目录，而不是安装目录旁边。

### AI 提供商自定义地址

- OpenAI / DeepSeek 默认只接受官方 HTTPS API 地址，避免把云端 API Key 发送到恶意或内网主机。
- 只有在你明确设置 `ALLOW_UNSAFE_AI_BASE_URLS=true` 时，才允许自定义公共 HTTPS 端点。

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
