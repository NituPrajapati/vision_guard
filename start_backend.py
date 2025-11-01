#!/usr/bin/env python3
"""
Simple startup script for Vision Guard backend
"""

import os
import sys
import subprocess

def main():
    print("🚀 Starting Vision Guard Backend")
    print("=" * 40)
    
    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    
    if not os.path.exists(backend_dir):
        print("❌ Backend directory not found")
        return
    
    # Check if we're in the right directory
    if not os.path.exists(os.path.join(backend_dir, "app.py")):
        print("❌ app.py not found in backend directory")
        return
    
    print(f"📁 Backend directory: {backend_dir}")
    
    # Create .env file if it doesn't exist
    env_file = os.path.join(backend_dir, ".env")
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
    
    # Start the server
    print("\n🌐 Starting Flask server...")
    print("📡 Server will be available at: http://localhost:5000")
    print("🔐 Test authentication at: http://localhost:5000/test-auth")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 40)
    
    try:
        # Change to backend directory and start the server
        os.chdir(backend_dir)
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()

