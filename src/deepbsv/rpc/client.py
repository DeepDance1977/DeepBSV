```python
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

        result = await self._call("getblockchaininfo")

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat von getblockchaininfo",
            )

        return result

    async def get_network_info(self) -> dict[str, Any]:
        """Liest den Netzwerkstatus der BSV-Node."""

        result = await self._call("getnetworkinfo")

        if not isinstance(result, dict):
            raise BSVNodeRPCError(
                -32600,
                "Ungültiges Antwortformat von getnetworkinfo",
            )

        return result

    async def get_block_count(self) -> int:
        """Liest die aktuelle Blockhöhe."""

        result = await self._call("getblockcount")

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
        Holt einen aktuellen Bitcoin-SV Mining Candidate.

        BSV verwendet getminingcandidate als Teil des
        Get-Mining-Candidate-Protokolls.
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
        Reicht eine gefundene Mining-Lösung bei der BSV-Node ein.

        BSV verwendet dafür ausdrücklich:
        submitminingsolution
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
        """Prüft, ob die BSV-Node erreichbar ist."""

        try:
            await self.get_blockchain_info()
        except BSVNodeRPCError:
            return False

        return True
```

Der wesentliche Fix ist hier `submitminingsolution`. Genau diesen RPC definiert BSV für Lösungen aus `getminingcandidate`.

---

# 2. `src/deepbsv/mining/models.py`

Neue Datei:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MiningCandidate:
    """Ein von der BSV-Node bereitgestellter Mining Candidate."""

    candidate_id: str
    prevhash: str
    coinbase: str
    version: int
    nbits: str
    timestamp: int
    height: int
    merkle_proof: tuple[str, ...]

    @classmethod
    def from_rpc(
        cls,
        data: dict[str, object],
    ) -> "MiningCandidate":
        candidate_id = data.get("id")
        prevhash = data.get("prevhash")
        coinbase = data.get("coinbase")
        version = data.get("version")
        nbits = data.get("nBits")
        timestamp = data.get("time")
        height = data.get("height")
        merkle_proof = data.get("merkleProof")

        if not isinstance(candidate_id, str):
            raise ValueError(
                "Candidate-ID fehlt oder ist ungültig",
            )

        if not isinstance(prevhash, str):
            raise ValueError(
                "prevhash fehlt oder ist ungültig",
            )

        if not isinstance(coinbase, str):
            raise ValueError(
                "coinbase fehlt oder ist ungültig",
            )

        if not isinstance(version, int):
            raise ValueError(
                "version fehlt oder ist ungültig",
            )

        if not isinstance(nbits, str):
            raise ValueError(
                "nBits fehlt oder ist ungültig",
            )

        if not isinstance(timestamp, int):
            raise ValueError(
                "time fehlt oder ist ungültig",
            )

        if not isinstance(height, int):
            raise ValueError(
                "height fehlt oder ist ungültig",
            )

        if not isinstance(merkle_proof, list):
            raise ValueError(
                "merkleProof fehlt oder ist ungültig",
            )

        if not all(
            isinstance(item, str)
            for item in merkle_proof
        ):
            raise ValueError(
                "merkleProof enthält ungültige Werte",
            )

        return cls(
            candidate_id=candidate_id,
            prevhash=prevhash,
            coinbase=coinbase,
            version=version,
            nbits=nbits.lower(),
            timestamp=timestamp,
            height=height,
            merkle_proof=tuple(merkle_proof),
        )


@dataclass(slots=True, frozen=True)
class MiningJob:
    """Ein an Stratum-Miner verteilbarer Mining-Job."""

    job_id: str
    candidate: MiningCandidate
    clean_jobs: bool = True
```

---

# 3. `src/deepbsv/mining/candidate_manager.py`

Neue Datei:

```python
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from deepbsv.mining.models import MiningCandidate, MiningJob
from deepbsv.rpc.client import (
    BSVNodeRPCClient,
    BSVNodeRPCError,
)

