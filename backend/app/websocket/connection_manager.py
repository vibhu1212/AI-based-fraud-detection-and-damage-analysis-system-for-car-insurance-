"""
WebSocket connection manager for real-time updates.
Handles client connections, subscriptions, and broadcasting.
"""
from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions."""
    
    def __init__(self):
        # Active connections: {user_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Claim subscriptions: {claim_id: Set[user_id]}
        self.claim_subscriptions: Dict[str, Set[str]] = {}
        
        # User subscriptions: {user_id: Set[claim_id]}
        self.user_subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and register user."""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = set()
        logger.info(f"WebSocket connected: user_id={user_id}")
    
    def disconnect(self, user_id: str):
        """Remove user connection and all subscriptions."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Remove from all claim subscriptions
        if user_id in self.user_subscriptions:
            for claim_id in self.user_subscriptions[user_id]:
                if claim_id in self.claim_subscriptions:
                    self.claim_subscriptions[claim_id].discard(user_id)
                    if not self.claim_subscriptions[claim_id]:
                        del self.claim_subscriptions[claim_id]
            del self.user_subscriptions[user_id]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    
    def subscribe(self, user_id: str, claim_id: str):
        """Subscribe user to claim updates."""
        if claim_id not in self.claim_subscriptions:
            self.claim_subscriptions[claim_id] = set()
        
        self.claim_subscriptions[claim_id].add(user_id)
        
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].add(claim_id)
        
        logger.info(f"User {user_id} subscribed to claim {claim_id}")
    
    def unsubscribe(self, user_id: str, claim_id: str):
        """Unsubscribe user from claim updates."""
        if claim_id in self.claim_subscriptions:
            self.claim_subscriptions[claim_id].discard(user_id)
            if not self.claim_subscriptions[claim_id]:
                del self.claim_subscriptions[claim_id]
        
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(claim_id)
        
        logger.info(f"User {user_id} unsubscribed from claim {claim_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user."""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_to_claim(self, message: dict, claim_id: str):
        """Broadcast message to all users subscribed to a claim."""
        if claim_id not in self.claim_subscriptions:
            logger.debug(f"No subscribers for claim {claim_id}")
            return
        
        subscribers = list(self.claim_subscriptions[claim_id])
        logger.info(f"Broadcasting to {len(subscribers)} subscribers of claim {claim_id}")
        
        for user_id in subscribers:
            await self.send_personal_message(message, user_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected users."""
        disconnected = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {user_id}: {e}")
                disconnected.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected:
            self.disconnect(user_id)
    
    def get_subscribers(self, claim_id: str) -> Set[str]:
        """Get all user IDs subscribed to a claim."""
        return self.claim_subscriptions.get(claim_id, set())
    
    def get_subscriptions(self, user_id: str) -> Set[str]:
        """Get all claim IDs a user is subscribed to."""
        return self.user_subscriptions.get(user_id, set())
    
    def is_connected(self, user_id: str) -> bool:
        """Check if user is connected."""
        return user_id in self.active_connections


# Global connection manager instance
manager = ConnectionManager()
