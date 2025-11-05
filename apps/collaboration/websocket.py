"""
WebSocket Connection Manager - Real-time communication.

Manages WebSocket connections for real-time agent updates.
"""

from typing import List, Dict, Any
from fastapi import WebSocket
import json
from libs.common.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections.

    Features:
    - Multiple concurrent connections
    - Broadcast to all clients
    - Send to specific clients
    - Connection lifecycle management
    """

    def __init__(self):
        # Active WebSocket connections
        self.active_connections: List[WebSocket] = []

        # Map connection to user/session info
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "connected_at": "now",
            "user_id": None,
        }

        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to Aurora Energy Agent Platform",
            "total_connections": len(self.active_connections)
        })

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            del self.connection_info[websocket]

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to client: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

        if disconnected:
            logger.info(f"Cleaned up {len(disconnected)} disconnected clients")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to all connections for a specific user."""
        sent_count = 0

        for connection, info in self.connection_info.items():
            if info.get("user_id") == user_id:
                try:
                    await connection.send_json(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send to user {user_id}: {e}")

        logger.info(f"Sent message to {sent_count} connections for user {user_id}")

    def register_user(self, websocket: WebSocket, user_id: str):
        """Register a user ID for a connection."""
        if websocket in self.connection_info:
            self.connection_info[websocket]["user_id"] = user_id
            logger.info(f"Registered user {user_id} for WebSocket connection")

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_user_connections(self, user_id: str) -> List[WebSocket]:
        """Get all connections for a user."""
        return [
            conn for conn, info in self.connection_info.items()
            if info.get("user_id") == user_id
        ]
