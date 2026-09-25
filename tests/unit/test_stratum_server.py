import asyncio
import json
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from deepbsv.stratum.server import StratumServer


@pytest_asyncio.fixture
async def stratum_server() -> AsyncGenerator[StratumServer, None]:
    """Fixture, die einen Stratum-Server auf einem dynamischen Port startet und wieder stoppt."""
    server = StratumServer(host="127.0.0.1", port=0)
    await server.start()
    assert server._server is not None
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_server_subscribe_flow(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    req = {"id": 1, "method": "mining.subscribe", "params": ["cgminer/4.10.0"]}
    writer.write(json.dumps(req).encode("utf-8") + b"\n")
    await writer.drain()

    line = await reader.readline()
    res = json.loads(line.decode("utf-8"))

    assert res["id"] == 1
    assert res["error"] is None
    assert len(res["result"]) == 3

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_invalid_json(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    writer.write(b"invalid json line\n")
    await writer.drain()

    line = await reader.readline()
    res = json.loads(line.decode("utf-8"))

    assert res["id"] is None
    assert res["error"]["code"] == -32700

    writer.close()
    await writer.wait_closed()
