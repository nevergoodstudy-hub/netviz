# NetOps Toolkit - 网络工程实施及测试工具集

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

面向网络工程师的多功能CLI工具箱,集成网络实施、测试、巡检、诊断功能于一体。

## ✨ 核心特性

- 🎨 **美观易用**  - 基于Rich/Questionary的现代化TUI界面
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

## 📦 安装

### 方式1: 从源码安装
```powershell
# 克隆仓库
git clone https://github.com/netops-toolkit/netops-toolkit.git
cd netops-toolkit

# 创建虚拟环境 (推荐)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/MacOS

# 安装依赖
pip install -r requirements.txt

# 可编辑模式安装
pip install -e .
```

### 方式2: 使用pip (未来)
```powershell
pip install netops-toolkit
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
netops ping 192.168.1.1

# 批量Ping
netops ping --targets 192.168.1.1,192.168.1.2,192.168.1.3

# SSH批量命令执行
netops ssh-batch --group core_switches --command "show version"
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

## 🗺️ 路线图

- [x] v1.0 - 核心框架与基础插件
- [ ] v1.5 - Web UI界面
- [ ] v2.0 - Ansible集成
- [ ] v2.5 - SNMP监控
- [ ] v3.0 - AI故障预测

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
