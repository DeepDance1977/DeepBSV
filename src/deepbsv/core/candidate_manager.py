import asyncio
from collections.abc import Awaitable, Callable

import structlog

from deepbsv.models.candidate import MiningCandidate
from deepbsv.rpc.client import BSVRPCClient
from deepbsv.rpc.exceptions import BSVRPCError

logger = structlog.get_logger()

CandidateCallback = Callable[[MiningCandidate], Awaitable[None]]


class CandidateManager:
    """
    Manages the lifecycle of BSV Mining Candidates.
    Polls the BSV node, tracks current active candidate, and notifies subscribers.
    """

    def __init__(self, rpc_client: BSVRPCClient, poll_interval_seconds: float = 1.0):
        self.rpc_client = rpc_client
        self.poll_interval = poll_interval_seconds
        self._current_candidate: MiningCandidate | None = None
        self._subscribers: list[CandidateCallback] = []
        self._polling_task: asyncio.Task[None] | None = None
        self._is_running = False

    @property
    def current_candidate(self) -> MiningCandidate | None:
        """Returns the currently active mining candidate."""
        return self._current_candidate

    @property
    def is_running(self) -> bool:
        """Indicates whether the polling loop is active."""
        return self._is_running

    def subscribe(self, callback: CandidateCallback) -> None:
        """Registers an async callback to be notified when a new candidate arrives."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: CandidateCallback) -> None:
        """Removes a registered callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _notify_subscribers(self, candidate: MiningCandidate) -> None:
        """Dispatches the new candidate to all registered async subscribers."""
        for callback in self._subscribers:
            try:
                await callback(candidate)
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Error executing candidate subscriber callback",
                    subscriber=getattr(callback, "__name__", str(callback)),
                    error=str(e),
                )

    async def fetch_and_update(self) -> MiningCandidate | None:
        """
        Fetches the latest candidate from RPC.
        Updates state and notifies subscribers if candidate ID or height changed.
        """
        try:
            candidate = await self.rpc_client.get_mining_candidate()
        except BSVRPCError as e:
            logger.warning("Failed to fetch mining candidate during update cycle", error=str(e))
            return None

        # Check if candidate has changed (new block or updated transaction set)
        if self._current_candidate is None or candidate.id != self._current_candidate.id:
            logger.info(
                "New Mining Candidate detected",
                candidate_id=candidate.id,
                height=candidate.height,
                prev_hash=candidate.prev_hash,
            )
            self._current_candidate = candidate
            await self._notify_subscribers(candidate)

        return self._current_candidate

    async def start_polling(self) -> None:
        """Starts the background loop polling for new mining candidates."""
        if self._is_running:
            logger.warning("CandidateManager polling loop is already running")
            return

        self._is_running = True
        self._polling_task = asyncio.create_task(self._poll_loop())
        logger.info("CandidateManager polling loop started", interval=self.poll_interval)

    async def _poll_loop(self) -> None:
        """Internal polling execution loop."""
        while self._is_running:
            await self.fetch_and_update()
            await asyncio.sleep(self.poll_interval)

    async def stop_polling(self) -> None:
        """Stops the background polling loop cleanly."""
        if not self._is_running:
            return

        self._is_running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

        logger.info("CandidateManager polling loop stopped")
