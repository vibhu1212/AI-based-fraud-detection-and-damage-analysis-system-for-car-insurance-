"""
WebSocket event broadcaster service.
Broadcasts events to subscribed clients.
"""
from app.websocket.connection_manager import manager
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Service for broadcasting events to WebSocket clients."""
    
    @staticmethod
    async def broadcast_claim_state_changed(
        claim_id: str,
        old_status: str,
        new_status: str,
        actor_user_id: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Broadcast claim state change event."""
        message = {
            "event": "CLAIM_STATE_CHANGED",
            "claim_id": claim_id,
            "data": {
                "old_status": old_status,
                "new_status": new_status,
                "actor_user_id": actor_user_id,
                "reason": reason
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted CLAIM_STATE_CHANGED: {claim_id} {old_status} -> {new_status}")
    
    @staticmethod
    async def broadcast_processing_progress(
        claim_id: str,
        step: str,
        status: str,
        progress: int,
        message: Optional[str] = None
    ):
        """Broadcast processing progress event."""
        event_message = {
            "event": "PROCESSING_PROGRESS",
            "claim_id": claim_id,
            "data": {
                "step": step,
                "status": status,
                "progress": progress,
                "message": message
            }
        }
        await manager.broadcast_to_claim(event_message, claim_id)
        logger.info(f"Broadcasted PROCESSING_PROGRESS: {claim_id} {step} {progress}%")
    
    @staticmethod
    async def broadcast_p0_lock_completed(
        claim_id: str,
        lock_name: str,
        lock_number: int,
        total_locks: int,
        result: Dict[str, Any]
    ):
        """Broadcast P0 lock completion event."""
        message = {
            "event": "P0_LOCK_COMPLETED",
            "claim_id": claim_id,
            "data": {
                "lock_name": lock_name,
                "lock_number": lock_number,
                "total_locks": total_locks,
                "progress": int((lock_number / total_locks) * 100),
                "result": result
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted P0_LOCK_COMPLETED: {claim_id} {lock_name} ({lock_number}/{total_locks})")
    
    @staticmethod
    async def broadcast_claim_approved(
        claim_id: str,
        surveyor_id: str,
        approved_amount: float,
        reason: Optional[str] = None
    ):
        """Broadcast claim approval event."""
        message = {
            "event": "CLAIM_APPROVED",
            "claim_id": claim_id,
            "data": {
                "surveyor_id": surveyor_id,
                "approved_amount": float(approved_amount),
                "reason": reason,
                "message": "Your claim has been approved! Payment will be processed shortly."
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted CLAIM_APPROVED: {claim_id} by {surveyor_id}")
    
    @staticmethod
    async def broadcast_claim_rejected(
        claim_id: str,
        surveyor_id: str,
        reason: str
    ):
        """Broadcast claim rejection event."""
        message = {
            "event": "CLAIM_REJECTED",
            "claim_id": claim_id,
            "data": {
                "surveyor_id": surveyor_id,
                "reason": reason,
                "message": "Your claim has been rejected. Please review the reason provided."
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted CLAIM_REJECTED: {claim_id} by {surveyor_id}")
    
    @staticmethod
    async def broadcast_info_requested(
        claim_id: str,
        surveyor_id: str,
        reason: str
    ):
        """Broadcast info request event."""
        message = {
            "event": "INFO_REQUESTED",
            "claim_id": claim_id,
            "data": {
                "surveyor_id": surveyor_id,
                "reason": reason,
                "message": "The surveyor has requested additional information."
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted INFO_REQUESTED: {claim_id} by {surveyor_id}")
    
    @staticmethod
    async def broadcast_draft_ready(
        claim_id: str,
        icve_total: float,
        damages_count: int
    ):
        """Broadcast draft ready event."""
        message = {
            "event": "DRAFT_READY",
            "claim_id": claim_id,
            "data": {
                "icve_total": float(icve_total),
                "damages_count": damages_count,
                "message": "Your claim has been processed and is ready for surveyor review."
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted DRAFT_READY: {claim_id}")
    
    @staticmethod
    async def broadcast_claim_assigned(
        claim_id: str,
        surveyor_id: str,
        surveyor_name: str
    ):
        """Broadcast claim assignment event to customer."""
        message = {
            "event": "CLAIM_ASSIGNED",
            "claim_id": claim_id,
            "data": {
                "surveyor_id": surveyor_id,
                "surveyor_name": surveyor_name,
                "message": f"Your claim has been assigned to surveyor {surveyor_name}."
            }
        }
        await manager.broadcast_to_claim(message, claim_id)
        logger.info(f"Broadcasted CLAIM_ASSIGNED: {claim_id} to {surveyor_name}")
    
    @staticmethod
    async def broadcast_surveyor_notification(
        surveyor_id: str,
        claim_id: str,
        claim_summary: Dict[str, Any]
    ):
        """Broadcast new claim assignment notification to surveyor."""
        message = {
            "event": "NEW_CLAIM_ASSIGNED",
            "surveyor_id": surveyor_id,
            "data": {
                "claim_id": claim_id,
                "claim_summary": claim_summary,
                "message": "A new claim has been assigned to you."
            }
        }
        await manager.broadcast_to_user(message, surveyor_id)
        logger.info(f"Broadcasted NEW_CLAIM_ASSIGNED to surveyor {surveyor_id}")


# Global broadcaster instance
broadcaster = EventBroadcaster()
