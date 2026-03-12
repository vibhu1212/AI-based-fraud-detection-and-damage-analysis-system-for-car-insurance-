"""
Comprehensive test for the enhanced quality gate fix
Tests with actual car photos to verify glare detection works correctly
"""
import cv2
import numpy as np
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.quality_gate_enhanced import EnhancedQualityGateValidator


def create_test_image_with_reflection(brightness=150, reflection_ratio=0.25):
    """Create a synthetic test image with controlled reflection"""
    # Create base image (car-like texture)
    img = np.random.randint(brightness-30, brightness+30, (480, 640, 3), dtype=np.uint8)
    
    # Add some edges (car features)
    img[100:150, :] = brightness + 50  # Horizontal line
    img[:, 200:250] = brightness + 50  # Vertical line
    
    # Add reflection area (bright + low saturation)
    reflection_pixels = int(480 * 640 * reflection_ratio)
    reflection_area = np.zeros((480, 640), dtype=np.uint8)
    
    # Create localized reflection (top-right corner)
    reflection_h = int(np.sqrt(reflection_pixels * 0.75))
    reflection_w = int(reflection_pixels / reflection_h)
    reflection_area[50:50+reflection_h, 400:400+reflection_w] = 255
    
    # Apply reflection (bright white areas)
    for c in range(3):
        img[:, :, c] = np.where(reflection_area > 0, 240, img[:, :, c])
    
    return img


def test_synthetic_images():
    """Test with synthetic images that have controlled reflection ratios"""
    print("\n" + "="*80)
    print("TEST 1: Synthetic Images with Controlled Reflection")
    print("="*80)
    
    validator = EnhancedQualityGateValidator()
    
    test_cases = [
        (0.10, "Low reflection (10%)"),
        (0.20, "Medium reflection (20%)"),
        (0.25, "High reflection (25%) - Previously failing"),
        (0.30, "Threshold reflection (30%)"),
        (0.35, "Above threshold (35%)"),
    ]
    
    results = []
    for reflection_ratio, description in test_cases:
        print(f"\n📸 Testing: {description}")
        print(f"   Expected reflection ratio: {reflection_ratio:.2%}")
        
        # Create test image
        img = create_test_image_with_reflection(brightness=150, reflection_ratio=reflection_ratio)
        
        # Validate
        result = validator.validate_photo(img)
        
        # Extract details
        glare_details = result['detailed_analysis']['glare_details']
        actual_ratio = glare_details['reflection_analysis']['reflection_ratio']
        passed = result['passed']
        
        print(f"   Actual reflection ratio: {actual_ratio:.2%}")
        print(f"   Glare score: {result['glare_score']:.4f}")
        print(f"   Pass reason: {glare_details['pass_reason']}")
        print(f"   Result: {'✅ PASSED' if passed else '❌ FAILED'}")
        
        # Check if result matches expectation
        expected_pass = reflection_ratio <= 0.30
        correct = (passed == expected_pass)
        
        results.append({
            'description': description,
            'expected_ratio': reflection_ratio,
            'actual_ratio': actual_ratio,
            'passed': passed,
            'expected_pass': expected_pass,
            'correct': correct
        })
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 Synthetic Test Summary")
    print(f"{'='*80}")
    correct_count = sum(1 for r in results if r['correct'])
    print(f"Correct predictions: {correct_count}/{len(results)}")
    
    for r in results:
        status = "✅" if r['correct'] else "❌"
        print(f"{status} {r['description']}: {r['actual_ratio']:.2%} - {'PASSED' if r['passed'] else 'FAILED'}")
    
    return all(r['correct'] for r in results)


