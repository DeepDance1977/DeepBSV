from __future__ import annotations

import hashlib


def double_sha256(data: bytes) -> bytes:
    """Berechnet SHA-256(SHA-256(data))."""
    first_hash = hashlib.sha256(data).digest()
    return hashlib.sha256(first_hash).digest()


def calculate_merkle_root(
    tx_hashes: list[bytes],
) -> bytes:
    """
    Berechnet die Merkle Root aus einer Liste von Transaction-Hashes.

    Die Hashes werden in ihrer internen Bitcoin-Byte-Reihenfolge
    verarbeitet. Bei einer ungeraden Anzahl von Hashes wird der
    letzte Hash auf der jeweiligen Ebene dupliziert.
    """
    if not tx_hashes:
        return b"\x00" * 32

    current_level = list(tx_hashes)

    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        next_level: list[bytes] = []

        for index in range(0, len(current_level), 2):
            left = current_level[index]
            right = current_level[index + 1]

            next_level.append(
                double_sha256(left + right)
            )

        current_level = next_level

    return current_level[0]


def build_merkle_branch(
    tx_hashes: list[bytes],
) -> list[bytes]:
    """
    Erstellt den Merkle-Branch für die Coinbase-Transaktion.

    Die Coinbase befindet sich immer an Position 0.
    Deshalb ist auf jeder Merkle-Ebene der Hash an Position 1
    der jeweilige Partner-Hash.

    Die zurückgegebene Reihenfolge entspricht der Reihenfolge,
    in der die Hashes zur Coinbase-Hashberechnung verarbeitet
    werden müssen.
    """
    if len(tx_hashes) <= 1:
        return []

    branch: list[bytes] = []
    current_level = list(tx_hashes)

    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        branch.append(current_level[1])

        next_level: list[bytes] = []

        for index in range(0, len(current_level), 2):
            left = current_level[index]
            right = current_level[index + 1]

            next_level.append(
                double_sha256(left + right)
            )

        current_level = next_level

    return branch


def calculate_merkle_root_from_branch(
    coinbase_hash: bytes,
    merkle_proof: list[bytes],
) -> bytes:
    """
    Berechnet die Merkle Root aus dem Coinbase-Hash und einem
    BSV-GMC-Merkle-Proof.

    BSV liefert die Merkle-Proof-Hashes als Little-Endian-
    Bytefolgen. Die Proof-Elemente werden deshalb direkt mit
    dem aktuellen Hash verkettet und anschließend doppelt
    SHA256-gehasht.

    Das entspricht der von Bitcoin SV verwendeten
    CalculateMerkleRoot-Logik für getminingcandidate.
    """
    if len(coinbase_hash) != 32:
        raise ValueError(
            "coinbase_hash muss genau 32 Bytes lang sein"
        )

    current_hash = coinbase_hash

    for branch_hash in merkle_proof:
        if len(branch_hash) != 32:
            raise ValueError(
                "Jeder Merkle-Proof-Hash muss genau 32 Bytes lang sein"
            )

        current_hash = double_sha256(
            current_hash + branch_hash
        )

    return current_hash


def calculate_merkle_root_from_hex(
    coinbase_hash_hex: str,
    merkle_proof_hex: list[str],
) -> str:
    """
    Komfortfunktion für die Verarbeitung der Hex-Werte aus
    getminingcandidate.

    Eingabe und Ausgabe verwenden die übliche Bitcoin-Hex-
    Darstellung. Intern wird mit den von BSV gelieferten
    Little-Endian-Bytes gearbeitet.
    """
    try:
        coinbase_hash = bytes.fromhex(
            coinbase_hash_hex
        )
    except ValueError as exc:
        raise ValueError(
            "Ungültiger Coinbase-Hash"
        ) from exc

    if len(coinbase_hash) != 32:
        raise ValueError(
            "Coinbase-Hash muss genau 32 Bytes enthalten"
        )

    merkle_proof: list[bytes] = []

    for proof_hex in merkle_proof_hex:
        try:
            proof_hash = bytes.fromhex(proof_hex)
        except ValueError as exc:
            raise ValueError(
                "Ungültiger Merkle-Proof-Hash"
            ) from exc

        if len(proof_hash) != 32:
            raise ValueError(
                "Jeder Merkle-Proof-Hash muss genau 32 Bytes enthalten"
            )

        merkle_proof.append(proof_hash)

    merkle_root = calculate_merkle_root_from_branch(
        coinbase_hash,
        merkle_proof,
    )

    return merkle_root.hex()
