import asyncio

import structlog

from deepbsv.core.config import settings
from deepbsv.core.logging import setup_logging
from deepbsv.rpc.client import BSVRPCClient
from deepbsv.rpc.exceptions import BSVRPCError

setup_logging(settings.log_level)
logger = structlog.get_logger()


async def main() -> None:
    logger.info("Starting DeepBSV Phase 1 CLI Test Runner...")
    rpc_client = BSVRPCClient(settings)

    try:
        candidate = await rpc_client.get_mining_candidate()
        logger.info(
            "Successfully fetched Mining Candidate",
            candidate_id=candidate.id,
            height=candidate.height,
            n_bits=candidate.n_bits,
        )
    except BSVRPCError as e:
        logger.error("Failed to fetch Mining Candidate", error=str(e))
    finally:
        await rpc_client.close()


if __name__ == "__main__":
    asyncio.run(main())
