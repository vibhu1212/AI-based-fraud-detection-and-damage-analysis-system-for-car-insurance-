"""
Comprehensive validation test with real dataset images
- Tests with actual car damage images
- Saves annotated images for visual inspection
- Compares system results with expected outcomes
- Identifies and reports any issues
"""
import cv2
import numpy as np
import sys
from pathlib import Path
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quality_gate_enhanced import EnhancedQualityGateValidator


def analyze_image_visually(image: np.ndarray, image_path: str) -> dict:
    """
    Perform visual analysis of the image to determine expected quality gate results
    This simulates what a human would assess
    """
    # Calculate basic metrics
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Blur assessment (Laplacian variance)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = laplacian_var < 50.0
    
    # Brightness assessment
    mean_brightness = float(np.mean(gray))
    is_too_dark = mean_brightness < 15.0
    is_too_bright = mean_brightness > 245.0
    
    # Glare assessment (bright pixels)
    bright_pixels = np.sum(gray > 220)
    total_pixels = gray.shape[0] * gray.shape[1]
    bright_ratio = bright_pixels / total_pixels
    
    # HSV analysis for reflections
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    
    # Reflections: high V, low S
    reflection_mask = np.logical_and(v > 200, s < 30)
    reflection_ratio = float(np.sum(reflection_mask) / reflection_mask.size)
    
    # Edge density for vehicle presence
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    has_vehicle_features = 0.01 < edge_density < 0.60
    
    # Determine expected result
    expected_pass = True
    issues = []
    
    if is_blurry:
        expected_pass = False
        issues.append(f"Blurry (variance: {laplacian_var:.2f})")
    
    if is_too_dark or is_too_bright:
        expected_pass = False
        issues.append(f"Poor exposure (brightness: {mean_brightness:.1f})")
    
    if reflection_ratio > 0.30:  # Above threshold
        expected_pass = False
        issues.append(f"Excessive glare ({reflection_ratio:.2%})")
    
    if not has_vehicle_features:
        expected_pass = False
        issues.append(f"No vehicle features (edge density: {edge_density:.3f})")
    
    return {
        "expected_pass": expected_pass,
        "issues": issues,
        "metrics": {
            "blur_score": laplacian_var,
            "brightness": mean_brightness,
            "reflection_ratio": reflection_ratio,
            "bright_pixel_ratio": bright_ratio,
            "edge_density": edge_density
        }
    }


def create_annotated_image(image: np.ndarray, result: dict, visual_analysis: dict, 
                          system_pass: bool, expected_pass: bool) -> np.ndarray:
    """Create an annotated image showing the analysis results"""
    # Create a copy for annotation
    annotated = image.copy()
    h, w = annotated.shape[:2]
    
    # Add semi-transparent overlay at top
    overlay = annotated.copy()
    cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
    annotated = cv2.addWeighted(annotated, 0.7, overlay, 0.3, 0)
    
    # Determine status color
    if system_pass == expected_pass:
        status_color = (0, 255, 0)  # Green - correct
        status_text = "✓ CORRECT"
    else:
        status_color = (0, 0, 255)  # Red - mismatch
        status_text = "✗ MISMATCH"
    
    # Add text annotations
    font = cv2.FONT_HERSHEY_SIMPLEX
    y_offset = 25
    
    # Status
    cv2.putText(annotated, status_text, (10, y_offset), font, 0.7, status_color, 2)
    y_offset += 25
    
    # System result
    system_color = (0, 255, 0) if system_pass else (0, 0, 255)
    cv2.putText(annotated, f"System: {'PASS' if system_pass else 'FAIL'}", 
                (10, y_offset), font, 0.6, system_color, 2)
    y_offset += 20
    
    # Expected result
    expected_color = (0, 255, 0) if expected_pass else (0, 0, 255)
    cv2.putText(annotated, f"Expected: {'PASS' if expected_pass else 'FAIL'}", 
                (10, y_offset), font, 0.6, expected_color, 2)
    y_offset += 20
    
    # Key metrics
    glare_details = result['detailed_analysis']['glare_details']
    reflection_ratio = glare_details['reflection_analysis']['reflection_ratio']
    
    cv2.putText(annotated, f"Glare: {reflection_ratio:.1%} | Blur: {result['blur_score']:.0f}", 
                (10, y_offset), font, 0.5, (255, 255, 255), 1)
    
    return annotated


