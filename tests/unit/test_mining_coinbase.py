from deepbsv.mining.coinbase import (
    build_coinbase,
    build_merkle_root,
    calculate_coinbase_hash,
    split_coinbase,
)

BSV_EXAMPLE_COINBASE = (
    "02000000"
    "01"
    "0000000000000000000000000000000000000000000000000000000000000000"
    "ffffffff"
    "05"
    "03878b1300"
    "ffffffff"
    "01"
    "c5a4a80400000000"
    "23"
    "2103b8310da7c413106c6ce63814dbcd366c55e8ae39c8c43c1fdaeb76df56e4ff7dac"
    "00000000"
)

BSV_EXAMPLE_MERKLE_PROOF = [
    "497d51f3a933dd6e933cd37a4a5799066086d4ff45dce23f0819c7a6c7174ccb",
    "c2de445eda326b4afcec1291fc0dad3c526ddb551cbb01e2e10a10ebe79d2482",
    "7f417e9de2e8c37566141e3057eec37747a924117413ee7c2b8f902dd81b095f",
    "b25810a0b826ea8bf848d6e3f98f6c0bf4d097f0d1854d50c6e12988f29757d6",
]


def test_split_coinbase_and_rebuild() -> None:
    coinbase1, coinbase2 = split_coinbase(
        coinbase_hex=BSV_EXAMPLE_COINBASE,
        extranonce1_size=4,
        extranonce2_size=4,
    )

    extranonce1 = "01020304"
    extranonce2 = "05060708"

    rebuilt = build_coinbase(
        coinbase1_hex=coinbase1,
        extranonce1_hex=extranonce1,
        extranonce2_hex=extranonce2,
        coinbase2_hex=coinbase2,
    )

    original = bytes.fromhex(
        BSV_EXAMPLE_COINBASE,
    )

    assert rebuilt != original
    assert len(rebuilt) == len(original) + 8

    assert rebuilt.startswith(
        bytes.fromhex(
            "02000000010000000000000000000000000000000000000000000000000000000000000000"
            "ffffffff"
            "0d"
            "03878b1300"
            "0102030405060708"
        )
    )


def test_coinbase_hash_is_32_bytes() -> None:
    coinbase = bytes.fromhex(
        BSV_EXAMPLE_COINBASE,
    )

    coinbase_hash = calculate_coinbase_hash(
        coinbase,
    )

    assert len(coinbase_hash) == 32


def test_merkle_root_from_bsv_proof() -> None:
    coinbase = bytes.fromhex(
        BSV_EXAMPLE_COINBASE,
    )

    merkle_root = build_merkle_root(
        coinbase=coinbase,
        merkle_proof=BSV_EXAMPLE_MERKLE_PROOF,
    )

    assert len(merkle_root) == 32
