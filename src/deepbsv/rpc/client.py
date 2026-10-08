```python
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BSVNodeRPCError(Exception):
    """Fehler bei der JSON-RPC-Kommunikation mit der BSV-Node."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BSVNodeRPCClient:
    """Asynchroner JSON-RPC-Client für Bitcoin SV."""

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

    async def _call(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> Any:
        """Führt einen einzelnen JSON-RPC-Aufruf aus."""

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
            ) as client:
                response = await client.post(
                    self.url,
                    json=payload,
                    auth=self.auth,
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
            logger.error(
                "Ungültige JSON-Antwort bei RPC-Aufruf %s",
                method,
            )

            raise BSVNodeRPCError(
                -32700,
                "Ungültige JSON-RPC-Antwort",
            ) from exc

        if not isinstance(data, dict):
            raise BSVNodeRPCError(
                -32603,
                "Ungültiges JSON-RPC-Antwortformat",
            )

        error = data.get("error")

        if error is not None:
            if isinstance(error, dict):
                code = int(
                    error.get("code", -1),
                )
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

    async def get_blockchain_info(
        self,
    ) -> dict[str, Any]:
        """Liest den aktuellen Blockchain-Status."""

        result = await self._call(
            "getblockchaininfo",
        )

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat für getblockchaininfo",
            )

        return result

    async def get_network_info(
        self,
    ) -> dict[str, Any]:
        """Liest den aktuellen Netzwerkstatus."""

        result = await self._call(
            "getnetworkinfo",
        )

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat für getnetworkinfo",
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
                "Ungültiges Antwortformat für getblockcount",
            )

        return result

    async def get_mining_candidate(
        self,
        provide_coinbase: bool = True,
    ) -> dict[str, Any]:
        """
        Holt einen aktuellen Bitcoin-SV Mining Candidate.

        BSV definiert getminingcandidate als Teil des
        Get-Mining-Candidate-Verfahrens.

        provide_coinbase=True ist für DeepBSV erforderlich,
        weil wir die Coinbase für Stratum V1 aufteilen müssen.
        """

        result = await self._call(
            "getminingcandidate",
            [provide_coinbase],
        )

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat für "
                "getminingcandidate",
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

        missing_fields = [
            field
            for field in required_fields
            if field not in result
        ]

        if missing_fields:
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate enthält nicht alle "
                "erforderlichen Felder: "
                + ", ".join(missing_fields),
            )

        if provide_coinbase:
            coinbase = result.get("coinbase")

            if not isinstance(coinbase, str) or not coinbase:
                raise BSVNodeRPCError(
                    -32600,
                    "Mining Candidate enthält keine Coinbase",
                )

        if not isinstance(
            result.get("id"),
            str,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate ID ist ungültig",
            )

        if not isinstance(
            result.get("prevhash"),
            str,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate prevhash ist ungültig",
            )

        if not isinstance(
            result.get("version"),
            int,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate version ist ungültig",
            )

        if not isinstance(
            result.get("nBits"),
            str,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate nBits ist ungültig",
            )

        if not isinstance(
            result.get("time"),
            int,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate time ist ungültig",
            )

        if not isinstance(
            result.get("height"),
            int,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate height ist ungültig",
            )

        merkle_proof = result.get("merkleProof")

        if not isinstance(
            merkle_proof,
            list,
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate merkleProof ist ungültig",
            )

        if not all(
            isinstance(item, str)
            for item in merkle_proof
        ):
            raise BSVNodeRPCError(
                -32600,
                "Mining Candidate merkleProof enthält "
                "ungültige Werte",
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

        Der korrekte BSV-RPC ist:

            submitminingsolution

        Der Candidate wird über seine ID identifiziert.
        """

        if not candidate_id:
            raise ValueError(
                "candidate_id darf nicht leer sein",
            )

        if not 0 <= nonce <= 0xFFFFFFFF:
            raise ValueError(
                "nonce muss zwischen 0 und 0xffffffff liegen",
            )

        solution: dict[str, Any] = {
            "id": candidate_id,
            "nonce": nonce,
        }

        if coinbase is not None:
            solution["coinbase"] = coinbase

        if time_value is not None:
            if not 0 <= time_value <= 0xFFFFFFFF:
                raise ValueError(
                    "time muss zwischen 0 und 0xffffffff liegen",
                )

            solution["time"] = time_value

        if version is not None:
            if not 0 <= version <= 0xFFFFFFFF:
                raise ValueError(
                    "version muss zwischen 0 und 0xffffffff liegen",
                )

            solution["version"] = version

        result = await self._call(
            "submitminingsolution",
            [solution],
        )

        return result

    async def ping(self) -> bool:
        """Prüft, ob die BSV-Node erreichbar ist."""

        try:
            await self.get_blockchain_info()
        except BSVNodeRPCError:
            return False

        return True
```

### Warum genau diese Änderung?

Die offizielle BSV-GMC-Spezifikation beschreibt `getminingcandidate` und `submitminingsolution` als zusammengehöriges Verfahren. Der Candidate enthält unter anderem `id`, `prevHash`, `version`, `nBits`, `time`, `height` und `merkleProof`; die ID wird beim späteren `submitminingsolution` wieder verwendet.

**Wir ändern jetzt bewusst noch nichts an `protocol.py`, `server.py`, API oder Dashboard.**

Das ist unser Kontrollpunkt.

### Danach

Wenn du diese **eine Datei** in GitHub ersetzt und committest, schick mir einfach **„fertig“**.

Dann prüfe ich den **tatsächlichen GitHub-Stand erneut**, insbesondere:

* `rpc/client.py`
* alle Imports darauf
* bestehende Tests
* `app.py`
* `protocol.py`
* `server.py`

**Erst wenn Schritt 1 sauber ist, gehen wir zu Schritt 2: Candidate/Job-Datenmodell.**
