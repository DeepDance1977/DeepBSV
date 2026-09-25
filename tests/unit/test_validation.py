from deepbsv.stratum.validation import (
    build_block_header,
    calculate_merkle_root,
    double_sha256,
    nbits_to_target,
    reconstruct_coinbase,
    validate_share,
)


def test_double_sha256() -> None:
    data = b"hello world"
    expected_hex = "bc62a933791176e336e16f731c3a50e50529124430f81d1134a6ef44b3602f23"
    result = double_sha256(data)
    assert result.hex() == expected_hex


def test_nbits_to_target() -> None:
    nbits = 0x1D00FFFF
    target = nbits_to_target(nbits)
    assert target == 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def test_reconstruct_coinbase() -> None:
    cb1 = "0100000001"
    ext1 = "00000001"
    ext2 = "00000002"
    cb2 = "ffffffff"

    expected = bytes.fromhex("01000000010000000100000002ffffffff")
    result = reconstruct_coinbase(cb1, ext1, ext2, cb2)
    assert result == expected


def test_calculate_merkle_root_single_branch() -> None:
    coinbase_hash = bytes.fromhex("11" * 32)
    branch = "22" * 32

    expected = double_sha256(coinbase_hash + bytes.fromhex(branch))
    result = calculate_merkle_root(coinbase_hash, [branch])
    assert result == expected


def test_build_block_header_length() -> None:
    version = 1
    prev_hash = "00" * 32
    merkle_root = b"\x00" * 32
    ntime = 1234567890
    nbits = 0x1D00FFFF
    nonce = 987654321

    header = build_block_header(
        version=version,
        prev_block_hash_hex=prev_hash,
        merkle_root=merkle_root,
        ntime=ntime,
        nbits=nbits,
        nonce=nonce,
    )

    assert len(header) == 80


def test_validate_share_success_and_failure() -> None:
    header = b"\x00" * 80

    high_target = (1 << 256) - 1
    is_valid, hash_hex, hash_int = validate_share(header, high_target)
    assert is_valid is True
    assert isinstance(hash_hex, str)
    assert hash_int <= high_target

    low_target = 0
    is_valid_fail, _, _ = validate_share(header, low_target)
    assert is_valid_fail is False