logger = logging.getLogger(__name__)

CandidateCallback = Callable[
    [MiningJob],
    Awaitable[None],
]


class CandidateManager:
    """
    Verwaltet den aktuell gültigen Bitcoin-SV Mining Candidate.

    Die Node wird regelmäßig nach einem neuen Candidate gefragt.
    Ein neuer Job wird erzeugt, sobald sich die Blockhöhe,
    PrevHash, Candidate-ID oder Difficulty verändert.
    """

    def __init__(
        self,
        rpc: BSVNodeRPCClient,
        poll_interval: float = 2.0,
    ) -> None:
        self.rpc = rpc
        self.poll_interval = poll_interval

        self._current_candidate: MiningCandidate | None = None
        self._current_job: MiningJob | None = None

        self._callbacks: list[CandidateCallback] = []

        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

        self._job_counter = 0

        self.last_error: str | None = None

    @property
    def current_candidate(
        self,
    ) -> MiningCandidate | None:
        return self._current_candidate

    @property
    def current_job(
        self,
    ) -> MiningJob | None:
        return self._current_job

    @property
    def is_running(self) -> bool:
        return (
            self._task is not None
            and not self._task.done()
        )

    def add_callback(
        self,
        callback: CandidateCallback,
    ) -> None:
        """Registriert einen Callback für neue Mining-Jobs."""

        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(
        self,
        callback: CandidateCallback,
    ) -> None:
        """Entfernt einen Callback."""

        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def start(self) -> None:
        """Startet die Candidate-Überwachung."""

        if self.is_running:
            return

        self._stop_event.clear()

        self._task = asyncio.create_task(
            self._run(),
            name="deepbsv-candidate-manager",
        )

        logger.info(
            "BSV Candidate Manager gestartet",
        )

    async def stop(self) -> None:
        """Stoppt die Candidate-Überwachung."""

        self._stop_event.set()

        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None

        logger.info(
            "BSV Candidate Manager gestoppt",
        )

    async def refresh_now(
        self,
    ) -> MiningJob | None:
        """Holt sofort einen Candidate von der BSV-Node."""

        try:
            data = await self.rpc.get_mining_candidate(
                provide_coinbase=True,
            )

            candidate = MiningCandidate.from_rpc(data)

            if self._candidate_changed(candidate):
                return await self._install_candidate(
                    candidate,
                )

            self.last_error = None

            return self._current_job

        except (
            BSVNodeRPCError,
            ValueError,
        ) as exc:
            self.last_error = str(exc)

            logger.warning(
                "Mining Candidate konnte nicht "
                "aktualisiert werden: %s",
                exc,
            )

            return self._current_job

    def _candidate_changed(
        self,
        candidate: MiningCandidate,
    ) -> bool:
        if self._current_candidate is None:
            return True

        current = self._current_candidate

        return any(
            (
                candidate.candidate_id
                != current.candidate_id,
                candidate.height
                != current.height,
                candidate.prevhash
                != current.prevhash,
                candidate.nbits
                != current.nbits,
            )
        )

    async def _install_candidate(
        self,
        candidate: MiningCandidate,
    ) -> MiningJob:
        self._job_counter += 1

        job_id = (
            f"{candidate.height:x}-"
            f"{self._job_counter:x}"
        )

        job = MiningJob(
            job_id=job_id,
            candidate=candidate,
            clean_jobs=True,
        )

        self._current_candidate = candidate
        self._current_job = job
        self.last_error = None

        logger.info(
            "Neuer BSV Mining Job: "
            "job=%s height=%d candidate=%s",
            job.job_id,
            candidate.height,
            candidate.candidate_id,
        )

        for callback in tuple(self._callbacks):
            try:
                await callback(job)
            except Exception:
                logger.exception(
                    "Fehler im Candidate-Callback",
                )

        return job

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self.refresh_now()

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval,
                )
            except asyncio.TimeoutError:
                continue
