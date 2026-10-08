from __future__ import annotations

import hashlib


def double_sha256(data: bytes) -> bytes:
    """Berechnet SHA256(SHA256(data))."""

    return hashlib.sha256(
        hashlib.sha256(data).digest()
    ).digest()


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    """Liest einen Bitcoin-CompactSize-Wert."""

    if offset >= len(data):
        raise ValueError(
            "Unerwartetes Ende beim Lesen der VarInt",
        )

    prefix = data[offset]

    if prefix < 0xFD:
        return prefix, offset + 1

    if prefix == 0xFD:
        end = offset + 3
        if end > len(data):
            raise ValueError(
                "Unerwartetes Ende beim Lesen der VarInt",
            )
        return int.from_bytes(
            data[offset + 1:end],
            "little",
        ), end

    if prefix == 0xFE:
        end = offset + 5
        if end > len(data):
            raise ValueError(
                "Unerwartetes Ende beim Lesen der VarInt",
            )
        return int.from_bytes(
            data[offset + 1:end],
            "little",
        ), end

    end = offset + 9
    if end > len(data):
        raise ValueError(
            "Unerwartetes Ende beim Lesen der VarInt",
        )

    return int.from_bytes(
        data[offset + 1:end],
        "little",
    ), end


def _encode_varint(value: int) -> bytes:
    """Kodiert einen Bitcoin-CompactSize-Wert."""

    if value < 0:
        raise ValueError(
            "VarInt darf nicht negativ sein",
        )

    if value < 0xFD:
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

    raise ValueError(
        "VarInt-Wert ist zu groß",
    )


def _read_pushdata(
    script: bytes,
) -> tuple[bytes, bytes]:
    """
    Liest den ersten Push aus einem Script.

    Der erste Push einer BSV-Coinbase enthält bei einem normalen
    aktuellen Candidate die Blockhöhe nach BIP34.
    """

    if not script:
        raise ValueError(
            "Coinbase-ScriptSig ist leer",
        )

    opcode = script[0]

    if opcode == 0:
        return b"", script[1:]

    if opcode <= 75:
        length = opcode
        prefix_length = 1
    elif opcode == 0x4C:
        if len(script) < 2:
            raise ValueError(
                "Ungültiger OP_PUSHDATA1",
            )
        length = script[1]
        prefix_length = 2
    elif opcode == 0x4D:
        if len(script) < 3:
            raise ValueError(
                "Ungültiger OP_PUSHDATA2",
            )
        length = int.from_bytes(
            script[1:3],
            "little",
        )
        prefix_length = 3
    elif opcode == 0x4E:
        if len(script) < 5:
            raise ValueError(
                "Ungültiger OP_PUSHDATA4",
            )
        length = int.from_bytes(
            script[1:5],
            "little",
        )
        prefix_length = 5
    else:
        raise ValueError(
            "Erster Coinbase-ScriptSig-Bestandteil ist kein Pushdata",
        )

    start = prefix_length
    end = start + length

    if end > len(script):
        raise ValueError(
            "Coinbase-ScriptSig enthält einen unvollständigen Push",
        )

    return script[:end], script[end:]


