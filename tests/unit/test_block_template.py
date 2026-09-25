import hashlib

from deepbsv.block.merkle import calculate_merkle_root, double_sha256
from deepbsv.block.template import BlockTemplate


def test_double_sha256() -> None:
    data = b"hello bsv"
    expected = hashlib.sha256(hashlib.sha256(data).digest()).digest()
    assert double_sha256(data) == expected


def test_merkle_root_single_tx() -> None:
    tx1 = b"\x01" * 32
    assert calculate_merkle_root([tx1]) == tx1


def test_merkle_root_two_txs() -> None:
    tx1 = b"\x01" * 32
    tx2 = b"\x02" * 32
    expected = double_sha256(tx1 + tx2)
    assert calculate_merkle_root([tx1, tx2]) == expected


def test_merkle_root_odd_txs() -> None:
    tx1 = b"\x01" * 32
    tx2 = b"\x02" * 32
    tx3 = b"\x03" * 32
    # tx3 wird auf der ersten Ebene verdoppelt
    level1_right = double_sha256(tx3 + tx3)
    level1_left = double_sha256(tx1 + tx2)
    expected_root = double_sha256(level1_left + level1_right)
    assert calculate_merkle_root([tx1, tx2, tx3]) == expected_root


def test_block_template_create_job() -> None:
    template = BlockTemplate(
        height=100,
        prev_block_hash="0000000000000000000000000000000000000000000000000000000000000000",
    )
    template.add_transaction_hash(b"\xaa" * 32)

    job = template.create_job(
        job_id="job_001", coinb1_hex="01000000", coinb2_hex="00000000"
    )

    params = job.to_notify_params()
    assert params[0] == "job_001"
    assert len(params[4]) == 1  # 1 Merkle branch entry
    assert params[8] is True  # clean_jobs
