"""
领域异常模块

定义 NetOps Toolkit 的统一异常层次结构。
遵循原则:
- 所有异常继承自 Exception (非 BaseException)
- 提供结构化的错误信息 (code, message, details)
- 支持 to_dict() 序列化，便于 API 返回
- 异常名称以 Error 结尾
"""

from typing import Any, Dict, Optional


class NetOpsError(Exception):
    """
    NetOps Toolkit 基础异常类

    所有自定义异常的根类，提供统一的错误结构。

    Attributes:
        message: 人类可读的错误描述
        code: 机器可读的错误代码
        details: 附加错误上下文信息
    """

    def __init__(
        self,
        message: str = "an unexpected error occurred",
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典，便于 API 响应"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ==================== 验证相关异常 ====================


class ValidationError(NetOpsError):
    """输入验证错误"""

    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class InvalidIPAddressError(ValidationError):
    """无效的 IP 地址"""

    def __init__(self, value: str):
        super().__init__(f"invalid IP address: {value}", field="ip_address")


class InvalidCIDRError(ValidationError):
    """无效的 CIDR 格式"""

    def __init__(self, value: str):
        super().__init__(f"invalid CIDR notation: {value}", field="cidr")


class InvalidHostnameError(ValidationError):
    """无效的主机名"""

    def __init__(self, value: str):
        super().__init__(f"invalid hostname: {value}", field="hostname")


class InvalidPortError(ValidationError):
    """无效的端口号"""

    def __init__(self, value: int):
        super().__init__(f"port must be 1-65535, got {value}", field="port")


class InvalidCronExpressionError(ValidationError):
    """无效的 Cron 表达式"""

    def __init__(self, value: str):
        super().__init__(f"invalid cron expression: {value}", field="cron_expression")


# ==================== 设备相关异常 ====================


class DeviceError(NetOpsError):
    """设备操作相关错误的基类"""

    def __init__(
        self,
        message: str,
        code: str = "DEVICE_ERROR",
        device: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details or {}
        if device:
            _details["device"] = device
        super().__init__(message, code, _details)
        self.device = device


class DeviceConnectionError(DeviceError):
    """设备连接失败"""

    def __init__(self, device: str, reason: str = ""):
        msg = f"failed to connect to {device}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "CONNECTION_ERROR", device, {"reason": reason})


class DeviceAuthenticationError(DeviceError):
    """设备认证失败"""

    def __init__(self, device: str):
        super().__init__(
            f"authentication failed for {device}",
            "AUTH_ERROR",
            device,
        )


class DeviceTimeoutError(DeviceError):
    """设备操作超时"""

    def __init__(self, device: str, operation: str = "", timeout: float = 0):
        msg = f"operation timed out on {device}"
        if operation:
            msg = f"'{operation}' timed out on {device}"
        if timeout > 0:
            msg += f" after {timeout}s"
        super().__init__(
            msg,
            "TIMEOUT_ERROR",
            device,
            {"operation": operation, "timeout": timeout},
        )


class DeviceCommandError(DeviceError):
    """设备命令执行失败"""

    def __init__(self, device: str, command: str, output: str = ""):
        super().__init__(
            f"command failed on {device}: {command}",
            "COMMAND_ERROR",
            device,
            {"command": command, "output": output},
        )


class DeviceNotFoundError(DeviceError):
    """设备未找到"""

    def __init__(self, identifier: str):
        super().__init__(
            f"device not found: {identifier}",
            "DEVICE_NOT_FOUND",
            identifier,
        )


# ==================== 插件相关异常 ====================


class PluginError(NetOpsError):
    """插件相关错误的基类"""

    def __init__(
        self,
        message: str,
        code: str = "PLUGIN_ERROR",
        plugin_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        _details = details or {}
        if plugin_name:
            _details["plugin"] = plugin_name
        super().__init__(message, code, _details)
        self.plugin_name = plugin_name


class PluginNotFoundError(PluginError):
    """插件未找到"""

    def __init__(self, name: str):
        super().__init__(f"plugin '{name}' not found", "PLUGIN_NOT_FOUND", name)


class PluginInitializationError(PluginError):
    """插件初始化失败"""

    def __init__(self, name: str, reason: str = ""):
        msg = f"failed to initialize plugin '{name}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "PLUGIN_INIT_ERROR", name, {"reason": reason})


class PluginDependencyError(PluginError):
    """插件依赖缺失"""

    def __init__(self, name: str, missing_deps: list[str]):
        super().__init__(
            f"plugin '{name}' missing dependencies: {', '.join(missing_deps)}",
            "PLUGIN_DEPENDENCY_ERROR",
            name,
            {"missing_dependencies": missing_deps},
        )


class PluginExecutionError(PluginError):
    """插件执行失败"""

    def __init__(self, name: str, reason: str = ""):
        msg = f"plugin '{name}' execution failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "PLUGIN_EXECUTION_ERROR", name, {"reason": reason})


class PluginLoadError(PluginError):
    """插件加载失败"""

    def __init__(self, name: str, reason: str = ""):
        msg = f"failed to load plugin '{name}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, "PLUGIN_LOAD_ERROR", name, {"reason": reason})


# ==================== 配置相关异常 ====================


class ConfigurationError(NetOpsError):
    """配置相关错误"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, "CONFIG_ERROR", details)
        self.config_key = config_key


class ConfigFileNotFoundError(ConfigurationError):
    """配置文件不存在"""

    def __init__(self, path: str):
        super().__init__(f"configuration file not found: {path}")


class ConfigParseError(ConfigurationError):
    """配置文件解析失败"""

    def __init__(self, path: str, reason: str = ""):
        msg = f"failed to parse configuration: {path}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


# ==================== 安全相关异常 ====================


class SecurityError(NetOpsError):
    """安全相关错误的基类"""

    def __init__(
        self,
        message: str,
        code: str = "SECURITY_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class CredentialError(SecurityError):
    """凭证相关错误"""

    def __init__(self, message: str = "credential operation failed"):
        super().__init__(message, "CREDENTIAL_ERROR")


class CredentialNotFoundError(CredentialError):
    """凭证未找到"""

    def __init__(self, name: str):
        super().__init__(f"credential not found: {name}")


class CommandInjectionError(SecurityError):
    """检测到命令注入"""

    def __init__(self, argument: str):
        # 不在错误信息中暴露具体的危险字符
        super().__init__(
            "potentially dangerous characters detected in argument",
            "COMMAND_INJECTION",
            {"argument_length": len(argument)},
        )


class EncryptionError(SecurityError):
    """加密/解密操作失败"""

    def __init__(self, operation: str = "encryption"):
        super().__init__(f"{operation} operation failed", "ENCRYPTION_ERROR")


# ==================== 网络服务相关异常 ====================


class NetworkError(NetOpsError):
    """网络操作相关错误的基类"""

    def __init__(
        self,
        message: str,
        code: str = "NETWORK_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class DNSResolutionError(NetworkError):
    """DNS 解析失败"""

    def __init__(self, hostname: str):
        super().__init__(
            f"DNS resolution failed for {hostname}",
            "DNS_ERROR",
            {"hostname": hostname},
        )


class SSHConnectionError(NetworkError):
    """SSH 连接失败"""

    def __init__(self, host: str, port: int = 22, reason: str = ""):
        msg = f"SSH connection failed to {host}:{port}"
        if reason:
            msg += f": {reason}"
        super().__init__(
            msg,
            "SSH_ERROR",
            {"host": host, "port": port, "reason": reason},
        )


# ==================== 服务层异常 ====================


class ServiceError(NetOpsError):
    """服务层错误的基类"""

    def __init__(
        self,
        message: str,
        code: str = "SERVICE_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class AuditError(ServiceError):
    """审计服务错误"""

    def __init__(self, message: str = "audit operation failed"):
        super().__init__(message, "AUDIT_ERROR")


class SchedulerError(ServiceError):
    """调度服务错误"""

    def __init__(self, message: str = "scheduler operation failed"):
        super().__init__(message, "SCHEDULER_ERROR")


class ReportGenerationError(ServiceError):
    """报告生成错误"""

    def __init__(self, message: str = "report generation failed"):
        super().__init__(message, "REPORT_ERROR")


__all__ = [
    # 基础
    "NetOpsError",
    # 验证
    "ValidationError",
    "InvalidIPAddressError",
    "InvalidCIDRError",
    "InvalidHostnameError",
    "InvalidPortError",
    "InvalidCronExpressionError",
    # 设备
    "DeviceError",
    "DeviceConnectionError",
    "DeviceAuthenticationError",
    "DeviceTimeoutError",
    "DeviceCommandError",
    "DeviceNotFoundError",
    # 插件
    "PluginError",
    "PluginNotFoundError",
    "PluginInitializationError",
    "PluginDependencyError",
    "PluginExecutionError",
    "PluginLoadError",
    # 配置
    "ConfigurationError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    # 安全
    "SecurityError",
    "CredentialError",
    "CredentialNotFoundError",
    "CommandInjectionError",
    "EncryptionError",
    # 网络
    "NetworkError",
    "DNSResolutionError",
    "SSHConnectionError",
    # 服务
    "ServiceError",
    "AuditError",
    "SchedulerError",
    "ReportGenerationError",
]
