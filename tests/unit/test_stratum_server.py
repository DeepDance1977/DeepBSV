
import asyncio
import json

import pytest

from deepbsv.block.template import BlockTemplate
from deepbsv.core.engine import MiningEngine
from deepbsv.stratum.server import StratumServer


@pytest.fixture
async def stratum_server():
    """Startet einen Stratum-Server und stoppt ihn nach dem Test."""
    server = StratumServer(host="127.0.0.1", port=0)
    await server.start()
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_server_subscribe_flow(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    try:
        request = {
            "id": 1,
            "method": "mining.subscribe",
            "params": ["DeepBSV-TestMiner/1.0"],
        }
        writer.write((json.dumps(request) + "\n").encode("utf-8"))
        await writer.drain()

        response = json.loads((await reader.readline()).decode("utf-8").strip())

        assert response["id"] == 1
        assert response["error"] is None
        assert isinstance(response["result"], list)
        assert len(response["result"]) == 3
        assert len(response["result"][1]) == 8
        assert response["result"][2] == 4
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_invalid_json(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    try:
        writer.write(b"invalid json line\n")
        await writer.drain()

        response = json.loads((await reader.readline()).decode("utf-8").strip())

        assert response["id"] is None
        assert response["error"] is not None
        assert response["error"][0] == -32700
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_authorized_miner_receives_job_notify(
    stratum_server: StratumServer,
) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    try:
        subscribe_request = {
            "id": 1,
            "method": "mining.subscribe",
            "params": ["DeepBSV-Integration-Test/1.0"],
        }
        writer.write(
            (json.dumps(subscribe_request) + "\n").encode("utf-8")
        )
        await writer.drain()

        subscribe_response = json.loads(
            (await reader.readline()).decode("utf-8").strip()
        )
        assert subscribe_response["id"] == 1
        assert subscribe_response["error"] is None

        authorize_request = {
            "id": 2,
            "method": "mining.authorize",
            "params": ["test-worker"],
        }
        writer.write(
            (json.dumps(authorize_request) + "\n").encode("utf-8")
        )
        await writer.drain()

        authorize_response = json.loads(
            (await reader.readline()).decode("utf-8").strip()
        )
        assert authorize_response["id"] == 2
        assert authorize_response["result"] is True
        assert authorize_response["error"] is None

        engine = MiningEngine(stratum_server)
        template = BlockTemplate(
            height=503,
            prev_block_hash=(
                "0000000000000000000000000000000000000000000000000000000000000000"
            ),
        )
        job = engine.create_job_from_template(template)

        sent = await engine.broadcast_job(job)
        assert sent == 1

        notification = json.loads(
            (await asyncio.wait_for(reader.readline(), timeout=2)).decode("utf-8").strip()
        )

        assert notification["id"] is None
        assert notification["method"] == "mining.notify"
        assert isinstance(notification["params"], list)
        assert len(notification["params"]) == 9
        assert notification["params"][0] == job.job_id
        assert notification["params"][1] == template.prev_block_hash
        assert notification["params"][8] is True
    finally:
        writer.close()
        await writer.wait_closed()
