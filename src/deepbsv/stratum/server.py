import asyncio
import logging
import uuid
from typing import Any

from deepbsv.stratum.protocol import (
    StratumError,
    StratumProtocolHandler,
    StratumSession,
)

logger = logging.getLogger(__name__)


class StratumServer:
    """Asyncio-basierter TCP Stratum Server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3333) -> None:
        self.host = host
        self.port = port
        self.handler = StratumProtocolHandler()
        self.sessions: dict[str, StratumSession] = {}
        self._server: asyncio.Server | None = None

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Verarbeitet eine eingehende Client-Verbindung."""
        session_id = uuid.uuid4().hex
        session = StratumSession(session_id)
        self.sessions[session_id] = session

        addr = writer.get_extra_info("peername")
        logger.info("Neue Miner-Verbindung von %s (Session ID: %s)", addr, session_id)

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break

                raw_line = line.decode("utf-8").strip()
                if not raw_line:
                    continue

                response = self._process_line(session, raw_line)
                if response:
                    writer.write(response.encode("utf-8") + b"\n")
                    await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Fehler in Client-Verbindung (%s)", session_id)
        finally:
            logger.info("Verbindung geschlossen für Session %s", session_id)
            self.sessions.pop(session_id, None)
            writer.close()
            await writer.wait_closed()

    def _process_line(self, session: StratumSession, raw_line: str) -> str | None:
        """Parst und verarbeitet eine Zeile und erzeugt den JSON-String für die Antwort."""
        try:
            request = self.handler.parse_message(raw_line)
            response = self.handle_request(session, request)
        except StratumError as se:
            response = self.handler.create_error_response(
                None, se.code, se.message, se.data
            )
        except Exception:
            logger.exception("Unerwarteter Fehler bei Nachrichtenverarbeitung")
            response = self.handler.create_error_response(
                None, -32603, "Internal error"
            )

        if response is None:
            return None

        import json

        return json.dumps(response)

    def handle_request(
        self, session: StratumSession, request: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Delegiert die Anfragen an den Protocol Handler."""
        return self.handler.handle_request(session, request)

    async def start(self) -> None:
        """Startet den TCP Server."""
        self._server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        logger.info("Stratum Server gestartet auf %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stoppt den TCP Server sauber."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Stratum Server gestoppt.")
