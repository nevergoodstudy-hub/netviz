"""
SSH连接工具模块

封装基于Netmiko的SSH连接和常用操作。
"""

from typing import Any, Dict, List, Optional
import time

try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False

from netops_toolkit.core.logger import get_logger
from netops_toolkit.utils.network_utils import retry_on_exception

logger = get_logger(__name__)


class SSHConnection:
    """SSH连接封装类"""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: str = "cisco_ios",
        port: int = 22,
        secret: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        初始化SSH连接
        
        Args:
            host: 目标主机
            username: 用户名
            password: 密码
            device_type: 设备类型 (netmiko格式)
            port: SSH端口
            secret: enable密码
            timeout: 连接超时
        """
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.secret = secret
        self.timeout = timeout
        self.connection = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        建立SSH连接
        
        Returns:
            True表示成功
        """
        if not NETMIKO_AVAILABLE:
            logger.error("Netmiko库未安装")
            return False
        
        try:
            device_params = {
                "device_type": self.device_type,
                "host": self.host,
                "username": self.username,
                "password": self.password,
                "port": self.port,
                "timeout": self.timeout,
                "session_timeout": self.timeout,
            }
            
            if self.secret:
                device_params["secret"] = self.secret
            
            logger.debug(f"正在连接到 {self.host}...")
            self.connection = ConnectHandler(**device_params)
            
            # 如果有enable密码,进入特权模式
            if self.secret and self.device_type.startswith("cisco"):
                self.connection.enable()
            
            self._connected = True
            logger.debug(f"已连接到 {self.host}")
            return True
            
        except NetmikoAuthenticationException as e:
            logger.error(f"认证失败 {self.host}: {e}")
            return False
        except NetmikoTimeoutException as e:
            logger.error(f"连接超时 {self.host}: {e}")
            return False
        except Exception as e:
            logger.error(f"连接失败 {self.host}: {e}")
            return False
    
    def execute_command(
        self,
        command: str,
        expect_string: Optional[str] = None,
    ) -> Optional[str]:
        """
        执行单个命令
        
        Args:
            command: 命令字符串
            expect_string: 期望的提示符
            
        Returns:
            命令输出,失败返回None
        """
        if not self._connected or not self.connection:
            logger.error(f"未连接到 {self.host}")
            return None
        
        try:
            logger.debug(f"执行命令: {command}")
            output = self.connection.send_command(
                command,
                expect_string=expect_string,
            )
            return output
        except Exception as e:
            logger.error(f"命令执行失败 {self.host}: {e}")
            return None
    
    def execute_commands(
        self,
        commands: List[str],
    ) -> Dict[str, str]:
        """
        执行多个命令
        
        Args:
            commands: 命令列表
            
        Returns:
            {命令: 输出} 字典
        """
        results = {}
        
        for command in commands:
            output = self.execute_command(command)
            results[command] = output if output is not None else ""
        
        return results
    
    def execute_config_commands(
        self,
        commands: List[str],
    ) -> Optional[str]:
        """
        执行配置命令
        
        Args:
            commands: 配置命令列表
            
        Returns:
            输出结果
        """
        if not self._connected or not self.connection:
            logger.error(f"未连接到 {self.host}")
            return None
        
        try:
            output = self.connection.send_config_set(commands)
            return output
        except Exception as e:
            logger.error(f"配置命令执行失败 {self.host}: {e}")
            return None
    
    def get_config(self, config_type: str = "running") -> Optional[str]:
        """
        获取设备配置
        
        Args:
            config_type: 配置类型 (running, startup)
            
        Returns:
            配置内容
        """
        if not self._connected or not self.connection:
            logger.error(f"未连接到 {self.host}")
            return None
        
        try:
            # 根据设备类型选择命令
            if self.device_type.startswith("cisco"):
                command = f"show {config_type}-config"
            elif self.device_type.startswith("huawei"):
                command = "display current-configuration"
            elif self.device_type.startswith("juniper"):
                command = "show configuration"
            else:
                command = f"show {config_type}-config"
            
            config = self.execute_command(command)
            return config
        except Exception as e:
            logger.error(f"获取配置失败 {self.host}: {e}")
            return None
    
    def save_config(self) -> bool:
        """
        保存配置
        
        Returns:
            True表示成功
        """
        if not self._connected or not self.connection:
            logger.error(f"未连接到 {self.host}")
            return False
        
        try:
            self.connection.save_config()
            return True
        except Exception as e:
            logger.error(f"保存配置失败 {self.host}: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        if self.connection:
            try:
                self.connection.disconnect()
                self._connected = False
                logger.debug(f"已断开 {self.host}")
            except Exception as e:
                logger.debug(f"断开连接时出错 {self.host}: {e}")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and self.connection is not None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
        return False


def check_netmiko_available() -> bool:
    """检查Netmiko是否可用"""
    return NETMIKO_AVAILABLE


def create_ssh_connection(
    host: str,
    username: str,
    password: str,
    device_type: str = "cisco_ios",
    **kwargs
) -> Optional[SSHConnection]:
    """
    创建SSH连接的便捷函数
    
    Args:
        host: 主机地址
        username: 用户名
        password: 密码
        device_type: 设备类型
        **kwargs: 其他参数
        
    Returns:
        SSH连接对象
    """
    if not NETMIKO_AVAILABLE:
        logger.error("Netmiko库未安装, 请运行: pip install netmiko")
        return None
    
    conn = SSHConnection(
        host=host,
        username=username,
        password=password,
        device_type=device_type,
        **kwargs
    )
    
    if conn.connect():
        return conn
    else:
        return None


__all__ = [
    "SSHConnection",
    "check_netmiko_available",
    "create_ssh_connection",
]
