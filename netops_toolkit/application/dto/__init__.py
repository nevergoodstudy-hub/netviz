"""
数据传输对象
"""

from netops_toolkit.application.dto.device_dto import (
    DeviceDTO,
    DeviceDetailDTO,
    DeviceFilterDTO,
    DeviceGroupDTO,
)
from netops_toolkit.application.dto.network_dto import (
    PingBatchResponseDTO,
    PingRequestDTO,
    PingResultDTO,
    PortScanBatchResponseDTO,
    PortScanRequestDTO,
    PortScanResultDTO,
    SSHBatchResponseDTO,
    SSHCommandRequestDTO,
    SSHCommandResultDTO,
)

__all__ = [
    "DeviceDTO",
    "DeviceDetailDTO",
    "DeviceGroupDTO",
    "DeviceFilterDTO",
    "PingRequestDTO",
    "PingResultDTO",
    "PingBatchResponseDTO",
    "PortScanRequestDTO",
    "PortScanResultDTO",
    "PortScanBatchResponseDTO",
    "SSHCommandRequestDTO",
    "SSHCommandResultDTO",
    "SSHBatchResponseDTO",
]