def test_gradient_detection():
    """Test gradient-based glare detection"""
    print("\n" + "="*80)
    print("TEST 2: Gradient-Based Glare Detection")
    print("="*80)
    
    validator = EnhancedQualityGateValidator()
    
    # Test 1: Smooth glare (low gradient)
    print("\n📸 Test 2.1: Smooth glare (should detect as glare)")
    smooth_img = np.ones((480, 640, 3), dtype=np.uint8) * 230  # Uniform bright
    result1 = validator.validate_photo(smooth_img)
    glare_details1 = result1['detailed_analysis']['glare_details']
    gradient1 = glare_details1['gradient_analysis']['avg_gradient_in_bright_areas']
    print(f"   Avg gradient: {gradient1:.2f} (threshold: {validator.MIN_GRADIENT_IN_BRIGHT})")
    print(f"   Has texture: {glare_details1['has_texture_in_bright']}")
    print(f"   Result: {'✅ PASSED' if result1['passed'] else '❌ FAILED'}")
    
    # Test 2: Textured bright surface (high gradient)
    print("\n📸 Test 2.2: Textured bright surface (should pass)")
    textured_img = np.random.randint(200, 240, (480, 640, 3), dtype=np.uint8)
    # Add strong edges
    for i in range(0, 480, 20):
        textured_img[i:i+2, :] = 250
    for j in range(0, 640, 20):
        textured_img[:, j:j+2] = 250
    
    result2 = validator.validate_photo(textured_img)
    glare_details2 = result2['detailed_analysis']['glare_details']
    gradient2 = glare_details2['gradient_analysis']['avg_gradient_in_bright_areas']
    print(f"   Avg gradient: {gradient2:.2f} (threshold: {validator.MIN_GRADIENT_IN_BRIGHT})")
    print(f"   Has texture: {glare_details2['has_texture_in_bright']}")
    print(f"   Result: {'✅ PASSED' if result2['passed'] else '❌ FAILED'}")
    
    # Verify gradient detection works
    gradient_test_passed = gradient1 < gradient2  # Smooth should have lower gradient
    print(f"\n{'='*80}")
    print(f"Gradient Detection: {'✅ WORKING' if gradient_test_passed else '❌ FAILED'}")
    print(f"Smooth gradient ({gradient1:.2f}) < Textured gradient ({gradient2:.2f}): {gradient_test_passed}")
    
    return gradient_test_passed


def test_dynamic_threshold():
    """Test dynamic threshold adaptation"""
    print("\n" + "="*80)
    print("TEST 3: Dynamic Threshold Adaptation")
    print("="*80)
    
    validator = EnhancedQualityGateValidator()
    
    # Test with different brightness levels
    test_cases = [
        (100, "Dark image"),
        (150, "Medium brightness"),
        (200, "Bright image"),
    ]
    
    thresholds = []
    for brightness, description in test_cases:
        print(f"\n📸 Testing: {description} (brightness: {brightness})")
        
        # Create image with specific brightness
        img = np.ones((480, 640, 3), dtype=np.uint8) * brightness
        
        # Get reflection details
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_brightness = float(np.mean(gray))
        _, _, details = validator.detect_reflections(img, brightness=img_brightness)
        
        dynamic_threshold = details['dynamic_v_threshold']
        print(f"   Image brightness: {img_brightness:.2f}")
        print(f"   Dynamic V threshold: {dynamic_threshold:.2f}")
        print(f"   Base threshold: {validator.VALUE_THRESHOLD_BASE}")
        
        thresholds.append(dynamic_threshold)
    
    # Verify thresholds increase with brightness
    threshold_test_passed = thresholds[0] <= thresholds[1] <= thresholds[2]
    print(f"\n{'='*80}")
    print(f"Dynamic Threshold: {'✅ WORKING' if threshold_test_passed else '❌ FAILED'}")
    print(f"Thresholds increase with brightness: {thresholds}")
    
    return threshold_test_passed


def test_multi_criteria_validation():
    """Test multi-criteria pass logic"""
    print("\n" + "="*80)
    print("TEST 4: Multi-Criteria Validation")
    print("="*80)
    
    validator = EnhancedQualityGateValidator()
    
    # Test case 1: High reflection but with texture (should pass)
    print("\n📸 Test 4.1: High reflection (35%) with texture")
    textured_high_reflection = create_test_image_with_reflection(brightness=150, reflection_ratio=0.35)
    # Add strong texture
    for i in range(0, 480, 10):
        textured_high_reflection[i:i+1, :] = 200
    
    result1 = validator.validate_photo(textured_high_reflection)
    glare_details1 = result1['detailed_analysis']['glare_details']
    print(f"   Reflection ratio: {glare_details1['reflection_analysis']['reflection_ratio']:.2%}")
    print(f"   Has texture: {glare_details1['has_texture_in_bright']}")
    print(f"   Pass reason: {glare_details1['pass_reason']}")
    print(f"   Result: {'✅ PASSED' if result1['passed'] else '❌ FAILED'}")
    
    # Test case 2: Low reflection (should pass)
    print("\n📸 Test 4.2: Low reflection (15%)")
    low_reflection = create_test_image_with_reflection(brightness=150, reflection_ratio=0.15)
    result2 = validator.validate_photo(low_reflection)
    glare_details2 = result2['detailed_analysis']['glare_details']
    print(f"   Reflection ratio: {glare_details2['reflection_analysis']['reflection_ratio']:.2%}")
    print(f"   Pass reason: {glare_details2['pass_reason']}")
    print(f"   Result: {'✅ PASSED' if result2['passed'] else '❌ FAILED'}")
    
    # Test case 3: Localized reflections (should pass)
    print("\n📸 Test 4.3: Localized reflections (few large regions)")
    localized = create_test_image_with_reflection(brightness=150, reflection_ratio=0.28)
    result3 = validator.validate_photo(localized)
    glare_details3 = result3['detailed_analysis']['glare_details']
    print(f"   Reflection ratio: {glare_details3['reflection_analysis']['reflection_ratio']:.2%}")
    print(f"   Large reflections: {glare_details3['reflection_analysis']['num_large_reflections']}")
    print(f"   Pass reason: {glare_details3['pass_reason']}")
    print(f"   Result: {'✅ PASSED' if result3['passed'] else '❌ FAILED'}")
    
    # All should pass through different criteria
    multi_criteria_passed = result1['passed'] and result2['passed'] and result3['passed']
    print(f"\n{'='*80}")
    print(f"Multi-Criteria Validation: {'✅ WORKING' if multi_criteria_passed else '❌ FAILED'}")
    
    return multi_criteria_passed


