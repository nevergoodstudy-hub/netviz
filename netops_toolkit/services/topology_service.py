"""NetOps Toolkit - 拓扑可视化服务

支持功能:
- 从设备清单构建网络拓扑图
- ASCII/Unicode 文本渲染
- 多种布局算法
- 设备分组和层级展示
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# NetworkX 可选导入
NETWORKX_AVAILABLE = False
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    pass


class NodeType(Enum):
    """节点类型"""

    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    SERVER = "server"
    WORKSTATION = "workstation"
    CLOUD = "cloud"
    UNKNOWN = "unknown"


class LayoutType(Enum):
    """布局类型"""

    HIERARCHICAL = "hierarchical"   # 层级布局
    CIRCULAR = "circular"           # 圆形布局
    SPRING = "spring"               # 弹簧布局
    TREE = "tree"                   # 树形布局


@dataclass
class TopologyNode:
    """拓扑节点"""

    id: str
    name: str
    node_type: NodeType = NodeType.UNKNOWN
    ip: str = ""
    group: str = ""
    layer: int = 0  # 层级 (0=核心, 1=分发, 2=接入, 3=终端)
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class TopologyLink:
    """拓扑链路"""

    source: str
    target: str
    link_type: str = "ethernet"
    bandwidth: str = ""
    label: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


class TopologyBuilder:
    """拓扑构建器
    
    从设备清单和链路定义构建网络拓扑图
    """

    def __init__(self):
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx 未安装，请运行: pip install networkx")

        self._graph: nx.Graph = nx.Graph()
        self._nodes: dict[str, TopologyNode] = {}
        self._links: list[TopologyLink] = []

    def add_node(self, node: TopologyNode) -> None:
        """添加节点"""
        self._nodes[node.id] = node
        self._graph.add_node(
            node.id,
            label=node.name,
            node_type=node.node_type.value,
            ip=node.ip,
            group=node.group,
            layer=node.layer,
            **node.attributes,
        )

    def add_link(self, link: TopologyLink) -> None:
        """添加链路"""
        self._links.append(link)
        self._graph.add_edge(
            link.source,
            link.target,
            link_type=link.link_type,
            bandwidth=link.bandwidth,
            label=link.label,
            **link.attributes,
        )

    def add_nodes_from_inventory(self, devices: list[dict[str, Any]]) -> None:
        """从设备清单添加节点"""
        for dev in devices:
            # 推断节点类型
            name = dev.get('name', '').lower()
            dev.get('vendor', '').lower()

            if 'router' in name or 'rt' in name or 'rtr' in name:
                node_type = NodeType.ROUTER
                layer = 0
            elif 'firewall' in name or 'fw' in name:
                node_type = NodeType.FIREWALL
                layer = 0
            elif 'core' in name:
                node_type = NodeType.SWITCH
                layer = 0
            elif 'dist' in name or 'distribution' in name:
                node_type = NodeType.SWITCH
                layer = 1
            elif 'switch' in name or 'sw' in name:
                node_type = NodeType.SWITCH
                layer = 2
            elif 'server' in name or 'srv' in name:
                node_type = NodeType.SERVER
                layer = 3
            else:
                node_type = NodeType.UNKNOWN
                layer = 2

            node = TopologyNode(
                id=dev.get('name', dev.get('ip', '')),
                name=dev.get('name', ''),
                node_type=node_type,
                ip=dev.get('ip', ''),
                group=dev.get('group', ''),
                layer=layer,
            )
            self.add_node(node)

    def auto_connect_by_group(self) -> None:
        """按组自动连接节点（简单星型拓扑）"""
        # 按组分类
        groups: dict[str, list[str]] = {}
        for node_id, node in self._nodes.items():
            group = node.group or "default"
            if group not in groups:
                groups[group] = []
            groups[group].append(node_id)

        # 每组内部连接（第一个节点作为中心）
        for group, nodes in groups.items():
            if len(nodes) > 1:
                center = nodes[0]
                for other in nodes[1:]:
                    self.add_link(TopologyLink(
                        source=center,
                        target=other,
                        label=group,
                    ))

        # 组间连接（核心层连接）
        core_nodes = [nid for nid, n in self._nodes.items() if n.layer == 0]
        for i, node1 in enumerate(core_nodes):
            for node2 in core_nodes[i+1:]:
                self.add_link(TopologyLink(
                    source=node1,
                    target=node2,
                    link_type="trunk",
                ))

    def get_graph(self) -> nx.Graph:
        """获取 NetworkX 图对象"""
        return self._graph

    def get_nodes(self) -> dict[str, TopologyNode]:
        """获取所有节点"""
        return self._nodes.copy()

    def get_links(self) -> list[TopologyLink]:
        """获取所有链路"""
        return self._links.copy()


class ASCIITopologyRenderer:
    """ASCII 拓扑渲染器
    
    将 NetworkX 图渲染为 ASCII/Unicode 文本
    """

    # 节点图标
    NODE_ICONS = {
        NodeType.ROUTER: "[R]",
        NodeType.SWITCH: "[S]",
        NodeType.FIREWALL: "[F]",
        NodeType.SERVER: "[H]",
        NodeType.WORKSTATION: "[W]",
        NodeType.CLOUD: "[C]",
        NodeType.UNKNOWN: "[?]",
    }

    # Unicode 版本
    NODE_ICONS_UNICODE = {
        NodeType.ROUTER: "🔀",
        NodeType.SWITCH: "🔲",
        NodeType.FIREWALL: "🛡️",
        NodeType.SERVER: "🖥️",
        NodeType.WORKSTATION: "💻",
        NodeType.CLOUD: "☁️",
        NodeType.UNKNOWN: "❓",
    }

    def __init__(self, graph: nx.Graph, use_unicode: bool = True):
        """初始化渲染器
        
        Args:
            graph: NetworkX 图对象
            use_unicode: 是否使用 Unicode 字符

        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("networkx 未安装")

        self._graph = graph
        self._use_unicode = use_unicode
        self._icons = self.NODE_ICONS_UNICODE if use_unicode else self.NODE_ICONS

    def render_tree(self, root: str | None = None) -> str:
        """渲染为树形文本
        
        Args:
            root: 根节点ID，如果为None则自动选择
        
        Returns:
            ASCII树形文本

        """
        if not self._graph.nodes():
            return "(空拓扑)"

        # 选择根节点
        if root is None:
            # 选择度最高的节点作为根
            root = max(self._graph.nodes(), key=lambda n: self._graph.degree(n))

        # 使用 NetworkX 内置的文本输出
        io.StringIO()

        # 构建树形表示
        visited: set[str] = set()
        lines = []
        self._render_tree_recursive(root, "", True, visited, lines)

        return "\n".join(lines)

    def _render_tree_recursive(
        self,
        node: str,
        prefix: str,
        is_last: bool,
        visited: set[str],
        lines: list[str],
    ) -> None:
        """递归渲染树形结构"""
        if node in visited:
            return
        visited.add(node)

        # 获取节点信息
        node_data = self._graph.nodes.get(node, {})
        node_type = NodeType(node_data.get('node_type', 'unknown'))
        icon = self._icons.get(node_type, "[?]")
        label = node_data.get('label', node)
        ip = node_data.get('ip', '')

        # 构建节点显示
        if self._use_unicode:
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "
        else:
            connector = "+-- " if is_last else "+-- "
            extension = "    " if is_last else "|   "

        node_str = f"{prefix}{connector}{icon} {label}"
        if ip:
            node_str += f" ({ip})"
        lines.append(node_str)

        # 获取子节点（邻居中未访问的）
        neighbors = [n for n in self._graph.neighbors(node) if n not in visited]

        for i, neighbor in enumerate(neighbors):
            is_last_child = (i == len(neighbors) - 1)
            self._render_tree_recursive(
                neighbor,
                prefix + extension,
                is_last_child,
                visited,
                lines,
            )

    def render_hierarchical(self) -> str:
        """渲染为层级视图"""
        if not self._graph.nodes():
            return "(空拓扑)"

        # 按层级分组
        layers: dict[int, list[str]] = {}
        for node in self._graph.nodes():
            layer = self._graph.nodes[node].get('layer', 0)
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(node)

        lines = []
        layer_names = {0: "核心层", 1: "分发层", 2: "接入层", 3: "终端层"}

        # 计算最大宽度
        max(len(nodes) for nodes in layers.values()) if layers else 1

        for layer_num in sorted(layers.keys()):
            nodes = layers[layer_num]
            layer_name = layer_names.get(layer_num, f"Layer {layer_num}")

            # 层级标题
            if self._use_unicode:
                lines.append(f"{'═' * 60}")
                lines.append(f"  {layer_name}")
                lines.append(f"{'─' * 60}")
            else:
                lines.append(f"{'=' * 60}")
                lines.append(f"  {layer_name}")
                lines.append(f"{'-' * 60}")

            # 节点行
            node_strs = []
            for node in nodes:
                node_data = self._graph.nodes[node]
                node_type = NodeType(node_data.get('node_type', 'unknown'))
                icon = self._icons.get(node_type, "[?]")
                label = node_data.get('label', node)
                ip = node_data.get('ip', '')

                if ip:
                    node_strs.append(f"  {icon} {label} ({ip})")
                else:
                    node_strs.append(f"  {icon} {label}")

            lines.extend(node_strs)
            lines.append("")

        # 连接信息
        if self._use_unicode:
            lines.append(f"{'═' * 60}")
            lines.append("  链路连接")
            lines.append(f"{'─' * 60}")
        else:
            lines.append(f"{'=' * 60}")
            lines.append("  Links")
            lines.append(f"{'-' * 60}")

        for edge in self._graph.edges(data=True):
            src, dst, data = edge
            data.get('link_type', 'ethernet')
            label = data.get('label', '')

            src_label = self._graph.nodes[src].get('label', src)
            dst_label = self._graph.nodes[dst].get('label', dst)

            if self._use_unicode:
                conn = f"  {src_label} ←→ {dst_label}"
            else:
                conn = f"  {src_label} <-> {dst_label}"

            if label:
                conn += f" [{label}]"
            lines.append(conn)

        return "\n".join(lines)

    def render_simple_box(self) -> str:
        """渲染为简单盒子图"""
        if not self._graph.nodes():
            return "(空拓扑)"

        lines = []

        # 按组分类
        groups: dict[str, list[str]] = {}
        for node in self._graph.nodes():
            group = self._graph.nodes[node].get('group', 'default')
            if group not in groups:
                groups[group] = []
            groups[group].append(node)

        for group, nodes in groups.items():
            # 组标题
            if self._use_unicode:
                lines.append(f"┌{'─' * 40}┐")
                lines.append(f"│ {group:^38} │")
                lines.append(f"├{'─' * 40}┤")
            else:
                lines.append(f"+{'-' * 40}+")
                lines.append(f"| {group:^38} |")
                lines.append(f"+{'-' * 40}+")

            # 节点列表
            for node in nodes:
                node_data = self._graph.nodes[node]
                node_type = NodeType(node_data.get('node_type', 'unknown'))
                icon = self._icons.get(node_type, "[?]")
                label = node_data.get('label', node)
                ip = node_data.get('ip', '')

                content = f"{icon} {label}"
                if ip:
                    content += f" ({ip})"

                if self._use_unicode:
                    lines.append(f"│ {content:<38} │")
                else:
                    lines.append(f"| {content:<38} |")

            if self._use_unicode:
                lines.append(f"└{'─' * 40}┘")
            else:
                lines.append(f"+{'-' * 40}+")

            lines.append("")

        return "\n".join(lines)

    def render_matrix(self) -> str:
        """渲染为邻接矩阵"""
        if not self._graph.nodes():
            return "(空拓扑)"

        nodes = list(self._graph.nodes())
        len(nodes)

        # 创建标签
        labels = []
        for node in nodes:
            label = self._graph.nodes[node].get('label', node)
            # 截断长标签
            if len(label) > 10:
                label = label[:9] + "~"
            labels.append(label)

        # 计算列宽
        col_width = max(len(label_text) for label_text in labels) + 1

        lines = []

        # 表头
        header = " " * (col_width + 1) + "".join(
            f"{label_text:>{col_width}}" for label_text in labels
        )
        lines.append(header)
        lines.append("-" * len(header))

        # 矩阵行
        for i, node in enumerate(nodes):
            row = f"{labels[i]:>{col_width}} "
            for j, other in enumerate(nodes):
                if self._graph.has_edge(node, other):
                    if self._use_unicode:
                        row += f"{'●':>{col_width}}"
                    else:
                        row += f"{'X':>{col_width}}"
                else:
                    if self._use_unicode:
                        row += f"{'·':>{col_width}}"
                    else:
                        row += f"{'.':>{col_width}}"
            lines.append(row)

        return "\n".join(lines)


