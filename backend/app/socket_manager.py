import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("socket_manager")

class ConnectionManager:
    def __init__(self):
        # team_id -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, team_id: str, websocket: WebSocket):
        await websocket.accept()
        if team_id not in self.active_connections:
            self.active_connections[team_id] = set()
        self.active_connections[team_id].add(websocket)
        logger.info(f"WebSocket connected for team {team_id}. Active: {len(self.active_connections[team_id])}")

    def disconnect(self, team_id: str, websocket: WebSocket):
        if team_id in self.active_connections:
            self.active_connections[team_id].discard(websocket)
            if not self.active_connections[team_id]:
                del self.active_connections[team_id]
        logger.info(f"WebSocket disconnected for team {team_id}.")

    async def broadcast(self, team_id: str, message: dict):
        if team_id not in self.active_connections:
            return
        
        # Serialize once
        text = json.dumps(message, default=str)
        dead_sockets = set()
        
        for connection in list(self.active_connections[team_id]):
            try:
                await connection.send_text(text)
            except Exception as e:
                logger.warning(f"Error broadcasting to socket: {e}")
                dead_sockets.add(connection)
                
        for dead in dead_sockets:
            self.disconnect(team_id, dead)

manager = ConnectionManager()

