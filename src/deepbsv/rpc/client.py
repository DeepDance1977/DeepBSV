from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BSVNodeRPCError(Exception):
    """Fehler bei der Kommunikation mit der Bitcoin-SV-Node."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BSVNodeRPCClient:
    """Asynchroner JSON-RPC-Client für eine Bitcoin-SV-Node."""

    def __init__(
        self,
        url: str = "http://127.0.0.1:8332",
        rpc_user: str = "user",
        rpc_password: str = "password",
        timeout: float = 15.0,
    ) -> None:
        self.url = url
        self.auth = (rpc_user, rpc_password)
        self.timeout = timeout
        self._request_id = 0

    async def _call(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> Any:
        self._request_id += 1

        payload = {
            "jsonrpc": "1.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                auth=self.auth,
            ) as client:
                response = await client.post(
                    self.url,
                    json=payload,
                )
                response.raise_for_status()

        except httpx.HTTPError as exc:
            logger.error(
                "HTTP-Fehler bei RPC-Aufruf %s: %s",
                method,
                exc,
            )

            raise BSVNodeRPCError(
                -32603,
                f"HTTP-Fehler bei {method}: {exc}",
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise BSVNodeRPCError(
                -32700,
                f"Ungültige JSON-RPC-Antwort bei {method}",
            ) from exc

        if not isinstance(data, dict):
            raise BSVNodeRPCError(
                -32603,
                f"Ungültiges RPC-Antwortformat bei {method}",
            )

        error = data.get("error")

        if error is not None:
            if isinstance(error, dict):
                code = int(error.get("code", -1))
                message = str(
                    error.get(
                        "message",
                        "Unbekannter RPC-Fehler",
                    )
                )
            else:
                code = -1
                message = str(error)

            raise BSVNodeRPCError(
                code,
                message,
            )

        return data.get("result")

    async def get_blockchain_info(self) -> dict[str, Any]:
        """Liest den aktuellen Blockchain-Status."""

        result = await self._call(
            "getblockchaininfo",
        )

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat von getblockchaininfo",
            )

        return result

    async def get_network_info(self) -> dict[str, Any]:
        """Liest den Netzwerkstatus der BSV-Node."""

        result = await self._call(
            "getnetworkinfo",
        )

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat von getnetworkinfo",
            )

        return result

    async def get_block_count(self) -> int:
        """Liest die aktuelle Blockhöhe."""

        result = await self._call(
            "getblockcount",
        )

        if not isinstance(result, int):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat von getblockcount",
            )

        return result

    async def get_mining_candidate(
        self,
        provide_coinbase: bool = True,
    ) -> dict[str, Any]:
        """
        Holt einen aktuellen BSV Mining Candidate.

        BSV unterstützt getminingcandidate mit einem optionalen
        Boolean-Parameter. Für DeepBSV benötigen wir die Coinbase,
        damit wir daraus die Stratum-Coinbase-Komponenten erzeugen
        können.
        """

        result = await self._call(
            "getminingcandidate",
            [provide_coinbase],
        )

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat von getminingcandidate",
            )

        required_fields = (
            "id",
            "prevhash",
            "version",
            "nBits",
            "time",
            "height",
            "merkleProof",
        )

        missing = [
            field
            for field in required_fields
            if field not in result
        ]

        if missing:
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate enthält nicht alle "
                f"erforderlichen Felder: {', '.join(missing)}",
            )

        if provide_coinbase and not result.get("coinbase"):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate enthält keine Coinbase-Transaktion",
            )

        return result

    async def submit_mining_solution(
        self,
        candidate_id: str,
        nonce: int,
        coinbase: str | None = None,
        time_value: int | None = None,
        version: int | None = None,
    ) -> Any:
        """
        Reicht eine gefundene Mining-Lösung bei BSV ein.

        Der BSV RPC heißt ausdrücklich submitminingsolution.
        """

        solution: dict[str, Any] = {
            "id": candidate_id,
            "nonce": nonce,
        }

        if coinbase is not None:
            solution["coinbase"] = coinbase

        if time_value is not None:
            solution["time"] = time_value

        if version is not None:
            solution["version"] = version

        return await self._call(
            "submitminingsolution",
            [solution],
        )

    async def ping(self) -> bool:
        """Prüft, ob die Node erreichbar ist."""

        try:
            await self.get_blockchain_info()
        except BSVNodeRPCError:
            return False

        return True
