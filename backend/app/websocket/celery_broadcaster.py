"""
Helper for broadcasting WebSocket events from Celery tasks.
Since Celery tasks run in separate processes, we need a synchronous wrapper.
"""
import asyncio
from app.websocket.broadcaster import broadcaster
import logging

logger = logging.getLogger(__name__)


def broadcast_sync(coro):
    """
    Run async broadcast function synchronously from Celery task.
    Creates new event loop if needed.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        return None


def broadcast_p0_lock_completed(claim_id: str, lock_name: str, lock_number: int, result: dict):
    """Broadcast P0 lock completion from Celery task."""
    broadcast_sync(broadcaster.broadcast_p0_lock_completed(
        claim_id=claim_id,
        lock_name=lock_name,
        lock_number=lock_number,
        total_locks=6,
        result=result
    ))


def broadcast_processing_progress(claim_id: str, step: str, status: str, progress: int, message: str = None):
    """Broadcast processing progress from Celery task."""
    broadcast_sync(broadcaster.broadcast_processing_progress(
        claim_id=claim_id,
        step=step,
        status=status,
        progress=progress,
        message=message
    ))


def broadcast_claim_state_changed(claim_id: str, old_status: str, new_status: str, reason: str = None):
    """Broadcast claim state change from Celery task."""
    broadcast_sync(broadcaster.broadcast_claim_state_changed(
        claim_id=claim_id,
        old_status=old_status,
        new_status=new_status,
        reason=reason
    ))


def broadcast_draft_ready(claim_id: str, icve_total: float, damages_count: int):
    """Broadcast draft ready from Celery task."""
    broadcast_sync(broadcaster.broadcast_draft_ready(
        claim_id=claim_id,
        icve_total=icve_total,
        damages_count=damages_count
    ))


def broadcast_claim_assigned(claim_id: str, surveyor_id: str, surveyor_name: str):
    """Broadcast claim assignment from Celery task."""
    broadcast_sync(broadcaster.broadcast_claim_assigned(
        claim_id=claim_id,
        surveyor_id=surveyor_id,
        surveyor_name=surveyor_name
    ))


def broadcast_surveyor_notification(surveyor_id: str, claim_id: str, claim_summary: dict):
    """Broadcast surveyor notification from Celery task."""
    broadcast_sync(broadcaster.broadcast_surveyor_notification(
        surveyor_id=surveyor_id,
        claim_id=claim_id,
        claim_summary=claim_summary
    ))
