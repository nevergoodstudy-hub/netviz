# 变更日志

所有重要的项目变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 威胁情报集成：支持 VirusTotal 和 AbuseIPDB API
- 完整的 TypeScript 类型定义
- React 路由懒加载优化
- GitHub Actions CI/CD 工作流
- 后端单元测试框架

### 改进
- Tauri sidecar 权限配置优化
- 前端代码分割减小包体积

## [0.1.0] - 2024-01-01

### 新增
- PCAP 文件上传和解析
- 协议分布可视化
- 时间序列流量图表
- 网络拓扑图
- 实时网络抓包（需要 Npcap）
- AI 分析助手（支持 OpenAI、Anthropic、DeepSeek、Ollama）
- 异常检测和告警
- Tauri 桌面应用支持
- 暗色/亮色主题切换

### 技术栈
- 前端：React 18 + TypeScript + Vite + TailwindCSS
- 后端：Python 3.11+ + FastAPI + SQLAlchemy
- 桌面：Tauri 2 + Rust
- 数据分析：Scapy + ECharts + D3.js
