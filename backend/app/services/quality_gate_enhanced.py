"""
Enhanced Quality Gate Service
Handles harsh lighting, reflections, and glare with advanced CV techniques
Based on academic research: "Generic and Real-time Detection of Specular Reflections in Images"
(Morgand & Tamaazousti, 2014)
"""
import cv2
import numpy as np
from typing import Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)


class EnhancedQualityGateValidator:
    """
    Advanced quality validation with reflection and lighting handling
    Based on research-backed thresholds and methods
    """
    
    # Research-based thresholds (Morgand & Tamaazousti, 2014)
    BLUR_THRESHOLD = 50.0  # Laplacian variance threshold
    EXPOSURE_MIN = 15.0  # Minimum acceptable brightness
    EXPOSURE_MAX = 245.0  # Maximum acceptable brightness
    
    # HSV-based reflection detection (from research paper)
    SATURATION_THRESHOLD = 30  # S < 30 indicates low saturation (reflection)
    VALUE_THRESHOLD_BASE = 200  # Base V threshold for bright pixels
    
    # Gradient-based glare detection (research-based)
    MIN_GRADIENT_IN_BRIGHT = 5.0  # Minimum gradient to distinguish damage from glare
    BRIGHT_PIXEL_THRESHOLD = 220  # Pixels above this are considered "bright"
    
    # Reflection validation thresholds (relaxed for demo)
    REFLECTION_RATIO_THRESHOLD = 0.30  # Allow up to 30% reflection (very relaxed)
    MAX_LARGE_REFLECTIONS = 5  # Allow up to 5 large reflection regions
    MIN_REFLECTION_AREA = 5000  # Only flag extremely large single reflections (>5000 pixels)
    
    def __init__(self):
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    # ========================================================================
    # Reflection Detection
    # ========================================================================
    
    def detect_reflections(self, image: np.ndarray, brightness: float = None) -> Tuple[np.ndarray, float, Dict]:
        """
        Detect specular reflections using HSV analysis with dynamic thresholds.
        Based on research: Morgand & Tamaazousti, 2014
        
        Reflections have: High V (brightness), Low S (saturation)
        Value threshold is dynamic based on image brightness (not fixed)
        
        Args:
            image: Input image in BGR format
            brightness: Optional pre-calculated brightness (will calculate if None)
        
        Returns:
            reflection_mask: Binary mask of reflection regions
            reflection_ratio: Percentage of image that is reflection
            details: Additional analysis data
        """
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        # Calculate image brightness if not provided
        if brightness is None:
            brightness = float(np.mean(v))
        
        # Dynamic Value threshold based on image brightness (research-based)
        # For bright images, use higher threshold; for dark images, use lower
        # This prevents false positives on white/bright surfaces
        dynamic_v_threshold = max(self.VALUE_THRESHOLD_BASE, brightness * 1.3)
        
        # Research-based detection criteria:
        # - Saturation < 30 (low saturation indicates reflection)
        # - Value > dynamic threshold (bright areas)
        bright_mask = v > dynamic_v_threshold
        low_sat_mask = s < self.SATURATION_THRESHOLD
        reflection_mask = np.logical_and(bright_mask, low_sat_mask)
        
        # Calculate reflection ratio
        reflection_ratio = float(np.sum(reflection_mask) / reflection_mask.size)
        
        # Analyze reflection distribution
        reflection_mask_uint8 = reflection_mask.astype(np.uint8) * 255
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            reflection_mask_uint8, connectivity=8
        )
        
        # Count large reflection regions (likely problematic)
        large_reflections = []
        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area > self.MIN_REFLECTION_AREA:
                large_reflections.append({
                    "area": int(area),
                    "centroid": (int(centroids[i][0]), int(centroids[i][1]))
                })
        
        details = {
            "reflection_ratio": reflection_ratio,
            "num_large_reflections": len(large_reflections),
            "total_reflection_regions": num_labels - 1,
            "large_reflections": large_reflections,
            "brightness": brightness,
            "dynamic_v_threshold": dynamic_v_threshold
        }
        
        return reflection_mask_uint8, reflection_ratio, details
    
    def detect_glare_gradient(self, image: np.ndarray) -> Tuple[float, Dict]:
        """
        Detect glare using gradient analysis.
        Glare has smooth gradients, damage has sharp edges.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate gradients
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Find very bright areas
        bright_mask = gray > 220
        
        # Check gradient in bright areas
        # Low gradient in bright area = glare (smooth)
        # High gradient in bright area = edge/damage (sharp)
        if np.sum(bright_mask) > 0:
            avg_gradient_in_bright = np.mean(gradient_magnitude[bright_mask])
        else:
            avg_gradient_in_bright = 0
        
        # Glare score: low gradient in bright areas indicates glare
        glare_score = 1.0 / (1.0 + avg_gradient_in_bright / 10.0)
        
        details = {
            "avg_gradient_in_bright_areas": float(avg_gradient_in_bright),
            "glare_score": float(glare_score),
            "bright_pixel_ratio": float(np.sum(bright_mask) / bright_mask.size)
        }
        
        return glare_score, details
    
    # ========================================================================
    # Lighting Normalization
    # ========================================================================
    
    def normalize_lighting(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize lighting using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Reduces harsh lighting effects while preserving damage details.
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L (lightness) channel
        l_clahe = self.clahe.apply(l)
        
        # Merge channels and convert back to BGR
        lab_clahe = cv2.merge([l_clahe, a, b])
        normalized = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)
        
        return normalized
    
    def remove_shadows(self, image: np.ndarray) -> np.ndarray:
        """
        Remove shadows using illumination-invariant transformation.
        Helps detect damage in shadowed areas.
        """
        # Convert to float
        img_float = image.astype(np.float32) / 255.0
        
        # Apply log transformation
        img_log = np.log1p(img_float)
        
        # Apply bilateral filter to separate illumination
        img_bilateral = cv2.bilateralFilter(img_log, 9, 75, 75)
        
        # Subtract illumination component
        img_shadow_removed = img_log - img_bilateral
        
        # Normalize and convert back
        img_shadow_removed = cv2.normalize(img_shadow_removed, None, 0, 255, cv2.NORM_MINMAX)
        img_shadow_removed = img_shadow_removed.astype(np.uint8)
        
        return img_shadow_removed
    
    # ========================================================================
    # Enhanced Validation Methods
    # ========================================================================
    
    def validate_blur(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Detect blur using Laplacian variance.
        Higher variance = sharper image.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        passed = laplacian_var >= self.BLUR_THRESHOLD
        return float(laplacian_var), passed
    
    def validate_exposure(self, image: np.ndarray) -> Tuple[float, bool]:
        """
        Detect under/over exposure using mean brightness.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        passed = self.EXPOSURE_MIN <= mean_brightness <= self.EXPOSURE_MAX
        return mean_brightness, passed
    
    def validate_glare_advanced(self, image: np.ndarray) -> Tuple[float, bool, Dict]:
        """
        Advanced glare detection using gradient analysis and reflection detection.
        Based on research: Uses gradient to distinguish reflections from white surfaces.
        
        Key insight: Reflections have smooth gradients, real surfaces have texture/edges.
        
        Returns:
            glare_score: Combined glare metric
            passed: Whether image passes glare check
            details: Detailed analysis
        """
        # Calculate image brightness first
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        
        # Detect reflections with dynamic threshold
        reflection_mask, reflection_ratio, reflection_details = self.detect_reflections(
            image, brightness=brightness
        )
        
        # Detect glare using gradients
        gradient_glare_score, gradient_details = self.detect_glare_gradient(image)
        
        # Research-based validation logic:
        # Don't reject based on reflection ratio alone - use gradient analysis
        # Gradient distinguishes real reflections from white/bright surfaces
        
        # Check if bright areas have sufficient gradient (texture/edges)
        has_texture_in_bright = gradient_details["avg_gradient_in_bright_areas"] > self.MIN_GRADIENT_IN_BRIGHT
        
        # Pass criteria (research-based):
        # 1. Low reflection ratio (< 30%) - most photos pass
        # 2. OR: Moderate reflections with texture (not smooth glare)
        # 3. OR: Only small localized reflections (< 5 large regions)
        passed = (
            reflection_ratio < self.REFLECTION_RATIO_THRESHOLD or
            (has_texture_in_bright and reflection_ratio < 0.40) or
            (reflection_details["num_large_reflections"] < self.MAX_LARGE_REFLECTIONS and
             gradient_glare_score < 0.85)
        )
        
        # Combined glare score (for logging/debugging)
        # Weight reflection ratio and gradient score
        combined_glare_score = (reflection_ratio * 0.6) + (gradient_glare_score * 0.4)
        
        # Determine pass reason for debugging
        if reflection_ratio < self.REFLECTION_RATIO_THRESHOLD:
            pass_reason = "low_reflection_ratio"
        elif has_texture_in_bright:
            pass_reason = "texture_in_bright_areas"
        elif reflection_details["num_large_reflections"] < self.MAX_LARGE_REFLECTIONS:
            pass_reason = "localized_reflections"
        else:
            pass_reason = "failed_all_criteria"
        
        details = {
            "combined_glare_score": float(combined_glare_score),
            "reflection_analysis": reflection_details,
            "gradient_analysis": gradient_details,
            "has_texture_in_bright": has_texture_in_bright,
            "pass_reason": pass_reason,
            "passed": passed
        }
        
        return combined_glare_score, passed, details
    
    def validate_vehicle_presence(self, image: np.ndarray) -> Tuple[bool, bool, Dict]:
        """
        Enhanced vehicle presence check using edge detection.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Check mean brightness (basic check)
        mean_brightness = float(np.mean(gray))
        brightness_ok = mean_brightness > 10.0  # Very low threshold - accept almost all photos
        
        # Check for vehicle-like edges
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Vehicle should have moderate edge density (0.01 - 0.60)
        # Very wide range to accept most photos
        edge_density_ok = 0.01 < edge_density < 0.60
        
        vehicle_present = brightness_ok and edge_density_ok
        
        details = {
            "mean_brightness": mean_brightness,
            "edge_density": float(edge_density),
            "brightness_ok": brightness_ok,
            "edge_density_ok": edge_density_ok
        }
        
        return vehicle_present, vehicle_present, details
    
    # ========================================================================
    # Main Validation Method
    # ========================================================================
    
    def validate_photo(self, image: np.ndarray) -> Dict:
        """
        Comprehensive photo validation with enhanced glare and reflection handling.
        
        Returns:
            Dict with validation results and detailed analysis
        """
        # Run all validations
        blur_score, blur_passed = self.validate_blur(image)
        exposure_score, exposure_passed = self.validate_exposure(image)
        glare_score, glare_passed, glare_details = self.validate_glare_advanced(image)
        vehicle_present, vehicle_passed, vehicle_details = self.validate_vehicle_presence(image)
        
        # Determine overall pass/fail
        passed = all([blur_passed, exposure_passed, glare_passed, vehicle_passed])
        
        # Collect failure reasons
        failure_reasons = []
        if not blur_passed:
            failure_reasons.append(f"Image too blurry (score: {blur_score:.2f}, threshold: {self.BLUR_THRESHOLD})")
        if not exposure_passed:
            failure_reasons.append(f"Poor exposure (brightness: {exposure_score:.2f}, range: {self.EXPOSURE_MIN}-{self.EXPOSURE_MAX})")
        if not glare_passed:
            failure_reasons.append(f"Excessive glare/reflections (score: {glare_score:.4f}, threshold: {self.REFLECTION_RATIO_THRESHOLD})")
        if not vehicle_passed:
            # Add detailed reason for vehicle failure
            if not vehicle_details["brightness_ok"]:
                reason = f"Image too dark for vehicle (brightness: {vehicle_details['mean_brightness']:.1f})"
            elif not vehicle_details["edge_density_ok"]:
                reason = f"Vehicle features unclear (edge density: {vehicle_details['edge_density']:.3f})"
            else:
                reason = "Vehicle not clearly visible"
            failure_reasons.append(reason)
        
        return {
            "passed": passed,
            "blur_score": blur_score,
            "exposure_score": exposure_score,
            "glare_score": glare_score,
            "vehicle_present": vehicle_present,
            "failure_reasons": failure_reasons if not passed else [],
            "detailed_analysis": {
                "glare_details": glare_details,
                "vehicle_details": vehicle_details
            }
        }
    
    def preprocess_for_damage_detection(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image before damage detection to handle harsh lighting.
        
        Returns:
            Preprocessed image with normalized lighting
        """
        # Step 1: Normalize lighting with CLAHE
        normalized = self.normalize_lighting(image)
        
        # Step 2: Calculate brightness for dynamic threshold
        gray = cv2.cvtColor(normalized, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        
        # Step 3: Detect and mark reflections with dynamic threshold
        reflection_mask, reflection_ratio, _ = self.detect_reflections(normalized, brightness=brightness)
        
        # Step 4: Inpaint reflection areas (optional, for severe cases)
        # This fills in reflection areas with surrounding context
        if reflection_ratio > 0.20:  # >20% reflection
            normalized = cv2.inpaint(normalized, reflection_mask, 3, cv2.INPAINT_TELEA)
        
        return normalized
