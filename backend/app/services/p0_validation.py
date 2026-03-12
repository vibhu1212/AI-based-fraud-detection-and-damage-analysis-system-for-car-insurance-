from celery.utils.log import get_task_logger
from app.models.claim import Claim

logger = get_task_logger(__name__)

def validate_p0_locks(claim: Claim) -> bool:
    """
    Validate all P0 Master Locks before DRAFT_READY transition (P0 Lock 10).
    Returns True only if ALL locks are satisfied.
    """
    if not claim.p0_locks:
        logger.error(f"Claim {claim.id} has no p0_locks initialized")
        return False
        
    required_locks = [
        "quality_gate_passed",      # P0 Lock 1
        "vin_hash_generated",        # P0 Lock 2
        "damage_detected",           # P0 Lock 3
        "damage_hash_generated",     # P0 Lock 4
        "duplicate_check_completed", # P0 Lock 5
        "icve_estimate_generated"    # P0 Lock 6
    ]
    
    missing_locks = []
    
    for lock_name in required_locks:
        if not claim.p0_locks.get(lock_name, False):
            missing_locks.append(lock_name)
    
    if missing_locks:
        logger.error(f"P0 locks missing for claim {claim.id}: {missing_locks}")
        return False
    
    logger.info(f"All P0 locks satisfied for claim {claim.id}")
    return True
