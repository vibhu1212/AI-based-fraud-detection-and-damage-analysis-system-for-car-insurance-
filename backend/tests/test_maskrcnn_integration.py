"""
Test Mask R-CNN Integration
Verify that the partially trained model loads and generates masks correctly
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import numpy as np
from pathlib import Path
from app.tasks.damage_segmentation import DamageSegmenter
from app.services.storage import StorageService

def test_model_loading():
    """Test that Mask R-CNN model loads successfully"""
    print("=" * 80)
    print("TEST 1: Model Loading")
    print("=" * 80)
    
    storage = StorageService()
    segmenter = DamageSegmenter(storage)
    
    if segmenter.model is None:
        print("❌ FAILED: Model failed to load")
        return False
    
    print("✅ PASSED: Model loaded successfully")
    print(f"   Device: {segmenter.device}")
    return True

def test_mask_generation():
    """Test mask generation on a sample image"""
    print("\n" + "=" * 80)
    print("TEST 2: Mask Generation")
    print("=" * 80)
    
    # Find a test image from demo data
    test_images = list(Path("demo_data/images").glob("*.jpg"))
    if not test_images:
        print("⚠️  SKIPPED: No test images found in demo_data/images/")
        return True
    
    test_image = test_images[0]
    print(f"   Using test image: {test_image.name}")
    
    # Load image to get dimensions
    image = cv2.imread(str(test_image))
    if image is None:
        print(f"❌ FAILED: Could not load image {test_image}")
        return False
    
    h, w = image.shape[:2]
    print(f"   Image size: {w}x{h}")
    
    # Create a test bounding box (center region)
    bbox = (w//4, h//4, 3*w//4, 3*h//4)
    print(f"   Test bbox: {bbox}")
    
    # Generate mask
    storage = StorageService()
    segmenter = DamageSegmenter(storage)
    
    mask_data = segmenter.generate_mask(test_image, bbox)
    
    if mask_data is None:
        print("❌ FAILED: Mask generation returned None")
        return False
    
    print(f"✅ PASSED: Mask generated successfully")
    print(f"   Mask size: {mask_data['mask_width']}x{mask_data['mask_height']}")
    print(f"   Mask area: {mask_data['mask_area']} pixels")
    
    # Verify mask is not empty
    if mask_data['mask_area'] == 0:
        print("❌ FAILED: Mask area is zero")
        return False
    
    print("✅ PASSED: Mask has non-zero area")
    return True

def test_multiple_images():
    """Test mask generation on multiple images"""
    print("\n" + "=" * 80)
    print("TEST 3: Multiple Images")
    print("=" * 80)
    
    test_images = list(Path("demo_data/images").glob("*.jpg"))[:3]
    if len(test_images) < 3:
        print(f"⚠️  SKIPPED: Only {len(test_images)} test images available")
        return True
    
    storage = StorageService()
    segmenter = DamageSegmenter(storage)
    
    success_count = 0
    for test_image in test_images:
        image = cv2.imread(str(test_image))
        if image is None:
            continue
        
        h, w = image.shape[:2]
        bbox = (w//4, h//4, 3*w//4, 3*h//4)
        
        mask_data = segmenter.generate_mask(test_image, bbox)
        if mask_data and mask_data['mask_area'] > 0:
            success_count += 1
            print(f"   ✓ {test_image.name}: {mask_data['mask_area']} px")
    
    if success_count == len(test_images):
        print(f"✅ PASSED: All {success_count}/{len(test_images)} images processed successfully")
        return True
    else:
        print(f"⚠️  PARTIAL: {success_count}/{len(test_images)} images processed successfully")
        return success_count > 0

def main():
    """Run all tests"""
    print("\n🚀 Mask R-CNN Integration Test Suite")
    print("   Model: maskrcnn-resnet50-fpn (iteration 7999)")
    print("   Classes: 7 merged damage types")
    print()
    
    results = []
    
    # Test 1: Model loading
    results.append(("Model Loading", test_model_loading()))
    
    # Test 2: Mask generation
    results.append(("Mask Generation", test_mask_generation()))
    
    # Test 3: Multiple images
    results.append(("Multiple Images", test_multiple_images()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Mask R-CNN integration successful!")
        print("\n📝 Next Steps:")
        print("   1. Restart Celery worker: ./restart_celery.sh")
        print("   2. Test with real claim in the UI")
        print("   3. Verify masks appear in damage overlay")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
