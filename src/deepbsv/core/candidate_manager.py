import logging

from deepbsv.models.candidate import MiningCandidate
from deepbsv.rpc.client import BSVNodeRPCClient
from deepbsv.rpc.exceptions import BSVRPCError

logger = logging.getLogger(__name__)


class CandidateManager:
    """Verwaltet den Abruf und das Caching von Mining-Kandidaten von der BSV Node."""

    def __init__(self, rpc_client: BSVNodeRPCClient, poll_interval_seconds: float = 1.0):
        self.rpc_client = rpc_client
        self.poll_interval = poll_interval_seconds
        self.current_candidate: MiningCandidate | None = None

    async def fetch_latest_candidate(self) -> MiningCandidate | None:
        """Holt den aktuellen Mining Candidate von der Node via getminingcandidate."""
        try:
            raw_candidate = await self.rpc_client.get_mining_candidate()
            candidate = MiningCandidate.model_validate(raw_candidate)
            self.current_candidate = candidate
            return candidate
        except BSVRPCError as e:
            logger.error("Fehler beim Abrufen des Mining Candidates: %s", e)
            return None
