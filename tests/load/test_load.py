import asyncio
import json
import logging
import time

from deepbsv.stratum.server import StratumServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deepbsv.load_test")


async def simulate_miner(client_id: int, host: str, port: int) -> None:
    """Simuliert einen einzelnen Mining-Client, der sich verbindet und anmeldet."""
    try:
        reader, writer = await asyncio.open_connection(host, port)

        # Stratum Subscribe senden
        subscribe_req = {
            "id": client_id,
            "method": "mining.subscribe",
            "params": [f"DeepBSV-LoadTest-Miner/{client_id}"],
        }
        writer.write((json.dumps(subscribe_req) + "\n").encode("utf-8"))
        await writer.drain()

        # Antwort lesen
        line = await reader.readline()
        response = json.loads(line.decode("utf-8"))

        if response.get("error") is None:
            logger.info("Miner %d erfolgreich verbunden und subscribed.", client_id)
        else:
            logger.warning(
                "Miner %d Fehler bei Subscription: %s",
                client_id,
                response.get("error"),
            )

        # Verbindung kurz halten, dann sauber trennen
        await asyncio.sleep(0.5)
        writer.close()
        await writer.wait_closed()

    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error("Netzwerkfehler bei Miner %d: %s", client_id, e)


async def run_load_test() -> None:
    # 1. Server temporär für den Test starten
    host = "127.0.0.1"
    server = StratumServer(host=host, port=0)
    await server.start()
    assert server._server is not None
    port = server._server.sockets[0].getsockname()[1]

    logger.info("Test-Server gestartet auf Port %d", port)

    # Einen Test-Job registrieren
    server.register_job("load_job_001", {"job_id": "load_job_001", "prevhash": "0" * 64})

    # 2. Parallele Clients definieren (z. B. 50 gleichzeitige Miner)
    num_clients = 50
    logger.info("Starte Lasttest mit %d parallelen Minern...", num_clients)

    start_time = time.time()
    tasks = [simulate_miner(i, host, port) for i in range(num_clients)]
    await asyncio.gather(*tasks)
    duration = time.time() - start_time

    logger.info("Lasttest abgeschlossen in %.2f Sekunden.", duration)

    # 3. Server stoppen
    await server.stop()


if __name__ == "__main__":
    asyncio.run(run_load_test())
