from typing import Any

import httpx
import structlog

from deepbsv.core.config import Settings
from deepbsv.models.candidate import MiningCandidate
from deepbsv.rpc.exceptions import (
    BSVRPCAuthenticationError,
    BSVRPCConnectionError,
    BSVRPCError,
    BSVRPCResponseError,
)

logger = structlog.get_logger()


class BSVRPCClient:
    """Async HTTP JSON-RPC Client for BSV Node interaction."""

    def __init__(self, config: Settings):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                auth=(self.config.rpc_user, self.config.rpc_password),
                timeout=self.config.rpc_timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call(self, method: str, params: list[Any] | None = None) -> Any:
        client = await self._get_client()
        payload = {
            "jsonrpc": "1.0",
            "id": "deepbsv",
            "method": method,
            "params": params or [],
        }

        try:
            response = await client.post(self.config.rpc_url, json=payload)
        except httpx.RequestError as exc:
            logger.error(
                "RPC connection failed",
                host=self.config.rpc_host,
                port=self.config.rpc_port,
                error=str(exc),
            )
            raise BSVRPCConnectionError(f"Could not connect to BSV Node: {exc}") from exc

        if response.status_code in (401, 403):
            logger.error("RPC authentication failed")
            raise BSVRPCAuthenticationError("Invalid RPC username or password")

        if response.status_code != 200:
            raise BSVRPCError(f"Unexpected HTTP status code from BSV Node: {response.status_code}")

        data = response.json()
        if data.get("error"):
            err = data["error"]
            raise BSVRPCResponseError(code=err.get("code", -1), message=err.get("message", "Unknown error"))

        return data.get("result")

    async def get_mining_candidate(self) -> MiningCandidate:
        """Fetches a new mining candidate from the BSV node via getminingcandidate RPC."""
        logger.debug("Executing RPC: getminingcandidate")
        result = await self._call("getminingcandidate")
        if not result or not isinstance(result, dict):
            raise BSVRPCError("Invalid or empty response structure for getminingcandidate")

        return MiningCandidate.model_validate(result)
