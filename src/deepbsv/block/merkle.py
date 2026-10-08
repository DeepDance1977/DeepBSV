from __future__ import annotations

import hashlib


def double_sha256(data: bytes) -> bytes:
    """Berechnet SHA256(SHA256(data))."""

    return hashlib.sha256(
        hashlib.sha256(data).digest()
    ).digest()


def calculate_merkle_root(
    coinbase_hash: bytes,
    merkle_branch: list[bytes],
) -> bytes:
    """
    Berechnet die Merkle Root aus Coinbase-Hash
    und Merkle Branch.

    Der BSV getminingcandidate-RPC liefert die
    Merkle-Proof-Hashes in Little-Endian/Internal
    Byte Order.
    """

    if len(coinbase_hash) != 32:
        raise ValueError(
            "Coinbase-Hash muss exakt 32 Bytes lang sein",
        )

    current = coinbase_hash

    for branch_hash in merkle_branch:
        if len(branch_hash) != 32:
            raise ValueError(
                "Merkle-Branch-Hash muss exakt 32 Bytes lang sein",
            )

        current = double_sha256(
            current + branch_hash,
        )

    return current


def calculate_merkle_root_from_hex(
    coinbase_hash_hex: str,
    merkle_branch_hex: list[str],
) -> str:
    """
    Berechnet die Merkle Root aus Hex-Werten und
    gibt sie als Little-Endian/Internal Hex zurück.
    """

    coinbase_hash = bytes.fromhex(
        coinbase_hash_hex,
    )

    branch = [
        bytes.fromhex(item)
        for item in merkle_branch_hex
    ]

    return calculate_merkle_root(
        coinbase_hash,
        branch,
    ).hex()


def build_merkle_branch(
    tx_hashes: list[bytes],
) -> list[bytes]:
    """
    Baut einen Merkle Branch für die Coinbase-Transaktion
    an Index 0.

    Diese Funktion ist hauptsächlich für Tests und
    lokale Berechnungen gedacht.
    """

    if not tx_hashes:
        return []

    current_level = list(tx_hashes)
    branch: list[bytes] = []

    while len(current_level) > 1:
        if len(current_level) % 2:
            current_level.append(
                current_level[-1],
            )

        branch.append(
            current_level[1],
        )

        next_level: list[bytes] = []

        for index in range(
            0,
            len(current_level),
            2,
        ):
            next_level.append(
                double_sha256(
                    current_level[index]
                    + current_level[index + 1],
                ),
            )

        current_level = next_level

    return branch
