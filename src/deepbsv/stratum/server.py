import asyncio
import json
import logging
from typing import Any

from deepbsv.stratum.validation import (
    build_block_header,
    calculate_merkle_root,
    nbits_to_target,
    reconstruct_coinbase,
    validate_share,
)

logger = logging.getLogger(__name__)


class StratumSession:
    """Repräsentiert eine aktive TCP-Verbindung eines Miners."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        session_id: str,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.session_id = session_id
        self.extranonce1 = session_id[:8].zfill(8)
        self.extranonce2_size = 4
        self.authorized_worker: str | None = None
        self.subscribed = False

    async def send_response(
        self, result: Any, error: Any = None, msg_id: Any = None
    ) -> None:
        payload = {"id": msg_id, "result": result, "error": error}
        data = json.dumps(payload) + "\n"
        self.writer.write(data.encode("utf-8"))
        await self.writer.drain()


class StratumServer:
    """Stratum V1 TCP Server für Solo-Mining Management."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 3333,
        rpc_client: Any = None,
    ) -> None:
        self.host = host
        self.port = port
        self.rpc_client = rpc_client
        self.sessions: dict[str, StratumSession] = {}
        self.active_jobs: dict[str, dict[str, Any]] = {}
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        """Startet den Stratum TCP Listener."""
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        logger.info("Stratum Server hört auf %s:%d", self.host, self.port)

    async def stop(self) -> None:
        """Stoppt den Stratum Server geordnet."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("Stratum Server gestoppt.")

    def register_job(self, job_id: str, job_data: dict[str, Any]) -> None:
        """Registriert einen neuen Job für spätere Validierung von Submissions."""
        self.active_jobs[job_id] = job_data

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        session_id = f"{id(reader):x}"
        session = StratumSession(reader, writer, session_id)
        self.sessions[session_id] = session

        try:
            while not reader.at_eof():
                line = await reader.readline()
                if not line:
                    break
                await self._process_message(session, line.decode("utf-8").strip())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Fehler in Session %s: %s", session_id, e)
        finally:
            self.sessions.pop(session_id, None)
            writer.close()
            await writer.wait_closed()

    async def _process_message(self, session: StratumSession, raw_msg: str) -> None:
        if not raw_msg:
            return

        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            logger.warning("Ungültiges JSON empfangen: %s", raw_msg)
            return

        method = data.get("method")
        msg_id = data.get("id")
        params = data.get("params", [])

        if method == "mining.subscribe":
            await self._handle_subscribe(session, msg_id)
        elif method == "mining.authorize":
            await self._handle_authorize(session, params, msg_id)
        elif method == "mining.submit":
            await self._handle_submit(session, params, msg_id)
        else:
            await session.send_response(
                None, error=[20, "Method not found", None], msg_id=msg_id
            )

    async def _handle_subscribe(
        self, session: StratumSession, msg_id: Any
    ) -> None:
        session.subscribed = True
        result = [
            [
                ["mining.set_difficulty", session.session_id],
                ["mining.notify", session.session_id],
            ],
            session.extranonce1,
            session.extranonce2_size,
        ]
        await session.send_response(result, msg_id=msg_id)

    async def _handle_authorize(
        self, session: StratumSession, params: list[Any], msg_id: Any
    ) -> None:
        worker_name = params[0] if params else "anonymous"
        session.authorized_worker = worker_name
        logger.info("Worker '%s' erfolgreich autorisiert.", worker_name)
        await session.send_response(True, msg_id=msg_id)

    async def _handle_submit(
        self, session: StratumSession, params: list[Any], msg_id: Any
    ) -> None:
        """
        Verarbeitet die Einreichung einer Nonce durch einen Miner (mining.submit).
        Params Format: [worker_name, job_id, extranonce2, ntime, nonce]
        """
        if len(params) < 5:
            await session.send_response(
                False, error=[21, "Ungültige Parameter-Anzahl", None], msg_id=msg_id
            )
            return

        _, job_id, extranonce2_hex, ntime_hex, nonce_hex = params[:5]

        job = self.active_jobs.get(job_id)
        if not job:
            logger.warning("Submission für unbekannten/abgelaufenen Job: %s", job_id)
            await session.send_response(
                False, error=[21, "Job nicht gefunden", None], msg_id=msg_id
            )
            return

        try:
            # 1. Parameter parsen
            ntime = int(ntime_hex, 16)
            nonce = int(nonce_hex, 16)

            # 2. Coinbase-Transaktion zusammensetzen
            coinbase_bytes = reconstruct_coinbase(
                job["coinbase_1"],
                session.extranonce1,
                extranonce2_hex,
                job["coinbase_2"],
            )

            # 3. Coinbase-Hash berechnen (Double-SHA256)
            import hashlib

            cb_hash = hashlib.sha256(hashlib.sha256(coinbase_bytes).digest()).digest()

            # 4. Merkle-Root berechnen
            merkle_root = calculate_merkle_root(cb_hash, job["merkle_branches"])

            # 5. Block-Header rekonstruieren (80 Bytes)
            header_bytes = build_block_header(
                version=job["version"],
                prev_block_hash_hex=job["prev_hash"],
                merkle_root=merkle_root,
                ntime=ntime,
                nbits=job["nbits"],
                nonce=nonce,
            )

            # 6. Target berechnen & Prüfen
            target = nbits_to_target(job["nbits"])
            is_valid, hash_hex, _ = validate_share(header_bytes, target)

            if not is_valid:
                logger.warning(
                    "Ungültiger Share von Worker %s (Hash verfehlt Target).",
                    session.authorized_worker,
                )
                await session.send_response(
                    False, error=[23, "Share erfüllt Difficulty nicht", None], msg_id=msg_id
                )
                return

            logger.info("GÜLTIGER BLOCK/SHARE GEFUNDEN! Hash: %s", hash_hex)

            # 7. Wenn RPC-Client vorhanden ist, an die BSV-Node übermitteln
            if self.rpc_client:
                await self.rpc_client.submit_mining_candidate(
                    candidate_id=job.get("candidate_id", job_id),
                    header_hex=header_bytes.hex(),
                    coinbase_hex=coinbase_bytes.hex(),
                )

            await session.send_response(True, msg_id=msg_id)

        except Exception as e:
            logger.error("Fehler bei der Validierung des Shares: %s", e)
            await session.send_response(
                False, error=[20, f"Validierungsfehler: {e}", None], msg_id=msg_id
            )
