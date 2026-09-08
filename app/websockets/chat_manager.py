from typing import Dict, Set, Optional, Any
import json
from datetime import datetime
import asyncio
from fastapi import WebSocket

class ChatConnectionManager:
    """
    Manages WebSocket connections for real-time chat
    """
    
    def __init__(self):
        # Active connections: match_id -> {user_id: WebSocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        
        # User match mapping: user_id -> set of match_ids
        self.user_matches: Dict[str, Set[str]] = {}
    
    async def connect(self, match_id: str, user_id: str, websocket: WebSocket):
        """Accept a WebSocket connection"""
        await websocket.accept()
        
        # Initialize match connections if not exists
        if match_id not in self.active_connections:
            self.active_connections[match_id] = {}
        
        # Store the connection
        self.active_connections[match_id][user_id] = websocket
        
        # Track user's matches
        if user_id not in self.user_matches:
            self.user_matches[user_id] = set()
        self.user_matches[user_id].add(match_id)
        
        # Notify others in the match that user is online
        await self.broadcast_to_match(
            match_id,
            {
                "type": "user_online",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            exclude_user_id=user_id
        )
    
    def disconnect(self, match_id: str, user_id: str):
        """Remove a WebSocket connection"""
        if match_id in self.active_connections:
            if user_id in self.active_connections[match_id]:
                del self.active_connections[match_id][user_id]
            
            # Clean up empty match rooms
            if not self.active_connections[match_id]:
                del self.active_connections[match_id]
        
        # Clean up user's match tracking
        if user_id in self.user_matches:
            self.user_matches[user_id].discard(match_id)
            if not self.user_matches[user_id]:
                del self.user_matches[user_id]
    
    async def send_personal_message(self, user_id: str, message: dict):
        """Send a message to a specific user"""
        # Find all matches this user is in
        if user_id not in self.user_matches:
            return False
        
        sent = False
        for match_id in self.user_matches[user_id]:
            if match_id in self.active_connections:
                if user_id in self.active_connections[match_id]:
                    try:
                        await self.active_connections[match_id][user_id].send_json(message)
                        sent = True
                    except Exception:
                        pass
        
        return sent
    
    async def broadcast_to_match(
        self,
        match_id: str,
        message: dict,
        exclude_user_id: Optional[str] = None
    ):
        """Broadcast a message to all users in a match"""
        if match_id not in self.active_connections:
            return
        
        for user_id, connection in self.active_connections[match_id].items():
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            try:
                await connection.send_json(message)
            except Exception:
                # Connection may be dead, will be cleaned up on disconnect
                pass
    
    async def broadcast_to_user_matches(
        self,
        user_id: str,
        message: dict
    ):
        """Broadcast a message to all matches of a user"""
        if user_id not in self.user_matches:
            return
        
        for match_id in self.user_matches[user_id]:
            await self.broadcast_to_match(match_id, message)
    
    def get_online_users_in_match(self, match_id: str) -> Set[str]:
        """Get all online users in a match"""
        if match_id not in self.active_connections:
            return set()
        return set(self.active_connections[match_id].keys())
    
    def is_user_online_in_match(self, match_id: str, user_id: str) -> bool:
        """Check if a user is online in a specific match"""
        if match_id not in self.active_connections:
            return False
        return user_id in self.active_connections[match_id]
    
    def get_all_user_matches(self, user_id: str) -> Set[str]:
        """Get all matches a user is connected to"""
        return self.user_matches.get(user_id, set())


# Global instance
chat_manager = ChatConnectionManager()