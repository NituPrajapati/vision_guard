#!/usr/bin/env python3
"""
Setup script to create environment configuration
Run this script to set up your environment variables
"""

import os

def create_env_file():
    """Create .env file with default configuration"""
    env_content = """# Vision Guard Environment Configuration
# Change these values for production

# JWT Secret Key - CHANGE THIS IN PRODUCTION!
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production-12345

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/
DB_NAME=visionguard

# Flask Configuration
FLASK_ENV=development
"""
    
    env_file_path = os.path.join("backend", ".env")
    
    if os.path.exists(env_file_path):
        print(f"⚠️  .env file already exists at {env_file_path}")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            print("Keeping existing .env file")
            return
    
    try:
        with open(env_file_path, 'w') as f:
            f.write(env_content)
        print(f"✅ Created .env file at {env_file_path}")
        print("📝 Please review and update the JWT_SECRET for production use!")
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

def check_requirements():
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
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Install missing packages with:")
        print("   pip install -r backend/requirements.txt")
        return False
    else:
        print("✅ All required packages are installed")
        return True

def main():
    print("🚀 Vision Guard Setup")
    print("=" * 50)
    
    # Check requirements
    print("\n1. Checking requirements...")
    if not check_requirements():
        return
    
    # Create .env file
    print("\n2. Setting up environment configuration...")
    create_env_file()
    
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print("   1. Make sure MongoDB is running")
    print("   2. Start the backend: python backend/app.py")
    print("   3. Start the frontend: npm run dev (in react-app folder)")
    print("   4. Open http://localhost:5173 in your browser")

if __name__ == "__main__":
    main()
