
import hashlib
import logging
import struct

logger = logging.getLogger(__name__)

MAX_UINT256 = (1 << 256) - 1

# Bitcoin-Difficulty-1-Target; wird als Referenz für Share-Difficulty verwendet.
DIFF1_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def double_sha256(data: bytes) -> bytes:
    """Berechnet den Double-SHA256-Hash von Binärdaten."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def nbits_to_target(nbits: int) -> int:
    """Konvertiert das kompakte nBits-Format in ein gültiges 256-Bit-Target."""
    if not isinstance(nbits, int) or isinstance(nbits, bool):
        raise TypeError("nBits muss eine Ganzzahl sein.")

    if not 0 <= nbits <= 0xFFFFFFFF:
        raise ValueError("nBits liegt außerhalb des 32-Bit-Bereichs.")

    exponent = nbits >> 24
    sign_bit = nbits & 0x00800000
    mantissa = nbits & 0x007FFFFF

    if sign_bit:
        raise ValueError("Negatives nBits-Target ist ungültig.")

    if mantissa == 0:
        raise ValueError("nBits darf kein Target von null ergeben.")

    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa << (8 * (exponent - 3))

    if target <= 0 or target > MAX_UINT256:
        raise ValueError("Das aus nBits berechnete Target ist ungültig.")

    return target


def difficulty_to_target(difficulty: float) -> int:
    """Berechnet das Share-Target aus einer positiven Difficulty."""
    if isinstance(difficulty, bool) or not isinstance(difficulty, (int, float)):
        raise TypeError("Difficulty muss eine Zahl sein.")

    if difficulty <= 0:
        raise ValueError("Difficulty muss größer als null sein.")

    target = int(DIFF1_TARGET / difficulty)

    if target < 1:
        return 1

    return min(target, MAX_UINT256)


def reconstruct_coinbase(
    coinbase_1_hex: str,
    extranonce1_hex: str,
    extranonce2_hex: str,
    coinbase_2_hex: str,
) -> bytes:
    """Fügt die vier Hex-Bestandteile der Coinbase-Transaktion zusammen."""
    parts = (
        coinbase_1_hex,
        extranonce1_hex,
        extranonce2_hex,
        coinbase_2_hex,
    )

    try:
        return b"".join(bytes.fromhex(part) for part in parts)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ungültige Hex-Daten in der Coinbase.") from exc


def calculate_merkle_root(
    coinbase_hash: bytes,
    merkle_branches: list[str],
) -> bytes:
    """Berechnet die Merkle-Root aus Coinbase-Hash und Merkle-Branches."""
    if len(coinbase_hash) != 32:
        raise ValueError("Der Coinbase-Hash muss 32 Bytes lang sein.")

    current_hash = coinbase_hash

    for branch_hex in merkle_branches:
        try:
            branch = bytes.fromhex(branch_hex)
        except (TypeError, ValueError) as exc:
            raise ValueError("Ungültiger Hex-Wert im Merkle-Proof.") from exc

        if len(branch) != 32:
            raise ValueError("Jeder Merkle-Branch muss 32 Bytes lang sein.")

        current_hash = double_sha256(current_hash + branch)

    return current_hash


def build_block_header(
    version: int,
    prev_block_hash_hex: str,
    merkle_root: bytes,
    ntime: int,
    nbits: int,
    nonce: int,
) -> bytes:
    """Konstruiert einen 80-Byte-Block-Header."""
    for name, value in (
        ("version", version),
        ("ntime", ntime),
        ("nBits", nbits),
        ("nonce", nonce),
    ):
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} muss eine Ganzzahl sein.")
        if not 0 <= value <= 0xFFFFFFFF:
            raise ValueError(f"{name} liegt außerhalb des 32-Bit-Bereichs.")

    try:
        prev_hash_bytes = bytes.fromhex(prev_block_hash_hex)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ungültiger vorheriger Block-Hash.") from exc

    if len(prev_hash_bytes) != 32:
        raise ValueError("Der vorherige Block-Hash muss 32 Bytes lang sein.")

    if len(merkle_root) != 32:
        raise ValueError("Die Merkle-Root muss 32 Bytes lang sein.")

    header = (
        struct.pack("<I", version)
        + prev_hash_bytes[::-1]
        + merkle_root
        + struct.pack("<I", ntime)
        + struct.pack("<I", nbits)
        + struct.pack("<I", nonce)
    )

    if len(header) != 80:
        raise ValueError(
            f"Ungültige Block-Header-Länge: {len(header)} Bytes."
        )

    return header


def validate_share(
    header_bytes: bytes,
    target: int,
) -> tuple[bool, str, int]:
    """Prüft den Double-SHA256-Hash eines Block-Headers gegen ein Target."""
    if not isinstance(header_bytes, bytes) or len(header_bytes) != 80:
        raise ValueError("Der Block-Header muss genau 80 Bytes lang sein.")

    if not isinstance(target, int) or isinstance(target, bool):
        raise TypeError("Target muss eine Ganzzahl sein.")

    if not 1 <= target <= MAX_UINT256:
        raise ValueError("Target muss zwischen 1 und 2^256-1 liegen.")

    block_hash_bytes = double_sha256(header_bytes)
    hash_int = int.from_bytes(block_hash_bytes, byteorder="little")
    hash_hex = block_hash_bytes[::-1].hex()

    is_valid = hash_int <= target
    return is_valid, hash_hex, hash_int
