from collections.abc import Callable
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class StratumError(Exception):
    """Spezifische Exception für Stratum JSON-RPC Fehler."""

    def __init__(self, code: int, message: str, data: Any | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        err = {"code": self.code, "message": self.message}
        if self.data is not None:
            err["data"] = self.data
        return err


class StratumSession:
    """Verwaltet den Zustand einer einzelnen Miner-Session."""

    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.is_subscribed: bool = False
        self.is_authorized: bool = False
        self.worker_name: str | None = None
        self.extranonce1: str | None = None
        self.extranonce2_size: int = 4
        self.difficulty: float = 1.0

    def subscribe(self, extranonce1: str, extranonce2_size: int = 4) -> None:
        self.is_subscribed = True
        self.extranonce1 = extranonce1
        self.extranonce2_size = extranonce2_size

    def authorize(self, worker_name: str) -> None:
        self.worker_name = worker_name
        self.is_authorized = True


class StratumProtocolHandler:
    """Standard Stratum Protocol Handler für JSON-RPC 1.0 (Stratum v1)."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {
            "mining.subscribe": self._handle_subscribe,
            "mining.authorize": self._handle_authorize,
            "mining.submit": self._handle_submit,
        }

    def parse_message(self, raw_line: str) -> dict[str, Any]:
        """Parst eine eingehende JSON-Zeile."""
        try:
            data = json.loads(raw_line.strip())
            if not isinstance(data, dict):
                raise TypeError("Payload muss ein JSON-Objekt sein.")
            return data
        except Exception as e:  # noqa: BLE001
            raise StratumError(-32700, f"Parse error: {e!s}") from e

    def handle_request(
        self, session: StratumSession, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Verarbeitet eine geparste JSON-RPC Anfrage und gibt die Antwort zurück."""
        msg_id = request.get("id")
        method = request.get("method")
        params = request.get("params", [])

        if method not in self._handlers:
            return self.create_error_response(
                msg_id, -32601, f"Method '{method}' not found"
            )

        try:
            result = self._handlers[method](session, params)
            return self.create_success_response(msg_id, result)
        except StratumError as se:
            return self.create_error_response(msg_id, se.code, se.message, se.data)
        except Exception as e:  # noqa: BLE001
            logger.exception("Unerwarteter Fehler bei Methode %s: %s", method, e)
            return self.create_error_response(msg_id, -32603, "Internal error")

    def create_success_response(self, msg_id: Any, result: Any) -> dict[str, Any]:
        return {"id": msg_id, "result": result, "error": None}

    def create_error_response(
        self,
        msg_id: Any,
        code: int,
        message: str,
        data: Any | None = None,
    ) -> dict[str, Any]:
        err_dict: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err_dict["data"] = data
        return {"id": msg_id, "result": None, "error": err_dict}

    def create_notification(
        self, method: str, params: list[Any]
    ) -> dict[str, Any]:
        """Erstellt eine Benachrichtigung vom Server an den Client (z. B. mining.notify)."""
        return {"id": None, "method": method, "params": params}

    # --- Intern Handlers ---

    def _handle_subscribe(
        self, session: StratumSession, _params: list[Any]
    ) -> list[Any]:
        extranonce1 = session.session_id[:8].zfill(8)
        extranonce2_size = 4
        session.subscribe(extranonce1, extranonce2_size)

        subscriptions = [
            ["mining.set_difficulty", session.session_id],
            ["mining.notify", session.session_id],
        ]
        return [subscriptions, extranonce1, extranonce2_size]

    def _handle_authorize(
        self, session: StratumSession, params: list[Any]
    ) -> bool:
        if not params or len(params) < 1:
            raise StratumError(-32602, "Invalid params: Missing worker name")

        worker_name = str(params[0])
        session.authorize(worker_name)
        return True

    def _handle_submit(
        self, session: StratumSession, params: list[Any]
    ) -> bool:
        if not session.is_authorized:
            raise StratumError(24, "Unauthorized worker")

        if len(params) < 5:
            raise StratumError(
                -32602,
                "Invalid params: Expected worker_name, job_id, extranonce2, ntime, nonce",
            )

        _worker_name, _job_id, _extranonce2, _ntime, _nonce = params[:5]
        return True
