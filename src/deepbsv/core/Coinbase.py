import hashlib


def double_sha256(data: bytes) -> bytes:
    """Computes SHA256(SHA256(data))."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def calculate_merkle_root(coinbase_hash_bin: bytes, merkle_proof_hex: list[str]) -> str:
    """
    Calculates the Merkle Root hash from a coinbase binary hash and
    a list of merkle proof hex branches (as provided by getminingcandidate).

    Args:
        coinbase_hash_bin: 32-byte binary hash of the generated coinbase transaction.
        merkle_proof_hex: List of hex strings representing merkle tree branches.

    Returns:
        Hex-encoded string of the calculated Merkle Root (internal byte order).
    """
    current_hash = coinbase_hash_bin

    for branch_hex in merkle_proof_hex:
        branch_bin = bytes.fromhex(branch_hex)
        # Concatenate and double SHA256
        current_hash = double_sha256(current_hash + branch_bin)

    return current_hash.hex()


def build_coinbase_parts(
    height: int,
    coinbase_value: int,
    script_pubkey_hex: str,
    extranonce1_size: int = 4,
    extranonce2_size: int = 8,
) -> tuple[str, str]:
    """
    Builds the split coinbase transaction parts (Coinbase1 and Coinbase2) for Stratum mining.

    The miner inserts ExtraNonce1 + ExtraNonce2 between Coinbase1 and Coinbase2.

    Args:
        height: Block height (used for BIP34 scriptSig height prefix).
        coinbase_value: Block reward + fees in Satoshis.
        script_pubkey_hex: Target payout scriptPubkey in hex.
        extranonce1_size: Byte size of ExtraNonce1.
        extranonce2_size: Byte size of ExtraNonce2.

    Returns:
        Tuple of (coinbase1_hex, coinbase2_hex).
    """
    # Version (4 bytes, Little Endian) -> 01000000
    version = "01000000"

    # Input count (1 byte)
    input_count = "01"

    # Input PrevOut Hash (32 bytes zero) + PrevOut Index (4 bytes 0xFFFFFFFF)
    prevout = "00" * 32 + "ffffffff"

    # BIP34: Height in scriptSig (Little Endian bytes with length byte)
    height_bytes = height.to_bytes((height.bit_length() + 7) // 8 or 1, byteorder="little")
    height_script = bytes([len(height_bytes)]) + height_bytes

    # ScriptSig Prefix (Height script)
    # Total scriptSig length = len(height_script) + extranonce1_size + extranonce2_size
    total_extranonce_size = extranonce1_size + extranonce2_size
    script_len = len(height_script) + total_extranonce_size

    coinbase1_hex = (
        version
        + input_count
        + prevout
        + f"{script_len:02x}"
        + height_script.hex()
    )

    # Sequence (4 bytes) -> FFFFFFFF
    sequence = "ffffffff"

    # Output count (1 byte)
    output_count = "01"

    # Value (8 bytes, Little Endian)
    value_hex = coinbase_value.to_bytes(8, byteorder="little").hex()

    # ScriptPubkey
    script_bytes = bytes.fromhex(script_pubkey_hex)
    script_len_hex = f"{len(script_bytes):02x}"

    # Locktime (4 bytes) -> 00000000
    locktime = "00000000"

    coinbase2_hex = (
        sequence
        + output_count
        + value_hex
        + script_len_hex
        + script_pubkey_hex
        + locktime
    )

    return coinbase1_hex, coinbase2_hex
