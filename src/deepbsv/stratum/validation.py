import hashlib
import struct
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def double_sha256(data: bytes) -> bytes:
    """Berechnet den Double-SHA256 Hash von Binärdaten."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def nbits_to_target(nbits: int) -> int:
    """Konvertiert nBits (Kompaktes Format) in eine 256-Bit Target-Zahl."""
    exponent = nbits >> 24
    mantissa = nbits & 0x7FFFFF

    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa << (8 * (exponent - 3))

    if nbits & 0x00800000:
        target = -target

    return target


def reconstruct_coinbase(
    coinbase_1_hex: str,
    extranonce1_hex: str,
    extranonce2_hex: str,
    coinbase_2_hex: str,
) -> bytes:
    """Fügt die Bestandteile der Coinbase-Transaktion zusammen."""
    cb1 = bytes.fromhex(coinbase_1_hex)
    ext1 = bytes.fromhex(extranonce1_hex)
    ext2 = bytes.fromhex(extranonce2_hex)
    cb2 = bytes.fromhex(coinbase_2_hex)
    return cb1 + ext1 + ext2 + cb2


def calculate_merkle_root(coinbase_hash: bytes, merkle_branches: list[str]) -> bytes:
    """
    Berechnet die Merkle-Root aus dem Coinbase-Hash und den Merkle-Branches.
    
    Jeder Branch in merkle_branches ist als Hex-String in Big-Endian/Little-Endian angegeben.
    """
    current_hash = coinbase_hash
    for branch_hex in merkle_branches:
        branch = bytes.fromhex(branch_hex)
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
    """
    Konstruiert den 80-Byte Bitcoin-Blockheader im Little-Endian-Format.
    
    Header-Struktur (80 Bytes):
    - Version (4 Bytes)
    - Prev Block Hash (32 Bytes, reverses Byte-Ordering)
    - Merkle Root (32 Bytes)
    - Timestamp / nTime (4 Bytes)
    - Bits / nBits (4 Bytes)
    - Nonce (4 Bytes)
    """
    version_bytes = struct.pack("<I", version)
    prev_hash_bytes = bytes.fromhex(prev_block_hash_hex)[::-1]
    ntime_bytes = struct.pack("<I", ntime)
    nbits_bytes = struct.pack("<I", nbits)
    nonce_bytes = struct.pack("<I", nonce)

    header = (
        version_bytes
        + prev_hash_bytes
        + merkle_root
        + ntime_bytes
        + nbits_bytes
        + nonce_bytes
    )
    
    if len(header) != 80:
        raise ValueError(f"Ungültige Block-Header-Länge: {len(header)} Bytes (erwartet: 80)")
        
    return header


def validate_share(
    header_bytes: bytes,
    target: int,
) -> Tuple[bool, str, int]:
    """
    Prüft, ob der Double-SHA256 Hash des Headers unter dem Target liegt.
    
    Gibt ein Tupel zurück:
    (is_valid, hash_hex, hash_int)
    """
    block_hash_bytes = double_sha256(header_bytes)
    # Der Hash wird in Little-Endian umgekehrt, um die numerische Größe zu bestimmen
    hash_int = int.from_bytes(block_hash_bytes[::-1], byteorder="big")
    hash_hex = block_hash_bytes[::-1].hex()

    is_valid = hash_int <= target
    return is_valid, hash_hex, hash_int