class TopologyService:
    """拓扑服务
    
    提供拓扑构建和渲染的统一接口
    """

    def __init__(self):
        if not NETWORKX_AVAILABLE:
            print("警告: networkx 未安装，拓扑功能不可用。请运行: pip install networkx")

        self._builder: TopologyBuilder | None = None

    def build_from_inventory(
        self,
        devices: list[dict[str, Any]] | None = None,
        auto_connect: bool = True,
    ) -> TopologyBuilder | None:
        """从设备清单构建拓扑
        
        Args:
            devices: 设备列表，如果为None则从配置加载
            auto_connect: 是否自动连接
        
        Returns:
            TopologyBuilder 实例

        """
        if not NETWORKX_AVAILABLE:
            return None

        # 如果未提供设备，尝试从配置加载
        if devices is None:
            devices = self._load_devices_from_config()

        if not devices:
            # 使用演示数据
            devices = self._get_demo_devices()

        self._builder = TopologyBuilder()
        self._builder.add_nodes_from_inventory(devices)

        if auto_connect:
            self._builder.auto_connect_by_group()

        return self._builder

    def _load_devices_from_config(self) -> list[dict[str, Any]]:
        """从配置文件加载设备"""
        devices = []
        try:
            from netops_toolkit.config.device_inventory import DeviceInventory

            config_paths = [
                Path("config/devices.yaml"),
                Path.cwd() / "config" / "devices.yaml",
            ]

            for path in config_paths:
                if path.exists():
                    inventory = DeviceInventory(path)
                    for device in inventory:
                        devices.append({
                            "name": device.name,
                            "ip": device.ip,
                            "vendor": device.vendor,
                            "group": device.group or "",
                        })
                    break
        except Exception:
            pass

        return devices

    def _get_demo_devices(self) -> list[dict[str, Any]]:
        """获取演示设备数据"""
        return [
            {"name": "RT-CORE-01", "ip": "192.168.1.1", "vendor": "cisco_ios", "group": "core"},
            {"name": "FW-MAIN-01", "ip": "192.168.1.254", "vendor": "cisco_asa", "group": "core"},
            {"name": "SW-CORE-01", "ip": "192.168.1.10", "vendor": "cisco_ios", "group": "core"},
            {"name": "SW-DIST-01", "ip": "192.168.1.20", "vendor": "cisco_ios", "group": "distribution"},
            {"name": "SW-DIST-02", "ip": "192.168.1.21", "vendor": "cisco_ios", "group": "distribution"},
            {"name": "SW-ACCESS-01", "ip": "192.168.1.30", "vendor": "cisco_ios", "group": "access"},
            {"name": "SW-ACCESS-02", "ip": "192.168.1.31", "vendor": "cisco_ios", "group": "access"},
            {"name": "SRV-WEB-01", "ip": "192.168.1.100", "vendor": "linux", "group": "servers"},
            {"name": "SRV-DB-01", "ip": "192.168.1.101", "vendor": "linux", "group": "servers"},
        ]

    def render(
        self,
        style: str = "hierarchical",
        use_unicode: bool = True,
    ) -> str:
        """渲染拓扑
        
        Args:
            style: 渲染样式 (hierarchical, tree, box, matrix)
            use_unicode: 是否使用 Unicode 字符
        
        Returns:
            渲染后的文本

        """
        if not NETWORKX_AVAILABLE:
            return "(networkx 未安装)"

        if self._builder is None:
            self.build_from_inventory()

        if self._builder is None:
            return "(无法构建拓扑)"

        renderer = ASCIITopologyRenderer(
            self._builder.get_graph(),
            use_unicode=use_unicode,
        )

        if style == "tree":
            return renderer.render_tree()
        elif style == "box":
            return renderer.render_simple_box()
        elif style == "matrix":
            return renderer.render_matrix()
        else:  # hierarchical
            return renderer.render_hierarchical()

    def get_summary(self) -> dict[str, Any]:
        """获取拓扑摘要"""
        if not NETWORKX_AVAILABLE or self._builder is None:
            return {"error": "拓扑未构建"}

        graph = self._builder.get_graph()

        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": nx.density(graph) if graph.number_of_nodes() > 1 else 0,
            "connected": nx.is_connected(graph) if graph.number_of_nodes() > 0 else False,
        }
