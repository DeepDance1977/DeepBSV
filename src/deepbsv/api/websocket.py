import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Verwaltet aktive WebSocket-Verbindungen für das Echtzeit-Dashboard."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("Neuer WebSocket-Client verbunden. Aktive Verbindungen: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)
        logger.info("WebSocket-Client getrennt. Aktive Verbindungen: %d", len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        """Sendet Daten an alle verbundenen Web-UI-Clients."""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:  # noqa: BLE001
                logger.error("Fehler beim Senden über WebSocket: %s", e)
                disconnected.add(connection)
        
        # Tote Verbindungen aufräumen
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


async def background_metrics_broadcaster() -> None:
    """Simuliert oder holt periodisch Live-Metriken und streamt sie an das Frontend."""
    while True:
        try:
            payload = {
                "type": "metrics_update",
                "hashrate": 0.0,
                "active_miners": 0,
                "current_height": 0,
            }
            await manager.broadcast(payload)
        except Exception as e:  # noqa: BLE001
            logger.error("Fehler im Metrics Broadcaster: %s", e)
        
        await asyncio.sleep(2.0)
