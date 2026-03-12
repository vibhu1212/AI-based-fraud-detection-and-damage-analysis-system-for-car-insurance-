"""
Duplicate Detection Task (P0 Lock 5)
Detects duplicate/fraudulent claims using VIN hash and damage hash matching
"""
import cv2
import numpy as np
from datetime import datetime, timedelta
from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import and_
from app.models.claim import Claim
from app.models.damage import DamageDetection, DuplicateCheckResult
from app.models.report import AIArtifact
from app.models.enums import RiskLevel
from typing import Dict, List, Tuple, Optional
import json

logger = get_task_logger(__name__)

# Duplicate detection settings
MATCH_WINDOW_DAYS = 180  # 6 months
PHASH_HAMMING_THRESHOLD_HIGH = 10  # < 10 = very similar (HIGH risk)
PHASH_HAMMING_THRESHOLD_MEDIUM = 20  # < 20 = similar (MEDIUM risk)
ORB_SIMILARITY_THRESHOLD_HIGH = 0.7  # > 0.7 = very similar (HIGH risk)
ORB_SIMILARITY_THRESHOLD_MEDIUM = 0.5  # > 0.5 = similar (MEDIUM risk)
OVERALL_SIMILARITY_THRESHOLD_HIGH = 0.75  # > 0.75 = HOLD
OVERALL_SIMILARITY_THRESHOLD_MEDIUM = 0.50  # > 0.50 = FLAG_REVIEW


