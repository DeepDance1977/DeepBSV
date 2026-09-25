import asyncio
import logging
import signal

from deepbsv.block.template import BlockTemplate
from deepbsv.core.candidate_manager import CandidateManager
from deepbsv.core.config import settings
from deepbsv.core.engine import MiningEngine
from deepbsv.core.logging import setup_logging
from deepbsv.models.candidate import MiningCandidate
from deepbsv.rpc.client import BSVNodeRPCClient
from deepbsv.stratum.server import StratumServer

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("Starte DeepBSV Solo-Mining Server...")

    # 1. RPC Client und Stratum Server initialisieren
    rpc_url = getattr(settings, "NODE_RPC_URL", "http://127.0.0.1:8332")
    rpc_user = getattr(settings, "NODE_RPC_USER", "user")
    rpc_password = getattr(settings, "NODE_RPC_PASSWORD", "password")

    rpc_client = BSVNodeRPCClient(
        url=rpc_url,
        rpc_user=rpc_user,
        rpc_password=rpc_password,
    )

    stratum_host = getattr(settings, "STRATUM_HOST", "0.0.0.0")
    stratum_port = getattr(settings, "STRATUM_PORT", 3333)

    stratum_server = StratumServer(host=stratum_host, port=stratum_port)
    engine = MiningEngine(stratum_server)
    candidate_manager = CandidateManager(rpc_client, poll_interval_seconds=1.0)

    # 2. Callback-Logik bei neuem Mining Candidate definieren
    async def on_new_candidate(candidate: MiningCandidate) -> None:
        logger.info("Neuer Mining Candidate empfangen: %s", candidate.id)
        template = BlockTemplate.from_candidate(candidate)
        job = engine.create_job_from_template(template, clean_jobs=True)
        await engine.broadcast_job(job)

    candidate_manager.subscribe(on_new_candidate)

    # 3. Server und Polling-Loop starten
    await stratum_server.start()
    await candidate_manager.start_polling()

    logger.info(
        "DeepBSV läuft erfolgreich auf %s:%d. Warte auf Miner...",
        stratum_host,
        stratum_port,
    )

    # 4. Graceful Shutdown Handlers einrichten
    stop_event = asyncio.Event()

    def _shutdown_signal() -> None:
        logger.info("Shutdown-Signal empfangen. Fahre DeepBSV herunter...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown_signal)
        except NotImplementedError:
            pass  # Fallback für Plattformen ohne Signal-Handler-Support

    await stop_event.wait()

    # 5. Ressourcen geordnet freigeben
    await candidate_manager.stop_polling()
    await stratum_server.stop()
    logger.info("DeepBSV beendet.")


if __name__ == "__main__":
    asyncio.run(main())
