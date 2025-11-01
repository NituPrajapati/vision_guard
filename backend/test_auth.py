#!/usr/bin/env python3
"""
Test script to verify authentication is working
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_register():
    """Test user registration"""
    print("Testing user registration...")
    
    test_user = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=test_user)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_login():
    """Test user login"""
    print("\nTesting user login...")
    
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_protected_endpoint(token):
    """Test a protected endpoint"""
    print("\nTesting protected endpoint...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/test-auth", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("🔐 Testing Vision Guard Authentication")
    print("=" * 50)
    
    # Test registration
    if not test_register():
        print("❌ Registration test failed")
        return
    
    # Test login
    token = test_login()
    if not token:
        print("❌ Login test failed")
        return
    
    # Test protected endpoint
    if not test_protected_endpoint(token):
        print("❌ Protected endpoint test failed")
        return
    
    print("\n✅ All authentication tests passed!")

if __name__ == "__main__":
    main()

