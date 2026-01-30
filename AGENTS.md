# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

NetOps Toolkit is a Python CLI toolbox for network engineers, providing network diagnostics, device management, scanning, performance testing, and utility functions. The project supports Chinese (zh_CN) as the primary UI language.

## Build and Development Commands

```powershell
# Create virtual environment and install
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -e .

# Run the application
netops                          # TUI mode (default)
python -m netops_toolkit        # TUI mode
python -m netops_toolkit --cli  # CLI mode
python -m netops_toolkit --interactive  # Legacy interactive mode

# Run specific CLI command
netops ping 192.168.1.1 -c 4
netops scan 192.168.1.1 -p 80,443
netops dns www.example.com -t MX

# Linting and formatting
black --line-length 100 netops_toolkit/
ruff check netops_toolkit/
mypy netops_toolkit/

# Testing (pytest with coverage)
pytest tests/ -v --cov=netops_toolkit --cov-report=term-missing

# Run single test file
pytest tests/test_ping.py -v
```

## Architecture

### Plugin System

All functionality is implemented as plugins. Plugins use a registration pattern:

```python
from netops_toolkit.plugins import (
    Plugin,
    PluginCategory,
    PluginResult,
    ResultStatus,
    ParamSpec,
    register_plugin,
)

@register_plugin
class MyPlugin(Plugin):
    name = "插件名称"  # Display name (Chinese)
    category = PluginCategory.DIAGNOSTICS  # or DEVICE_MGMT, SCANNING, PERFORMANCE, UTILS
    description = "插件描述"
    version = "1.0.0"
    
    def validate_dependencies(self) -> bool:
        return True
    
    def get_required_params(self) -> List[ParamSpec]:
        return [ParamSpec(name="target", param_type=str, description="目标", required=True)]
    
    def run(self, **kwargs) -> PluginResult:
        # Implementation
        return PluginResult(status=ResultStatus.SUCCESS, message="完成", data={})
```

Plugin categories map to directories under `netops_toolkit/plugins/`:
- `diagnostics/` - Ping, Traceroute, DNS lookup
- `device_mgmt/` - SSH batch, Config backup/diff
- `scanning/` - Port scan, ARP scan
- `performance/` - Network quality, Bandwidth test
- `utils/` - HTTP debug, Subnet calc, IP converter, MAC lookup, WHOIS

### Entry Points

- `netops_toolkit/__main__.py` - Module entry point, routes to TUI/CLI/Interactive mode
- `netops_toolkit/cli.py` - Typer CLI application with all subcommands
- `netops_toolkit/tui/app.py` - Textual TUI application

### Key Modules

- `netops_toolkit/core/logger.py` - Loguru-based logging with audit support
- `netops_toolkit/config/config_manager.py` - YAML config loader with nested key access
- `netops_toolkit/config/device_inventory.py` - Device groups and credentials management
- `netops_toolkit/ui/theme.py` - Rich console theme and color scheme
- `netops_toolkit/ui/components.py` - Reusable Rich UI components (tables, panels, progress)
- `netops_toolkit/utils/network_utils.py` - IP validation, CIDR expansion, DNS utilities
- `netops_toolkit/utils/ssh_utils.py` - SSHConnection wrapper using Netmiko

### Configuration Files

- `config/settings.yaml` - Global app settings (timeouts, logging, UI options)
- `config/devices.yaml` - Device inventory with groups and connection parameters
- `config/secrets.yaml` - Encrypted credentials (use `secrets.yaml.example` as template)

## Code Style Conventions

- Line length: 100 characters (configured in pyproject.toml)
- Use Chinese for user-facing strings (messages, descriptions, menu items)
- Use English for code identifiers and docstrings
- Plugin display names should be concise Chinese phrases (e.g., "Ping测试", "端口扫描")
- All plugins must return `PluginResult` with appropriate `ResultStatus`

## Adding New CLI Commands

When adding a new CLI command to `cli.py`:
1. Create the plugin in the appropriate category directory
2. Add `@app.command()` decorated function in `cli.py`
3. Use `typer.Argument` and `typer.Option` for parameters
4. Import plugin dynamically inside the command function
5. Call `log_audit()` after execution for audit trail

## Dependencies

Core dependencies (always available):
- `typer` - CLI framework
- `rich` - Terminal formatting
- `textual` - TUI framework
- `questionary` - Interactive prompts
- `netmiko` - SSH to network devices
- `ping3` - ICMP ping (may fall back to system ping)
- `dnspython` - DNS queries
- `pyyaml` - Configuration files
- `loguru` - Logging
- `cryptography` - Password encryption

Optional (check availability before use):
- `scapy` - Packet manipulation (ARP scanning)
- `speedtest-cli` - Bandwidth testing
- `pandas`/`openpyxl` - Excel export