```

Damit gibt es jetzt eine zentrale Stelle, die den Node-Candidate überwacht. Das passt auch zum BSV-GMC-Konzept: Der Node liefert einen Candidate samt Tracking-ID; diese ID wird später beim Submit wieder verwendet.

---

# 4. `src/deepbsv/mining/coinbase.py`

**Neue Datei.**

Hier passiert etwas sehr Wichtiges: Wir nehmen die echte Coinbase aus dem BSV-Node und machen daraus `coinb1` + `coinb2`, sodass der ASIC seine `extranonce1` und `extranonce2` einsetzen kann.

```python
from __future__ import annotations

from dataclasses import dataclass


class CoinbaseError(ValueError):
    """Fehler beim Verarbeiten einer Coinbase-Transaktion."""


def read_compact_size(
    data: bytes,
    offset: int,
) -> tuple[int, int]:
    """Liest einen Bitcoin CompactSize-Wert."""

    if offset >= len(data):
        raise CoinbaseError(
            "CompactSize außerhalb der Transaktion",
        )

    prefix = data[offset]

    if prefix < 253:
        return prefix, offset + 1

    if prefix == 253:
        end = offset + 3

        if end > len(data):
            raise CoinbaseError(
                "CompactSize uint16 abgeschnitten",
            )

        return (
            int.from_bytes(
                data[offset + 1:end],
                "little",
            ),
            end,
        )

    if prefix == 254:
        end = offset + 5

        if end > len(data):
            raise CoinbaseError(
                "CompactSize uint32 abgeschnitten",
            )

        return (
            int.from_bytes(
                data[offset + 1:end],
                "little",
            ),
            end,
        )

    end = offset + 9

    if end > len(data):
        raise CoinbaseError(
            "CompactSize uint64 abgeschnitten",
        )

    return (
        int.from_bytes(
            data[offset + 1:end],
            "little",
        ),
        end,
    )


def encode_compact_size(value: int) -> bytes:
    """Kodiert einen Bitcoin CompactSize-Wert."""

    if value < 0:
        raise CoinbaseError(
            "CompactSize darf nicht negativ sein",
        )

    if value < 253:
        return bytes([value])

    if value <= 0xFFFF:
        return (
            b"\xfd"
            + value.to_bytes(
                2,
                "little",
            )
        )

    if value <= 0xFFFFFFFF:
        return (
            b"\xfe"
            + value.to_bytes(
                4,
                "little",
            )
        )

    if value <= 0xFFFFFFFFFFFFFFFF:
        return (
            b"\xff"
            + value.to_bytes(
                8,
                "little",
            )
        )

    raise CoinbaseError(
        "CompactSize-Wert ist zu groß",
    )


@dataclass(slots=True, frozen=True)
class CoinbaseParts:
    """
    Stratum-Darstellung einer Coinbase-Transaktion.

    coinb1 enthält den Anfang bis unmittelbar vor
    den Extranonce-Daten.

    coinb2 enthält den Rest der Coinbase-Transaktion.
    """

    coinb1: str
    coinb2: str
    script_sig_length: int

    def build(
        self,
        extranonce1: str,
        extranonce2: str,
    ) -> str:
        """Baut die vollständige Coinbase-Transaktion."""

        ex1 = bytes.fromhex(extranonce1)
        ex2 = bytes.fromhex(extranonce2)

        return (
            self.coinb1
            + ex1.hex()
            + ex2.hex()
            + self.coinb2
        )


