import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from deepbsv.models.candidate import MiningCandidate
from deepbsv.rpc.client import BSVNodeRPCClient
from deepbsv.rpc.exceptions import BSVRPCConnectionError, BSVRPCError

logger = logging.getLogger(__name__)

CandidateCallback = Callable[[MiningCandidate], Coroutine[Any, Any, None]]


class CandidateManager:
    """Verwaltet den Abruf, das Polling und das Caching von Mining-Kandidaten von der BSV Node."""

    def __init__(
        self, rpc_client: BSVNodeRPCClient, poll_interval_seconds: float = 1.0
    ) -> None:
        self.rpc_client = rpc_client
        self.poll_interval = poll_interval_seconds
        self.current_candidate: MiningCandidate | None = None
        self._subscribers: list[CandidateCallback] = []
        self._polling_task: asyncio.Task[None] | None = None
        self._is_polling = False

    def subscribe(self, callback: CandidateCallback) -> None:
        """Registriert eine Callback-Funktion für neue Kandidaten-Events."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    async def fetch_and_update(self) -> MiningCandidate | None:
        """Holt den neuesten Candidate und benachrichtigt Subscriber bei Änderungen."""
        try:
            raw_candidate = await self.rpc_client.get_mining_candidate()
            candidate = (
                MiningCandidate.model_validate(raw_candidate)
                if isinstance(raw_candidate, dict)
                else raw_candidate
            )

            if (
                self.current_candidate is None
                or candidate.id != self.current_candidate.id
            ):
                self.current_candidate = candidate
                await self._notify_subscribers(candidate)

            return self.current_candidate

        except (BSVRPCError, BSVRPCConnectionError) as e:
            logger.error("Fehler beim Abrufen des Mining Candidates: %s", e)
            return None

    async def _notify_subscribers(self, candidate: MiningCandidate) -> None:
        for callback in self._subscribers:
            try:
                await callback(candidate)
            except Exception as e:  # noqa: BLE001
                logger.error("Fehler im Candidate-Subscriber Callback: %s", e)

    async def start_polling(self) -> None:
        """Startet den asynchronen Polling-Loop."""
        if self._is_polling:
            return
        self._is_polling = True
        self._polling_task = asyncio.create_task(self._poll_loop())

    async def stop_polling(self) -> None:
        """Stoppt den Polling-Loop sauber."""
        self._is_polling = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

    async def _poll_loop(self) -> None:
        while self._is_polling:
            await self.fetch_and_update()
            await asyncio.sleep(self.poll_interval)
