"""
Test the enhanced quality gate with real photos from storage
"""
import cv2
import numpy as np
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quality_gate_enhanced import EnhancedQualityGateValidator


def test_real_photo(image_path: str, validator: EnhancedQualityGateValidator):
    """Test a single real photo"""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(image_path).parent.parent.name}")
    print(f"{'='*80}")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Failed to load image")
        return None
    
    # Check if image is valid (not all same color)
    if np.std(image) < 1.0:
        print(f"⚠️  Image appears to be uniform/corrupted (std: {np.std(image):.2f})")
        return None
    
    print(f"✓ Image loaded: {image.shape}, std: {np.std(image):.2f}")
    
    # Run validation
    result = validator.validate_photo(image)
    
    # Print results
    print(f"\n📊 Validation Results:")
    print(f"  Overall: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
    print(f"  Blur Score: {result['blur_score']:.2f} (threshold: {validator.BLUR_THRESHOLD})")
    print(f"  Exposure: {result['exposure_score']:.2f} (range: {validator.EXPOSURE_MIN}-{validator.EXPOSURE_MAX})")
    print(f"  Glare Score: {result['glare_score']:.4f}")
    print(f"  Vehicle Present: {result['vehicle_present']}")
    
    # Print glare details
    if 'detailed_analysis' in result and 'glare_details' in result['detailed_analysis']:
        glare_details = result['detailed_analysis']['glare_details']
        print(f"\n🔍 Glare Analysis:")
        print(f"  Reflection Ratio: {glare_details['reflection_analysis']['reflection_ratio']:.2%} (threshold: {validator.REFLECTION_RATIO_THRESHOLD:.0%})")
        print(f"  Large Reflections: {glare_details['reflection_analysis']['num_large_reflections']} (max: {validator.MAX_LARGE_REFLECTIONS})")
        print(f"  Avg Gradient: {glare_details['gradient_analysis']['avg_gradient_in_bright_areas']:.2f} (min: {validator.MIN_GRADIENT_IN_BRIGHT})")
        print(f"  Has Texture: {glare_details['has_texture_in_bright']}")
        print(f"  Pass Reason: {glare_details['pass_reason']}")
    
    # Print failure reasons
    if result['failure_reasons']:
        print(f"\n❌ Failure Reasons:")
        for reason in result['failure_reasons']:
            print(f"  - {reason}")
    
    return result


def main():
    """Test with real photos from storage"""
    print("🚀 Testing Enhanced Quality Gate with Real Photos")
    print("="*80)
    
    # Initialize validator
    validator = EnhancedQualityGateValidator()
    print(f"✓ Validator initialized (Threshold: {validator.REFLECTION_RATIO_THRESHOLD:.0%})")
    
    # Find real photos
    storage_path = Path("backend/storage")
    test_photos = []
    
    if storage_path.exists():
        for item in storage_path.iterdir():
            if item.is_dir() and item.name.endswith('.jpg'):
                original_path = item / "original"
                if original_path.exists():
                    for photo in original_path.iterdir():
                        if photo.is_file():
                            test_photos.append(str(photo))
                            if len(test_photos) >= 5:  # Test first 5 photos
                                break
            if len(test_photos) >= 5:
                break
    
    if not test_photos:
        print("❌ No photos found in storage")
        return 1
    
    print(f"Found {len(test_photos)} photos to test\n")
    
    # Test photos
    results = []
    valid_tests = 0
    
    for photo_path in test_photos:
        result = test_real_photo(photo_path, validator)
        if result is not None:
            results.append((photo_path, result))
            valid_tests += 1
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📈 Test Summary")
    print(f"{'='*80}")
    print(f"Valid Photos Tested: {valid_tests}")
    
    if results:
        passed = sum(1 for _, r in results if r['passed'])
        failed = sum(1 for _, r in results if not r['passed'])
        
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        # Check glare-specific failures
        glare_failures = []
        for photo_path, result in results:
            if not result['passed']:
                for reason in result['failure_reasons']:
                    if 'glare' in reason.lower() or 'reflection' in reason.lower():
                        glare_failures.append((Path(photo_path).parent.parent.name, reason))
        
        if glare_failures:
            print(f"\n⚠️  Glare-related failures:")
            for photo, reason in glare_failures:
                print(f"  - {photo}: {reason}")
        else:
            print(f"\n✅ No glare-related failures!")
        
        # Show what passed
        print(f"\n📋 Detailed Results:")
        for photo_path, result in results:
            status = "✅ PASSED" if result['passed'] else "❌ FAILED"
            photo_name = Path(photo_path).parent.parent.name
            print(f"  {status}: {photo_name}")
            if not result['passed'] and result['failure_reasons']:
                for reason in result['failure_reasons']:
                    print(f"      → {reason}")
    
    return 0


if __name__ == "__main__":
    exit(main())
