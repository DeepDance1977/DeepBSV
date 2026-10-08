from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from deepbsv.mining.models import MiningCandidate, MiningJob
from deepbsv.rpc.client import (
    BSVNodeRPCClient,
    BSVNodeRPCError,
)

logger = logging.getLogger(__name__)

CandidateCallback = Callable[
    [MiningJob],
    Awaitable[None],
]


class CandidateManager:
    """
    Verwaltet den aktuell gültigen BSV Mining Candidate.

    Die Node wird regelmäßig nach einem neuen Candidate gefragt.
    Ein neuer Job wird erzeugt, sobald sich die Blockhöhe,
    prevhash oder Candidate-ID verändert.
    """

    def __init__(
        self,
        rpc: BSVNodeRPCClient,
        poll_interval: float = 2.0,
    ) -> None:
        self.rpc = rpc
        self.poll_interval = poll_interval

        self._current_candidate: MiningCandidate | None = None
        self._current_job: MiningJob | None = None

        self._callbacks: list[CandidateCallback] = []

        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

        self._job_counter = 0

        self.last_error: str | None = None
        self.last_update_time: float | None = None

    @property
    def current_candidate(
        self,
    ) -> MiningCandidate | None:
        return self._current_candidate

    @property
    def current_job(self) -> MiningJob | None:
        return self._current_job

    @property
    def is_running(self) -> bool:
        return (
            self._task is not None
            and not self._task.done()
        )

    def add_callback(
        self,
        callback: CandidateCallback,
    ) -> None:
        """Registriert einen Callback für neue Mining-Jobs."""

        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(
        self,
        callback: CandidateCallback,
    ) -> None:
        """Entfernt einen zuvor registrierten Callback."""

        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def start(self) -> None:
        """Startet den Candidate-Überwachungsdienst."""

        if self.is_running:
            return

        self._stop_event.clear()

        self._task = asyncio.create_task(
            self._run(),
            name="deepbsv-candidate-manager",
        )

        logger.info(
            "BSV Candidate Manager gestartet",
        )

    async def stop(self) -> None:
        """Stoppt den Candidate-Überwachungsdienst."""

        self._stop_event.set()

        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._task = None

        logger.info(
            "BSV Candidate Manager gestoppt",
        )

    async def refresh_now(self) -> MiningJob | None:
        """
        Holt sofort einen Candidate.

        Gibt einen neuen Job zurück, wenn sich der Candidate
        geändert hat. Andernfalls wird der aktuelle Job zurückgegeben.
        """

        try:
            data = await self.rpc.get_mining_candidate(
                provide_coinbase=True,
            )

            candidate = MiningCandidate.from_rpc(
                data,
            )

            changed = self._candidate_changed(
                candidate,
            )

            if changed:
                return await self._install_candidate(
                    candidate,
                )

            self.last_error = None

            return self._current_job

        except (
            BSVNodeRPCError,
            ValueError,
        ) as exc:
            self.last_error = str(exc)

            logger.warning(
                "BSV Mining Candidate konnte nicht "
                "aktualisiert werden: %s",
                exc,
            )

            return self._current_job

    def _candidate_changed(
        self,
        candidate: MiningCandidate,
    ) -> bool:
        if self._current_candidate is None:
            return True

        current = self._current_candidate

        return any(
            (
                candidate.candidate_id
                != current.candidate_id,
                candidate.height
                != current.height,
                candidate.prevhash
                != current.prevhash,
                candidate.nbits
                != current.nbits,
            )
        )

    async def _install_candidate(
        self,
        candidate: MiningCandidate,
    ) -> MiningJob:
        self._job_counter += 1

        job_id = (
            f"{candidate.height:x}-"
            f"{self._job_counter:x}"
        )

        job = MiningJob(
            job_id=job_id,
            candidate=candidate,
            clean_jobs=True,
        )

        self._current_candidate = candidate
        self._current_job = job
        self.last_error = None

        logger.info(
            "Neuer BSV Mining Job: job=%s height=%d "
            "candidate=%s",
            job.job_id,
            candidate.height,
            candidate.candidate_id,
        )

        for callback in tuple(self._callbacks):
            try:
                await callback(job)
            except Exception:
                logger.exception(
                    "Fehler im Candidate-Callback",
                )

        return job

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self.refresh_now()

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval,
                )
            except asyncio.TimeoutError:
                continue
