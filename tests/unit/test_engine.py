
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from deepbsv.block.template import BlockTemplate
from deepbsv.core.engine import MiningEngine
from deepbsv.stratum.server import StratumServer


@pytest_asyncio.fixture
async def engine() -> MiningEngine:
    server = StratumServer(host="127.0.0.1", port=0)
    return MiningEngine(server)


def test_create_job_from_template(engine: MiningEngine) -> None:
    template = BlockTemplate(
        height=500,
        prev_block_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    job = engine.create_job_from_template(template, clean_jobs=True)

    assert job.job_id == "1"
    assert job.clean_jobs is True
    assert len(job.to_notify_params()) == 9


@pytest.mark.asyncio
async def test_broadcast_job_empty_sessions(engine: MiningEngine) -> None:
    template = BlockTemplate(
        height=501,
        prev_block_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    job = engine.create_job_from_template(template)
    sent = await engine.broadcast_job(job)

    assert sent == 0


@pytest.mark.asyncio
async def test_broadcast_job_sends_notify(engine: MiningEngine) -> None:
    template = BlockTemplate(
        height=502,
        prev_block_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    job = engine.create_job_from_template(template)
    broadcast = AsyncMock(return_value=2)
    engine.stratum_server.broadcast_notification = broadcast

    sent = await engine.broadcast_job(job)

    assert sent == 2
    broadcast.assert_awaited_once_with(
        "mining.notify",
        job.to_notify_params(),
        authorized_only=True,
    )
