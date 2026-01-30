# NetOps Toolkit - 网络工程实施及测试工具集

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

面向网络工程师的多功能CLI工具箱,集成网络实施、测试、巡检、诊断功能于一体。

## ✨ 核心特性

- 🎨 **美观易用**  - 基于Rich/Questionary的现代化CLI界面
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
- Python 3.8 或更高版本

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

### 交互模式(推荐)
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

### 凭证管理 (config/secrets.yaml)
```yaml
credentials:
  admin_cred:
    username: "admin"
    password: "encrypted_password_here"
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

## 🗓️ 路线图

- [x] v1.0 - 核心框架与基础插件
- [x] v1.1 - 完整插件集 (15个插件)
- [x] v1.4 - **多系统支持** (Windows/Linux/macOS/BSD)
- [x] v1.6 - **工具增强** (导出/依赖管理/跨平台)
- [ ] v2.0 - Web UI界面
- [ ] v2.5 - Ansible集成
- [ ] v3.0 - SNMP监控
- [ ] v3.5 - AI故障预测

## 🆕 v1.6 更新日志 (2026-01-30)

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
