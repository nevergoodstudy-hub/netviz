# NetOps Toolkit 架构迁移指南

> **版本**: 1.0 → 2.0  
> **日期**: 2026-02-08

---

## 一、概述

NetOps Toolkit 2.0 采用**清洁架构 (Clean Architecture)** 进行了全面重构。本指南帮助开发者理解新旧架构差异，并提供逐步迁移路径。

### 核心变化

- **分层架构**: Domain → Application → Infrastructure → Presentation 四层分离
- **依赖注入**: 使用 `dependency-injector` 框架替代全局单例
- **Pydantic v2**: 实体和 DTO 使用 Pydantic BaseModel，自动验证
- **全异步**: Web API 层全面使用 `asyncio` 替代阻塞调用
- **插件重构**: 简化插件基类，引入泛型输入/输出

---

## 二、目录结构对照

### 旧结构 → 新结构

```
旧                              新
├── cli.py                     → presentation/cli/
├── plugins/base.py            → plugins/core/base.py (简化的 Plugin[TInput, TOutput])
├── plugins/diagnostics/       → plugins/diagnostics/ (不变)
├── services/                  → application/commands/ + application/queries/
├── config/device_inventory.py → infrastructure/persistence/yaml_device_repository.py
├── config/settings.yaml       → infrastructure/config/settings.py (Pydantic Settings)
├── utils/                     → domain/validators.py + infrastructure/security/
└── web/app.py                 → presentation/api/ (路由拆分到 routers/)
```

### 新增目录

```
netops_toolkit/
├── domain/
│   ├── entities/        # Pydantic 领域实体 (Device, Credential, ScanResult)
│   ├── services/        # 纯业务逻辑函数
│   ├── events/          # 领域事件
│   ├── validators.py    # IP/Port/Hostname 验证
│   └── exceptions.py    # ~30 种领域异常
├── application/
│   ├── commands/        # 写操作 (PingCommand, SSHBatchCommand)
│   ├── queries/         # 读操作 (DeviceQuery)
│   ├── dto/             # 数据传输对象
│   └── interfaces/      # 抽象接口 (Repository, Service)
├── infrastructure/
│   ├── persistence/     # YamlDeviceRepository
│   ├── network/         # AsyncPingService, AsyncSSHService
│   ├── security/        # FernetCredentialStore, SensitiveDataMasker
│   └── config/          # Pydantic Settings v2
├── presentation/
│   ├── api/schemas/     # API 请求/响应 Schema
│   └── api/middleware/  # 统一错误处理中间件
├── plugins/
│   ├── core/            # 插件框架 (base, registry, loader, executor)
│   ├── builtin/         # 内置插件
│   └── contrib/         # 社区插件
└── container.py         # DI 容器
```

---

## 三、迁移步骤

### 3.1 配置迁移

**旧方式** — 直接读取 YAML:
```python
# 旧
config = yaml.safe_load(open("config/settings.yaml"))
timeout = config.get("network", {}).get("ssh_timeout", 30)
```

**新方式** — Pydantic Settings:
```python
# 新: infrastructure/config/settings.py
from netops_toolkit.infrastructure.config.settings import get_settings

settings = get_settings()
timeout = settings.network.ssh_timeout  # 自动验证、类型安全
```

### 3.2 设备管理迁移

**旧方式** — DeviceInventory:
```python
# 旧
from netops_toolkit.config.device_inventory import DeviceInventory
inventory = DeviceInventory(Path("config/devices.yaml"))
devices = list(inventory)
```

**新方式** — Repository 模式:
```python
# 新: 通过 DI 容器注入
from netops_toolkit.infrastructure.persistence import YamlDeviceRepository

repo = YamlDeviceRepository(config_path=Path("config/devices.yaml"))
devices = repo.list_all()
device = repo.get_by_name("router-01")
```

### 3.3 凭证管理迁移

**旧方式** — 环境变量直接读取:
```python
# 旧
password = os.getenv("NETOPS_PASSWORD", "")
```

**新方式** — 加密凭证存储:
```python
# 新
from netops_toolkit.infrastructure.security import FernetCredentialStore
from netops_toolkit.domain.entities.credential import Credential

store = FernetCredentialStore()
store.store(Credential(name="default", username="admin", password="secret"))
cred = store.retrieve("default")
```

