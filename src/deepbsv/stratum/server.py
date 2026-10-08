from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from deepbsv.stratum.protocol import StratumProtocolHandler, StratumSession

logger = logging.getLogger(__name__)


class StratumServer:
    """Asynchroner Stratum-V1-Mining-Server."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.Server | None = None
        self.active_connections = 0
        self.start_time: float | None = None
        self._is_running = False
        self._jobs: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, StratumSession] = {}
        self._protocol = StratumProtocolHandler()

    async def start(self) -> None:
        """Startet den TCP-Stratum-Server."""
        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
        )
        self._is_running = True
        self.start_time = time.time()

        if self._server.sockets:
            self.port = self._server.sockets[0].getsockname()[1]

        logger.info(
            "StratumServer gestartet auf %s:%d",
            self.host,
            self.port,
        )

    async def stop(self) -> None:
        """Stoppt den Server und schließt alle Verbindungen sauber."""
        self._is_running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._sessions.clear()
        self.active_connections = 0

        logger.info("StratumServer gestoppt.")

    def register_job(
        self,
        job_id: str,
        job_data: dict[str, Any],
    ) -> None:
        """Registriert einen neuen Mining-Job im Server."""
        self._jobs[job_id] = job_data

        logger.info(
            "Job %s erfolgreich im Server registriert.",
            job_id,
        )

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        response: dict[str, Any],
    ) -> None:
        """Sendet eine JSON-RPC-Antwort oder Notification an den Miner."""
        writer.write(
            (
                json.dumps(
                    response,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8"),
        )
        await writer.drain()

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Verwaltet eine einzelne Stratum-Client-Verbindung."""
        self.active_connections += 1

        peername = writer.get_extra_info("peername")
        session_id = uuid.uuid4().hex

        session = StratumSession(session_id)
        self._sessions[session_id] = session

        logger.info(
            "Neuer Stratum-Client verbunden: %s (Session %s)",
            peername,
            session_id,
        )

        try:
            while self._is_running:
                data = await reader.readline()

                if not data:
                    break

                message_str = data.decode("utf-8").strip()

                if not message_str:
                    continue

                try:
                    request = self._protocol.parse_message(
                        message_str,
                    )
                except Exception:
                    response = {
                        "id": None,
                        "result": None,
                        "error": [
                            -32700,
                            "Parse error: Invalid JSON",
                            None,
                        ],
                    }
                    await self._send_response(
                        writer,
                        response,
                    )
                    continue

                method = request.get("method")

                if method == "mining.notify":
                    logger.warning(
                        "Miner %s hat eine Server-Notification "
                        "als Request gesendet.",
                        session_id,
                    )

                response = self._protocol.handle_request(
                    session,
                    request,
                )

                await self._send_response(
                    writer,
                    response,
                )

                if method == "mining.subscribe":
                    logger.info(
                        "Miner %s erfolgreich subscribed.",
                        session_id,
                    )

                elif method == "mining.authorize":
                    if session.is_authorized:
                        logger.info(
                            "Miner %s autorisiert als %s.",
                            session_id,
                            session.worker_name,
                        )

                elif method == "mining.submit":
                    logger.info(
                        "Share von Miner %s empfangen.",
                        session.worker_name or session_id,
                    )

        except ConnectionError:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Unerwarteter Fehler bei Stratum-Client %s.",
                peername,
            )
        finally:
            self._sessions.pop(session_id, None)

            if self.active_connections > 0:
                self.active_connections -= 1

            logger.info(
                "Client-Verbindung getrennt: %s",
                peername,
            )

            writer.close()

            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    def get_health_status(self) -> dict[str, Any]:
        """Gibt den aktuellen Gesundheits- und Metrikstatus zurück."""
        uptime = (
            time.time() - self.start_time
            if self.start_time
            else 0.0
        )

        return {
            "status": (
                "healthy"
                if self._is_running
                else "stopped"
            ),
            "is_running": self._is_running,
            "active_connections": self.active_connections,
            "authorized_miners": sum(
                1
                for session in self._sessions.values()
                if session.is_authorized
            ),
            "uptime_seconds": round(
                uptime,
                2,
            ),
            "host": self.host,
            "port": self.port,
            "registered_jobs_count": len(self._jobs),
        }