def test_dataset_images(num_images=10):
    """Test with real dataset images and validate results"""
    print("🔍 Comprehensive Dataset Validation Test")
    print("="*80)
    print("Testing with real car damage images from dataset")
    print("Comparing system results with visual analysis")
    print("="*80)
    
    # Initialize validator
    validator = EnhancedQualityGateValidator()
    print(f"\n✓ Validator initialized")
    print(f"  Reflection threshold: {validator.REFLECTION_RATIO_THRESHOLD:.0%}")
    print(f"  Blur threshold: {validator.BLUR_THRESHOLD}")
    
    # Find test images from different datasets
    datasets = [
        "backend/datasets/raw/cdd/train/images",
        "backend/datasets/raw/urfu_damage/train/images",
        "backend/datasets/raw/curacel_ai/train/images",
    ]
    
    test_images = []
    for dataset_path in datasets:
        path = Path(dataset_path)
        if path.exists():
            images = list(path.glob("*.jpg"))[:4]  # Take 4 from each
            test_images.extend(images)
    
    if not test_images:
        print("❌ No images found in datasets")
        return 1
    
    # Limit to requested number
    test_images = test_images[:num_images]
    print(f"\n📸 Found {len(test_images)} images to test\n")
    
    # Create output directory for annotated images
    output_dir = Path("backend/tests/validation_output")
    output_dir.mkdir(exist_ok=True)
    
    # Test each image
    results = []
    correct_predictions = 0
    
    for idx, image_path in enumerate(test_images, 1):
        print(f"\n{'='*80}")
        print(f"Test {idx}/{len(test_images)}: {image_path.name}")
        print(f"{'='*80}")
        
        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"❌ Failed to load image")
            continue
        
        print(f"✓ Image loaded: {image.shape}")
        
        # Perform visual analysis
        print(f"\n🔍 Visual Analysis:")
        visual_analysis = analyze_image_visually(image, str(image_path))
        print(f"  Expected: {'✅ PASS' if visual_analysis['expected_pass'] else '❌ FAIL'}")
        if visual_analysis['issues']:
            print(f"  Issues detected:")
            for issue in visual_analysis['issues']:
                print(f"    - {issue}")
        print(f"  Metrics:")
        for key, value in visual_analysis['metrics'].items():
            print(f"    {key}: {value:.2f}")
        
        # Run system validation
        print(f"\n🤖 System Validation:")
        result = validator.validate_photo(image)
        system_pass = result['passed']
        
        print(f"  Result: {'✅ PASS' if system_pass else '❌ FAIL'}")
        print(f"  Blur: {result['blur_score']:.2f} (threshold: {validator.BLUR_THRESHOLD})")
        print(f"  Exposure: {result['exposure_score']:.2f}")
        print(f"  Glare: {result['glare_score']:.4f}")
        
        # Glare details
        glare_details = result['detailed_analysis']['glare_details']
        reflection_ratio = glare_details['reflection_analysis']['reflection_ratio']
        print(f"  Reflection ratio: {reflection_ratio:.2%} (threshold: {validator.REFLECTION_RATIO_THRESHOLD:.0%})")
        print(f"  Pass reason: {glare_details['pass_reason']}")
        
        if result['failure_reasons']:
            print(f"  Failure reasons:")
            for reason in result['failure_reasons']:
                print(f"    - {reason}")
        
        # Compare results
        expected_pass = visual_analysis['expected_pass']
        matches = (system_pass == expected_pass)
        
        print(f"\n📊 Comparison:")
        print(f"  System: {'PASS' if system_pass else 'FAIL'}")
        print(f"  Expected: {'PASS' if expected_pass else 'FAIL'}")
        print(f"  Match: {'✅ YES' if matches else '❌ NO - MISMATCH!'}")
        
        if matches:
            correct_predictions += 1
        else:
            print(f"\n⚠️  MISMATCH DETECTED!")
            print(f"  System said: {'PASS' if system_pass else 'FAIL'}")
            print(f"  Should be: {'PASS' if expected_pass else 'FAIL'}")
            print(f"  Visual issues: {', '.join(visual_analysis['issues']) if visual_analysis['issues'] else 'None'}")
            print(f"  System issues: {', '.join(result['failure_reasons']) if result['failure_reasons'] else 'None'}")
        
        # Create annotated image
        annotated = create_annotated_image(image, result, visual_analysis, 
                                          system_pass, expected_pass)
        
        # Save annotated image
        output_path = output_dir / f"test_{idx:02d}_{image_path.stem}_{'match' if matches else 'mismatch'}.jpg"
        cv2.imwrite(str(output_path), annotated)
        print(f"\n💾 Saved annotated image: {output_path.name}")
        
        # Store result
        results.append({
            "image": image_path.name,
            "system_pass": system_pass,
            "expected_pass": expected_pass,
            "matches": matches,
            "visual_analysis": visual_analysis,
            "system_result": {
                "blur_score": result['blur_score'],
                "exposure_score": result['exposure_score'],
                "glare_score": result['glare_score'],
                "reflection_ratio": reflection_ratio,
                "failure_reasons": result['failure_reasons']
            }
        })
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"📈 VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total images tested: {len(results)}")
    print(f"Correct predictions: {correct_predictions}/{len(results)} ({correct_predictions/len(results)*100:.1f}%)")
    print(f"Mismatches: {len(results) - correct_predictions}")
    
    # Detailed results
    print(f"\n📋 Detailed Results:")
    for idx, r in enumerate(results, 1):
        status = "✅" if r['matches'] else "❌"
        print(f"{status} {idx}. {r['image']}: System={'PASS' if r['system_pass'] else 'FAIL'}, Expected={'PASS' if r['expected_pass'] else 'FAIL'}")
    
    # Analyze mismatches
    mismatches = [r for r in results if not r['matches']]
    if mismatches:
        print(f"\n⚠️  MISMATCHES ANALYSIS:")
        for r in mismatches:
            print(f"\n  Image: {r['image']}")
            print(f"    System: {'PASS' if r['system_pass'] else 'FAIL'}")
            print(f"    Expected: {'PASS' if r['expected_pass'] else 'FAIL'}")
            print(f"    Visual issues: {', '.join(r['visual_analysis']['issues']) if r['visual_analysis']['issues'] else 'None'}")
            print(f"    System issues: {', '.join(r['system_result']['failure_reasons']) if r['system_result']['failure_reasons'] else 'None'}")
            print(f"    Reflection: {r['system_result']['reflection_ratio']:.2%}")
    
    # Save results to JSON
    results_file = output_dir / "validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {results_file}")
    
    print(f"\n📁 Annotated images saved to: {output_dir}/")
    print(f"   Review images to see visual comparison")
    
    # Determine if validation passed
    accuracy = correct_predictions / len(results) * 100
    if accuracy >= 80:
        print(f"\n✅ VALIDATION PASSED (Accuracy: {accuracy:.1f}%)")
        return 0
    else:
        print(f"\n⚠️  VALIDATION NEEDS REVIEW (Accuracy: {accuracy:.1f}%)")
        print(f"   Review annotated images in {output_dir}/")
        return 1


if __name__ == "__main__":
    import sys
    num_images = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    exit(test_dataset_images(num_images))
