import asyncio
import json

import pytest

from deepbsv.stratum.server import StratumServer


@pytest.fixture
async def stratum_server():
    server = StratumServer(host="127.0.0.1", port=0)
    await server.start()
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_server_subscribe_flow(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    # Subscribe-Anfrage senden
    subscribe_req = {
        "id": 1,
        "method": "mining.subscribe",
        "params": [],
    }
    writer.write((json.dumps(subscribe_req) + "\n").encode("utf-8"))
    await writer.drain()

    line = await reader.readline()
    response = json.loads(line.decode("utf-8"))
    assert response["id"] == 1
    assert response["error"] is None

    # Authorize-Anfrage senden
    auth_req = {
        "id": 2,
        "method": "mining.authorize",
        "params": ["worker1", "pass"],
    }
    writer.write((json.dumps(auth_req) + "\n").encode("utf-8"))
    await writer.drain()

    line = await reader.readline()
    response = json.loads(line.decode("utf-8"))
    assert response["id"] == 2
    assert response["result"] is True

    writer.close()
    await writer.wait_closed()


@pytest.mark.asyncio
async def test_server_invalid_json(stratum_server: StratumServer) -> None:
    assert stratum_server._server is not None
    port = stratum_server._server.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)

    writer.write(b"invalid json line\n")
    await writer.drain()

    # Da der Server bei ungültigem JSON die Verbindung schließt,
    # erhalten wir direkt EOF (leere Daten).
    data = await reader.read(1024)
    assert data == b""

    writer.close()
    await writer.wait_closed()
