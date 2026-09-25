import time
from typing import Any

from deepbsv.block.merkle import build_merkle_branch


class MiningJob:
    """Repräsentiert einen einzelnen Mining-Job, der an Stratum-Clients gesendet wird."""

    def __init__(
        self,
        job_id: str,
        prev_hash: str,
        coinb1: str,
        coinb2: str,
        merkle_branch: list[str],
        version: str,
        nbits: str,
        ntime: str,
        clean_jobs: bool = True,
    ):
        self.job_id = job_id
        self.prev_hash = prev_hash
        self.coinb1 = coinb1
        self.coinb2 = coinb2
        self.merkle_branch = merkle_branch
        self.version = version
        self.nbits = nbits
        self.ntime = ntime
        self.clean_jobs = clean_jobs

    def to_notify_params(self) -> list[Any]:
        """Konvertiert den Job in die Parameter-Liste für `mining.notify`."""
        return [
            self.job_id,
            self.prev_hash,
            self.coinb1,
            self.coinb2,
            self.merkle_branch,
            self.version,
            self.nbits,
            self.ntime,
            self.clean_jobs,
        ]


class BlockTemplate:
    """Verwaltet Daten für ein Block-Template."""

    def __init__(
        self,
        height: int,
        prev_block_hash: str,
        version: int = 0x20000000,
        nbits: str = "1d00ffff",
    ):
        self.height = height
        self.prev_block_hash = prev_block_hash
        self.version = version
        self.nbits = nbits
        self.tx_hashes: list[bytes] = []

    def add_transaction_hash(self, tx_hash: bytes) -> None:
        """Fügt einen Transaktions-Hash (ohne Coinbase) hinzu."""
        self.tx_hashes.append(tx_hash)

    def create_job(
        self,
        job_id: str,
        coinb1_hex: str,
        coinb2_hex: str,
        clean_jobs: bool = True,
    ) -> MiningJob:
        """Erzeugt einen `MiningJob` für das Stratum-Protokoll."""
        # Platzhalter-Hash für Coinbase (32 Zero-Bytes) an Position 0 einfügen
        all_hashes = [b"\x00" * 32, *self.tx_hashes]
        branch_bytes = build_merkle_branch(all_hashes)
        merkle_branch_hex = [b.hex() for b in branch_bytes]

        version_hex = f"{self.version:08x}"
        ntime_hex = f"{int(time.time()):08x}"

        return MiningJob(
            job_id=job_id,
            prev_hash=self.prev_block_hash,
            coinb1=coinb1_hex,
            coinb2=coinb2_hex,
            merkle_branch=merkle_branch_hex,
            version=version_hex,
            nbits=self.nbits,
            ntime=ntime_hex,
            clean_jobs=clean_jobs,
        )