class DuplicateDetector:
    """Duplicate detection logic using hash matching"""
    
    def calculate_hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Calculate Hamming distance between two pHash strings.
        Returns number of differing bits.
        """
        if not hash1 or not hash2:
            return 999  # Max distance if either hash is missing
            
        try:
            # Convert hex strings to integers and XOR them
            h1 = int(hash1, 16)
            h2 = int(hash2, 16)
            xor = h1 ^ h2
            
            # Count number of 1s in binary representation
            distance = bin(xor).count('1')
            return distance
        except Exception as e:
            logger.error(f"Failed to calculate Hamming distance: {e}")
            return 999
            
    def calculate_orb_similarity(
        self, 
        orb1: Dict, 
        orb2: Dict
    ) -> float:
        """
        Calculate ORB descriptor similarity using BFMatcher.
        Returns similarity score [0, 1] where 1 = identical.
        """
        if not orb1 or not orb2:
            return 0.0
            
        desc1 = orb1.get('descriptors', [])
        desc2 = orb2.get('descriptors', [])
        
        if not desc1 or not desc2:
            return 0.0
            
        try:
            # Convert to numpy arrays
            desc1_np = np.array(desc1, dtype=np.uint8)
            desc2_np = np.array(desc2, dtype=np.uint8)
            
            # Use BFMatcher with Hamming distance
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(desc1_np, desc2_np)
            
            # Calculate similarity as ratio of good matches
            max_matches = min(len(desc1), len(desc2))
            if max_matches == 0:
                return 0.0
                
            similarity = len(matches) / max_matches
            return min(1.0, similarity)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Failed to calculate ORB similarity: {e}")
            return 0.0
            
    def compare_damages(
        self,
        damages1: List[DamageDetection],
        damages2: List[DamageDetection]
    ) -> Tuple[float, List[Dict]]:
        """
        Compare two sets of damages and calculate overall similarity.
        Returns (overall_similarity, match_details).
        """
        if not damages1 or not damages2:
            return 0.0, []
            
        match_details = []
        total_similarity = 0.0
        comparison_count = 0
        
        # Compare each damage in set 1 with all damages in set 2
        for d1 in damages1:
            best_match_score = 0.0
            best_match_id = None
            
            for d2 in damages2:
                # Calculate pHash similarity (inverse of Hamming distance)
                hamming_dist = self.calculate_hamming_distance(
                    d1.damage_hash_phash,
                    d2.damage_hash_phash
                )
                phash_similarity = max(0.0, 1.0 - (hamming_dist / 64.0))  # Normalize to [0, 1]
                
                # Calculate ORB similarity
                orb_similarity = self.calculate_orb_similarity(
                    d1.damage_hash_orb,
                    d2.damage_hash_orb
                )
                
                # Combined similarity (weighted average)
                combined_similarity = (phash_similarity * 0.6) + (orb_similarity * 0.4)
                
                if combined_similarity > best_match_score:
                    best_match_score = combined_similarity
                    best_match_id = str(d2.id)
            
            if best_match_score > 0.3:  # Only count meaningful matches
                match_details.append({
                    "damage1_id": str(d1.id),
                    "damage2_id": best_match_id,
                    "similarity": best_match_score
                })
                total_similarity += best_match_score
                comparison_count += 1
        
        # Calculate overall similarity
        if comparison_count == 0:
            return 0.0, []
            
        overall_similarity = total_similarity / comparison_count
        return overall_similarity, match_details
        
    def determine_fraud_action(
        self,
        similarity_score: float,
        hamming_distance: int,
        orb_similarity: float
    ) -> str:
        """
        Determine fraud action based on similarity metrics.
        Returns: PROCEED, FLAG_REVIEW, or HOLD
        """
        # HOLD: Very high similarity (likely duplicate/fraud)
        if (similarity_score >= OVERALL_SIMILARITY_THRESHOLD_HIGH or
            hamming_distance < PHASH_HAMMING_THRESHOLD_HIGH or
            orb_similarity >= ORB_SIMILARITY_THRESHOLD_HIGH):
            return "HOLD"
        
        # FLAG_REVIEW: Medium similarity (suspicious)
        if (similarity_score >= OVERALL_SIMILARITY_THRESHOLD_MEDIUM or
            hamming_distance < PHASH_HAMMING_THRESHOLD_MEDIUM or
            orb_similarity >= ORB_SIMILARITY_THRESHOLD_MEDIUM):
            return "FLAG_REVIEW"
        
        # PROCEED: Low similarity (likely legitimate)
        return "PROCEED"
        
    def determine_risk_level(self, fraud_action: str) -> RiskLevel:
        """Map fraud action to risk level"""
        if fraud_action == "HOLD":
            return RiskLevel.RED
        elif fraud_action == "FLAG_REVIEW":
            return RiskLevel.AMBER
        else:
            return RiskLevel.GREEN


@shared_task(name="app.tasks.duplicate_detection.check_duplicates")
def check_duplicates(claim_id: str) -> Dict:
    """
    Celery task: Check for duplicate claims using VIN hash and damage hash matching.
    Sets P0 Lock 5: duplicate_check_completed
    """
    from app.models.base import SessionLocal
    
    logger.info(f"Starting duplicate check for claim {claim_id}")
    
    db = SessionLocal()
    try:
        # Get claim
        claim = db.query(Claim).filter(Claim.id == claim_id).first()
        if not claim:
            raise ValueError(f"Claim {claim_id} not found")
            
        # Check previous locks
        if not claim.p0_locks.get("vin_hash_generated", False):
            logger.warning(f"VIN hash not generated for claim {claim_id}, skipping duplicate check")
            return {"status": "skipped", "reason": "VIN hash not generated"}
            
        if not claim.p0_locks.get("damage_hash_generated", False):
            logger.warning(f"Damage hashes not generated for claim {claim_id}, skipping duplicate check")
            return {"status": "skipped", "reason": "Damage hashes not generated"}
            
        # Check if VIN hash exists
        if not claim.vin_hash:
            logger.warning(f"No VIN hash found for claim {claim_id}")
            # Still complete the check but with PROCEED action
            result = DuplicateCheckResult(
                claim_id=claim_id,
                fraud_action="PROCEED",
                match_window_days=MATCH_WINDOW_DAYS,
                duplicate_check_version="v1.0"
            )
            db.add(result)
            
            claim.p0_locks["duplicate_check_completed"] = True
            flag_modified(claim, "p0_locks")
            db.commit()
            
            return {"status": "completed", "claim_id": claim_id, "fraud_action": "PROCEED", "reason": "No VIN hash"}
        
        # Query historical claims with same VIN hash within time window
        cutoff_date = datetime.utcnow() - timedelta(days=MATCH_WINDOW_DAYS)
        
        historical_claims = db.query(Claim).filter(
            and_(
                Claim.vin_hash == claim.vin_hash,
                Claim.id != claim_id,  # Exclude current claim
                Claim.created_at >= cutoff_date
            )
        ).all()
        
        logger.info(f"Found {len(historical_claims)} historical claims with same VIN hash")
        
        if not historical_claims:
            # No duplicates found - PROCEED
            result = DuplicateCheckResult(
                claim_id=claim_id,
                fraud_action="PROCEED",
                match_window_days=MATCH_WINDOW_DAYS,
                duplicate_check_version="v1.0"
            )
            db.add(result)
            
            claim.risk_level = RiskLevel.GREEN
            claim.p0_locks["duplicate_check_completed"] = True
            flag_modified(claim, "p0_locks")
            db.commit()
            
            logger.info(f"No duplicates found for claim {claim_id} - PROCEED")
            return {
                "status": "completed",
                "claim_id": claim_id,
                "fraud_action": "PROCEED",
                "historical_claims_checked": 0
            }
        
        # Get damages for current claim
        current_damages = db.query(DamageDetection).filter(
            DamageDetection.claim_id == claim_id
        ).all()
        
        detector = DuplicateDetector()
        
        # Compare with each historical claim
        best_match = None
        highest_similarity = 0.0
        
        for hist_claim in historical_claims:
            hist_damages = db.query(DamageDetection).filter(
                DamageDetection.claim_id == hist_claim.id
            ).all()
            
            if not hist_damages:
                continue
            
            # Compare damages
            similarity, match_details = detector.compare_damages(current_damages, hist_damages)
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = {
                    "claim_id": str(hist_claim.id),
                    "similarity": similarity,
                    "match_details": match_details
                }
        
        # Determine fraud action and risk level
        if best_match:
            # Calculate aggregate metrics for fraud action
            avg_hamming = 64 * (1.0 - highest_similarity)  # Approximate
            fraud_action = detector.determine_fraud_action(
                highest_similarity,
                int(avg_hamming),
                highest_similarity  # Using overall similarity as proxy
            )
            risk_level = detector.determine_risk_level(fraud_action)
            
            # Store result
            result = DuplicateCheckResult(
                claim_id=claim_id,
                matched_claim_id=best_match["claim_id"],
                similarity_score=highest_similarity,
                hamming_distance=int(avg_hamming),
                orb_similarity=highest_similarity,
                fraud_action=fraud_action,
                match_window_days=MATCH_WINDOW_DAYS,
                duplicate_check_version="v1.0"
            )
            db.add(result)
            
            # Update claim risk level
            claim.risk_level = risk_level
            
        else:
            # No meaningful matches found
            fraud_action = "PROCEED"
            result = DuplicateCheckResult(
                claim_id=claim_id,
                fraud_action=fraud_action,
                match_window_days=MATCH_WINDOW_DAYS,
                duplicate_check_version="v1.0"
            )
            db.add(result)
            claim.risk_level = RiskLevel.GREEN
        
        # Update P0 lock
        claim.p0_locks["duplicate_check_completed"] = True
        flag_modified(claim, "p0_locks")
        
        # Create artifact
        artifact = AIArtifact(
            claim_id=claim_id,
            artifact_type="duplicate_check_result",
            model_name="phash+orb-matcher",
            model_version="v1.0",
            artifact_json={
                "fraud_action": fraud_action,
                "historical_claims_checked": len(historical_claims),
                "best_match": best_match,
                "match_window_days": MATCH_WINDOW_DAYS
            }
        )
        db.add(artifact)
        
        db.commit()
        
        logger.info(f"Duplicate check complete for claim {claim_id}. Action: {fraud_action}")
        
        return {
            "status": "completed",
            "claim_id": claim_id,
            "fraud_action": fraud_action,
            "risk_level": claim.risk_level.value,
            "historical_claims_checked": len(historical_claims),
            "best_match_similarity": highest_similarity if best_match else 0.0
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Duplicate check failed for claim {claim_id}: {str(e)}")
        raise
        
    finally:
        db.close()
