#!/usr/bin/env python3
"""
Pipeline API Integration Tests
Verifies that all API endpoints (M3, M4, M7, Pipeline Run & Health) are healthy
and accepting traffic gracefully.
"""
import requests
import io
import time
import sys
import numpy as np
import cv2

BASE_URL = "http://localhost:8000"

def create_dummy_image():
    """Create a dummy BGR image, returning its bytes."""
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    cv2.putText(img, "Test Image", (100, 320), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    _, encoded = cv2.imencode('.jpg', img)
    return io.BytesIO(encoded.tobytes())

def check_server():
    """Check if the backend server is reachable."""
    try:
        requests.get(f"{BASE_URL}/", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
        return False

def test_endpoint(name: str, url: str, files: dict) -> bool:
    print(f"\n[TEST] {name} -> {url}")
    start = time.time()
    try:
        response = requests.post(url, files=files)
        files["files"][1].seek(0)  # Reset pointer for next test
        
        elapsed = round((time.time() - start) * 1000)
        print(f"       Status Code: {response.status_code} ({elapsed}ms)")
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown") if isinstance(data, dict) else "unknown"
            if isinstance(data, list) and len(data) > 0:
                status = data[0].get("status", "unknown")
            print(f"       App Status: {status}")
            return True
        else:
            print(f"       Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"       Exception: {e}")
        return False

def test_health():
    print(f"\n[TEST] Pipeline Health -> /api/pipeline/health")
    try:
        response = requests.get(f"{BASE_URL}/api/pipeline/health")
        if response.status_code == 200:
            data = response.json()
            print(f"       Overall Status: {data.get('status')}")
            print(f"       Modules Available: {data.get('modules_available')}/{data.get('modules_total')}")
            return True
        else:
            print(f"       Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"       Exception: {e}")
        return False

if __name__ == "__main__":
    if not check_server():
        print("Backend server is not running on localhost:8000. Start it with uvicorn app.main:app.")
        sys.exit(1)
        
    print("Starting API Integration Tests...")
    
    file_tuple = ("test.jpg", create_dummy_image(), "image/jpeg")
    
    success = True
    success &= test_health()
    success &= test_endpoint("M3 (Segmentation)", f"{BASE_URL}/api/modules/M3/process", {"files": file_tuple})
    success &= test_endpoint("M4 (Damage Analysis)", f"{BASE_URL}/api/modules/M4/process", {"files": file_tuple})
    success &= test_endpoint("M7 (Reporting)", f"{BASE_URL}/api/modules/M7/process", {"files": file_tuple})
    success &= test_endpoint("Full Pipeline Run", f"{BASE_URL}/api/pipeline/run", {"files": file_tuple})
    
    if success:
        print("\n✅ All integration tests passed! Pipeline components are communicating successfully.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the logs above.")
        sys.exit(1)
