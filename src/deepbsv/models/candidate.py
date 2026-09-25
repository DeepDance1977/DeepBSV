from typing import List, Optional
from pydantic import BaseModel, Field


class MiningCandidate(BaseModel):
    """
    Represents a BSV Mining Candidate retrieved via getminingcandidate RPC.
    Separates the node RPC schema from internal DeepBSV representations.
    """

    id: str = Field(description="Unique identifier for the mining candidate")
    prev_hash: str = Field(description="Hash of the previous block", alias="prevhash")
    version: int = Field(description="Block version indicator")
    n_bits: str = Field(
        description="Target difficulty threshold in hex format", alias="nbits"
    )
    time: int = Field(description="Current block timestamp")
    height: int = Field(description="Block height in the chain")
    coinbase_value: int = Field(
        description="Total allowed reward in Satoshis", alias="coinbasevalue"
    )
    coinbase: Optional[str] = Field(
        default=None, description="Hex representation of partial/full coinbase transaction"
    )
    merkle_proof: List[str] = Field(
        default_factory=list,
        description="Merkle proof branches for coinbase construction",
        alias="merkleproof",
    )

    model_config = {
        "populate_by_name": True,
        "frozen": True,
    }