def split_coinbase(
    coinbase_hex: str,
    extranonce1_size: int,
    extranonce2_size: int,
) -> tuple[str, str]:
    """
    Teilt eine vorhandene BSV-Coinbase für Stratum V1 auf.

    Die Extranonces werden direkt hinter den ersten Push des Coinbase-
    ScriptSigs eingefügt. Bei einer BIP34-Coinbase ist dies der
    Blockhöhen-Push.

    Die zurückgegebenen Teile ergeben zusammen mit
    Extranonce1 + Extranonce2 wieder eine vollständige Coinbase:

        coinbase1 + extranonce1 + extranonce2 + coinbase2
    """

    if extranonce1_size < 0:
        raise ValueError(
            "extranonce1_size darf nicht negativ sein",
        )

    if extranonce2_size < 0:
        raise ValueError(
            "extranonce2_size darf nicht negativ sein",
        )

    try:
        coinbase = bytes.fromhex(
            coinbase_hex,
        )
    except ValueError as exc:
        raise ValueError(
            "Coinbase enthält ungültiges Hex",
        ) from exc

    if len(coinbase) < 4:
        raise ValueError(
            "Coinbase ist zu kurz",
        )

    offset = 4

    input_count, offset = _read_varint(
        coinbase,
        offset,
    )

    if input_count != 1:
        raise ValueError(
            "Coinbase muss genau einen Input enthalten",
        )

    if offset + 36 > len(coinbase):
        raise ValueError(
            "Coinbase enthält keinen vollständigen Prevout",
        )

    prevout = coinbase[
        offset:offset + 36
    ]
    offset += 36

    script_length, script_offset = _read_varint(
        coinbase,
        offset,
    )

    script_start = script_offset
    script_end = script_start + script_length

    if script_end > len(coinbase):
        raise ValueError(
            "Coinbase-ScriptSig ist unvollständig",
        )

    script_sig = coinbase[
        script_start:script_end
    ]

    height_push, script_remainder = _read_pushdata(
        script_sig,
    )

    new_script_length = (
        len(script_sig)
        + extranonce1_size
        + extranonce2_size
    )

    if new_script_length > 100:
        raise ValueError(
            "Coinbase-ScriptSig überschreitet 100 Bytes",
        )

    prefix = (
        coinbase[:4]
        + bytes([input_count])
        + prevout
        + _encode_varint(new_script_length)
        + height_push
    )

    coinbase2 = (
        script_remainder
        + coinbase[script_end:]
    )

    return (
        prefix.hex(),
        coinbase2.hex(),
    )


def build_coinbase(
    coinbase1_hex: str,
    extranonce1_hex: str,
    extranonce2_hex: str,
    coinbase2_hex: str,
) -> bytes:
    """
    Setzt einen vollständigen Stratum-Coinbase-Job zusammen.
    """

    try:
        coinbase1 = bytes.fromhex(
            coinbase1_hex,
        )
        extranonce1 = bytes.fromhex(
            extranonce1_hex,
        )
        extranonce2 = bytes.fromhex(
            extranonce2_hex,
        )
        coinbase2 = bytes.fromhex(
            coinbase2_hex,
        )
    except ValueError as exc:
        raise ValueError(
            "Coinbase oder Extranonce enthält ungültiges Hex",
        ) from exc

    return (
        coinbase1
        + extranonce1
        + extranonce2
        + coinbase2
    )


def calculate_coinbase_hash(
    coinbase: bytes,
) -> bytes:
    """Berechnet den Double-SHA256-Hash der Coinbase."""

    if not coinbase:
        raise ValueError(
            "Coinbase darf nicht leer sein",
        )

    return double_sha256(
        coinbase,
    )


def calculate_merkle_root(
    coinbase_hash: bytes,
    merkle_proof: list[str] | tuple[str, ...],
) -> bytes:
    """
    Berechnet die Merkle-Root aus Coinbase-Hash und BSV-Merkle-Proof.

    Die BSV-Spezifikation liefert die Merkle-Proof-Hashes als
    Little-Endian-Hex und in der Reihenfolge von oben nach unten.
    """

    if len(coinbase_hash) != 32:
        raise ValueError(
            "Coinbase-Hash muss genau 32 Bytes enthalten",
        )

    current_hash = coinbase_hash

    for branch_hex in merkle_proof:
        try:
            branch = bytes.fromhex(
                branch_hex,
            )
        except ValueError as exc:
            raise ValueError(
                "Merkle-Proof enthält ungültiges Hex",
            ) from exc

        if len(branch) != 32:
            raise ValueError(
                "Jeder Merkle-Proof-Hash muss genau 32 Bytes enthalten",
            )

        current_hash = double_sha256(
            current_hash + branch,
        )

    return current_hash


def build_merkle_root(
    coinbase: bytes,
    merkle_proof: list[str] | tuple[str, ...],
) -> bytes:
    """Berechnet die Merkle-Root direkt aus der Coinbase."""

    coinbase_hash = calculate_coinbase_hash(
        coinbase,
    )

    return calculate_merkle_root(
        coinbase_hash,
        merkle_proof,
    )
