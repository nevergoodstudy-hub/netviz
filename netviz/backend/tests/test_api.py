"""
NetViz API 端点测试
"""

import pytest


class TestHealthEndpoints:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查端点"""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_info_endpoint(self, client):
        """测试系统信息端点"""
        response = await client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data


class TestPcapEndpoints:
    """PCAP 文件管理端点测试"""

    @pytest.mark.asyncio
    async def test_list_pcap_files(self, client):
        """测试列出 PCAP 文件"""
        response = await client.get("/api/pcap/list")
        assert response.status_code == 200
        data = response.json()
        # 返回 PcapListResponse 格式: {items: [], total: 0}
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_upload_invalid_file(self, client):
        """测试上传无效文件"""
        files = {"file": ("test.txt", b"not a pcap file", "text/plain")}
        response = await client.post("/api/pcap/upload", files=files)
        # 应该返回 400 或验证错误
        assert response.status_code in [400, 422]


class TestCaptureEndpoints:
    """网络捕获端点测试"""

    @pytest.mark.asyncio
    async def test_list_interfaces(self, client):
        """测试列出网络接口"""
        response = await client.get("/api/capture/interfaces")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAnalysisEndpoints:
    """分析端点测试"""

    @pytest.mark.asyncio
    async def test_list_alerts(self, client):
        """测试列出告警"""
        response = await client.get("/api/analysis/alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSettingsEndpoints:
    """设置端点测试"""

    @pytest.mark.asyncio
    async def test_get_ai_providers(self, client):
        """测试获取 AI 提供商列表"""
        response = await client.get("/api/settings/ai-providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # 应该有默认的提供商
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_settings(self, client):
        """测试获取设置 (端点为 /api/settings/)"""
        response = await client.get("/api/settings/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestAIEndpoints:
    """AI 分析端点测试"""

    @pytest.mark.asyncio
    async def test_ai_chat_endpoint_exists(self, client):
        """测试 AI 聊天端点存在"""
        # 发送测试请求，验证端点存在
        response = await client.post(
            "/api/ai/chat",
            json={"message": "test", "pcap_id": None}
        )
        # 端点存在应返回以下码之一
        # 200: 成功, 400: 请求无效, 422: 验证错误, 500: AI 未配置
        assert response.status_code in [200, 400, 422, 500]
