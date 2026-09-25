import hashlib

from deepbsv.core.coinbase import (
    build_coinbase_parts,
    calculate_merkle_root,
    double_sha256,
)


def test_double_sha256():
    data = b"deepbsv_test"
    expected = hashlib.sha256(hashlib.sha256(data).digest()).digest()
    assert double_sha256(data) == expected


def test_build_coinbase_parts():
    height = 820000
    coinbase_value = 625000000  # 6.25 BSV
    # Standard P2PKH scriptPubkey example
    script_pubkey = "76a914123456789012345678901234567890123456789088ac"

    cb1, cb2 = build_coinbase_parts(
        height=height,
        coinbase_value=coinbase_value,
        script_pubkey_hex=script_pubkey,
        extranonce1_size=4,
        extranonce2_size=8,
    )

    # Assert version and input count in CB1
    assert cb1.startswith("0100000001")
    # Assert sequence and output count in CB2
    assert "ffffffff01" in cb2
    # Assert scriptPubkey is present in CB2
    assert script_pubkey in cb2


def test_calculate_merkle_root_single_node():
    coinbase_hash = b"\x01" * 32
    proof_branch = ("02" * 32)

    root = calculate_merkle_root(coinbase_hash, [proof_branch])

    expected_hash = double_sha256(coinbase_hash + bytes.fromhex(proof_branch)).hex()
    assert root == expected_hash


def test_calculate_merkle_root_empty_proof():
    coinbase_hash = b"\xaa" * 32
    root = calculate_merkle_root(coinbase_hash, [])
    assert root == coinbase_hash.hex()
