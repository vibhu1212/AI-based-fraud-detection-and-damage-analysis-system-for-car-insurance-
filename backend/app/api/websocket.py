"""
WebSocket endpoint for real-time updates.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from app.websocket.connection_manager import manager
from app.services.auth import auth_service
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for real-time claim updates.
    
    Authentication: JWT token via query parameter
    
    Message Format (Client -> Server):
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "claim_id": "uuid" (optional, required for subscribe/unsubscribe)
    }
    
    Message Format (Server -> Client):
    {
        "event": "CLAIM_STATE_CHANGED" | "PROCESSING_PROGRESS" | "P0_LOCK_COMPLETED" | "CLAIM_APPROVED" | "CLAIM_REJECTED",
        "claim_id": "uuid",
        "data": {...}
    }
    """
    
    # Authenticate user via JWT
    try:
        payload = auth_service.verify_token(token)
        if not payload:
             await websocket.close(code=1008, reason="Invalid token")
             return
             
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token: missing user_id")
            return
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Accept connection
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await manager.send_personal_message({
            "event": "CONNECTED",
            "user_id": user_id,
            "message": "WebSocket connection established"
        }, user_id)
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    claim_id = message.get("claim_id")
                    if claim_id:
                        manager.subscribe(user_id, claim_id)
                        await manager.send_personal_message({
                            "event": "SUBSCRIBED",
                            "claim_id": claim_id
                        }, user_id)
                    else:
                        await manager.send_personal_message({
                            "event": "ERROR",
                            "message": "claim_id required for subscribe"
                        }, user_id)
                
                elif action == "unsubscribe":
                    claim_id = message.get("claim_id")
                    if claim_id:
                        manager.unsubscribe(user_id, claim_id)
                        await manager.send_personal_message({
                            "event": "UNSUBSCRIBED",
                            "claim_id": claim_id
                        }, user_id)
                
                elif action == "ping":
                    await manager.send_personal_message({
                        "event": "PONG",
                        "timestamp": message.get("timestamp")
                    }, user_id)
                
                else:
                    await manager.send_personal_message({
                        "event": "ERROR",
                        "message": f"Unknown action: {action}"
                    }, user_id)
            
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "event": "ERROR",
                    "message": "Invalid JSON"
                }, user_id)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_personal_message({
                    "event": "ERROR",
                    "message": str(e)
                }, user_id)
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)
