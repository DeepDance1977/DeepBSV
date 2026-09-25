import json
import logging
from typing import Dict, Any, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


class StratumError(Exception):
    """Spezifische Exception für Stratum JSON-RPC Fehler."""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
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
        self.worker_name: Optional[str] = None
        self.extranonce1: Optional[str] = None
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

    def __init__(self):
        self._handlers: Dict[str, Callable] = {
            "mining.subscribe": self._handle_subscribe,
            "mining.authorize": self._handle_authorize,
            "mining.submit": self._handle_submit,
        }

    def parse_message(self, raw_line: str) -> Dict[str, Any]:
        """Parst eine eingehende JSON-Zeile."""
        try:
            data = json.loads(raw_line.strip())
            if not isinstance(data, dict):
                raise ValueError("Payload muss ein JSON-Objekt sein.")
            return data
        except Exception as e:
            raise StratumError(-32700, f"Parse error: {str(e)}")

    def handle_request(self, session: StratumSession, request: Dict[str, Any]) -> Dict[str, Any]:
        """Verarbeitet eine geparste JSON-RPC Anfrage und gibt die Antwort zurück."""
        msg_id = request.get("id")
        method = request.get("method")
        params = request.get("params", [])

        if method not in self._handlers:
            return self.create_error_response(msg_id, -32601, f"Method '{method}' not found")

        try:
            result = self._handlers[method](session, params)
            return self.create_success_response(msg_id, result)
        except StratumError as se:
            return self.create_error_response(msg_id, se.code, se.message, se.data)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei Methode {method}: {e}", exc_info=True)
            return self.create_error_response(msg_id, -32603, "Internal error")

    def create_success_response(self, msg_id: Any, result: Any) -> Dict[str, Any]:
        return {
            "id": msg_id,
            "result": result,
            "error": None
        }

    def create_error_response(self, msg_id: Any, code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
        err_dict = {"code": code, "message": message}
        if data is not None:
            err_dict["data"] = data
        return {
            "id": msg_id,
            "result": None,
            "error": err_dict
        }

    def create_notification(self, method: str, params: list) -> Dict[str, Any]:
        """Erstellt eine Benachrichtigung vom Server an den Client (z. B. mining.notify)."""
        return {
            "id": None,
            "method": method,
            "params": params
        }

    # --- Intern Handlers ---

    def _handle_subscribe(self, session: StratumSession, params: list) -> list:
        # Erzeuge extranonce1 basierend auf der Session ID
        extranonce1 = session.session_id[:8].zfill(8)
        extranonce2_size = 4
        session.subscribe(extranonce1, extranonce2_size)

        subscriptions = [
            ["mining.set_difficulty", session.session_id],
            ["mining.notify", session.session_id]
        ]
        return [subscriptions, extranonce1, extranonce2_size]

    def _handle_authorize(self, session: StratumSession, params: list) -> bool:
        if not params or len(params) < 1:
            raise StratumError(-32602, "Invalid params: Missing worker name")
        
        worker_name = str(params[0])
        # Hier könnte ggf. eine Passwort-Validierung (params[1]) integriert werden
        session.authorize(worker_name)
        return True

    def _handle_submit(self, session: StratumSession, params: list) -> bool:
        if not session.is_authorized:
            raise StratumError(24, "Unauthorized worker")
        
        if len(params) < 5:
            raise StratumError(-32602, "Invalid params: Expected worker_name, job_id, extranonce2, ntime, nonce")

        # Parameter-Schema: [worker_name, job_id, extranonce2, ntime, nonce]
        worker_name, job_id, extranonce2, ntime, nonce = params[:5]
        
        # Validierungslogik für den Share (in einer vollständigen Engine würde hier der Hash geprüft)
        return True