### 3.4 插件迁移

**旧方式** — 复杂基类:
```python
# 旧
class MyPlugin(Plugin):
    name = "my_plugin"
    def validate_dependencies(self): ...
    def get_required_params(self): ...
    def run(self, **kwargs): ...
```

**新方式** — 泛型基类 + Pydantic 输入/输出:
```python
# 新
from pydantic import BaseModel
from netops_toolkit.plugins.core.base import Plugin, PluginMetadata
from netops_toolkit.plugins.core.registry import register

class MyInput(BaseModel):
    target: str

class MyOutput(BaseModel):
    result: str

@register
class MyPlugin(Plugin[MyInput, MyOutput]):
    metadata = PluginMetadata(name="my_plugin", category="utils")

    async def execute(self, input: MyInput) -> MyOutput:
        return MyOutput(result=f"done: {input.target}")
```

### 3.5 异常处理迁移

**旧方式** — 通用 Exception:
```python
# 旧
raise Exception("设备未找到")
```

**新方式** — 领域异常:
```python
# 新
from netops_toolkit.domain.exceptions import DeviceNotFoundError
raise DeviceNotFoundError("router-01")
```

所有领域异常定义在 `domain/exceptions.py`，包括:
- `InvalidIPAddressError`, `InvalidPortError`, `InvalidHostnameError`
- `DeviceNotFoundError`, `DeviceConnectionError`
- `CredentialError`, `EncryptionError`
- `PluginNotFoundError`, `PluginExecutionError`
- `CommandInjectionError`
- 等 (~30 种)

### 3.6 Web API 迁移

**旧方式** — 阻塞 subprocess:
```python
# 旧: web/app.py
result = subprocess.run(cmd, capture_output=True, timeout=3)
```

**新方式** — 异步 subprocess:
```python
# 新: 使用 asyncio.create_subprocess_exec
proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.DEVNULL,
    stderr=asyncio.subprocess.DEVNULL,
)
await asyncio.wait_for(proc.wait(), timeout=3.0)
```

---

## 四、依赖注入使用

### 容器配置

```python
from netops_toolkit.container import Container

container = Container()
# 使用容器获取服务
ping_service = container.ping_service()
credential_store = container.credential_store()
```

### 在 CLI/API 中使用

```python
from dependency_injector.wiring import inject, Provide

@inject
def my_command(
    ping_service=Provide[Container.ping_service],
):
    result = await ping_service.ping("10.0.0.1")
```

---

## 五、测试迁移

### 新增测试位置

```
tests/
├── test_domain/
│   ├── test_entities.py       # 领域实体测试
│   ├── test_validators.py     # 验证器测试
│   ├── test_exceptions.py     # 异常测试
│   ├── test_services.py       # 领域服务测试
│   └── test_events.py         # 领域事件测试
├── test_infrastructure/
│   └── test_audit_log_enhancer.py  # 脱敏器测试
└── ...
```

### 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 仅领域层
python -m pytest tests/test_domain/ -v

# 仅基础设施层
python -m pytest tests/test_infrastructure/ -v
```

---

## 六、审计日志增强

### 敏感信息自动脱敏

```python
from netops_toolkit.infrastructure.security import (
    SensitiveDataMasker,
    AuditLogEnhancer,
    create_loguru_filter,
)

# 文本脱敏
masker = SensitiveDataMasker()
safe = masker.mask_text("password=admin123")  # "password=******"

# 字典脱敏
safe_dict = masker.mask_dict({"password": "secret", "host": "10.0.0.1"})

# loguru 集成
from loguru import logger
logger.add("app.log", filter=create_loguru_filter())
```

---

## 七、兼容性说明

- 旧的 `plugins/` 目录下的插件 (diagnostics, scanning, utils 等) **保持不变**，仍然可以正常使用
- `services/` 目录下的服务 (audit_service, scheduler_service 等) **保持不变**
- `config/settings.yaml` 仍然被读取，新的 Pydantic Settings 作为包装层
- 新老代码可以共存，建议逐步迁移

---

## 八、依赖变更

`pyproject.toml` 新增依赖:

```toml
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "dependency-injector>=4.40",
    "httpx>=0.25",
    "pytest-asyncio>=0.23",
]
```

安装:
```bash
pip install -e ".[dev]"
```
