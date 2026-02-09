# NetOps Toolkit - 网络工程实施及测试工具集

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

面向网络工程师的多功能CLI工具箱,集成网络实施、测试、巡检、诊断功能于一体。

## ✨ 核心特性

- 🖥️ **现代TUI** - 基于Textual的全屏终端界面,支持鼠标/键盘双模式 (**新!**)
- 🎨 **美观易用** - 基于Rich/Questionary的现代化CLI界面
- 🔌 **插件化架构** - 模块化设计,易于扩展
- 🏢 **多厂商支持** - Cisco, Huawei, H3C, Juniper等
- 🚀 **批量操作** - 并发处理,提升效率
- 🔐 **安全可靠** - 密码加密存储,操作审计日志
- 📊 **可视化报告** - 表格化展示,支持导出JSON/CSV/Excel

## 🛠️ 功能模块

### 1. 基础诊断工具
- **Ping测试** - ICMP/TCP Ping,批量测试,统计分析
- **Traceroute** - 路由追踪,MTR集成
- **DNS查询** - 正向/反向解析,多服务器查询

### 2. 设备管理
- **SSH批量执行** - 多设备并发命令执行
- **配置备份** - 自动备份,版本管理
- **配置对比** - 差异高亮显示

### 3. 网络扫描
- **端口扫描** - TCP/UDP端口探测
- **ARP扫描** - 局域网主机发现
- **IP冲突检测** - 网段内重复IP检测

### 4. 性能测试
- **带宽测速** - Speedtest集成
- **RTT/Jitter** - 延迟抖动测试
- **iPerf3包装** - 网络吞吐量测试

### 5. 实用工具
- **子网计算器** - CIDR/VLSM计算
- **IP地址转换** - 十进制/二进制/十六进制
- **HTTP调试** - API请求测试

## 💻 CLI命令概览

| 命令 | 说明 | 示例 |
|------|------|------|
| `ping` | Ping连通性测试 | `netops ping 192.168.1.1 -c 4` |
| `traceroute` | 路由追踪 | `netops traceroute 8.8.8.8` |
| `dns` | DNS查询 | `netops dns www.baidu.com -t MX` |
| `scan` | 端口扫描 | `netops scan 192.168.1.1 -p 80,443` |
| `arp-scan` | ARP主机发现 | `netops arp-scan 192.168.1.0/24` |
| `ssh-batch` | SSH批量执行 | `netops ssh-batch -g switches -c "show ver"` |
| `config-backup` | 配置备份 | `netops config-backup -g routers` |
| `config-diff` | 配置对比 | `netops config-diff file1.txt file2.txt` |
| `quality` | 网络质量测试 | `netops quality 8.8.8.8 -c 50` |
| `speedtest` | 带宽测速 | `netops speedtest` |
| `subnet` | 子网计算器 | `netops subnet 192.168.1.0/24` |
| `ip-convert` | IP格式转换 | `netops ip-convert 192.168.1.1` |
| `mac-lookup` | MAC地址查询 | `netops mac-lookup 00:0C:29:12:34:56` |
| `http` | HTTP调试 | `netops http https://api.example.com` |
| `whois` | WHOIS查询 | `netops whois baidu.com` |
| `tui` | 启动现代TUI界面 | `netops tui` |

## 📦 安装

### 系统要求

| 操作系统 | 支持版本 | 备注 |
|---------|---------|------|
| Windows | 10/11 | 完全支持 |
| Linux | 主流发行版 (Ubuntu, CentOS, Debian, Fedora 等) | 完全支持 |
| macOS | 10.14+ | 完全支持 |
| FreeBSD | 12+ | 支持 |
| OpenBSD | 6+ | 支持 |

### Python 版本要求
- Python 3.14 或更高版本

### 方式1: 从源码安装

#### Windows
```powershell
# 克隆仓库
git clone https://github.com/netops-toolkit/netops-toolkit.git
cd netops-toolkit

# 创建虚拟环境 (推荐)
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 可编辑模式安装
pip install -e .
```

