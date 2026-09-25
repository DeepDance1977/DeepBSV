import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class StratumServer:
    """Einfacher Stratum V1 Server für DeepBSV."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3333) -> None:
        self.host = host
        self.port = port
        self.sessions: dict[Any, Any] = {}
        self.jobs: dict[str, Any] = {}
        self._server: asyncio.Server | None = None

    def register_job(self, job_id: str, job_data: dict[str, Any]) -> None:
        """Registriert einen neuen Mining-Job."""
        self.jobs[job_id] = job_data

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        session_id = id(writer)
        self.sessions[session_id] = {
            "reader": reader,
            "writer": writer,
            "subscribed": False,
            "authorized_worker": None,
        }

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                
                line = data.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Ungültiges JSON empfangen: %s", line)
                    writer.close()
                    await writer.wait_closed()
                    break

                method = message.get("method")
                msg_id = message.get("id")

                if method == "mining.subscribe":
                    response = {
                        "id": msg_id,
                        "result": [["mining.notify", "subscription_id"], "extranonce1", 4],
                        "error": None,
                    }
                    self.sessions[session_id]["subscribed"] = True
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()
                elif method == "mining.authorize":
                    response = {"id": msg_id, "result": True, "error": None}
                    params = message.get("params", [None])
                    self.sessions[session_id]["authorized_worker"] = params[0] if params else None
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()

        except (TimeoutError, ConnectionError) as e:
            logger.info("Client-Verbindung getrennt: %s", e)
        finally:
            if session_id in self.sessions:
                del self.sessions[session_id]
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def start(self) -> None:
        """Startet den Stratum TCP Server."""
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )

    async def stop(self) -> None:
        """Stoppt den Stratum TCP Server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
