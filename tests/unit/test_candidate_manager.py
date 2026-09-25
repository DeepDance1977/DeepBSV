import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from deepbsv.core.candidate_manager import CandidateManager
from deepbsv.models.candidate import MiningCandidate
from deepbsv.rpc.exceptions import BSVRPCConnectionError
from tests.mocks.rpc_responses import VALID_GETMININGCANDIDATE_RESPONSE


@pytest.fixture
def sample_candidate() -> MiningCandidate:
    return MiningCandidate.model_validate(VALID_GETMININGCANDIDATE_RESPONSE)


@pytest.fixture
def mock_rpc_client(sample_candidate) -> MagicMock:
    client = MagicMock()
    client.get_mining_candidate = AsyncMock(return_value=sample_candidate)
    return client


@pytest.mark.asyncio
async def test_fetch_and_update_new_candidate(mock_rpc_client, sample_candidate):
    manager = CandidateManager(mock_rpc_client)
    callback_mock = AsyncMock()
    manager.subscribe(callback_mock)

    candidate = await manager.fetch_and_update()

    assert candidate == sample_candidate
    assert manager.current_candidate == sample_candidate
    callback_mock.assert_called_once_with(sample_candidate)


@pytest.mark.asyncio
async def test_fetch_and_update_duplicate_candidate(mock_rpc_client, sample_candidate):
    manager = CandidateManager(mock_rpc_client)
    callback_mock = AsyncMock()
    manager.subscribe(callback_mock)

    # First fetch -> notifies subscriber
    await manager.fetch_and_update()
    assert callback_mock.call_count == 1

    # Second fetch with identical candidate -> does NOT trigger subscriber again
    await manager.fetch_and_update()
    assert callback_mock.call_count == 1


@pytest.mark.asyncio
async def test_fetch_and_update_rpc_failure(mock_rpc_client):
    mock_rpc_client.get_mining_candidate = AsyncMock(
        side_effect=BSVRPCConnectionError("RPC unavailable")
    )
    manager = CandidateManager(mock_rpc_client)

    candidate = await manager.fetch_and_update()

    assert candidate is None
    assert manager.current_candidate is None


@pytest.mark.asyncio
async def test_polling_loop_lifecycle(mock_rpc_client):
    manager = CandidateManager(mock_rpc_client, poll_interval_seconds=0.01)

    await manager.start_polling()
    assert manager.is_running is True

    await asyncio.sleep(0.03)  # Allow a few poll cycles

    await manager.stop_polling()
    assert manager.is_running is False
    assert mock_rpc_client.get_mining_candidate.call_count >= 1
