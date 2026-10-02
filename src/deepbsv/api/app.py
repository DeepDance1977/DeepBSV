import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from deepbsv.api.websocket import background_metrics_broadcaster, manager
from deepbsv.core.config import settings
from deepbsv.rpc.client import BSVNodeRPCClient, BSVNodeRPCError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Hintergrund-Task für WebSocket-Broadcast beim Start der App aktivieren."""
    broadcaster_task = asyncio.create_task(background_metrics_broadcaster())
    yield
    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="DeepBSV API",
    description="Status- und Steuerungsschnittstelle für das DeepBSV Solo-Mining",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS für lokale Weboberfläche konfigurieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SystemStatusResponse(BaseModel):
    status: str
    node_connected: bool
    active_miners: int
    current_height: int
    hashrate: float


rpc_client = BSVNodeRPCClient(
    url=settings.rpc_url,
    rpc_user=settings.rpc_user,
    rpc_password=settings.rpc_password,
    timeout=settings.rpc_timeout,
)


@app.get("/api/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """Liefert den aktuellen Systemstatus und die BSV-Blockhöhe über JSON-RPC."""

    try:
        blockchain_info = await rpc_client.get_blockchain_info()

        current_height = int(blockchain_info.get("blocks", 0))

        logger.info(
            "BSV-Node verbunden: Blockhöhe %s",
            current_height,
        )

        return SystemStatusResponse(
            status="running",
            node_connected=True,
            active_miners=0,
            current_height=current_height,
            hashrate=0.0,
        )

    except BSVNodeRPCError as e:
        logger.error(
            "BSV-RPC-Fehler bei getblockchaininfo: code=%s message=%s",
            e.code,
            e.message,
        )

        return SystemStatusResponse(
            status="running",
            node_connected=False,
            active_miners=0,
            current_height=0,
            hashrate=0.0,
        )

    except Exception as e:
        logger.exception(
            "Unerwarteter Fehler beim Abrufen des BSV-Node-Status: %s",
            e,
        )

        raise HTTPException(
            status_code=500,
            detail="Interner Serverfehler",
        ) from e


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Einfacher Health-Check für Docker und Container-Monitoring."""
    return {"status": "ok"}


@app.websocket("/ws/metrics")
async def websocket_metrics_endpoint(websocket: WebSocket) -> None:
    """WebSocket-Endpunkt für Live-Datenstreaming an die Web-UI."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
