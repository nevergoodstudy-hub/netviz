"""
NetOps Toolkit 工具模块

提供各种通用工具函数。
"""

from .network_utils import (
    is_valid_ip,
    is_valid_network,
    expand_ip_range,
    is_valid_port,
    resolve_hostname,
    reverse_dns_lookup,
    get_network_info,
    retry_on_exception,
    parse_port_list,
    get_common_ports,
    COMMON_PORTS,
)

from .export_utils import (
    export_to_json,
    export_to_csv,
    format_table_data,
    generate_report_filename,
    save_report,
    dict_to_pretty_string,
    flatten_dict,
)

from .security_utils import (
    encrypt_string,
    decrypt_string,
    CredentialManager,
    mask_password,
)

__all__ = [
    # network_utils
    "is_valid_ip",
    "is_valid_network",
    "expand_ip_range",
    "is_valid_port",
    "resolve_hostname",
    "reverse_dns_lookup",
    "get_network_info",
    "retry_on_exception",
    "parse_port_list",
    "get_common_ports",
    "COMMON_PORTS",
    # export_utils
    "export_to_json",
    "export_to_csv",
    "format_table_data",
    "generate_report_filename",
    "save_report",
    "dict_to_pretty_string",
    "flatten_dict",
    # security_utils
    "encrypt_string",
    "decrypt_string",
    "CredentialManager",
    "mask_password",
]
