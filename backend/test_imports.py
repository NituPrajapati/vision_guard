#!/usr/bin/env python3
"""
Test script to identify import and configuration issues
"""

import sys
import os

def test_imports():
    """Test all imports one by one"""
    print("Testing imports...")
    
    try:
        print("1. Testing Flask...")
        from flask import Flask
        print("   ✅ Flask imported successfully")
    except Exception as e:
        print(f"   ❌ Flask import failed: {e}")
        return False
    
    try:
        print("2. Testing Flask-CORS...")
        from flask_cors import CORS
        print("   ✅ Flask-CORS imported successfully")
    except Exception as e:
        print(f"   ❌ Flask-CORS import failed: {e}")
        return False
    
    try:
        print("3. Testing Flask-JWT-Extended...")
        from flask_jwt_extended import JWTManager
        print("   ✅ Flask-JWT-Extended imported successfully")
    except Exception as e:
        print(f"   ❌ Flask-JWT-Extended import failed: {e}")
        return False
    
    try:
        print("4. Testing Ultralytics...")
        from ultralytics import YOLO
        print("   ✅ Ultralytics imported successfully")
    except Exception as e:
        print(f"   ❌ Ultralytics import failed: {e}")
        return False
    
    try:
        print("5. Testing OpenCV...")
        import cv2
        print("   ✅ OpenCV imported successfully")
    except Exception as e:
        print(f"   ❌ OpenCV import failed: {e}")
        return False
    
    try:
        print("6. Testing PyMongo...")
        from pymongo import MongoClient
        print("   ✅ PyMongo imported successfully")
    except Exception as e:
        print(f"   ❌ PyMongo import failed: {e}")
        return False
    
    try:
        print("7. Testing python-dotenv...")
        from dotenv import load_dotenv
        print("   ✅ python-dotenv imported successfully")
    except Exception as e:
        print(f"   ❌ python-dotenv import failed: {e}")
        return False
    
    try:
        print("8. Testing BSON...")
        from bson import ObjectId
        print("   ✅ BSON imported successfully")
    except Exception as e:
        print(f"   ❌ BSON import failed: {e}")
        return False
    
    return True

def test_model_loading():
    """Test YOLO model loading"""
    print("\nTesting model loading...")
    
    try:
        from ultralytics import YOLO
        
        print("1. Testing COCO model...")
        if os.path.exists("yolov8n.pt"):
            model = YOLO("yolov8n.pt")
            print("   ✅ COCO model loaded successfully")
        else:
            print("   ❌ yolov8n.pt not found")
            return False
        
        print("2. Testing ID Card model...")
        model_path = "runs/detect/train3/weights/best.pt"
        if os.path.exists(model_path):
            model = YOLO(model_path)
            print("   ✅ ID Card model loaded successfully")
        else:
            print(f"   ❌ {model_path} not found")
            return False
            
    except Exception as e:
        print(f"   ❌ Model loading failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("DB_NAME", "visionguard")
        
        print(f"1. Connecting to MongoDB at {mongo_uri}")
        client = MongoClient(mongo_uri)
        
        print("2. Testing connection...")
        client.admin.command('ping')
        print("   ✅ MongoDB connection successful")
        
        print("3. Testing database access...")
        db = client[db_name]
        collections = db.list_collection_names()
        print(f"   ✅ Database '{db_name}' accessible, collections: {collections}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

def test_app_import():
    """Test importing the main app"""
    print("\nTesting app import...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        print("1. Testing db import...")
        from db import users_collection, detections_collection
        print("   ✅ db module imported successfully")
        
        print("2. Testing auth_routes import...")
        from auth_routes import auth_bp
        print("   ✅ auth_routes module imported successfully")
        
        print("3. Testing app import...")
        import app
        print("   ✅ app module imported successfully")
        
        return True
        
    except Exception as e:
        print(f"   ❌ App import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🔍 Vision Guard Diagnostic Test")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Please install missing packages.")
        return
    
    # Test model loading
    if not test_model_loading():
        print("\n❌ Model loading tests failed. Check model files.")
        return
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database tests failed. Check MongoDB connection.")
        return
    
    # Test app import
    if not test_app_import():
        print("\n❌ App import tests failed. Check app configuration.")
        return
    
    print("\n✅ All tests passed! The application should work correctly.")
    print("\n📋 Next steps:")
    print("   1. Start MongoDB if not running")
    print("   2. Run: python app.py")
    print("   3. Open http://localhost:5000 in browser")

if __name__ == "__main__":
    main()

