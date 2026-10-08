
import logging
from typing import Any

from deepbsv.block.template import BlockTemplate
from deepbsv.stratum.server import StratumServer

logger = logging.getLogger(__name__)


class MiningJob:
    """Repräsentiert einen Mining-Job mit Stratum-V1-Notify-Parametern."""

    def __init__(self, job_data: dict[str, Any]) -> None:
        self._data = job_data

    @property
    def job_id(self) -> str:
        return str(self._data.get("job_id", ""))

    @property
    def clean_jobs(self) -> bool:
        return bool(self._data.get("clean_jobs", True))

    def to_notify_params(self) -> list[Any]:
        """Liefert die neun Parameter für mining.notify."""
        return [
            self.job_id,
            self._data.get("prev_hash", ""),
            self._data.get("coinbase_1", ""),
            self._data.get("coinbase_2", ""),
            self._data.get("merkle_branches", []),
            self._data.get("version", "00000001"),
            self._data.get("nbits", "1d00ffff"),
            self._data.get("ntime", "00000000"),
            self.clean_jobs,
        ]

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class MiningEngine:
    """Verwaltet Mining-Jobs und verteilt sie an Stratum-Sessions."""

    def __init__(self, stratum_server: StratumServer) -> None:
        self.stratum_server = stratum_server
        self.current_job_id = 0

    def create_job_from_template(
        self,
        template: BlockTemplate,
        clean_jobs: bool = True,
    ) -> MiningJob:
        """Erstellt einen Stratum-Job aus einem BlockTemplate."""
        self.current_job_id += 1
        job_id = str(self.current_job_id)

        job_data = {
            "job_id": job_id,
            "prev_hash": getattr(
                template,
                "prev_block_hash",
                getattr(template, "prevhash", ""),
            ),
            "coinbase_1": getattr(template, "coinbase_1", ""),
            "coinbase_2": getattr(template, "coinbase_2", ""),
            "merkle_branches": getattr(template, "merkle_branches", []),
            "version": getattr(template, "version", "00000001"),
            "nbits": getattr(template, "nbits", "1d00ffff"),
            "ntime": getattr(template, "ntime", "00000000"),
            "clean_jobs": clean_jobs,
        }

        self.stratum_server.register_job(job_id, job_data)
        return MiningJob(job_data)

    async def broadcast_job(self, job: MiningJob | dict[str, Any]) -> int:
        """Verteilt mining.notify an abonnierte und autorisierte Miner."""
        mining_job = job if isinstance(job, MiningJob) else MiningJob(job)

        job_id = mining_job.job_id
        if not job_id:
            logger.warning("Mining-Job ohne job_id wird nicht verteilt.")
            return 0

        self.stratum_server.register_job(job_id, mining_job._data)

        sent = await self.stratum_server.broadcast_notification(
            "mining.notify",
            mining_job.to_notify_params(),
            authorized_only=True,
        )

        logger.info("Job %s an %d Miner verteilt.", job_id, sent)
        return sent
