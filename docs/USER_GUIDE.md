# NetOps Toolkit 用户操作指南

## 目录
1. [快速入门](#快速入门)
2. [诊断工具](#诊断工具)
3. [网络扫描](#网络扫描)
4. [设备管理](#设备管理)
5. [性能测试](#性能测试)
6. [实用工具](#实用工具)
7. [交互模式](#交互模式)
8. [配置管理](#配置管理)

---

## 快速入门

### 安装

```bash
# 克隆仓库
git clone https://github.com/netops-toolkit/netops-toolkit.git
cd netops-toolkit

# 安装依赖
pip install -r requirements.txt

# 可编辑模式安装
pip install -e .
```

### 基本使用

```bash
# 查看帮助
netops --help

# 查看版本
netops --version

# 启动交互模式
netops
```

---

## 诊断工具

### ping - Ping连通性测试

测试与目标主机的网络连通性。

```bash
# 基本用法
netops ping 192.168.1.1

# 指定Ping次数
netops ping 192.168.1.1 -c 10

# 设置超时时间
netops ping 192.168.1.1 -t 2

# 批量Ping (逗号分隔)
netops ping 192.168.1.1,192.168.1.2,192.168.1.3

# CIDR批量Ping
netops ping 192.168.1.0/24

# 导出结果到JSON
netops ping 192.168.1.0/24 -o results.json
```

**参数说明:**
- `-c, --count`: Ping次数,默认4
- `-t, --timeout`: 超时时间(秒),默认2
- `-o, --output`: 导出文件路径

---

### traceroute - 路由追踪

追踪数据包到目标主机的路径。

```bash
# 基本用法
netops traceroute 8.8.8.8

# 追踪域名
netops traceroute www.baidu.com

# 设置最大跳数
netops traceroute 8.8.8.8 -m 15

# 设置超时时间
netops traceroute 8.8.8.8 -t 5

# 导出结果
netops traceroute 8.8.8.8 -o trace.json
```

**参数说明:**
- `-m, --max-hops`: 最大跳数,默认30
- `-t, --timeout`: 超时时间(秒),默认3
- `-o, --output`: 导出文件路径

---

### dns - DNS查询

进行DNS域名解析查询。

```bash
# 基本A记录查询
netops dns www.baidu.com

# 查询MX记录
netops dns baidu.com -t MX

# 查询NS记录
netops dns baidu.com -t NS

# 查询TXT记录
netops dns baidu.com -t TXT

# 反向DNS查询 (IP转域名)
netops dns 8.8.8.8

# 指定DNS服务器
netops dns www.google.com -s 8.8.8.8
```

**参数说明:**
- `-t, --type`: 记录类型 (A, AAAA, MX, CNAME, NS, TXT, SOA, PTR)
- `-s, --server`: 指定DNS服务器

**支持的记录类型:**
- `A`: IPv4地址记录
- `AAAA`: IPv6地址记录
- `MX`: 邮件交换记录
- `CNAME`: 别名记录
- `NS`: 名称服务器记录
- `TXT`: 文本记录
- `SOA`: 授权起始记录
- `PTR`: 反向DNS记录

---

## 网络扫描

### scan - 端口扫描

扫描目标主机的开放端口。

```bash
# 扫描常用端口
netops scan 192.168.1.1

# 扫描指定端口
netops scan 192.168.1.1 -p 22,80,443

# 扫描端口范围
netops scan 192.168.1.1 -p 1-1000

# 扫描全部端口
netops scan 192.168.1.1 -p 1-65535

# 设置并发线程数
netops scan 192.168.1.1 -p 1-10000 -T 100
```

**参数说明:**
- `-p, --ports`: 端口范围,默认1-1024
- `-T, --threads`: 并发线程数,默认50

---

### arp-scan - ARP扫描

扫描局域网中的活跃主机。

```bash
# 扫描整个子网
netops arp-scan 192.168.1.0/24

# 扫描较小范围
netops arp-scan 192.168.1.0/28

# 设置超时和并发
netops arp-scan 192.168.1.0/24 -t 2 -w 100
```

**参数说明:**
- `-t, --timeout`: 超时时间(秒),默认1
- `-w, --workers`: 并发数,默认50

**输出信息:**
- IP地址
- MAC地址
- 主机名(如果可解析)
- 厂商信息

---

## 设备管理

### ssh-batch - SSH批量执行

在多台设备上并发执行SSH命令。

```bash
# 对单台设备执行命令
netops ssh-batch -t 192.168.1.1 -c "show version" -u admin -p password

# 对多台设备执行命令
netops ssh-batch -t 192.168.1.1 -t 192.168.1.2 -c "show version" -u admin -p password

# 执行多条命令
netops ssh-batch -t 192.168.1.1 -c "show version" -c "show ip int brief" -u admin -p password

# 按设备组执行
netops ssh-batch -g core_switches -c "show running-config"

# 配置模式执行
netops ssh-batch -t 192.168.1.1 -c "interface gi0/0" -c "description Test" --config -u admin -p password

# 指定设备类型
netops ssh-batch -t 192.168.1.1 -c "display version" --device-type huawei_vrp -u admin -p password
```

**参数说明:**
- `-t, --target`: 目标设备IP (可多次指定)
- `-g, --group`: 设备组名称
- `-c, --command`: 执行的命令 (可多次指定)
- `-u, --username`: SSH用户名
- `-p, --password`: SSH密码
- `--device-type`: 设备类型,默认cisco_ios
- `-w, --workers`: 最大并发数,默认5
- `--timeout`: 连接超时(秒),默认30
- `--config`: 配置模式执行

**支持的设备类型:**
- `cisco_ios`: Cisco IOS
- `cisco_xe`: Cisco IOS-XE
- `cisco_nxos`: Cisco NX-OS
- `huawei_vrp`: Huawei VRP
- `juniper_junos`: Juniper Junos
- `arista_eos`: Arista EOS

---

### config-backup - 配置备份

备份网络设备配置。

```bash
# 备份单台设备
netops config-backup -t 192.168.1.1 -u admin -p password

# 备份多台设备
netops config-backup -t 192.168.1.1 -t 192.168.1.2 -u admin -p password

# 指定备份目录
netops config-backup -t 192.168.1.1 -d ./backups/core -u admin -p password

# 按设备组备份
netops config-backup -g core_switches -d ./backups

# 指定设备类型
netops config-backup -t 192.168.1.1 --device-type huawei_vrp -u admin -p password
```

**参数说明:**
- `-t, --target`: 目标设备IP
- `-g, --group`: 设备组名称
- `-u, --username`: SSH用户名
- `-p, --password`: SSH密码
- `-d, --dir`: 备份目录,默认./backups
- `--device-type`: 设备类型
- `-w, --workers`: 最大并发数
- `--timeout`: 连接超时

**备份文件结构:**
```
backups/
├── 192_168_1_1/
│   ├── config_20260123_120000.txt
│   ├── config_latest.txt
│   └── metadata.json
└── 192_168_1_2/
    ├── config_20260123_120000.txt
    └── ...
```

---

### config-diff - 配置对比

对比两个配置文件的差异。

```bash
# 基本对比
netops config-diff config1.txt config2.txt

# 设置上下文行数
netops config-diff config1.txt config2.txt -c 5

# 忽略空白字符
netops config-diff config1.txt config2.txt --ignore-ws

# 忽略注释行
netops config-diff config1.txt config2.txt --ignore-comments
```

**参数说明:**
- `-c, --context`: 上下文行数,默认3
- `--ignore-ws`: 忽略空白字符
- `--ignore-comments`: 忽略注释行

---

## 性能测试

### quality - 网络质量测试

综合测试网络延迟、抖动、丢包率。

```bash
# 基本测试
netops quality 8.8.8.8

# 指定测试次数
netops quality 8.8.8.8 -c 100

# 调整测试间隔
netops quality 8.8.8.8 -c 50 -i 0.5

# 设置超时
netops quality 8.8.8.8 -t 5
```

**参数说明:**
- `-c, --count`: 测试次数,默认50
- `-i, --interval`: 测试间隔(秒),默认0.2
- `-t, --timeout`: 超时时间(秒),默认3

**输出指标:**
- 发送/接收数量
- 丢包率
- 最小/平均/最大延迟
- 延迟标准差
- 平均抖动
- 质量等级 (A-F)

**质量等级标准:**
| 等级 | 延迟 | 抖动 | 丢包 |
|------|------|------|------|
| A (优秀) | <30ms | <5ms | <1% |
| B (良好) | <50ms | <10ms | <3% |
| C (一般) | <100ms | <20ms | <5% |
| D (较差) | <200ms | <50ms | <10% |
| F (很差) | >200ms | >50ms | >10% |

---

### speedtest - 带宽测速

测试网络上下行带宽。

```bash
# 基本测速
netops speedtest

# 简化输出
netops speedtest --simple

# 指定测速服务器
netops speedtest -s 12345

# 设置超时
netops speedtest -t 120
```

**参数说明:**
- `-s, --server`: 指定测速服务器ID
- `-t, --timeout`: 超时时间(秒),默认60
- `--simple`: 简化输出

**注意:** 需要安装speedtest-cli: `pip install speedtest-cli`

---

## 实用工具

### subnet - 子网计算器

计算子网的详细信息。

```bash
# 计算子网信息
netops subnet 192.168.1.0/24

# 其他示例
netops subnet 10.0.0.0/8
netops subnet 172.16.0.0/12
```

**输出信息:**
- 网络地址
- 广播地址
- 子网掩码
- 前缀长度
- 总地址数
- 可用主机数
- 第一个/最后一个可用主机

---

### ip-convert - IP格式转换

在不同IP格式间转换。

```bash
# 从点分十进制转换
netops ip-convert 192.168.1.1

# 从整数转换
netops ip-convert 3232235777

# 从十六进制转换
netops ip-convert 0xC0A80101
```

**支持的输入格式:**
- 点分十进制: 192.168.1.1
- 整数: 3232235777
- 十六进制: 0xC0A80101
- 二进制点分: 11000000.10101000.00000001.00000001

**输出格式:**
- 点分十进制
- 整数值
- 十六进制
- 二进制 (点分/完整)
- 八进制
- IP类别 (A/B/C/D/E)
- 地址类型 (私有/公网/环回等)

---

### mac-lookup - MAC地址查询

查询MAC地址对应的厂商信息。

```bash
# 标准格式
netops mac-lookup 00:0C:29:12:34:56

# Windows格式
netops mac-lookup 00-0C-29-12-34-56

# 无分隔符
netops mac-lookup 000C29123456

# Cisco格式
netops mac-lookup 000c.2912.3456
```

**输出信息:**
- 厂商名称
- OUI信息
- 多种格式转换
- MAC类型 (单播/多播, UAA/LAA)

---

### http - HTTP调试

测试HTTP/HTTPS请求。

```bash
# GET请求
netops http https://www.baidu.com

# 指定HTTP方法
netops http https://api.example.com -m POST

# 设置超时
netops http https://api.example.com -t 30

# 导出结果
netops http https://api.example.com -o result.json
```

**参数说明:**
- `-m, --method`: HTTP方法,默认GET
- `-t, --timeout`: 超时时间(秒),默认10
- `-o, --output`: 导出文件路径

---

### whois - WHOIS查询

查询域名或IP的注册信息。

```bash
# 域名查询
netops whois baidu.com
netops whois google.com

# IP查询
netops whois 8.8.8.8

# 设置超时
netops whois example.com -t 60
```

**参数说明:**
- `-t, --timeout`: 查询超时(秒),默认30

**注意:** Windows系统需要安装whois工具

---

## 交互模式

启动交互式菜单界面:

```bash
netops
# 或
python -m netops_toolkit
```

交互模式特点:
- 分类菜单导航
- 参数引导输入
- 实时结果展示
- 适合新手用户

---

## 配置管理

### 全局配置文件

**位置:** `config/settings.yaml`

```yaml
app:
  name: "NetOps Toolkit"
  log_level: "INFO"

network:
  ssh_timeout: 30
  connect_retry: 3
  
output:
  log_dir: "./logs"
  reports_dir: "./reports"

ui:
  show_banner: true
  color_theme: "default"

security:
  encrypt_passwords: true
```

### 设备清单

**位置:** `config/devices.yaml`

```yaml
groups:
  core_switches:
    vendor: "cisco_ios"
    credentials: "admin_cred"
    devices:
      - name: "SW-CORE-01"
        host: "192.168.1.10"
      - name: "SW-CORE-02"
        host: "192.168.1.11"

  access_switches:
    vendor: "huawei_vrp"
    devices:
      - name: "SW-ACC-01"
        host: "192.168.2.10"
        username: "admin"
```

### 凭证管理

**位置:** `config/secrets.yaml`

```yaml
credentials:
  admin_cred:
    username: "admin"
    password: "your_password"
    
  readonly_cred:
    username: "readonly"
    password: "readonly_password"
```

**注意:** secrets.yaml 不应提交到版本控制系统

---

## 常见问题

### Q: Ping测试需要管理员权限吗?
A: 在Windows上可能需要管理员权限才能发送ICMP包。

### Q: SSH连接超时怎么办?
A: 检查网络连通性、防火墙设置,或增加`--timeout`参数值。

### Q: 如何添加新的设备类型?
A: 参考Netmiko支持的设备类型列表,在`--device-type`参数中指定。

### Q: speedtest命令找不到?
A: 运行 `pip install speedtest-cli` 安装speedtest工具。

---

## 获取帮助

```bash
# 查看所有命令
netops --help

# 查看特定命令帮助
netops ping --help
netops ssh-batch --help
```

---

**版本:** v1.1.0  
**最后更新:** 2026-01-23
