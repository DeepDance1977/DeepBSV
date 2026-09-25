import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StratumServer:
    """Asynchroner Stratum V1 Mining Server mit Client-Verwaltung und Health-Check."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._server: Optional[asyncio.Server] = None
        self.active_connections = 0
        self.start_time: Optional[float] = None
        self._is_running = False
        self._jobs: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        """Startet den TCP-Stratum-Server."""
        self._server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        self._is_running = True
        self.start_time = time.time()
        
        # Port auslesen, falls port=0 (dynamischer Port für Tests) gewählt wurde
        if self._server.sockets:
            self.port = self._server.sockets[0].getsockname()[1]

        logger.info("StratumServer gestartet auf %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stoppt den Server und schließt alle Verbindungen sauber."""
        self._is_running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("StratumServer gestoppt.")

    def register_job(self, job_id: str, job_data: Dict[str, Any]) -> None:
        """Registriert einen neuen Mining-Job im Server."""
        self._jobs[job_id] = job_data
        logger.info("Job %s erfolgreich im Server registriert.", job_id)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Verwaltet eine einzelne Client-Verbindung über das Stratum-Protokoll."""
        self.active_connections += q := 1  # Zähler erhöhen
        peername = writer.get_extra_info("peername")
        logger.info("Neuer Client verbunden: %s", peername)

        try:
            while self._is_running:
                data = await reader.readline()
                if not data:
                    break

                message_str = data.decode("utf-8").strip()
                if not message_str:
                    continue

                try:
                    message = json.loads(message_str)
                except json.JSONDecodeError:
                    # JSON-Fehlerantwort senden
                    error_resp = {
                        "id": None,
                        "result": None,
                        "error": [-32700, "Parse error: Invalid JSON", None],
                    }
                    writer.write((json.dumps(error_resp) + "\n").encode("utf-8"))
                    await writer.drain()
                    continue

                msg_id = message.get("id")
                method = message.get("method")

                # Stratum Subscribe behandeln
                if method == "mining.subscribe":
                    response = {
                        "id": msg_id,
                        "result": [
                            [["mining.set_difficulty", "subscription_id_1"], ["mining.notify", "subscription_id_2"]],
                            "extranonce1_hex",
                            4,
                        ],
                        "error": None,
                    }
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()

        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            self.active_connections -= 1
            logger.info("Client-Verbindung getrennt: %s", peername)
            writer.close()
            await writer.wait_closed()

    def get_health_status(self) -> Dict[str, Any]:
        """Gibt den aktuellen Gesundheits- und Metrikstatus des Servers zurück."""
        uptime = time.time() - self.start_time if self.start_time else 0.0
        return {
            "status": "healthy" if self._is_running else "stopped",
            "is_running": self._is_running,
            "active_connections": self.active_connections,
            "uptime_seconds": round(uptime, 2),
            "host": self.host,
            "port": self.port,
            "registered_jobs_count": len(self._jobs),
        }
