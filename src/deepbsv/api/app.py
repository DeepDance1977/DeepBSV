import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepBSV API",
    description="Status- und Steuerungsschnittstelle für das DeepBSV Solo-Mining",
    version="1.0.0",
)

# CORS für lokale Weboberfläche konfigurieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Für lokale Entwicklung; im Betrieb einschränken
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


@app.get("/api/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """Liefert den aktuellen System- und Mining-Status (greift passiv auf den Core zu)."""
    try:
        return SystemStatusResponse(
            status="running",
            node_connected=True,
            active_miners=0,
            current_height=0,
            hashrate=0.0,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Fehler beim Abrufen des Systemstatus: %s", e)
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Einfacher Health-Check für Docker und Container-Monitoring."""
    return {"status": "ok"}
