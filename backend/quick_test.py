#!/usr/bin/env python3
"""
Quick test to verify the JSON serialization fix
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_utils():
    """Test the utils module"""
    print("Testing utils module...")
    
    try:
        from utils import make_json_serializable, safe_jsonify
        from bson import ObjectId
        import datetime
        
        # Test ObjectId serialization
        test_obj_id = ObjectId()
        serialized = make_json_serializable(test_obj_id)
        print(f"✅ ObjectId serialization: {type(serialized)} = {serialized}")
        
        # Test datetime serialization
        test_datetime = datetime.datetime.utcnow()
        serialized = make_json_serializable(test_datetime)
        print(f"✅ Datetime serialization: {type(serialized)} = {serialized}")
        
        # Test complex object
        test_data = {
            "user_id": test_obj_id,
            "created_at": test_datetime,
            "username": "testuser",
            "nested": {
                "id": test_obj_id,
                "timestamp": test_datetime
            }
        }
        
        serialized = make_json_serializable(test_data)
        print(f"✅ Complex object serialization: {serialized}")
        
        return True
        
    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False

def test_auth_import():
    """Test importing auth_routes"""
    print("\nTesting auth_routes import...")
    
    try:
        from auth_routes import auth_bp
        print("✅ auth_routes imported successfully")
        return True
    except Exception as e:
        print(f"❌ auth_routes import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_import():
    """Test importing main app"""
    print("\nTesting app import...")
    
    try:
        import app
        print("✅ app imported successfully")
        return True
    except Exception as e:
        print(f"❌ app import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Quick Test for JSON Serialization Fix")
    print("=" * 50)
    
    tests = [
        ("Utils Module", test_utils),
        ("Auth Routes Import", test_auth_import),
        ("App Import", test_app_import),
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("✅ All tests passed! The JSON serialization fix should work.")
    else:
        print("❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()




















