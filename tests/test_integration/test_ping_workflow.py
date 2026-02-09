"""
集成测试: Ping 工作流

测试 PingCommand → PingService → PingResult 完整链路。
使用 Mock PingService 避免实际网络调用。
"""

import asyncio

import pytest
from unittest.mock import AsyncMock

from netops_toolkit.application.commands.network_commands import PingCommand
from netops_toolkit.application.dto.network_dto import PingRequestDTO
from netops_toolkit.domain.entities.scan_result import PingResult
from netops_toolkit.infrastructure.network.connection_pool import ConnectionPool


class TestPingCommandIntegration:
    """PingCommand 集成测试: 命令 → 服务 → DTO"""

    @pytest.fixture
    def mock_ping_service(self):
        """Mock PingService 返回预设结果"""
        service = AsyncMock()
        service.ping_batch.return_value = [
            PingResult(
                host="10.0.0.1",
                is_alive=True,
                avg_latency=5.0,
                packet_loss=0.0,
                packets_sent=4,
                packets_received=4,
            ),
            PingResult(
                host="10.0.0.2",
                is_alive=False,
                packet_loss=100.0,
                packets_sent=4,
                packets_received=0,
            ),
        ]
        return service

    @pytest.mark.asyncio
    async def test_ping_command_full_flow(self, mock_ping_service):
        """验证完整链路: PingCommand → PingService → PingBatchResponseDTO"""
        cmd = PingCommand(ping_service=mock_ping_service)
        request = PingRequestDTO(
            targets=["10.0.0.1", "10.0.0.2"],
            count=4,
            timeout=2.0,
        )

        result = await cmd.execute(request)

        # 验证命令调用了服务
        mock_ping_service.ping_batch.assert_called_once_with(
            hosts=["10.0.0.1", "10.0.0.2"],
            count=4,
            timeout=2.0,
            concurrency=50,
        )

        # 验证 DTO 聚合结果
        assert result.total == 2
        assert result.alive_count == 1
        assert result.dead_count == 1
        assert result.duration is not None
        assert result.duration >= 0

        # 验证各结果映射正确
        assert result.results[0].host == "10.0.0.1"
        assert result.results[0].is_alive is True
        assert result.results[0].avg_latency == 5.0
        assert result.results[1].host == "10.0.0.2"
        assert result.results[1].is_alive is False

    @pytest.mark.asyncio
    async def test_ping_command_empty_targets(self, mock_ping_service):
        """空结果集"""
        mock_ping_service.ping_batch.return_value = []
        cmd = PingCommand(ping_service=mock_ping_service)
        request = PingRequestDTO(targets=["10.0.0.1"])

        result = await cmd.execute(request)
        assert result.total == 0
        assert result.alive_count == 0


class TestConnectionPoolIntegration:
    """连接池集成测试"""

    @pytest.mark.asyncio
    async def test_pool_acquire_release(self):
        pool = ConnectionPool(max_connections=2)
        assert pool.available == 2

        async with pool.acquire():
            assert pool.available == 1
            assert pool.stats.active_connections == 1

        assert pool.available == 2
        assert pool.stats.total_acquired == 1
        assert pool.stats.total_released == 1

    @pytest.mark.asyncio
    async def test_pool_concurrent_limit(self):
        """测试并发上限"""
        pool = ConnectionPool(max_connections=2)
        acquired_count = 0

        async def _worker():
            nonlocal acquired_count
            async with pool.acquire():
                acquired_count += 1
                await asyncio.sleep(0.05)

        # 启动 3 个 worker，池大小为 2
        tasks = [asyncio.create_task(_worker()) for _ in range(3)]
        await asyncio.gather(*tasks)

        assert acquired_count == 3
        assert pool.stats.total_acquired == 3
        assert pool.stats.active_connections == 0

    @pytest.mark.asyncio
    async def test_pool_timeout(self):
        """测试获取连接超时"""
        pool = ConnectionPool(max_connections=1)

        async with pool.acquire():
            # 池满，第二次 acquire 应超时
            with pytest.raises(asyncio.TimeoutError):
                async with pool.acquire(timeout=0.05):
                    pass

        assert pool.stats.total_timeouts == 1


class TestPluginRegistration:
    """插件注册集成测试"""

    def test_builtin_ping_registered(self):
        """验证 PingPlugin 通过 @register 自动注册"""
        from netops_toolkit.plugins.core.registry import PluginRegistry

        # 导入 ping_plugin 会触发 @register
        import netops_toolkit.plugins.builtin.ping_plugin  # noqa: F401

        assert PluginRegistry.has("ping")
        plugin_cls = PluginRegistry.get("ping")
        assert plugin_cls.metadata.name == "ping"
        assert plugin_cls.metadata.category == "diagnostics"
