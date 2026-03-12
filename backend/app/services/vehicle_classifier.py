"""
Vehicle Classification Service
Classifies vehicle type using trained YOLOv8n classifier
"""
import torch
from pathlib import Path
from typing import Optional, Dict
from celery.utils.log import get_task_logger
from ultralytics import YOLO

logger = get_task_logger(__name__)

# Vehicle type mapping from model classes to our system
VEHICLE_TYPE_MAPPING = {
    "bus": "BUS",
    "car": "CAR",
    "motorbike": "MOTORCYCLE",
    "threewheel": "AUTO_RICKSHAW",
    "truck": "TRUCK",
    "van": "VAN"
}

# Reverse mapping for display
VEHICLE_TYPE_DISPLAY = {
    "BUS": "Bus",
    "CAR": "Car",
    "MOTORCYCLE": "Motorcycle",
    "AUTO_RICKSHAW": "Auto-rickshaw",
    "TRUCK": "Truck",
    "VAN": "Van"
}


class VehicleClassifier:
    """
    Vehicle type classifier using trained YOLOv8n model
    Achieves 97.6% accuracy on test set
    """
    
    def __init__(self, model_path: str = "yolov8n_vehicle_classifier.pt"):
        # Handle both absolute and relative paths
        if not Path(model_path).is_absolute():
            # If relative, check current directory first, then backend directory
            if Path(model_path).exists():
                self.model_path = Path(model_path)
            elif (Path("backend") / model_path).exists():
                self.model_path = Path("backend") / model_path
            else:
                self.model_path = Path(model_path)
        else:
            self.model_path = Path(model_path)
        
        self.model = self._load_model()
        
    def _load_model(self) -> YOLO:
        """Load trained vehicle classification model"""
        try:
            # Patch torch.load for YOLOv8 compatibility
            original_load = torch.load
            
            def patched_load(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            
            torch.load = patched_load
            
            # Check for trained model
            if self.model_path.exists():
                logger.info(f"Loading trained vehicle classifier: {self.model_path}")
                model = YOLO(str(self.model_path))
            else:
                logger.warning(f"Trained vehicle classifier not found at {self.model_path}")
                logger.warning("Vehicle classification will not be available")
                model = None
            
            # Restore original torch.load
            torch.load = original_load
            
            return model
        except Exception as e:
            logger.error(f"Failed to load vehicle classifier: {e}")
            return None
    
    def classify(self, image_path: str, confidence_threshold: float = 0.5) -> Optional[Dict]:
        """
        Classify vehicle type from image
        
        Args:
            image_path: Path to image file
            confidence_threshold: Minimum confidence for classification
            
        Returns:
            Dict with vehicle_type, confidence, and raw_class or None if classification fails
        """
        if self.model is None:
            logger.warning("Vehicle classifier not available")
            return None
        
        try:
            # Run inference
            results = self.model(image_path, verbose=False)
            
            if not results or len(results) == 0:
                logger.warning(f"No classification results for {image_path}")
                return None
            
            # Get top prediction
            result = results[0]
            
            # For classification, probs contains the class probabilities
            if hasattr(result, 'probs') and result.probs is not None:
                top_class_idx = int(result.probs.top1)
                confidence = float(result.probs.top1conf)
                
                # Get class name from model
                if hasattr(self.model, 'names'):
                    raw_class = self.model.names[top_class_idx]
                else:
                    raw_class = f"class_{top_class_idx}"
                
                # Check confidence threshold
                if confidence < confidence_threshold:
                    logger.warning(f"Low confidence ({confidence:.2f}) for vehicle classification")
                    return None
                
                # Map to our vehicle type
                vehicle_type = VEHICLE_TYPE_MAPPING.get(raw_class, "CAR")  # Default to CAR
                
                logger.info(f"Classified vehicle: {vehicle_type} (confidence: {confidence:.2f})")
                
                return {
                    "vehicle_type": vehicle_type,
                    "confidence": confidence,
                    "raw_class": raw_class,
                    "display_name": VEHICLE_TYPE_DISPLAY.get(vehicle_type, vehicle_type)
                }
            else:
                logger.warning("No probability data in classification result")
                return None
                
        except Exception as e:
            logger.error(f"Vehicle classification failed: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if vehicle classifier is available"""
        return self.model is not None
