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
    ) -> MiningCandidate:
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
                "Candidate-ID fehlt oder ist ungültig"
            )

        if not isinstance(prevhash, str):
            raise ValueError(
                "prevhash fehlt oder ist ungültig"
            )

        if not isinstance(coinbase, str):
            raise ValueError(
                "coinbase fehlt oder ist ungültig"
            )

        if not isinstance(version, int):
            raise ValueError(
                "version fehlt oder ist ungültig"
            )

        if not isinstance(nbits, str):
            raise ValueError(
                "nBits fehlt oder ist ungültig"
            )

        if not isinstance(timestamp, int):
            raise ValueError(
                "time fehlt oder ist ungültig"
            )

        if not isinstance(height, int):
            raise ValueError(
                "height fehlt oder ist ungültig"
            )

        if not isinstance(merkle_proof, list):
            raise ValueError(
                "merkleProof fehlt oder ist ungültig"
            )

        if not all(
            isinstance(item, str)
            for item in merkle_proof
        ):
            raise ValueError(
                "merkleProof enthält ungültige Werte"
            )

        return cls(
            candidate_id=candidate_id,
            prevhash=prevhash,
            coinbase=coinbase,
            version=version,
            nbits=nbits,
            timestamp=timestamp,
            height=height,
            merkle_proof=tuple(merkle_proof),
        )


@dataclass(slots=True, frozen=True)
class MiningJob:
    """Ein von Stratum-Miner verteilbarer Mining-Job."""

    job_id: str
    candidate: MiningCandidate
    clean_jobs: bool = True
