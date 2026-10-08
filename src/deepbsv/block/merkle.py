from __future__ import annotations

import hashlib


def double_sha256(data: bytes) -> bytes:
    """Berechnet SHA256(SHA256(data))."""

    return hashlib.sha256(
        hashlib.sha256(data).digest()
    ).digest()


def hash_pair(left: bytes, right: bytes) -> bytes:
    """Berechnet den Double-SHA256-Hash eines Hash-Paares."""

    return double_sha256(left + right)


def calculate_merkle_root(
    coinbase_hash: bytes,
    merkle_proof: tuple[str, ...] | list[str],
) -> bytes:
    """
    Berechnet die Merkle-Root aus Coinbase-Hash und BSV-Merkle-Proof.

    Die Einträge des BSV-Merkle-Proofs werden als Little-Endian
    Hexwerte geliefert und entsprechend verarbeitet.
    """

    current = coinbase_hash

    for proof_hash_hex in merkle_proof:
        if len(proof_hash_hex) != 64:
            raise ValueError(
                "Merkle-Proof-Eintrag muss 32 Bytes enthalten",
            )

        try:
            proof_hash = bytes.fromhex(
                proof_hash_hex,
            )
        except ValueError as exc:
            raise ValueError(
                "Merkle-Proof enthält ungültiges Hex",
            ) from exc

        current = hash_pair(
            current,
            proof_hash,
        )

    return current


def calculate_merkle_root_hex(
    coinbase_hash: bytes,
    merkle_proof: tuple[str, ...] | list[str],
) -> str:
    """Berechnet die Merkle-Root und gibt sie als Hex zurück."""

    return calculate_merkle_root(
        coinbase_hash,
        merkle_proof,
    ).hex()
