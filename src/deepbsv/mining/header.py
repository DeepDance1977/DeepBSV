from __future__ import annotations

import hashlib


def double_sha256(data: bytes) -> bytes:
    """Berechnet SHA256(SHA256(data))."""

    return hashlib.sha256(
        hashlib.sha256(data).digest()
    ).digest()


def _parse_nbits(nbits: str) -> int:
    """Wandelt compact difficulty nBits in ein Target um."""

    if len(nbits) != 8:
        raise ValueError(
            "nBits muss genau 4 Bytes enthalten",
        )

    try:
        compact = int(nbits, 16)
    except ValueError as exc:
        raise ValueError(
            "nBits enthält ungültiges Hex",
        ) from exc

    exponent = compact >> 24
    mantissa = compact & 0x007FFFFF

    if compact & 0x00800000:
        raise ValueError(
            "Negatives nBits-Target ist ungültig",
        )

    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa << (8 * (exponent - 3))

    if target <= 0:
        raise ValueError(
            "nBits ergibt ein ungültiges Target",
        )

    return target


def target_from_nbits(nbits: str) -> int:
    """Gibt das vollständige numerische Mining-Target zurück."""

    return _parse_nbits(nbits)


def _uint32_to_le(value: int) -> bytes:
    """Kodiert einen Integer als Little-Endian uint32."""

    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(
            "Wert muss zwischen 0 und 0xffffffff liegen",
        )

    return value.to_bytes(
        4,
        "little",
    )


def _hash_to_wire_bytes(hash_hex: str) -> bytes:
    """Wandelt einen Hash aus RPC-Hex in Wire-Byte-Reihenfolge um."""

    if len(hash_hex) != 64:
        raise ValueError(
            "Hash muss genau 32 Bytes enthalten",
        )

    try:
        value = bytes.fromhex(hash_hex)
    except ValueError as exc:
        raise ValueError(
            "Hash enthält ungültiges Hex",
        ) from exc

    return value[::-1]


def build_block_header(
    version: int,
    prevhash: str,
    merkle_root: bytes,
    timestamp: int,
    nbits: str,
    nonce: int,
) -> bytes:
    """Erstellt einen vollständigen 80-Byte-Bitcoin-Blockheader."""

    if len(merkle_root) != 32:
        raise ValueError(
            "Merkle-Root muss genau 32 Bytes enthalten",
        )

    header = (
        _uint32_to_le(version)
        + _hash_to_wire_bytes(prevhash)
        + merkle_root
        + _uint32_to_le(timestamp)
        + _uint32_to_le(
            int(nbits, 16),
        )
        + _uint32_to_le(nonce)
    )

    if len(header) != 80:
        raise ValueError(
            "Blockheader muss genau 80 Bytes lang sein",
        )

    return header


def hash_block_header(header: bytes) -> bytes:
    """Berechnet den Double-SHA256-Hash eines Blockheaders."""

    if len(header) != 80:
        raise ValueError(
            "Blockheader muss genau 80 Bytes lang sein",
        )

    return double_sha256(header)


def hash_block_header_int(header: bytes) -> int:
    """Gibt den Blockheader-Hash als Integer zurück."""

    return int.from_bytes(
        hash_block_header(header),
        "little",
    )


def meets_target(
    header: bytes,
    nbits: str,
) -> bool:
    """Prüft, ob ein Blockheader das Netzwerk-Target erreicht."""

    target = target_from_nbits(
        nbits,
    )

    hash_value = hash_block_header_int(
        header,
    )

    return hash_value <= target


def validate_nonce(
    version: int,
    prevhash: str,
    merkle_root: bytes,
    timestamp: int,
    nbits: str,
    nonce: int,
) -> tuple[bytes, bool]:
    """Erstellt und prüft einen Blockheader für einen Nonce."""

    header = build_block_header(
        version=version,
        prevhash=prevhash,
        merkle_root=merkle_root,
        timestamp=timestamp,
        nbits=nbits,
        nonce=nonce,
    )

    return (
        header,
        meets_target(
            header,
            nbits,
        ),
    )
