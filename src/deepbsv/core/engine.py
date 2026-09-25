import json
import logging
from typing import Any

from deepbsv.block.template import BlockTemplate
from deepbsv.stratum.server import StratumServer

logger = logging.getLogger(__name__)


class MiningEngine:
    """Verwaltet Mining-Jobs und orchestriert die Verteilung an Stratum-Sessions."""

    def __init__(self, stratum_server: StratumServer) -> None:
        self.stratum_server = stratum_server
        self.current_job_id = 0

    def create_job_from_template(
        self, template: BlockTemplate, clean_jobs: bool = True
    ) -> dict[str, Any]:
        """Erstellt ein Stratum-Job-Diktionär aus einem BlockTemplate."""
        self.current_job_id += 1
        job_id = f"{self.current_job_id:x}"

        job_data = {
            "job_id": job_id,
            "prev_hash": template.prev_block_hash,
            "coinbase_1": getattr(template, "coinbase_1", ""),
            "coinbase_2": getattr(template, "coinbase_2", ""),
            "merkle_branches": getattr(template, "merkle_branches", []),
            "version": template.version,
            "nbits": template.nbits,
            "ntime": getattr(template, "ntime", 0),
            "clean_jobs": clean_jobs,
        }

        self.stratum_server.register_job(job_id, job_data)
        return job_data

    async def broadcast_job(self, job_data: dict[str, Any]) -> None:
        """Sendet den neuen Job via mining.notify an alle aktiven & autorisierten Miner."""
        job_id = job_data["job_id"]
        params = [
            job_id,
            job_data["prev_hash"],
            job_data["coinbase_1"],
            job_data["coinbase_2"],
            job_data["merkle_branches"],
            f"{job_data['version']:08x}",
            f"{job_data['nbits']:08x}",
            f"{job_data['ntime']:08x}",
            job_data["clean_jobs"],
        ]

        payload = {
            "id": None,
            "method": "mining.notify",
            "params": params,
        }
        data = (json.dumps(payload) + "\n").encode("utf-8")

        count = 0
        for session in list(self.stratum_server.sessions.values()):
            if session.subscribed and session.authorized_worker is not None:
                session.writer.write(data)
                await session.writer.drain()
                count += 1

        logger.info("Job %s an %d Miner verteilt.", job_id, count)
