from pydantic import AliasChoices, BaseModel, Field


class MiningCandidate(BaseModel):
    """
    Repräsentiert einen BSV Mining Candidate aus getminingcandidate.

    Das Modell akzeptiert sowohl die offiziellen BSV-Feldnamen als auch
    die bisher im Projekt verwendeten Kleinschreibungen.
    """

    id: str = Field(
        description="Eindeutige ID des Mining Candidates",
    )

    prev_hash: str = Field(
        description="Hash des vorherigen Blocks",
        validation_alias=AliasChoices(
            "prevhash",
            "prev_hash",
        ),
    )

    version: int = Field(
        description="Block-Version",
    )

    n_bits: str = Field(
        description="Kompaktes Mining-Target (nBits)",
        validation_alias=AliasChoices(
            "nBits",
            "nbits",
        ),
    )

    time: int = Field(
        description="Block-Zeitstempel",
    )

    height: int = Field(
        description="Höhe des Kandidatenblocks",
    )

    coinbase_value: int = Field(
        description="Verfügbarer Coinbase-Betrag in Satoshis",
        validation_alias=AliasChoices(
            "coinbaseValue",
            "coinbasevalue",
        ),
    )

    coinbase: str | None = Field(
        default=None,
        description="Hex-kodierte Coinbase-Transaktion",
    )

    merkle_proof: list[str] = Field(
        default_factory=list,
        description="Merkle-Proof des Mining Candidates",
        validation_alias=AliasChoices(
            "merkleProof",
            "merkleproof",
        ),
    )

    model_config = {
        "populate_by_name": True,
        "frozen": True,
    }
