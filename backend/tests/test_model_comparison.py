"""
Model Comparison Test: Current vs Senior's Approach
Compares detection accuracy, speed, and quality metrics
"""
import sys
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.tasks.damage_detection import DamageDetector
from app.tasks.damage_detection_v2 import EnhancedDamageDetector
from app.services.storage import StorageService
from app.models.enums import DamageType


class ModelComparison:
    """Compare current model vs senior's enhanced approach"""
    
    def __init__(self):
        self.storage = StorageService()
        
        # Initialize both detectors
        print("🔧 Initializing detectors...")
        self.current_detector = DamageDetector(self.storage)
        self.enhanced_detector = EnhancedDamageDetector(self.storage)
        print("✓ Both detectors initialized\n")
    
    def get_test_images(self) -> List[str]:
        """Get list of test images from storage"""
        test_images = []
        
        # Check storage/original subdirectories
        storage_path = Path("storage/original")
            # Get all jpg/png files from subdirectories
            for subdir in storage_path.iterdir():
                if subdir.is_dir():
                    for img_file in subdir.glob("*.jpg"):
                        test_images.append(str(img_file))
                    for img_file in subdir.glob("*.png"):
                        test_images.append(str(img_file))
        
        # Also check root storage
        root_storage = Path("backend/storage")
        for img_file in root_storage.glob("*.jpg"):
            test_images.append(str(img_file))
        for img_file in root_storage.glob("*.png"):
            test_images.append(str(img_file))
        
        return test_images[:10]  # Limit to 10 images for quick comparison
    
    def test_detection_speed(self, image_path: str, detector, detector_name: str) -> Tuple[float, int]:
        """Test detection speed and count"""
        start_time = time.time()
        
        try:
            if detector_name == "current":
                # Current detector returns List[Dict]
                detections = detector.process_photo(image_path)
                detection_count = len(detections)
            else:
                # Enhanced detector returns (List[Dict], Dict)
                detections, price_analysis = detector.process_photo(image_path)
                detection_count = len(detections)
        except Exception as e:
            print(f"  ⚠️  Error in {detector_name}: {e}")
            return 0.0, 0
        
        elapsed_time = time.time() - start_time
        return elapsed_time, detection_count
    
    def analyze_detection_quality(self, detections: List[Dict], detector_name: str) -> Dict:
        """Analyze quality metrics of detections"""
        if not detections:
            return {
                "avg_confidence": 0.0,
                "high_confidence_count": 0,
                "damage_types": [],
                "bbox_sizes": []
            }
        
        confidences = [d.get("confidence", 0.0) for d in detections]
        high_conf = sum(1 for c in confidences if c > 0.5)
        
        # Get damage types
        damage_types = []
        for d in detections:
            if "damage_type" in d:
                dt = d["damage_type"]
                if isinstance(dt, DamageType):
                    damage_types.append(dt.value)
                else:
                    damage_types.append(str(dt))
        
        # Calculate bbox sizes (area)
        bbox_sizes = []
        for d in detections:
            bbox = d.get("bbox", [0, 0, 0, 0])
            if len(bbox) == 4:
                width = abs(bbox[2] - bbox[0])
                height = abs(bbox[3] - bbox[1])
                area = width * height
                bbox_sizes.append(area)
        
        return {
            "avg_confidence": np.mean(confidences) if confidences else 0.0,
            "min_confidence": np.min(confidences) if confidences else 0.0,
            "max_confidence": np.max(confidences) if confidences else 0.0,
            "high_confidence_count": high_conf,
            "high_confidence_ratio": high_conf / len(detections) if detections else 0.0,
            "damage_types": list(set(damage_types)),
            "damage_type_diversity": len(set(damage_types)),
            "avg_bbox_size": np.mean(bbox_sizes) if bbox_sizes else 0.0
        }
    
    def run_comparison(self) -> Dict:
        """Run full comparison between models"""
        print("=" * 80)
        print("MODEL COMPARISON: Current vs Senior's Enhanced Approach")
        print("=" * 80)
        print()
        
        # Get test images
        test_images = self.get_test_images()
        
        if not test_images:
            print("❌ No test images found in storage/original/")
            print("   Please run create_test_claim_with_real_photos.py first")
            return {}
        
        print(f"📸 Found {len(test_images)} test images")
        print()
        
        results = {
            "current": {
                "total_time": 0.0,
                "total_detections": 0,
                "images_processed": 0,
                "avg_time_per_image": 0.0,
                "quality_metrics": []
            },
            "enhanced": {
                "total_time": 0.0,
                "total_detections": 0,
                "images_processed": 0,
                "avg_time_per_image": 0.0,
                "quality_metrics": [],
                "total_estimated_cost": 0
            }
        }
        
        # Test each image with both detectors
        for idx, img_path in enumerate(test_images, 1):
            img_name = Path(img_path).name
            print(f"[{idx}/{len(test_images)}] Testing: {img_name}")
            
            # Test current detector
            print("  🔵 Current detector...", end=" ")
            try:
                current_time, current_count = self.test_detection_speed(
                    img_path, self.current_detector, "current"
                )
                current_detections = self.current_detector.process_photo(img_path)
                current_quality = self.analyze_detection_quality(current_detections, "current")
                
                results["current"]["total_time"] += current_time
                results["current"]["total_detections"] += current_count
                results["current"]["images_processed"] += 1
                results["current"]["quality_metrics"].append(current_quality)
                
                print(f"✓ {current_count} detections in {current_time:.3f}s")
            except Exception as e:
                print(f"✗ Error: {e}")
            
            # Test enhanced detector
            print("  🟢 Enhanced detector...", end=" ")
            try:
                enhanced_time, enhanced_count = self.test_detection_speed(
                    img_path, self.enhanced_detector, "enhanced"
                )
                enhanced_detections, price_analysis = self.enhanced_detector.process_photo(img_path)
                enhanced_quality = self.analyze_detection_quality(enhanced_detections, "enhanced")
                
                results["enhanced"]["total_time"] += enhanced_time
                results["enhanced"]["total_detections"] += enhanced_count
                results["enhanced"]["images_processed"] += 1
                results["enhanced"]["quality_metrics"].append(enhanced_quality)
                
                if price_analysis and "total_cost" in price_analysis:
                    results["enhanced"]["total_estimated_cost"] += price_analysis["total_cost"]
                
                print(f"✓ {enhanced_count} detections in {enhanced_time:.3f}s")
                if price_analysis and "total_cost" in price_analysis:
                    print(f"     💰 Estimated cost: ₹{price_analysis['total_cost']:,}")
            except Exception as e:
                print(f"✗ Error: {e}")
            
            print()
        
        # Calculate averages
        if results["current"]["images_processed"] > 0:
            results["current"]["avg_time_per_image"] = (
                results["current"]["total_time"] / results["current"]["images_processed"]
            )
        
        if results["enhanced"]["images_processed"] > 0:
            results["enhanced"]["avg_time_per_image"] = (
                results["enhanced"]["total_time"] / results["enhanced"]["images_processed"]
            )
        
        return results
    
    def print_comparison_report(self, results: Dict):
        """Print detailed comparison report"""
        print("=" * 80)
        print("COMPARISON REPORT")
        print("=" * 80)
        print()
        
        current = results.get("current", {})
        enhanced = results.get("enhanced", {})
        
        # Performance metrics
        print("📊 PERFORMANCE METRICS")
        print("-" * 80)
        print(f"{'Metric':<40} {'Current':<20} {'Enhanced':<20}")
        print("-" * 80)
        
        print(f"{'Images Processed':<40} {current.get('images_processed', 0):<20} {enhanced.get('images_processed', 0):<20}")
        print(f"{'Total Detections':<40} {current.get('total_detections', 0):<20} {enhanced.get('total_detections', 0):<20}")
        print(f"{'Total Time (s)':<40} {current.get('total_time', 0):<20.3f} {enhanced.get('total_time', 0):<20.3f}")
        print(f"{'Avg Time per Image (s)':<40} {current.get('avg_time_per_image', 0):<20.3f} {enhanced.get('avg_time_per_image', 0):<20.3f}")
        
        if current.get('images_processed', 0) > 0:
            current_avg_det = current['total_detections'] / current['images_processed']
            print(f"{'Avg Detections per Image':<40} {current_avg_det:<20.2f}", end="")
        else:
            print(f"{'Avg Detections per Image':<40} {'N/A':<20}", end="")
        
        if enhanced.get('images_processed', 0) > 0:
            enhanced_avg_det = enhanced['total_detections'] / enhanced['images_processed']
            print(f"{enhanced_avg_det:<20.2f}")
        else:
            print(f"{'N/A':<20}")
        
        print()
        
        # Quality metrics
        print("🎯 QUALITY METRICS")
        print("-" * 80)
        
        # Calculate aggregate quality metrics
        for detector_name, detector_results in [("Current", current), ("Enhanced", enhanced)]:
            quality_metrics = detector_results.get("quality_metrics", [])
            if quality_metrics:
                avg_confidence = np.mean([q["avg_confidence"] for q in quality_metrics])
                avg_high_conf_ratio = np.mean([q["high_confidence_ratio"] for q in quality_metrics])
                all_damage_types = set()
                for q in quality_metrics:
                    all_damage_types.update(q["damage_types"])
                
                print(f"\n{detector_name} Detector:")
                print(f"  Average Confidence: {avg_confidence:.3f}")
                print(f"  High Confidence Ratio: {avg_high_conf_ratio:.3f} ({avg_high_conf_ratio*100:.1f}%)")
                print(f"  Unique Damage Types: {len(all_damage_types)}")
                print(f"  Damage Types: {', '.join(sorted(all_damage_types))}")
        
        print()
        
        # Cost estimation (enhanced only)
        if enhanced.get("total_estimated_cost", 0) > 0:
            print("💰 COST ESTIMATION (Enhanced Only)")
            print("-" * 80)
            print(f"Total Estimated Repair Cost: ₹{enhanced['total_estimated_cost']:,}")
            if enhanced.get('images_processed', 0) > 0:
                avg_cost = enhanced['total_estimated_cost'] / enhanced['images_processed']
                print(f"Average Cost per Image: ₹{avg_cost:,.2f}")
            print()
        
        # Recommendation
        print("=" * 80)
        print("🎯 RECOMMENDATION")
        print("=" * 80)
        
        # Compare key metrics
        improvements = []
        regressions = []
        
        if enhanced.get('total_detections', 0) > current.get('total_detections', 0):
            diff = enhanced['total_detections'] - current['total_detections']
            pct = (diff / current['total_detections'] * 100) if current.get('total_detections', 0) > 0 else 0
            improvements.append(f"✓ {diff} more detections (+{pct:.1f}%)")
        elif enhanced.get('total_detections', 0) < current.get('total_detections', 0):
            diff = current['total_detections'] - enhanced['total_detections']
            pct = (diff / current['total_detections'] * 100) if current.get('total_detections', 0) > 0 else 0
            regressions.append(f"✗ {diff} fewer detections (-{pct:.1f}%)")
        
        # Compare quality
        if current.get("quality_metrics") and enhanced.get("quality_metrics"):
            current_avg_conf = np.mean([q["avg_confidence"] for q in current["quality_metrics"]])
            enhanced_avg_conf = np.mean([q["avg_confidence"] for q in enhanced["quality_metrics"]])
            
            if enhanced_avg_conf > current_avg_conf:
                diff = enhanced_avg_conf - current_avg_conf
                improvements.append(f"✓ Higher confidence: {enhanced_avg_conf:.3f} vs {current_avg_conf:.3f} (+{diff:.3f})")
            elif enhanced_avg_conf < current_avg_conf:
                diff = current_avg_conf - enhanced_avg_conf
                regressions.append(f"✗ Lower confidence: {enhanced_avg_conf:.3f} vs {current_avg_conf:.3f} (-{diff:.3f})")
        
        # Speed comparison
        if enhanced.get('avg_time_per_image', 0) < current.get('avg_time_per_image', 0):
            diff = current['avg_time_per_image'] - enhanced['avg_time_per_image']
            pct = (diff / current['avg_time_per_image'] * 100) if current.get('avg_time_per_image', 0) > 0 else 0
            improvements.append(f"✓ Faster: {diff:.3f}s per image ({pct:.1f}% faster)")
        elif enhanced.get('avg_time_per_image', 0) > current.get('avg_time_per_image', 0):
            diff = enhanced['avg_time_per_image'] - current['avg_time_per_image']
            pct = (diff / current['avg_time_per_image'] * 100) if current.get('avg_time_per_image', 0) > 0 else 0
            regressions.append(f"✗ Slower: +{diff:.3f}s per image ({pct:.1f}% slower)")
        
        # Additional features
        if enhanced.get("total_estimated_cost", 0) > 0:
            improvements.append("✓ Provides cost estimation (new feature)")
        
        print("\nImprovements:")
        if improvements:
            for imp in improvements:
                print(f"  {imp}")
        else:
            print("  None detected")
        
        print("\nRegressions:")
        if regressions:
            for reg in regressions:
                print(f"  {reg}")
        else:
            print("  None detected")
        
        print()
        
        # Final recommendation
        improvement_score = len(improvements) - len(regressions)
        
        if improvement_score > 0:
            print("✅ RECOMMENDATION: ADOPT ENHANCED APPROACH")
            print("   The senior's approach shows measurable improvements.")
            print("   Benefits: Better detection, cost estimation, and class-specific damage types.")
        elif improvement_score == 0:
            print("⚖️  RECOMMENDATION: NEUTRAL")
            print("   Both approaches perform similarly. Consider enhanced for additional features.")
        else:
            print("❌ RECOMMENDATION: KEEP CURRENT APPROACH")
            print("   Current implementation performs better on key metrics.")
        
        print("=" * 80)


def main():
    """Run model comparison"""
    try:
        comparison = ModelComparison()
        results = comparison.run_comparison()
        
        if results:
            comparison.print_comparison_report(results)
            
            # Save results to file
            output_file = Path("backend/model_comparison_results.json")
            with open(output_file, 'w') as f:
                # Convert numpy types to native Python types for JSON serialization
                def convert_types(obj):
                    if isinstance(obj, np.integer):
                        return int(obj)
                    elif isinstance(obj, np.floating):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    elif isinstance(obj, dict):
                        return {k: convert_types(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_types(item) for item in obj]
                    return obj
                
                json.dump(convert_types(results), f, indent=2)
            
            print(f"\n📄 Detailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
