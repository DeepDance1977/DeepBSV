import asyncio
import json
import pytest

from deepbsv.stratum.server import StratumServer


@pytest.fixture
async def stratum_server():
    """Fixture, die einen Stratum-Server auf einem freien Port startet und nach dem Test stoppt."""
    server = StratumServer(host="127.0.0.1", port=0)
    await server.start()
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_server_subscribe_flow(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # Stratum Subscribe Request senden
    request = {
        "id": 1,
        "method": "mining.subscribe",
        "params": ["DeepBSV-TestMiner/1.0"],
    }
    writer.write((json.dumps(request) + "\n").encode("utf-8"))
    await writer.drain()

    # Antwort lesen
    line = await reader.readline()
    response = json.loads(line.decode("utf-8").strip())

    assert response["id"] == 1
    assert response["error"] is None
    assert isinstance(response["result"], list)

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_invalid_json(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    writer.write(b"invalid json line\n")
    await writer.drain()

    # Prüfen, ob der Server wie implementiert eine JSON-Fehlerantwort sendet
    line = await reader.readline()
    response = json.loads(line.decode("utf-8").strip())

    assert response["id"] is None
    assert response["error"] is not None
    assert response["error"][0] == -32700  # Parse error code

    writer.close()
    await writer.wait_closed()
