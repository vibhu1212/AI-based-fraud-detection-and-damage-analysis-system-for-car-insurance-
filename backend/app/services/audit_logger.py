"""
Audit logging service for tracking all claim actions.
Ensures immutable audit trail for compliance.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from app.models.audit import AuditEvent
from app.models.claim import ClaimStateTransition

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging audit events."""
    
    @staticmethod
    def log_event(
        db: Session,
        claim_id: str,
        action: str,
        actor_user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            action: Action performed (e.g., "CLAIM_CREATED", "DAMAGE_MODIFIED")
            actor_user_id: User who performed the action
            details: Additional details (before/after state, etc.)
            ip_address: IP address of the actor
            user_agent: User agent string
        
        Returns:
            AuditEvent: Created audit event
        """
        try:
            audit_event = AuditEvent(
                claim_id=claim_id,
                actor_user_id=actor_user_id,
                action=action,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(audit_event)
            db.commit()
            db.refresh(audit_event)
            
            logger.info(f"Audit event logged: {action} for claim {claim_id} by {actor_user_id}")
            return audit_event
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def log_state_transition(
        db: Session,
        claim_id: str,
        from_status: str,
        to_status: str,
        actor_user_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> AuditEvent:
        """
        Log a claim state transition.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            from_status: Previous status
            to_status: New status
            actor_user_id: User who triggered the transition
            reason: Reason for transition
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "from_status": from_status,
            "to_status": to_status,
            "reason": reason
        }
        
        return AuditLogger.log_event(
            db=db,
            claim_id=claim_id,
            action="STATE_TRANSITION",
            actor_user_id=actor_user_id,
            details=details
        )
    
    @staticmethod
    def log_surveyor_action(
        db: Session,
        claim_id: str,
        action: str,
        surveyor_id: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log a surveyor action with before/after state.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            action: Action performed (e.g., "DAMAGE_MODIFIED", "REPORT_EDITED")
            surveyor_id: Surveyor user ID
            before_state: State before modification
            after_state: State after modification
            changes: Summary of changes made
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "before": before_state,
            "after": after_state,
            "changes": changes
        }
        
        return AuditLogger.log_event(
            db=db,
            claim_id=claim_id,
            action=action,
            actor_user_id=surveyor_id,
            details=details
        )
    
    @staticmethod
    def log_authentication(
        db: Session,
        action: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an authentication event.
        
        Args:
            db: Database session
            action: Action performed (e.g., "LOGIN_SUCCESS", "LOGIN_FAILED")
            user_id: User ID (if available)
            details: Additional details (email, reason, etc.)
            ip_address: IP address
            user_agent: User agent string
        
        Returns:
            AuditEvent: Created audit event
        
        Note:
            For authentication events, claim_id is set to a special value
            since they're not claim-specific.
        """
        # Use a special claim_id for auth events
        auth_claim_id = "00000000-0000-0000-0000-000000000000"
        
        return AuditLogger.log_event(
            db=db,
            claim_id=auth_claim_id,
            action=action,
            actor_user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_damage_modification(
        db: Session,
        claim_id: str,
        damage_id: str,
        surveyor_id: str,
        modification_type: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """
        Log damage modification by surveyor.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            damage_id: Damage detection UUID
            surveyor_id: Surveyor user ID
            modification_type: Type of modification (CREATE, UPDATE, DELETE)
            before: State before modification
            after: State after modification
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "damage_id": damage_id,
            "modification_type": modification_type,
            "before": before,
            "after": after
        }
        
        return AuditLogger.log_event(
            db=db,
            claim_id=claim_id,
            action="DAMAGE_MODIFIED",
            actor_user_id=surveyor_id,
            details=details
        )
    
    @staticmethod
    def log_report_modification(
        db: Session,
        claim_id: str,
        report_id: str,
        surveyor_id: str,
        version: int,
        changes_summary: Optional[str] = None
    ) -> AuditEvent:
        """
        Log report modification by surveyor.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            report_id: Report draft UUID
            surveyor_id: Surveyor user ID
            version: New version number
            changes_summary: Summary of changes made
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "report_id": report_id,
            "version": version,
            "changes_summary": changes_summary
        }
        
        return AuditLogger.log_event(
            db=db,
            claim_id=claim_id,
            action="REPORT_MODIFIED",
            actor_user_id=surveyor_id,
            details=details
        )
    
    @staticmethod
    def log_approval_decision(
        db: Session,
        claim_id: str,
        surveyor_id: str,
        decision: str,
        reason: Optional[str] = None,
        approved_amount: Optional[float] = None
    ) -> AuditEvent:
        """
        Log claim approval/rejection decision.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            surveyor_id: Surveyor user ID
            decision: Decision made (APPROVED, REJECTED, NEEDS_MORE_INFO)
            reason: Reason for decision
            approved_amount: Approved amount (if applicable)
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "decision": decision,
            "reason": reason,
            "approved_amount": approved_amount
        }
        
        return AuditLogger.log_event(
            db=db,
            claim_id=claim_id,
            action=f"CLAIM_{decision}",
            actor_user_id=surveyor_id,
            details=details
        )
    
    @staticmethod
    def log_profile_modification(
        db: Session,
        user_id: str,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        changes: Dict[str, Any]
    ) -> AuditEvent:
        """
        Log a user profile modification.
        
        Args:
            db: Database session
            user_id: User UUID
            before_state: Profile state before modification
            after_state: Profile state after modification
            changes: Dictionary of changes made
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "before": before_state,
            "after": after_state,
            "changes": changes
        }
        
        # Create audit event without claim_id (profile changes are user-level)
        try:
            audit_event = AuditEvent(
                claim_id=None,  # Profile changes are not claim-specific
                actor_user_id=user_id,
                action="PROFILE_MODIFIED",
                details=details
            )
            
            db.add(audit_event)
            db.commit()
            db.refresh(audit_event)
            
            logger.info(f"Profile modification logged for user {user_id}")
            return audit_event
            
        except Exception as e:
            logger.error(f"Failed to log profile modification: {e}")
            db.rollback()
            raise

    @staticmethod
    def log_logout(
        user_id: str,
        user_role: str,
        db: Session,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditEvent:
        """
        Log a user logout event.
        
        Args:
            user_id: User UUID
            user_role: User role (CUSTOMER, SURVEYOR, ADMIN)
            db: Database session
            ip_address: IP address (optional)
            user_agent: User agent string (optional)
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "user_role": user_role
        }
        
        return AuditLogger.log_authentication(
            db=db,
            action="LOGOUT",
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def log_claim_assignment(
        db: Session,
        claim_id: str,
        surveyor_id: str,
        risk_level: str,
        assignment_reason: Optional[str] = None
    ) -> AuditEvent:
        """
        Log automatic claim assignment to surveyor.
        
        Args:
            db: Database session
            claim_id: Claim UUID
            surveyor_id: Assigned surveyor user ID
            risk_level: Claim risk level (GREEN, AMBER, RED)
            assignment_reason: Reason for assignment
        
        Returns:
            AuditEvent: Created audit event
        """
        details = {
            "assigned_surveyor_id": surveyor_id,
            "risk_level": risk_level,
            "assignment_reason": assignment_reason or "Auto-assigned by system"
        }
        
        return AuditLogger.log_event(
            db=db,
            claim_id=claim_id,
            action="CLAIM_ASSIGNED",
            actor_user_id="SYSTEM",  # System-triggered assignment
            details=details
        )

# Global audit logger instance
audit_logger = AuditLogger()


