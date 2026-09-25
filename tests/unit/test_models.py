from deepbsv.models.candidate import MiningCandidate
from tests.mocks.rpc_responses import VALID_GETMININGCANDIDATE_RESPONSE


def test_mining_candidate_parsing():
    candidate = MiningCandidate.model_validate(VALID_GETMININGCANDIDATE_RESPONSE)
    assert candidate.id == "cand_00112233445566778899"
    assert candidate.height == 820000
    assert candidate.coinbase_value == 625000000
    assert len(candidate.merkle_proof) == 2
