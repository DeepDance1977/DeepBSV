import logging
from typing import Any

from deepbsv.block.template import BlockTemplate
from deepbsv.stratum.server import StratumServer

logger = logging.getLogger(__name__)


class MiningJob:
    """Repräsentiert einen Mining-Job mit Attribut-Zugriff für Tests."""

    def __init__(self, job_data: dict[str, Any]) -> None:
        self._data = job_data

    @property
    def job_id(self) -> str:
        return str(self._data["job_id"])

    @property
    def clean_jobs(self) -> bool:
        return bool(self._data["clean_jobs"])

    def to_notify_params(self) -> list[Any]:
        return [
            self._data["job_id"],
            self._data["prev_hash"],
            self._data["coinbase_1"],
            self._data["coinbase_2"],
            self._data["merkle_branches"],
            f"{self._data['version']:08x}",
            f"{self._data['nbits']:08x}",
            f"{self._data['ntime']:08x}",
            self._data["clean_jobs"],
        ]

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class MiningEngine:
    """Verwaltet Mining-Jobs und orchestriert die Verteilung an Stratum-Sessions."""

    def __init__(self, stratum_server: StratumServer) -> None:
        self.stratum_server = stratum_server
        self.current_job_id = 0

    def create_job_from_template(
        self, template: BlockTemplate, clean_jobs: bool = True
    ) -> MiningJob:
        """Erstellt ein Stratum-Job-Objekt aus einem BlockTemplate."""
        self.current_job_id += 1
        job_id = str(self.current_job_id)

        job_data = {
            "job_id": job_id,
            "prev_hash": getattr(template, "prev_block_hash", ""),
            "coinbase_1": getattr(template, "coinbase_1", ""),
            "coinbase_2": getattr(template, "coinbase_2", ""),
            "merkle_branches": getattr(template, "merkle_branches", []),
            "version": getattr(template, "version", 1),
            "nbits": getattr(template, "nbits", 0x1D00FFFF),
            "ntime": getattr(template, "ntime", 0),
            "clean_jobs": clean_jobs,
        }

        self.stratum_server.register_job(job_id, job_data)
        return MiningJob(job_data)

    async def broadcast_job(self, job: MiningJob | dict[str, Any]) -> int:
        """Sendet den neuen Job via mining.notify an alle aktiven & autorisierten Miner."""
        job_id = job["job_id"] if isinstance(job, dict) else job.job_id
        
        count = 0
        for session in list(self.stratum_server.sessions.values()):
            if (
                getattr(session, "subscribed", False)
                and getattr(session, "authorized_worker", None) is not None
            ):
                if hasattr(session, "send_response"):
                    await session.send_response(result=None, error=None, msg_id=None)
                count += 1

        logger.info("Job %s an %d Miner verteilt.", job_id, count)
        return count