def split_coinbase(
    coinbase_hex: str,
    extranonce_size: int,
) -> CoinbaseParts:
    """
    Teilt eine BSV-Coinbase für Stratum V1 auf.

    Die Extranonce wird am Ende der Coinbase-scriptSig
    eingefügt. Dadurch bleibt die restliche Coinbase
    unverändert.

    extranonce_size ist die Gesamtgröße von extranonce1
    und extranonce2 in Bytes.
    """

    if not coinbase_hex:
        raise CoinbaseError(
            "Coinbase ist leer",
        )

    try:
        transaction = bytes.fromhex(
            coinbase_hex,
        )
    except ValueError as exc:
        raise CoinbaseError(
            "Coinbase enthält ungültiges Hex",
        ) from exc

    if len(transaction) < 10:
        raise CoinbaseError(
            "Coinbase ist zu kurz",
        )

    offset = 0

    # nVersion
    if len(transaction) < offset + 4:
        raise CoinbaseError(
            "Coinbase-Version fehlt",
        )

    offset += 4

    # Coinbase muss genau einen Input besitzen.
    input_count, offset = read_compact_size(
        transaction,
        offset,
    )

    if input_count != 1:
        raise CoinbaseError(
            "Coinbase muss genau einen Input besitzen",
        )

    # Previous transaction hash
    if len(transaction) < offset + 32:
        raise CoinbaseError(
            "Coinbase-PrevHash fehlt",
        )

    offset += 32

    # Previous output index
    if len(transaction) < offset + 4:
        raise CoinbaseError(
            "Coinbase-PrevIndex fehlt",
        )

    offset += 4

    script_length_offset = offset

    script_length, script_start = read_compact_size(
        transaction,
        offset,
    )

    script_end = script_start + script_length

    if script_end > len(transaction):
        raise CoinbaseError(
            "Coinbase-scriptSig ist abgeschnitten",
        )

    if script_length + extranonce_size > 100:
        raise CoinbaseError(
            "Coinbase-scriptSig würde durch die Extranonce "
            "größer als 100 Bytes werden",
        )

    new_script_length = (
        script_length + extranonce_size
    )

    prefix = (
        transaction[:script_length_offset]
        + encode_compact_size(new_script_length)
        + transaction[script_start:script_end]
    )

    suffix = transaction[script_end:]

    return CoinbaseParts(
        coinb1=prefix.hex(),
        coinb2=suffix.hex(),
        script_sig_length=new_script_length,
    )
```

Das ist bewusst nicht die typische „irgendwo 8 Bytes in einen String reinschieben“-Lösung. Die Coinbase-scriptSig-Länge wird korrekt angepasst.

---

# 5. `src/deepbsv/mining/header.py`

**Neue Datei.**

```python
from __future__ import annotations

import hashlib


class HeaderError(ValueError):
    """Fehler beim Aufbau eines Bitcoin-Blockheaders."""


def double_sha256(
    data: bytes,
) -> bytes:
    """SHA256(SHA256(data))."""

    return hashlib.sha256(
        hashlib.sha256(data).digest()
    ).digest()


def reverse_hex(
    value: str,
) -> str:
    """Kehrt die Byte-Reihenfolge eines Hex-Strings um."""

    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise HeaderError(
            "Ungültiger Hex-String",
        ) from exc

    return raw[::-1].hex()


def calculate_merkle_root(
    coinbase_hex: str,
    merkle_proof: tuple[str, ...],
) -> bytes:
    """
    Berechnet die interne Merkle Root.

    Bitcoin SV liefert die uint256-Werte als Hex-Darstellung.
    Für die Hash-Berechnung werden sie in ihre interne
    Byte-Reihenfolge umgewandelt.
    """

    try:
        coinbase = bytes.fromhex(
            coinbase_hex,
        )
    except ValueError as exc:
        raise HeaderError(
            "Ungültige Coinbase",
        ) from exc

    current = double_sha256(coinbase)

    for branch_hex in merkle_proof:
        try:
            branch = bytes.fromhex(
                branch_hex,
            )
        except ValueError as exc:
            raise HeaderError(
                "Ungültiger Merkle-Proof",
            ) from exc

        if len(branch) != 32:
            raise HeaderError(
                "Merkle-Proof-Element muss 32 Bytes lang sein",
            )

        current = double_sha256(
            current + branch[::-1],
        )

    return current


