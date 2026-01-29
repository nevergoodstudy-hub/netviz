"""
SSL证书检查插件

检查HTTPS网站SSL证书的有效期、颁发者、过期时间等信息。
"""

import socket
import ssl
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netops_toolkit.core.logger import get_logger
from netops_toolkit.plugins import (
    Plugin,
    PluginCategory,
    PluginResult,
    ResultStatus,
    ParamSpec,
    register_plugin,
)
from netops_toolkit.ui.theme import console
from netops_toolkit.ui.components import create_summary_panel

logger = get_logger(__name__)


@register_plugin
class SslCheckerPlugin(Plugin):
    """SSL证书检查插件"""
    
    name = "SSL证书检查"
    category = PluginCategory.UTILS
    description = "检查HTTPS网站SSL证书信息"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [
            ParamSpec(
                name="host",
                param_type=str,
                description="目标主机名",
                required=True,
            ),
            ParamSpec(
                name="port",
                param_type=int,
                description="端口",
                required=False,
                default=443,
            ),
            ParamSpec(
                name="timeout",
                param_type=float,
                description="超时时间(秒)",
                required=False,
                default=10.0,
            ),
        ]
    
    def run(
        self,
        host: str,
        port: int = 443,
        timeout: float = 10.0,
        **kwargs,
    ) -> PluginResult:
        """检查SSL证书"""
        start_time = datetime.now()
        
        console.print(f"[cyan]正在检查 {host}:{port} 的SSL证书...[/cyan]\n")
        
        try:
            cert_info = self._get_certificate_info(host, port, timeout)
        except Exception as e:
            return PluginResult(
                status=ResultStatus.ERROR,
                message=f"无法获取证书: {e}",
                start_time=start_time,
                end_time=datetime.now(),
            )
        
        # 显示证书信息
        self._display_certificate(cert_info, host, port)
        
        # 检查证书状态
        days_remaining = cert_info.get("days_remaining", 0)
        
        if days_remaining < 0:
            status = ResultStatus.FAILED
            message = f"证书已过期 {abs(days_remaining)} 天!"
        elif days_remaining < 30:
            status = ResultStatus.PARTIAL
            message = f"证书将在 {days_remaining} 天后过期,请尽快更新!"
        else:
            status = ResultStatus.SUCCESS
            message = f"证书有效,剩余 {days_remaining} 天"
        
        return PluginResult(
            status=status,
            message=message,
            data=cert_info,
            start_time=start_time,
            end_time=datetime.now(),
        )
    
    def _get_certificate_info(self, host: str, port: int, timeout: float) -> Dict[str, Any]:
        """获取SSL证书信息"""
        context = ssl.create_default_context()
        
        # 允许自签名证书
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssl_sock:
                cert = ssl_sock.getpeercert(binary_form=True)
                
                # 解析证书
                from ssl import DER_cert_to_PEM_cert
                pem_cert = DER_cert_to_PEM_cert(cert)
                
                # 使用 ssl 库解析
                cert_dict = ssl_sock.getpeercert()
                
                # 如果 getpeercert() 返回 None (自签名证书)
                # 使用 cryptography 库解析
                if cert_dict is None:
                    try:
                        from cryptography import x509
                        from cryptography.hazmat.backends import default_backend
                        
                        x509_cert = x509.load_der_x509_certificate(cert, default_backend())
                        
                        return self._parse_x509_cert(x509_cert, host)
                    except ImportError:
                        return {
                            "host": host,
                            "port": port,
                            "error": "无法解析自签名证书 (需要 cryptography 库)",
                            "is_valid": False,
                        }
                
                return self._parse_ssl_cert(cert_dict, host, port)
    
    def _parse_ssl_cert(self, cert: Dict, host: str, port: int) -> Dict[str, Any]:
        """解析SSL证书字典"""
        # 解析时间
        not_before = datetime.strptime(cert.get("notBefore", ""), "%b %d %H:%M:%S %Y %Z")
        not_after = datetime.strptime(cert.get("notAfter", ""), "%b %d %H:%M:%S %Y %Z")
        
        now = datetime.now()
        days_remaining = (not_after - now).days
        
        # 解析颁发者
        issuer = cert.get("issuer", ())
        issuer_dict = {}
        for item in issuer:
            for key, value in item:
                issuer_dict[key] = value
        
        # 解析主体
        subject = cert.get("subject", ())
        subject_dict = {}
        for item in subject:
            for key, value in item:
                subject_dict[key] = value
        
        # 解析SAN
        san_list = []
        for ext_type, ext_value in cert.get("subjectAltName", ()):
            san_list.append(f"{ext_type}: {ext_value}")
        
        return {
            "host": host,
            "port": port,
            "subject_cn": subject_dict.get("commonName", ""),
            "subject_org": subject_dict.get("organizationName", ""),
            "issuer_cn": issuer_dict.get("commonName", ""),
            "issuer_org": issuer_dict.get("organizationName", ""),
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "days_remaining": days_remaining,
            "serial_number": cert.get("serialNumber", ""),
            "san": san_list[:5],  # 只取前5个
            "is_valid": days_remaining > 0,
            "is_expiring_soon": 0 < days_remaining < 30,
        }
    
    def _parse_x509_cert(self, cert, host: str) -> Dict[str, Any]:
        """使用 cryptography 解析证书"""
        from cryptography.x509.oid import NameOID, ExtensionOID
        
        now = datetime.now()
        not_before = cert.not_valid_before
        not_after = cert.not_valid_after
        days_remaining = (not_after - now).days
        
        # 获取 CN
        subject_cn = ""
        try:
            subject_cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except:
            pass
        
        issuer_cn = ""
        try:
            issuer_cn = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        except:
            pass
        
        issuer_org = ""
        try:
            issuer_org = cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        except:
            pass
        
        # 获取 SAN
        san_list = []
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for name in san_ext.value:
                san_list.append(str(name.value))
        except:
            pass
        
        return {
            "host": host,
            "subject_cn": subject_cn,
            "issuer_cn": issuer_cn,
            "issuer_org": issuer_org,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "days_remaining": days_remaining,
            "serial_number": str(cert.serial_number),
            "san": san_list[:5],
            "is_valid": days_remaining > 0,
            "is_expiring_soon": 0 < days_remaining < 30,
        }
    
    def _display_certificate(self, info: Dict, host: str, port: int) -> None:
        """显示证书信息"""
        # 状态颜色
        days = info.get("days_remaining", 0)
        if days < 0:
            status_color = "red"
            status_text = f"[red]已过期 {abs(days)} 天[/red]"
        elif days < 30:
            status_color = "yellow"
            status_text = f"[yellow]即将过期 ({days}天)[/yellow]"
        else:
            status_color = "green"
            status_text = f"[green]有效 ({days}天)[/green]"
        
        # 显示信息
        display_info = {
            "主机": f"{host}:{port}",
            "状态": status_text,
            "主体(CN)": info.get("subject_cn", "-"),
            "颁发者(CN)": info.get("issuer_cn", "-"),
            "颁发机构": info.get("issuer_org", "-"),
            "有效期起始": info.get("not_before", "-"),
            "有效期结束": info.get("not_after", "-"),
            "剩余天数": f"{days} 天",
            "序列号": info.get("serial_number", "-")[:30] + "..." if len(str(info.get("serial_number", ""))) > 30 else info.get("serial_number", "-"),
        }
        
        console.print(create_summary_panel(
            f"SSL证书信息: {host}",
            display_info,
            timestamp=datetime.now()
        ))
        
        # 显示 SAN
        san_list = info.get("san", [])
        if san_list:
            console.print("\n[cyan]Subject Alternative Names (SAN):[/cyan]")
            for san in san_list:
                console.print(f"  • {san}")
