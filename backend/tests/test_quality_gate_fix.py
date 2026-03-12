"""
Test script to verify the enhanced quality gate fix
Tests with photos that were previously failing
"""
import cv2
import numpy as np
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quality_gate_enhanced import EnhancedQualityGateValidator


def test_photo(image_path: str, validator: EnhancedQualityGateValidator):
    """Test a single photo with the enhanced validator"""
    print(f"\n{'='*80}")
    print(f"Testing: {image_path}")
    print(f"{'='*80}")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image: {image_path}")
        return False
    
    print(f"✓ Image loaded: {image.shape}")
    
    # Run validation
    result = validator.validate_photo(image)
    
    # Print results
    print(f"\n📊 Validation Results:")
    print(f"  Overall: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
    print(f"  Blur Score: {result['blur_score']:.2f} (threshold: {validator.BLUR_THRESHOLD})")
    print(f"  Exposure: {result['exposure_score']:.2f} (range: {validator.EXPOSURE_MIN}-{validator.EXPOSURE_MAX})")
    print(f"  Glare Score: {result['glare_score']:.4f}")
    print(f"  Vehicle Present: {result['vehicle_present']}")
    
    # Print detailed glare analysis
    if 'detailed_analysis' in result and 'glare_details' in result['detailed_analysis']:
        glare_details = result['detailed_analysis']['glare_details']
        print(f"\n🔍 Glare Analysis Details:")
        print(f"  Reflection Ratio: {glare_details['reflection_analysis']['reflection_ratio']:.4f} (threshold: {validator.REFLECTION_RATIO_THRESHOLD})")
        print(f"  Large Reflections: {glare_details['reflection_analysis']['num_large_reflections']} (max: {validator.MAX_LARGE_REFLECTIONS})")
        print(f"  Total Reflection Regions: {glare_details['reflection_analysis']['total_reflection_regions']}")
        print(f"  Avg Gradient in Bright: {glare_details['gradient_analysis']['avg_gradient_in_bright_areas']:.2f} (min: {validator.MIN_GRADIENT_IN_BRIGHT})")
        print(f"  Has Texture in Bright: {glare_details['has_texture_in_bright']}")
        print(f"  Pass Reason: {glare_details['pass_reason']}")
        print(f"  Image Brightness: {glare_details['reflection_analysis']['brightness']:.2f}")
        print(f"  Dynamic V Threshold: {glare_details['reflection_analysis']['dynamic_v_threshold']:.2f}")
    
    # Print failure reasons if any
    if result['failure_reasons']:
        print(f"\n❌ Failure Reasons:")
        for reason in result['failure_reasons']:
            print(f"  - {reason}")
    
    return result['passed']


def main():
    """Test the enhanced quality gate with sample photos"""
    print("🚀 Testing Enhanced Quality Gate Validator")
    print("=" * 80)
    
    # Initialize validator
    validator = EnhancedQualityGateValidator()
    print(f"✓ Validator initialized")
    print(f"  Reflection Ratio Threshold: {validator.REFLECTION_RATIO_THRESHOLD}")
    print(f"  Max Large Reflections: {validator.MAX_LARGE_REFLECTIONS}")
    print(f"  Min Reflection Area: {validator.MIN_REFLECTION_AREA}")
    print(f"  Min Gradient in Bright: {validator.MIN_GRADIENT_IN_BRIGHT}")
    
    # Test photos from storage (photos that were failing)
    test_photos = [
        "backend/storage/20260126_124340_front.jpg/original/20260126_124340_31cdee5b-75f8-4d58-9dfe-537f62196f66",
        "backend/storage/20260126_113911_vin.jpg/original/20260126_113911_4489339d-c87c-4fad-84d3-c24d14ff05a9",
    ]
    
    # Also check if there are any other photos in storage
    storage_path = Path("backend/storage")
    if storage_path.exists():
        for item in storage_path.iterdir():
            if item.is_dir() and item.name.endswith('.jpg'):
                original_path = item / "original"
                if original_path.exists():
                    for photo in original_path.iterdir():
                        if photo.is_file() and str(photo) not in test_photos:
                            test_photos.append(str(photo))
    
    # Run tests
    results = []
    for photo_path in test_photos:
        if Path(photo_path).exists():
            passed = test_photo(photo_path, validator)
            results.append((photo_path, passed))
        else:
            print(f"\n⚠️  Photo not found: {photo_path}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📈 Test Summary")
    print(f"{'='*80}")
    print(f"Total Photos Tested: {len(results)}")
    print(f"Passed: {sum(1 for _, passed in results if passed)}")
    print(f"Failed: {sum(1 for _, passed in results if not passed)}")
    
    if results:
        print(f"\n📋 Detailed Results:")
        for photo_path, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status}: {Path(photo_path).name}")
    
    # Return exit code
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print(f"\n✅ All tests passed!")
        return 0
    else:
        print(f"\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
