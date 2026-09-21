import asyncio
from typing import Set, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.logging import get_logger

logger = get_logger("app.api.websocket")

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total subscribers: {len(self.active_connections)}")
        # Send initial welcome message
        await self.send_personal_message(
            {"type": "CONNECTION_ESTABLISHED", "message": "Subscribed to RESQROUTE Live Mission Telemetry Stream"},
            websocket,
        )

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Remaining subscribers: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message to WebSocket: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast mission update JSON payload to all active WebSocket clients."""
        async with self._lock:
            disconnected_clients = set()
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Error broadcasting to client, marking for disconnection: {e}")
                    disconnected_clients.add(connection)

            for dead_client in disconnected_clients:
                self.active_connections.discard(dead_client)

    def broadcast_sync(self, message: Dict[str, Any]):
        """Synchronous helper to broadcast payloads to all WebSocket clients."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            try:
                asyncio.run(self.broadcast(message))
            except Exception:
                pass


ws_manager = ConnectionManager()


@router.websocket("/ws/missions")
async def websocket_missions_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live emergency mission updates and telemetry stream.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and listen for client ping/messages
            data = await websocket.receive_text()
            if data.lower() == "ping":
                await websocket.send_json({"type": "PONG"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection exception: {e}")
        await ws_manager.disconnect(websocket)