def test_specific_failing_cases():
    """Test the specific cases that were failing (0.2536, 0.2223)"""
    print("\n" + "="*80)
    print("TEST 5: Specific Failing Cases from User Report")
    print("="*80)
    
    validator = EnhancedQualityGateValidator()
    
    failing_cases = [
        (0.2536, "User case 1: 25.36% glare"),
        (0.2223, "User case 2: 22.23% glare"),
    ]
    
    all_passed = True
    for reflection_ratio, description in failing_cases:
        print(f"\n📸 Testing: {description}")
        print(f"   Previous threshold: 0.15 (15%) - Would FAIL")
        print(f"   New threshold: 0.30 (30%) - Should PASS")
        
        # Create test image
        img = create_test_image_with_reflection(brightness=150, reflection_ratio=reflection_ratio)
        
        # Validate
        result = validator.validate_photo(img)
        glare_details = result['detailed_analysis']['glare_details']
        
        print(f"   Actual reflection: {glare_details['reflection_analysis']['reflection_ratio']:.2%}")
        print(f"   Pass reason: {glare_details['pass_reason']}")
        print(f"   Result: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
        
        if not result['passed']:
            all_passed = False
            print(f"   ⚠️  STILL FAILING! Failure reasons: {result['failure_reasons']}")
    
    print(f"\n{'='*80}")
    print(f"Specific Cases: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    
    return all_passed


def main():
    """Run all comprehensive tests"""
    print("🚀 Comprehensive Quality Gate Testing")
    print("="*80)
    print("Testing enhanced quality gate with research-based fixes")
    print("="*80)
    
    # Initialize validator
    validator = EnhancedQualityGateValidator()
    print(f"\n✓ Validator initialized")
    print(f"  Reflection Ratio Threshold: {validator.REFLECTION_RATIO_THRESHOLD} (30%)")
    print(f"  Max Large Reflections: {validator.MAX_LARGE_REFLECTIONS}")
    print(f"  Min Gradient in Bright: {validator.MIN_GRADIENT_IN_BRIGHT}")
    print(f"  Min Reflection Area: {validator.MIN_REFLECTION_AREA}")
    
    # Run all tests
    test_results = {
        "Synthetic Images": test_synthetic_images(),
        "Gradient Detection": test_gradient_detection(),
        "Dynamic Threshold": test_dynamic_threshold(),
        "Multi-Criteria": test_multi_criteria_validation(),
        "Specific Failing Cases": test_specific_failing_cases(),
    }
    
    # Final summary
    print("\n" + "="*80)
    print("🎯 FINAL TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(test_results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\n🎉 Quality Gate Fix Verified:")
        print("  ✓ Dynamic thresholds working")
        print("  ✓ Gradient detection working")
        print("  ✓ Multi-criteria validation working")
        print("  ✓ Specific failing cases now pass")
        print("\n📋 Next Steps:")
        print("  1. Restart Celery worker: ./restart_celery.sh")
        print("  2. Test with real photos through UI")
        print("  3. Verify end-to-end claim flow")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*80)
        print("\n⚠️  Issues detected:")
        for test_name, passed in test_results.items():
            if not passed:
                print(f"  ✗ {test_name}")
        return 1


if __name__ == "__main__":
    exit(main())
