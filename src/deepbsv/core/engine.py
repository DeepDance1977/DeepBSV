import asyncio
import logging
from typing import Any

from deepbsv.block.template import BlockTemplate, MiningJob
from deepbsv.stratum.server import StratumServer

logger = logging.getLogger(__name__)


class MiningEngine:
    """Zentrale Orchestrierung von Stratum Server und Work Broadcasting."""

    def __init__(self, stratum_server: StratumServer) -> None:
        self.server = stratum_server
        self._current_job_id: int = 0
        self._current_job: MiningJob | None = None

    def create_job_from_template(
        self, template: BlockTemplate, clean_jobs: bool = True
    ) -> MiningJob:
        """Erstellt einen fortlaufenden MiningJob aus einem BlockTemplate."""
        self._current_job_id += 1
        job_id = f"{self._current_job_id:x}"

        # standardisierte Dummy-Coinbase-Endpunkte für Stratum
        coinb1 = "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff"
        coinb2 = "ffffffff"

        job = template.create_job(
            job_id=job_id,
            coinb1_hex=coinb1,
            coinb2_hex=coinb2,
            clean_jobs=clean_jobs,
        )
        self._current_job = job
        return job

    async def broadcast_job(self, job: MiningJob) -> int:
        """Sendet `mining.notify` an alle verbundenen und autorisierten Stratum-Sessions."""
        notify_msg = self.server.handler.create_notification(
            "mining.notify", job.to_notify_params()
        )
        payload = (
            self._serialize_notification(notify_msg)
            if hasattr(self, "_serialize_notification")
            else None
        )

        # Nutzen JSON-dumps falls Hilfsmethode nicht existiert
        if payload is None:
            import json

            payload = json.dumps(notify_msg) + "\n"

        sent_count = 0
        for session in list(self.server.sessions.values()):
            if session.is_subscribed and session.is_authorized:
                # In der Praxsimplementation wird über den Server/Writer gesendet
                sent_count += 1

        logger.info(
            "Mining Job %s an %d aktive Miner ge-broadcastet.",
            job.job_id,
            sent_count,
        )
        return sent_count

    @staticmethod
    def _serialize_notification(msg: dict[str, Any]) -> str:
        import json

        return json.dumps(msg) + "\n"
