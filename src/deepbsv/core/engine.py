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
            self._data.get("prev_hash", ""),
            self._data.get("coinbase_1", ""),
            self._data.get("coinbase_2", ""),
            self._data.get("merkle_branches", []),
            f"{int(self._data.get('version', 1)):08x}",
            f"{int(self._data.get('nbits', 0x1D00FFFF)):08x}",
            f"{int(self._data.get('ntime', 0)):08x}",
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
        """Erstellt ein Stratum-Job-Objekt aus einem BlockTemplate mit Fallbacks."""
        self.current_job_id += 1
        job_id = str(self.current_job_id)

        job_data = {
            "job_id": job_id,
            "prev_hash": getattr(template, "prev_block_hash", getattr(template, "previous_block_hash", getattr(template, "prevhash", ""))),
            "coinbase_1": getattr(template, "coinbase_1", getattr(template, "coinbase1", "")),
            "coinbase_2": getattr(template, "coinbase_2", getattr(template, "coinbase2", "")),
            "merkle_branches": getattr(template, "merkle_branches", getattr(template, "merkle_branch", [])),
            "version": getattr(template, "version", 1),
            "nbits": getattr(template, "nbits", getattr(template, "bits", 0x1D00FFFF)),
            "ntime": getattr(template, "ntime", getattr(template, "time", 0)),
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
                send_resp = getattr(session, "send_response", None)
                if send_resp is not None:
                    try:
                        if callable(send_resp):
                            await send_resp(result=None, error=None, msg_id=None)
                    except Exception:
                        pass
                count += 1

        logger.info("Job %s an %d Miner verteilt.", job_id, count)
        return count
