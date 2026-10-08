import asyncio
import json

import pytest

from deepbsv.stratum.server import StratumServer


@pytest.mark.asyncio
async def test_e2e_stratum_and_engine_workflow() -> None:
    """Simuliert einen vollständigen End-to-End-Workflow:
    Serverstart, Job-Registrierung und Client-Verbindung mit Stratum-Subscribe.
    """
    # 1. Server auf einem zufälligen freien Port starten
    server = StratumServer(host="127.0.0.1", port=0)
    await server.start()

    assert server._server is not None

    port = server._server.sockets[0].getsockname()[1]

    # 2. Einen Test-Job im Server registrieren
    job_id = "test_job_e2e_001"

    server.register_job(
        job_id,
        {
            "job_id": job_id,
            "prevhash": "0" * 64,
        },
    )

    # 3. Echten TCP-Client simulieren und Verbindung aufbauen
    reader, writer = await asyncio.open_connection(
        "127.0.0.1",
        port,
    )

    # Stratum Subscribe-Anfrage senden
    subscribe_req = {
        "id": 1,
        "method": "mining.subscribe",
        "params": ["DeepBSV-Client/0.1.0"],
    }

    writer.write(
        (json.dumps(subscribe_req) + "\n").encode("utf-8"),
    )
    await writer.drain()

    # Antwort des Servers empfangen und validieren
    line = await reader.readline()

    response = json.loads(
        line.decode("utf-8"),
    )

    assert response["id"] == 1
    assert response["error"] is None

    result = response["result"]

    assert isinstance(result, list)
    assert len(result) == 3

    subscriptions = result[0]
    extranonce1 = result[1]
    extranonce2_size = result[2]

    assert isinstance(subscriptions, list)
    assert len(subscriptions) == 2

    assert subscriptions[0][0] == "mining.set_difficulty"
    assert subscriptions[1][0] == "mining.notify"

    assert isinstance(extranonce1, str)
    assert len(extranonce1) == 8

    assert extranonce2_size == 4

    # Session muss nach Subscribe als subscribed markiert sein
    assert server.active_connections == 1

    # 4. Sauberes Aufräumen (Cleanup)
    writer.close()
    await writer.wait_closed()

    await server.stop()

    assert server.active_connections == 0
