from unittest.mock import AsyncMock, Mock

import pytest

from app.profile.repository import SqlAlchemyProfileRepository


@pytest.mark.asyncio
async def test_upsert_profile_refreshes_server_generated_timestamps() -> None:
    session = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repository = SqlAlchemyProfileRepository(session)

    await repository.upsert_profile("user-1", {"age": 30})

    session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_disable_memory_refreshes_updated_timestamp() -> None:
    session = Mock()
    profile = type("Profile", (), {"memory_enabled": True})()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repository = SqlAlchemyProfileRepository(session)
    repository.upsert_profile = AsyncMock(return_value=profile)

    await repository.disable_memory("user-1")

    session.refresh.assert_awaited_once_with(profile)
