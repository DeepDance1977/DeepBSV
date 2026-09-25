import hashlib


def double_sha256(data: bytes) -> bytes:
    """Berechnet SHA-256(SHA-256(data))."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def calculate_merkle_root(tx_hashes: list[bytes]) -> bytes:
    """Berechnet den Merkle Root aus einer Liste von Transaktions-Hashes (in Little-Endian/Internal Byte Order)."""
    if not tx_hashes:
        return b"\x00" * 32

    current_level = list(tx_hashes)
    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            next_level.append(double_sha256(combined))
        current_level = next_level

    return current_level[0]


def build_merkle_branch(tx_hashes: list[bytes]) -> list[bytes]:
    """Erstellt den Merkle Branch für die Coinbase-Transaktion (Index 0).

    Gibt die Liste der Partner-Hashes zurück, die der Stratum-Miner benötigt,
    um den Merkle Root zu berechnen.
    """
    if not tx_hashes:
        return []

    branch: list[bytes] = []
    current_level = list(tx_hashes)

    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        # Der Partner für Index 0 liegt auf diesem Level immer an Index 1
        branch.append(current_level[1])

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            next_level.append(double_sha256(combined))

        current_level = next_level

    return branch