#### Linux/macOS/BSD
```bash
# 克隆仓库
git clone https://github.com/netops-toolkit/netops-toolkit.git
cd netops-toolkit

# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 可编辑模式安装
pip install -e .
```

### 方式2: 使用pip (未来)
```bash
pip install netops-toolkit
```

### 可选: 系统依赖

某些功能需要系统级工具，请根据您的操作系统安装：

**Linux (Debian/Ubuntu)**
```bash
sudo apt install iputils-ping traceroute mtr net-tools iproute2
```

**Linux (RHEL/CentOS/Fedora)**
```bash
sudo dnf install iputils traceroute mtr net-tools iproute
```

**macOS**
```bash
brew install mtr
```

**FreeBSD**
```bash
pkg install mtr
```

## 🚀 快速开始

### Web UI 模式 (新!)
```powershell
# 启动 Web UI 界面
netops web
# 或
python -m netops_toolkit --web
```

Web UI 特性:
- 🌐 基于 FastAPI + HTMX + Tailwind CSS
- 📱 响应式设计，支持移动端
- 📡 WebSocket 实时监控
- 📊 API 文档 (http://localhost:8000/api/docs)
- 🌙 暗色/亮色主题切换

### TUI 模式
```powershell
# 启动现代化全屏TUI界面
netops tui
# 或
python -m netops_toolkit --tui
```

TUI界面特性:
- 🖱️ 鼠标/键盘双模式交互
- 🌙 暗色/亮色主题切换 (T键)
- 🔍 命令面板快速搜索 (Ctrl+P)
- 📊 实时监控仪表板 (M键) - Ping监控、设备状态、自动刷新
- 📄 报表中心 (R键) - PDF/Excel导出、多种模板
- 📅 任务调度 - 定时备份、巡检、报表生成
- 🗺️ 网络拓扑 (O键) - ASCII/Unicode拓扑可视化、多种渲染样式
- ✅ 合规检查 (P键) - 配置审计、内置规则、差异报告
- 📝 变更审计 (A键) - 操作日志、变更追溯、导出报表 **(新!)**

**TUI快捷键:**
| 键位 | 功能 |
|------|------|
| H | 返回主页 |
| D | 设备管理 |
| C | 配置中心 |
| X | 诊断工具 |
| M | 监控仪表板 |
| R | 报表中心 |
| O | 网络拓扑 |
| P | 合规检查 |
| A | 变更审计 |
| T | 切换主题 |
| ? | 帮助 |
| Q | 退出 |
| Esc | 返回上一级 |
| Ctrl+P | 命令面板 |

### 交互模式
```powershell
# 启动交互式菜单
netops
# 或
python -m netops_toolkit
```

### 命令行模式
```powershell
# Ping测试
netops ping 192.168.1.1 -c 4
netops ping 192.168.1.0/24 -o results.json  # CIDR批量+导出

# DNS查询
netops dns www.baidu.com
netops dns baidu.com -t MX

# 网络质量测试
netops quality 8.8.8.8 -c 50

# 端口扫描
netops scan 192.168.1.1 -p 1-1000

# SSH批量执行
netops ssh-batch -t 192.168.1.1 -c "show version" -u admin -p password

# 配置备份
netops config-backup -g core_switches -d ./backups

# 子网计算
netops subnet 10.0.0.0/8

# IP转换
netops ip-convert 3232235777

# MAC查询
netops mac-lookup 00:0C:29:12:34:56
```

## ⚙️ 配置

### 全局配置 (config/settings.yaml)
```yaml
app:
  name: "NetOps Toolkit"
  log_level: "INFO"
  
network:
  ssh_timeout: 30
  connect_retry: 3
```

### 设备清单 (config/devices.yaml)
```yaml
groups:
  core_switches:
    vendor: "cisco_ios"
    credentials: "admin_cred"
    devices:
      - name: "SW-CORE-01"
        ip: "192.168.1.10"
      - name: "SW-CORE-02"
        ip: "192.168.1.11"
```

### 凭证管理

推荐通过环境变量设置凭据，避免在配置文件中存储明文密码：

**Windows (PowerShell)**
```powershell
# 临时设置（当前会话有效）
$env:NETOPS_USERNAME = "admin"
$env:NETOPS_PASSWORD = "your_password"

# 永久设置（当前用户）
[Environment]::SetEnvironmentVariable("NETOPS_USERNAME", "admin", "User")
[Environment]::SetEnvironmentVariable("NETOPS_PASSWORD", "your_password", "User")
```

**Linux/macOS/BSD**
```bash
# 临时设置
export NETOPS_USERNAME="admin"
export NETOPS_PASSWORD="your_password"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export NETOPS_USERNAME="admin"' >> ~/.bashrc
echo 'export NETOPS_PASSWORD="your_password"' >> ~/.bashrc
```

**注意：** 如果未设置环境变量，TUI将使用模拟输出演示功能。

**备选: 配置文件凭据 (config/secrets.yaml)**
```yaml
credentials:
  admin_cred:
    username: "admin"
    password: "encrypted_password_here"  # 建议加密存储
```

## 📚 使用示例

### 示例1: 批量Ping测试
```python
from netops_toolkit.plugins.diagnostics.ping import PingPlugin

plugin = PingPlugin()
result = plugin.run(
    targets=["192.168.1.1", "192.168.1.2"],
    count=4,
    timeout=2.0
)
print(result)
```

### 示例2: SSH批量命令
```python
from netops_toolkit.plugins.device_mgmt.ssh_batch import SSHBatchPlugin

plugin = SSHBatchPlugin()
result = plugin.run(
    device_group="core_switches",
    commands=["show version", "show ip int brief"]
)
```

## 🤝 参与贡献

欢迎提交Issue和Pull Request!

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 插件开发指南
参见 [docs/plugin_dev.md](docs/plugin_dev.md)

## 📖 文档

- [用户指南](docs/user_guide.md)
- [插件开发](docs/plugin_dev.md)
- [API参考](docs/api_reference.md)
- [常见问题](docs/faq.md)
- [架构重构方案](ARCHITECTURE_REFACTORING_PROPOSAL.md)
- [迁移指南](MIGRATION_GUIDE.md)
- [测试报告](TEST_REPORT.md)

## 🗓️ 路线图

- [x] v1.0 - 核心框架与基础插件
- [x] v1.1 - 完整插件集 (15个插件)
- [x] v1.4 - **多系统支持** (Windows/Linux/macOS/BSD)
- [x] v1.6 - **工具增强** (导出/依赖管理/跨平台)
- [x] v1.7 - **现代TUI界面** (基于Textual的全屏终端界面)
- [x] v2.0 - **Clean Architecture重构 + Web API + QA测试** ✨
- [ ] v2.5 - Ansible集成
- [ ] v3.0 - SNMP监控
- [ ] v3.5 - AI故障预测

## 🆕 v2.0 更新日志 (2026-02-09)

### Clean Architecture 重构 & QA 测试
本版本完成了全面的架构重构，引入 Clean Architecture 分层设计，并通过完整 QA 测试验证。

**架构重构：**
- 🏗️ **Clean Architecture 四层架构** - Domain / Application / Infrastructure / Presentation 清晰分层
- 🔧 **依赖注入容器** - 基于 dependency-injector 的 DI 容器
- ⚙️ **Pydantic Settings** - 类型安全的环境变量配置管理
- 🔌 **插件系统升级** - 三级目录 (core/builtin/contrib) + 异步插件支持
- 🌐 **异步 Web API** - FastAPI + HTMX + Tailwind CSS 的现代 Web 界面
- 🔐 **安全加固** - 命令注入防护、敏感数据脱敏、审计日志增强

**QA 测试结果：**
- ✅ 417/417 测试通过 (0 失败)
- 🔒 35/35 安全测试通过
- 📊 19% 整体覆盖率 (核心域层 75%+)
- 📋 7 个问题已记录 (详见 `TEST_ISSUES.txt`)

**新增文档：**
- `ARCHITECTURE_REFACTORING_PROPOSAL.md` - 架构重构方案 (5阶段)
- `MIGRATION_GUIDE.md` - 迁移指南
- `TEST_REPORT.md` - 完整测试报告 (IEEE 829 格式)
- `TEST_ISSUES.txt` - 测试问题清单

---

## 🆕 v1.7 更新日志 (2026-01-30)

### 现代TUI界面
本版本引入基于Textual框架的全屏终端用户界面，大幅提升用户体验。

**新特性：**
- 🖥️ **全屏TUI界面** - 现代化终端用户界面，支持鼠标/键盘双模式
- 🌙 **主题切换** - 暗色/亮色主题一键切换 (T键)
- 🔍 **命令面板** - Ctrl+P快速搜索插件
- 📊 **实时进度** - 后台任务实时进度显示
- 📄 **结果导出** - 支持JSON/CSV/Excel/Markdown格式
- ⚡ **性能优化** - 懒加载、批量更新减少重绘

**新增文件：**
- `netops_toolkit/tui/` - TUI模块目录
- `netops_toolkit/tui/app.py` - 主应用类
- `netops_toolkit/tui/screens/` - 屏幕组件
- `netops_toolkit/tui/widgets/` - 自定义组件
- `netops_toolkit/tui/adapters/` - 插件适配层

**使用方式：**
```bash
netops tui
# 或
python -m netops_toolkit --tui
```

---

## v1.6 更新日志 (2026-01-30)

### 工具增强版本
本版本添加了多项实用工具，优化架构设计。

**新特性：**
- 💾 **多格式导出** - 支持 JSON/CSV/HTML/Markdown 格式导出执行结果
- 📦 **依赖管理工具** - 检测和安装缺少的依赖
- 📂 **参数预设管理** - 保存和加载常用参数配置
- 🔒 **安全增强** - 路径验证/命令注入防护/输入过滤

**新增文件：**
- `netops_toolkit/utils/export_utils.py` - 多格式导出工具
- `netops_toolkit/utils/dependency_utils.py` - 依赖管理工具
- `netops_toolkit/utils/preset_utils.py` - 参数预设管理

---

## 🆕 v1.4 更新日志 (2026-01-29)

### 多系统支持
本版本添加了完整的多操作系统支持，包括 BSD 系列系统。

**新特性：**
- 💻 **多系统支持** - 支持 Windows, Linux, macOS, FreeBSD, OpenBSD 等
- 🔧 **跨平台工具模块** - 新增 `platform_utils.py` 统一处理系统差异
- 📡 **网络诊断增强** - 所有网络诊断插件现支持多系统
- 🔍 **智能命令检测** - 自动检测并使用合适的系统命令

**更新的插件：**
- `ping.py` - BSD 系统参数适配
- `traceroute.py` - BSD traceroute 支持
- `mtr.py` - 改进跨平台实现
- `netstat.py` - BSD netstat 解析
- `route_table.py` - BSD 路由表支持
- `arp_scan.py` - BSD ARP 命令支持

**新增文件：**
- `netops_toolkit/utils/platform_utils.py` - 跨平台工具模块
- `netops_toolkit/core/system_info.py` - 系统信息检测模块

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 🙏 致谢

本项目使用了以下优秀的开源库:
- [Textual](https://github.com/Textualize/textual) - 现代TUI框架
- [Rich](https://github.com/Textualize/rich) - 终端美化
- [Questionary](https://github.com/tmbo/questionary) - 交互式提示
- [Netmiko](https://github.com/ktbyers/netmiko) - SSH自动化
- [TextFSM](https://github.com/google/textfsm) - 文本解析
- [ntc-templates](https://github.com/networktocode/ntc-templates) - 解析模板

## 📧 联系方式

- 问题反馈: [GitHub Issues](https://github.com/netops-toolkit/netops-toolkit/issues)
- 邮件: netops@example.com

---

⭐ 如果这个项目对你有帮助,请给个Star支持一下!