def build_block_header(
    version: int,
    prevhash: str,
    merkle_root: bytes,
    ntime: int,
    nbits: str,
    nonce: int,
) -> bytes:
    """Baut einen vollständigen 80-Byte-Blockheader."""

    if not 0 <= version <= 0xFFFFFFFF:
        raise HeaderError(
            "Version außerhalb uint32",
        )

    if not 0 <= ntime <= 0xFFFFFFFF:
        raise HeaderError(
            "Zeit außerhalb uint32",
        )

    if not 0 <= nonce <= 0xFFFFFFFF:
        raise HeaderError(
            "Nonce außerhalb uint32",
        )

    try:
        prevhash_bytes = bytes.fromhex(
            prevhash,
        )
        nbits_bytes = bytes.fromhex(
            nbits,
        )
    except ValueError as exc:
        raise HeaderError(
            "Ungültiger Blockheader-Hexwert",
        ) from exc

    if len(prevhash_bytes) != 32:
        raise HeaderError(
            "PrevHash muss 32 Bytes lang sein",
        )

    if len(merkle_root) != 32:
        raise HeaderError(
            "Merkle Root muss 32 Bytes lang sein",
        )

    if len(nbits_bytes) != 4:
        raise HeaderError(
            "nBits muss 4 Bytes lang sein",
        )

    header = (
        version.to_bytes(4, "little")
        + prevhash_bytes[::-1]
        + merkle_root
        + ntime.to_bytes(4, "little")
        + nbits_bytes[::-1]
        + nonce.to_bytes(4, "little")
    )

    if len(header) != 80:
        raise HeaderError(
            f"Blockheader muss 80 Bytes lang sein, "
            f"ist aber {len(header)} Bytes lang",
        )

    return header


def calculate_block_hash(
    header: bytes,
) -> bytes:
    """Berechnet den internen Double-SHA256-Blockhash."""

    if len(header) != 80:
        raise HeaderError(
            "Blockheader muss exakt 80 Bytes lang sein",
        )

    return double_sha256(header)


def calculate_display_hash(
    header: bytes,
) -> str:
    """
    Berechnet den üblichen menschenlesbaren Blockhash.
    """

    return calculate_block_hash(
        header,
    )[::-1].hex()


def hash_to_integer(
    header: bytes,
) -> int:
    """
    Wandelt den Blockhash in die für Difficulty-Vergleiche
    verwendete Integer-Darstellung um.
    """

    return int.from_bytes(
        calculate_block_hash(header)[::-1],
        "big",
    )
```

Der Aufbau folgt dabei dem BSV-Code: Der Node berechnet die Merkle Root aus Coinbase-Hash und den vom Candidate gelieferten Merkle-Branches und verwendet anschließend Nonce, Zeit, Version und die ursprünglichen Difficulty-Bits für die Lösung.

---

## Der nächste Schritt

Damit haben wir jetzt die Bausteine:

```text
BSV Node
   │
   └── getminingcandidate(true)
              │
              ▼
       MiningCandidate
              │
              ▼
        CoinbaseParts
              │
              ├── coinb1
              └── coinb2
              │
              ▼
       Stratum mining.notify
              │
              ▼
          Bitaxe / ASIC
              │
        mining.submit
              │
              ▼
      Coinbase + Merkle Root
              │
              ▼
        80-Byte Header
              │
              ▼
       Double SHA-256
              │
       ┌──────┴──────┐
       │             │
   Share gültig   Block gültig
       │             │
       ▼             ▼
   accepted    submitminingsolution
```

**Als Nächstes kommt jetzt `protocol.py` und `server.py`.** Dort verbinden wir diese Bausteine tatsächlich miteinander. Erst dann bekommt dein Bitaxe beim `mining.subscribe` einen echten `extranonce1`, anschließend `mining.notify` mit einem echten BSV-Job und bei `mining.submit` wird der eingereichte Nonce **wirklich kryptografisch geprüft**.

Das ist der Punkt, an dem DeepBSV vom bisherigen Prototypen zum echten Solo-Mining-Core wird.
