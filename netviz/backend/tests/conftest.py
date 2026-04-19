"""
NetViz 测试配置
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import Base, get_db
from app.core.config import settings
import app.core.secret_store as secret_store_module
from app.main import app


# 测试数据库 URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """创建测试数据库"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """创建测试客户端"""
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app, client=("127.0.0.1", 12345))
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolate_settings_encryption(monkeypatch, tmp_path):
    """为每个测试隔离设置加密密钥文件，避免污染工作区。"""
    monkeypatch.setattr(settings, "settings_encryption_key", None)
    monkeypatch.setattr(
        settings,
        "settings_encryption_key_file",
        tmp_path / "settings-encryption.key",
    )
    secret_store_module._generated_install_key.cache_clear()
    yield
    secret_store_module._generated_install_key.cache_clear()


@pytest.fixture
def sample_pcap_path():
    """示例 PCAP 文件路径"""
    test_data_dir = Path(__file__).parent / "data"
    test_data_dir.mkdir(exist_ok=True)
    return test_data_dir / "sample.pcap"
