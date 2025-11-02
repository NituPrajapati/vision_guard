import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Required credentials - no defaults for security
    JWT_SECRET_KEY = os.getenv("JWT_SECRET")
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET environment variable is required")
    
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is required")
    
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    if not GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_SECRET environment variable is required")
    
    # Database settings (with defaults for local development)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "visionguard")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'mp4', 'avi'}
    
    # Model paths
    IDCARD_MODEL_PATH = "runs/detect/train3/weights/best.pt"
    COCO_MODEL_PATH = "yolov8n.pt"
    
    # Temporary processing folder (files are cleaned up after Cloudinary upload)
    # Only used for: 1) Temporary file processing, 2) Live detection stream
    RESULT_FOLDER = "results"

    # Cloudinary settings - required from environment
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    if not CLOUDINARY_CLOUD_NAME:
        raise ValueError("CLOUDINARY_CLOUD_NAME environment variable is required")
    
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    if not CLOUDINARY_API_KEY:
        raise ValueError("CLOUDINARY_API_KEY environment variable is required")
    
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    if not CLOUDINARY_API_SECRET:
        raise ValueError("CLOUDINARY_API_SECRET environment variable is required")

    # Google OAuth URIs (standard endpoints, safe to have defaults)
    GOOGLE_AUTH_URI = os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
    GOOGLE_TOKEN_URI = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
    GOOGLE_USERINFO_URI = os.getenv("GOOGLE_USERINFO_URI", "https://www.googleapis.com/oauth2/v2/userinfo")
    
    # Frontend URLs (with defaults for local development)
    FRONTEND_BASE_3000 = os.getenv("FRONTEND_BASE_3000", "http://localhost:3000")
    FRONTEND_BASE_5173 = os.getenv("FRONTEND_BASE_5173", "http://localhost:5173")
    # Primary redirect base (default to 5173 for local dev, should be set in production)
    FRONTEND_BASE = os.getenv("FRONTEND_BASE", FRONTEND_BASE_5173)
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI") or (FRONTEND_BASE + "/auth/callback")

