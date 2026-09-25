import asyncio
import logging

from deepbsv.core.config import settings
from deepbsv.core.logging import setup_logging
from deepbsv.rpc.client import BSVNodeRPCClient
from deepbsv.rpc.exceptions import BSVRPCError

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("Starting DeepBSV Phase 1 CLI Test Runner...")
    rpc_client = BSVNodeRPCClient(
        url=settings.NODE_RPC_URL,
        rpc_user=settings.NODE_RPC_USER,
        rpc_password=settings.NODE_RPC_PASSWORD,
    )

    try:
        logger.info("Verbindung zur BSV Node wird hergestellt...")
        candidate = await rpc_client.get_mining_candidate()
        logger.info("Mining Candidate erfolgreich abgerufen: %s", candidate.get("id"))
    except BSVRPCError as e:
        logger.error("RPC-Fehler beim Starten: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
