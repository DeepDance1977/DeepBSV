import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BSVNodeRPCError(Exception):
    """Exception für RPC-Fehler der BSV Node."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BSVNodeRPCClient:
    """Async Client für die JSON-RPC Kommunikation mit einer BSV Node (Pruned-compatible)."""

    def __init__(
        self,
        url: str = "http://127.0.0.1:8332",
        rpc_user: str = "user",
        rpc_password: str = "password",
        timeout: float = 10.0,
    ) -> None:
        self.url = url
        self.auth = (rpc_user, rpc_password)
        self.timeout = timeout
        self._request_id = 0

    async def _call(self, method: str, params: list[Any] | None = None) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "1.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.url,
                    json=payload,
                    auth=self.auth,
                )
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("HTTP-Fehler bei RPC-Aufruf %s: %s", method, e)
                raise BSVNodeRPCError(-32603, f"HTTP Error: {e!s}") from e

            data = response.json()
            if data.get("error") is not None:
                err = data["error"]
                raise BSVNodeRPCError(
                    err.get("code", -1), err.get("message", "Unknown RPC error")
                )

            return data.get("result")

    async def get_mining_candidate() -> dict[str, Any]:
        """Ruft einen neuen Mining Candidate ab (optimal für Pruned Nodes)."""
        result = await self._call("getminingcandidate")
        if not isinstance(result, dict):
            raise BSVNodeRPCError(-32600, "Ungültiges Antwortformat für Candidate")
        return result

    async def submit_mining_candidate(
        self, candidate_id: str, coinbase_tx_hex: str, header_hex: str
    ) -> dict[str, Any]:
        """Reicht eine gefundene Block-Lösung an die Node ein."""
        params = [{
            "id": candidate_id,
            "coinbase": coinbase_tx_hex,
            "header": header_hex,
        }]
        result = await self._call("submitminingcandidate", params)
        if not isinstance(result, dict):
            raise BSVNodeRPCError(-32600, "Ungültiges Antwortformat bei Submit")
        return result
