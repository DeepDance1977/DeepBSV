from __future__ import annotations

import asyncio
import logging

from deepbsv.mining.models import MiningCandidate, MiningJob
from deepbsv.rpc.client import BSVNodeRPCClient, BSVNodeRPCError

logger = logging.getLogger(__name__)


class CandidateManager:
    """Verwaltet den aktuellen BSV-Mining-Candidate."""

    def __init__(
        self,
        rpc_client: BSVNodeRPCClient,
        refresh_interval: float = 5.0,
    ) -> None:
        self.rpc_client = rpc_client
        self.refresh_interval = refresh_interval

        self._current_job: MiningJob | None = None
        self._job_counter = 0
        self._lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def current_job(self) -> MiningJob | None:
        """Gibt den aktuell verwendeten Mining-Job zurück."""
        return self._current_job

    async def get_current_job(
        self,
        force_refresh: bool = False,
    ) -> MiningJob:
        """Lädt bei Bedarf einen aktuellen Mining-Job."""

        async with self._lock:
            if self._current_job is not None and not force_refresh:
                return self._current_job

            return await self._refresh_locked()

    async def refresh(self) -> MiningJob:
        """Erzwingt das Laden eines neuen Mining-Candidates."""

        async with self._lock:
            return await self._refresh_locked()

    async def _refresh_locked(self) -> MiningJob:
        """Lädt einen Candidate, während der Lock gehalten wird."""

        candidate_data = await self.rpc_client.get_mining_candidate(
            provide_coinbase=True,
        )

        candidate = MiningCandidate.from_rpc(
            candidate_data,
        )

        self._job_counter += 1

        job = MiningJob(
            job_id=f"{candidate.height}-{self._job_counter}",
            candidate=candidate,
            clean_jobs=True,
        )

        self._current_job = job

        logger.info(
            "Neuer BSV-Mining-Job: job_id=%s height=%s candidate=%s",
            job.job_id,
            candidate.height,
            candidate.candidate_id,
        )

        return job

    async def start(self) -> None:
        """Startet die automatische Candidate-Aktualisierung."""

        if self._running:
            return

        self._running = True

        try:
            await self.refresh()
        except BSVNodeRPCError:
            logger.exception(
                "Initiales Laden des BSV-Mining-Candidates fehlgeschlagen",
            )

        self._refresh_task = asyncio.create_task(
            self._refresh_loop(),
        )

    async def stop(self) -> None:
        """Stoppt die automatische Candidate-Aktualisierung."""

        self._running = False

        if self._refresh_task is None:
            return

        self._refresh_task.cancel()

        try:
            await self._refresh_task
        except asyncio.CancelledError:
            pass

        self._refresh_task = None

    async def _refresh_loop(self) -> None:
        """Aktualisiert den Mining-Candidate regelmäßig."""

        while self._running:
            await asyncio.sleep(
                self.refresh_interval,
            )

            if not self._running:
                break

            try:
                await self.refresh()
            except BSVNodeRPCError:
                logger.exception(
                    "Aktualisierung des BSV-Mining-Candidates fehlgeschlagen",
                )
            except ValueError:
                logger.exception(
                    "Ungültiger BSV-Mining-Candidate",
                )
