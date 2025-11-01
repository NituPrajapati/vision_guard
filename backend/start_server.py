#!/usr/bin/env python3
"""
Startup script for Vision Guard backend
This script checks for common issues and starts the server
"""

import os
import sys
import subprocess

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_required_files():
    """Check if required files exist"""
    required_files = [
        "app.py",
        "auth_routes.py", 
        "db.py",
        "requirements.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

def check_model_files():
    """Check if model files exist"""
    model_files = [
        "yolov8n.pt",
        "runs/detect/train3/weights/best.pt"
    ]
    
    missing_models = []
    for model in model_files:
        if not os.path.exists(model):
            missing_models.append(model)
    
    if missing_models:
        print(f"⚠️  Missing model files: {missing_models}")
        print("   The app will start but detection features may not work")
        return False
    
    print("✅ All model files exist")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'flask', 'flask-cors', 'flask-jwt-extended', 
        'ultralytics', 'pymongo', 'python-dotenv', 
        'opencv-python', 'werkzeug'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
        print("   Install with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = ".env"
    if not os.path.exists(env_file):
        print("📝 Creating .env file...")
        env_content = """# Vision Guard Environment Configuration
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production-12345
MONGO_URI=mongodb://localhost:27017/
DB_NAME=visionguard
FLASK_ENV=development
"""
        try:
            with open(env_file, 'w') as f:
                f.write(env_content)
            print("✅ .env file created")
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("✅ .env file exists")
    
    return True

def check_mongodb():
    """Check if MongoDB is accessible"""
    try:
        from pymongo import MongoClient
        from dotenv import load_dotenv
        
        load_dotenv()
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        client.close()
        print("✅ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"⚠️  MongoDB connection failed: {e}")
        print("   Make sure MongoDB is running")
        return False

def start_server():
    """Start the Flask server"""
    print("\n🚀 Starting Vision Guard server...")
    try:
        # Import and run the app
        from app import app
        print("✅ Server starting on http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔍 Vision Guard Server Startup Check")
    print("=" * 50)
    
    # Run all checks
    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_required_files),
        ("Dependencies", check_dependencies),
        ("Environment File", create_env_file),
        ("Model Files", check_model_files),
        ("MongoDB Connection", check_mongodb),
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            failed_checks.append(check_name)
    
    print("\n" + "=" * 50)
    
    if failed_checks:
        print(f"❌ {len(failed_checks)} check(s) failed: {failed_checks}")
        print("\nPlease fix the issues above before starting the server.")
        
        # Ask if user wants to continue anyway
        response = input("\nDo you want to start the server anyway? (y/N): ")
        if response.lower() != 'y':
            return
    else:
        print("✅ All checks passed!")
    
    # Start the server
    start_server()

if __name__ == "__main__":
    main()

