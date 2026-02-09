"""
TopologyService 测试模块

测试覆盖:
- TopologyNode
- TopologyLink
- TopologyBuilder
- ASCIITopologyRenderer
"""

import pytest
from unittest.mock import Mock, patch


# 检查 networkx 是否可用
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class TestTopologyEnums:
    """测试拓扑相关枚举"""
    
    def test_node_type_import(self):
        """测试 NodeType 导入"""
        from netops_toolkit.services.topology_service import NodeType
        
        assert NodeType is not None
    
    def test_node_type_values(self):
        """测试 NodeType 值"""
        from netops_toolkit.services.topology_service import NodeType
        
        # 应该有常见的网络设备类型
        assert hasattr(NodeType, 'ROUTER')
        assert hasattr(NodeType, 'SWITCH')
    
    def test_layout_type_import(self):
        """测试 LayoutType 导入"""
        from netops_toolkit.services.topology_service import LayoutType
        
        assert LayoutType is not None
    
    def test_layout_type_values(self):
        """测试 LayoutType 值"""
        from netops_toolkit.services.topology_service import LayoutType
        
        # 应该有常见的布局类型
        assert hasattr(LayoutType, 'HIERARCHICAL')


class TestTopologyNode:
    """测试拓扑节点"""
    
    def test_topology_node_import(self):
        """测试导入"""
        from netops_toolkit.services.topology_service import TopologyNode
        
        assert TopologyNode is not None
    
    def test_topology_node_creation(self):
        """测试创建节点"""
        from netops_toolkit.services.topology_service import TopologyNode, NodeType
        
        node = TopologyNode(
            id="node1",
            name="Router1",
            node_type=NodeType.ROUTER
        )
        
        assert node.id == "node1"
        assert node.name == "Router1"
        assert node.node_type == NodeType.ROUTER


class TestTopologyLink:
    """测试拓扑链路"""
    
    def test_topology_link_import(self):
        """测试导入"""
        from netops_toolkit.services.topology_service import TopologyLink
        
        assert TopologyLink is not None
    
    def test_topology_link_creation(self):
        """测试创建链路"""
        from netops_toolkit.services.topology_service import TopologyLink
        
        link = TopologyLink(
            source="node1",
            target="node2"
        )
        
        assert link.source == "node1"
        assert link.target == "node2"


@pytest.mark.skipif(not NETWORKX_AVAILABLE, reason="networkx not installed")
class TestTopologyBuilder:
    """测试拓扑构建器"""
    
    def test_topology_builder_import(self):
        """测试导入"""
        from netops_toolkit.services.topology_service import TopologyBuilder
        
        assert TopologyBuilder is not None
    
    def test_topology_builder_creation(self):
        """测试创建"""
        from netops_toolkit.services.topology_service import TopologyBuilder
        
        builder = TopologyBuilder()
        assert builder is not None
    
    def test_add_node(self):
        """测试添加节点"""
        from netops_toolkit.services.topology_service import TopologyBuilder, TopologyNode, NodeType
        
        builder = TopologyBuilder()
        node = TopologyNode(
            id="node1",
            name="Router1",
            node_type=NodeType.ROUTER
        )
        
        builder.add_node(node)
        
        # 验证节点已添加
        nodes = builder.get_nodes()
        assert "node1" in nodes
    
    def test_add_link(self):
        """测试添加链路"""
        from netops_toolkit.services.topology_service import TopologyBuilder, TopologyNode, TopologyLink, NodeType
        
        builder = TopologyBuilder()
        
        # 添加两个节点
        node1 = TopologyNode(id="node1", name="Router1", node_type=NodeType.ROUTER)
        node2 = TopologyNode(id="node2", name="Switch1", node_type=NodeType.SWITCH)
        
        builder.add_node(node1)
        builder.add_node(node2)
        
        # 添加链路
        link = TopologyLink(source="node1", target="node2")
        builder.add_link(link)
        
        # 验证链路已添加
        links = builder.get_links()
        assert len(links) > 0


class TestASCIITopologyRenderer:
    """测试 ASCII 拓扑渲染器"""
    
    def test_renderer_import(self):
        """测试导入"""
        from netops_toolkit.services.topology_service import ASCIITopologyRenderer
        
        assert ASCIITopologyRenderer is not None
