import asyncio
import logging

from deepbsv.core.config import settings
from deepbsv.core.logging import setup_logging
from deepbsv.rpc.client import BSVNodeRPCClient, BSVNodeRPCError

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("Starting DeepBSV Phase 1 CLI Test Runner...")

    rpc_url = getattr(settings, "NODE_RPC_URL", "http://127.0.0.1:8332")
    rpc_user = getattr(settings, "NODE_RPC_USER", "user")
    rpc_password = getattr(settings, "NODE_RPC_PASSWORD", "password")

    rpc_client = BSVNodeRPCClient(
        url=rpc_url,
        rpc_user=rpc_user,
        rpc_password=rpc_password,
    )

    try:
        logger.info("Verbindung zur BSV Node wird hergestellt...")
        candidate = await rpc_client.get_mining_candidate()
        logger.info("Mining Candidate erfolgreich abgerufen: %s", candidate.get("id"))
    except BSVNodeRPCError as e:
        logger.error("RPC-Fehler beim Starten: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
