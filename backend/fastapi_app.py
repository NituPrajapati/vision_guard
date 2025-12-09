from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from config import Config
from ultralytics import YOLO
import os
import cv2
import threading
import time
import datetime
import shutil
import jwt
from pydantic import BaseModel
from typing import Optional
from db import users_collection, detections_collection
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.parse
import requests
import logging
from authlib.integrations.starlette_client import OAuth
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from typing import Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Email configuration is now in Config class

app = FastAPI()

app.mount("/results", StaticFiles(directory=Config.RESULT_FOLDER), name="results")

@app.on_event("startup")
def on_startup():
    global idcard_model, coco_model
    os.makedirs(Config.RESULT_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(Config.RESULT_FOLDER, "predictions"), exist_ok=True)
    # Lazy load models at startup to avoid import-time issues with reload on Windows
    idcard_model = YOLO(Config.IDCARD_MODEL_PATH)
    coco_model = YOLO(Config.COCO_MODEL_PATH)
    
# Configure Cloudinary
cloudinary.config(
    cloud_name=Config.CLOUDINARY_CLOUD_NAME,
    api_key=Config.CLOUDINARY_API_KEY,
    api_secret=Config.CLOUDINARY_API_SECRET
)

# CORS configuration - supports multiple origins from environment variable
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:5173,http://localhost:3000"
).split(",")
allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://visionguard-delta.vercel.app",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Required for Authlib (stores OAuth state in server-side session)
app.add_middleware(SessionMiddleware, secret_key=Config.JWT_SECRET_KEY)
# Mount results static dir ONLY for live detection stream
# All other processed files are uploaded to Cloudinary and local files are cleaned up
app.mount("/results", StaticFiles(directory=Config.RESULT_FOLDER), name="results")

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return JSONResponse({"message": "Vision Guard backend is running 🚀"})

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})

idcard_model = None
coco_model = None


# -------------------- Cloudinary helper functions --------------------
def upload_to_cloudinary(file_path: str, public_id: str = None, resource_type: str = "image") -> dict:
    """Upload a file to Cloudinary and return the URL
    
    Args:
        file_path: Local path to the file
        public_id: Optional custom public ID for the file
        resource_type: 'image' or 'video'
    
    Returns:
        dict with 'url' and 'public_id' keys
    """
    try:
        # Config validation is done in config.py startup
        
        upload_result = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type=resource_type,
            folder="detections"  # Organize uploads in a folder
        )
        return {
            "url": upload_result.get("secure_url"),
            "public_id": upload_result.get("public_id"),
            "format": upload_result.get("format")
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Cloudinary upload failed: {error_msg}")
        
        # Provide helpful error messages
        if "Invalid cloud_name" in error_msg or "cloud_name" in error_msg.lower():
            raise HTTPException(
                status_code=500, 
                detail=f"Invalid Cloudinary cloud_name '{Config.CLOUDINARY_CLOUD_NAME}'. Please check your CLOUDINARY_CLOUD_NAME in .env file. It should match your Cloudinary account cloud name (usually lowercase)."
            )
        elif "401" in error_msg or "Unauthorized" in error_msg:
            raise HTTPException(
                status_code=500,
                detail="Cloudinary authentication failed. Please check your CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET in .env file."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to upload to cloud storage: {error_msg}")


def delete_from_cloudinary(public_id: str, resource_type: str = "image"):
    """Delete a file from Cloudinary"""
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result.get("result") == "ok"
    except Exception as e:
        logger.warning(f"Failed to delete from Cloudinary: {str(e)}")
        return False


# -------------------- JWT from HttpOnly cookie helpers --------------------
def get_user_from_cookie(request: Request) -> Optional[str]:
    """Extract username from username cookie"""
    username = request.cookies.get("username")
    if not username:
        logger.debug("[GET_USER] No username cookie found")
        return None
    logger.debug(f"[GET_USER] Username cookie found: {username}")
    return username

# -------------------- OAuth (Authlib) --------------------
oauth = OAuth()
oauth.register(
    name="google",
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile", "prompt": "select_account"},
)

def get_user_info_from_cookie(request: Request) -> Optional[dict]:
    """Get user info from username cookie (email) and lookup in DB"""
    email = request.cookies.get("username")
    if not email:
        return None
    try:
        user = users_collection.find_one({"email": email})
        if user:
            return {"user_id": str(user.get("_id")), "username": user.get("username"), "email": email}
        return None
    except Exception:
        return None

def send_alert_email(email: str, detection_type: str = "static") -> Dict:
    """
    Send alert email with retry mechanism (2 retries)
    
    Args:
        email: Recipient email address
        detection_type: Type of detection ("static" or "live")
    
    Returns:
        Dict with success status and message/error
    """
    if not email:
        logger.warning("[EMAIL] No email address provided")
        return {"success": False, "error": "No email address provided"}
    
    # Check if email credentials are configured
    if not Config.EMAIL_USER or not Config.EMAIL_PASSWORD:
        logger.info(f"[EMAIL] Email credentials not configured - EMAIL_USER: {bool(Config.EMAIL_USER)}, EMAIL_PASSWORD: {bool(Config.EMAIL_PASSWORD)}")
        logger.info("[EMAIL] Please add EMAIL_USER and EMAIL_PASSWORD to your .env file in the backend directory")
        return {"success": False, "error": "Email service not configured. Check .env file in backend directory."}
    
    logger.info(f"[EMAIL] Using SMTP server: {Config.SMTP_SERVER}:{Config.SMTP_PORT}")
    logger.info(f"[EMAIL] From email: {Config.EMAIL_USER}")
    
    logger.info(f"[EMAIL] Preparing to send email to {email}...")
    
    # Prepare email content
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    detection_type_text = "live detection" if detection_type == "live" else "static detection"
    
    # Simple HTML template
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
        <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #ff6b6b; margin-top: 0;">🚨 VisionGuard Alert</h2>
            <p>No objects were detected in your <strong>{detection_type_text}</strong>.</p>
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 4px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Detection Type:</strong> {detection_type_text.title()}</p>
                <p style="margin: 5px 0;"><strong>Timestamp:</strong> {now}</p>
            </div>
            <p>This means the image was processed but no objects (like ID cards, persons, or other items) were found.</p>
            <p>Please try again with another image or adjust your camera/view.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px; margin: 0;">VisionGuard Detection System</p>
        </div>
    </div>
    """
    
    # Plain text version
    text_content = f"""
VisionGuard Alert

No objects were detected in your {detection_type_text}.

Detection Type: {detection_type_text.title()}
Timestamp: {now}

This means the image was processed but no objects (like ID cards, persons, or other items) were found.
Please try again with another image or adjust your camera/view.

---
VisionGuard Detection System
"""
    
    # Retry logic (2 retries = 3 total attempts)
    max_retries = 2
    retry_delay = 2  # seconds
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Create new SMTP connection for every email
            logger.info(f"[EMAIL] Creating new SMTP connection (attempt {attempt + 1}/{max_retries + 1})")
            server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10)
            server.starttls()
            server.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "VisionGuard Alert: No Objects Detected"
            msg['From'] = Config.EMAIL_USER
            msg['To'] = email
            
            # Attach parts
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email sent successfully to {email}")
            return {"success": True, "message": "Email sent successfully"}
            
        except smtplib.SMTPAuthenticationError as e:
            last_error = f"SMTP Authentication failed: {str(e)}"
            logger.error(f"[EMAIL] {last_error}")
            # Don't retry on auth errors - credentials are wrong
            return {"success": False, "error": f"Email authentication failed: {str(e)}. Please check your EMAIL_USER and EMAIL_PASSWORD in .env file."}
            
        except (smtplib.SMTPServerDisconnected, OSError, ConnectionError) as e:
            last_error = f"SMTP connection error: {str(e)}"
            logger.warning(f"[EMAIL] {last_error}, attempt {attempt + 1}/{max_retries + 1}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return {"success": False, "error": last_error}
                
        except smtplib.SMTPException as e:
            last_error = f"SMTP error: {str(e)}"
            logger.error(f"[EMAIL] {last_error}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return {"success": False, "error": last_error}
                
        except Exception as e:
            last_error = f"Unexpected error: {str(e)}"
            logger.error(f"[EMAIL] {last_error}", exc_info=True)
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                return {"success": False, "error": last_error}
    
    return {"success": False, "error": last_error or "Failed to send email after retries"}

@app.post("/detect")
async def detect(file: UploadFile = File(...), request: Request = None):
    try:
        if idcard_model is None or coco_model is None:
            raise HTTPException(status_code=503, detail="Models not initialized yet")
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded")

        filename = file.filename
        save_path = os.path.join(Config.RESULT_FOLDER, filename)

        # Save uploaded file
        with open(save_path, "wb") as f:
            f.write(await file.read())

        # Determine if file is video or image
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        file_ext = os.path.splitext(filename)[1].lower()
        is_video = file_ext in video_extensions

        detected_labels = set()
        out_dir = os.path.join(Config.RESULT_FOLDER, "predictions")
        os.makedirs(out_dir, exist_ok=True)
        
        # Variables for Cloudinary upload
        cloudinary_url = None
        cloudinary_public_id = None
        out_path = None  # Initialize to avoid undefined variable errors

        if is_video:
            # Process video
            cap = cv2.VideoCapture(save_path)
            if not cap.isOpened():
                raise HTTPException(status_code=400, detail="Unable to read video file")

            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Output video path
            output_filename = f"merged_{os.path.splitext(filename)[0]}.mp4"
            out_path = os.path.join(out_dir, output_filename)
            
            # Define codec and create VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_video = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Run detection on frame
                idcard_results = idcard_model.predict(frame, conf=0.5, verbose=False)
                coco_results = coco_model.predict(frame, conf=0.5, verbose=False)

                # Draw ID card detections
                for r in idcard_results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = f"IDCard {box.conf[0]:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        detected_labels.add("IDCard")

                # Draw COCO detections
                for r in coco_results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls = int(box.cls[0])
                        label = f"{coco_model.names[cls]} {box.conf[0]:.2f}"
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                        detected_labels.add(coco_model.names[cls])

                out_video.write(frame)
                frame_count += 1

                # Progress logging every 30 frames
                if frame_count % 30 == 0:
                    logger.info(f"Processed {frame_count}/{total_frames} frames")

            cap.release()
            out_video.release()
            logger.info(f"Video processing complete: {frame_count} frames processed")
            
            # Upload processed video to Cloudinary
            cloudinary_result = upload_to_cloudinary(out_path, resource_type="video")
            cloudinary_url = cloudinary_result["url"]
            cloudinary_public_id = cloudinary_result["public_id"]
            logger.info(f"Video uploaded to Cloudinary: {cloudinary_url}")

        else:
            # Process image (existing logic)
            img = cv2.imread(save_path)
            if img is None:
                raise HTTPException(status_code=400, detail="Unable to read image file")

            # Run models
            idcard_results = idcard_model(save_path, conf=0.5)
            coco_results = coco_model(save_path, conf=0.5)

            # Draw ID card detections
            for r in idcard_results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = f"IDCard {box.conf[0]:.2f}"
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    detected_labels.add("IDCard")

            # Draw COCO detections
            for r in coco_results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    label = f"{coco_model.names[cls]} {box.conf[0]:.2f}"
                    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    detected_labels.add(coco_model.names[cls])

            output_filename = f"merged_{filename}"
            out_path = os.path.join(out_dir, output_filename)
            cv2.imwrite(out_path, img)
            
            # Upload processed image to Cloudinary
            cloudinary_result = upload_to_cloudinary(out_path, resource_type="image")
            cloudinary_url = cloudinary_result["url"]
            cloudinary_public_id = cloudinary_result["public_id"]
            logger.info(f"Image uploaded to Cloudinary: {cloudinary_url}")

        # Validate that we have a result before saving
        if not cloudinary_url:
            logger.error("Cloudinary upload failed - no URL returned")
            # Try to keep local file as fallback
            if out_path and os.path.exists(out_path):
                logger.warning("Keeping local file due to Cloudinary upload failure")
                cloudinary_url = f"/results/predictions/{os.path.basename(out_path)}"
                cloudinary_public_id = None
            else:
                raise HTTPException(status_code=500, detail="Failed to upload processed file to cloud storage")
        
        if not out_path:
            logger.error("Processing failed - no output path")
            raise HTTPException(status_code=500, detail="Processing failed - no output file generated")

        # Save detection history tied to user with Cloudinary URL
        user_info = get_user_info_from_cookie(request) if request else None
        
        detections_collection.insert_one({
            "email": user_info.get("email") if user_info else None,
            "filename": filename,
            "result_url": cloudinary_url,  # Cloudinary URL for frontend
            "cloudinary_public_id": cloudinary_public_id,  # For deletion
            "result_path": out_path.replace("\\", "/") if out_path else None,  # Keep for backward compatibility/cleanup
            "labels": list(detected_labels),
            "detection_type": "video" if is_video else "static",
            "timestamp": datetime.datetime.utcnow()
        })

        # Send email if no objects detected
        if len(detected_labels) == 0:
            logger.info(f"No objects detected. Checking for user email to send notification...")
            # Use the user_info we already retrieved above, or get it again if needed
            if not user_info:
                user_info = get_user_info_from_cookie(request)
            user_email = user_info.get("email") if user_info else None
            
            logger.info(f"User info: {user_info}, Email: {user_email}")
            
            if user_email:
                # Use "static" for both static images and videos (non-live detection)
                logger.info(f"Attempting to send alert email to {user_email}...")
                result = send_alert_email(user_email, detection_type="static")
                if result.get("success"):
                    detection_type_text = "video" if is_video else "static"
                    logger.info(f"✅ Alert email sent: No objects detected in {detection_type_text} detection to {user_email}")
                else:
                    logger.error(f"❌ Failed to send alert email: {result.get('error')}")
            else:
                logger.warning(f"⚠️ No user email found. User might not be logged in. Cannot send alert email.")

        # Clean up local temporary files after upload
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
                logger.info(f"Cleaned up uploaded file: {save_path}")
            if out_path and os.path.exists(out_path):
                os.remove(out_path)
                logger.info(f"Cleaned up processed file: {out_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up local files: {str(e)}")

        return {"result_urls": [cloudinary_url], "labels": list(detected_labels), "type": "video" if is_video else "image"}
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Error in /detect endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# Live detection state
is_live_running = False
_live_thread = None
_live_user_email = None  # Store user email for saving snapshots
_last_snapshot_time = 0
_snapshot_interval = 10  # Save snapshot every 10 seconds


def _run_live_detection(cam_index: int = 0, user_email: str = None):
    global is_live_running, _last_snapshot_time
    if idcard_model is None or coco_model is None:
        return
    cap = cv2.VideoCapture(cam_index)
    save_dir = os.path.join(Config.RESULT_FOLDER, "live")
    os.makedirs(save_dir, exist_ok=True)
    
    frame_count = 0
    _last_snapshot_time = time.time()
    last_detected_labels = set()  # Store labels from last frame

    while is_live_running and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        idcard_results = idcard_model.predict(frame, conf=0.5, verbose=False)
        coco_results = coco_model.predict(frame, conf=0.5, verbose=False)
        
        detected_labels = set()

        for r in idcard_results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = f"IDCard {box.conf[0]:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                detected_labels.add("IDCard")

        for r in coco_results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                label = f"{coco_model.names[cls]} {box.conf[0]:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                detected_labels.add(coco_model.names[cls])

        out_path = os.path.join(save_dir, "latest.jpg")
        cv2.imwrite(out_path, frame)
        
        # Store labels for final snapshot
        last_detected_labels = detected_labels.copy()
        
        # Save snapshot to Cloudinary and database periodically
        current_time = time.time()
        if current_time - _last_snapshot_time >= _snapshot_interval and user_email:
            try:
                snapshot_filename = f"live_snapshot_{int(current_time)}.jpg"
                snapshot_path = os.path.join(save_dir, snapshot_filename)
                cv2.imwrite(snapshot_path, frame)
                
                # Upload to Cloudinary
                cloudinary_result = upload_to_cloudinary(snapshot_path, resource_type="image")
                cloudinary_url = cloudinary_result["url"]
                cloudinary_public_id = cloudinary_result["public_id"]
                
                # Save to database
                detections_collection.insert_one({
                    "email": user_email,
                    "filename": f"live_detection_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg",
                    "result_url": cloudinary_url,
                    "cloudinary_public_id": cloudinary_public_id,
                    "result_path": snapshot_path.replace("\\", "/"),
                    "labels": list(detected_labels),
                    "detection_type": "live",
                    "timestamp": datetime.datetime.utcnow()
                })
                
                logger.info(f"Live detection snapshot saved: {cloudinary_url}")
                
                # Send email if no objects detected
                if len(detected_labels) == 0 and user_email:
                    result = send_alert_email(user_email, detection_type="live")
                    if result.get("success"):
                        logger.info(f"Alert email sent: No objects detected in live detection to {user_email}")
                    else:
                        logger.warning(f"Failed to send alert email: {result.get('error')}")
                # Clean up local snapshot file

                try:
                    if os.path.exists(snapshot_path):
                        os.remove(snapshot_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up snapshot file: {str(e)}")
                
                _last_snapshot_time = current_time
            except Exception as e:
                logger.error(f"Failed to save live detection snapshot: {str(e)}", exc_info=True)
        
        frame_count += 1
        time.sleep(0.05)  # Small delay to prevent excessive CPU usage

    cap.release()
    
    # Save final snapshot when stopping (if we have detections)
    if user_email and os.path.exists(out_path):
        try:
            final_snapshot_path = os.path.join(save_dir, f"final_snapshot_{int(time.time())}.jpg")
            # Copy latest.jpg as final snapshot
            shutil.copy2(out_path, final_snapshot_path)
            
            # Get detected labels from the last frame (we'll need to run detection again or store them)
            # For simplicity, we'll just save the frame
            cloudinary_result = upload_to_cloudinary(final_snapshot_path, resource_type="image")
            cloudinary_url = cloudinary_result["url"]
            cloudinary_public_id = cloudinary_result["public_id"]
            
            # Save to database
            detections_collection.insert_one({
                "email": user_email,
                "filename": f"live_detection_final_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg",
                "result_url": cloudinary_url,
                "cloudinary_public_id": cloudinary_public_id,
                "result_path": final_snapshot_path.replace("\\", "/"),
                "labels": list(last_detected_labels),
                "detection_type": "live",
                "timestamp": datetime.datetime.utcnow()
            })
            
            logger.info(f"Final live detection snapshot saved: {cloudinary_url}")
            # Send email if no objects detected in final snapshot
            if len(last_detected_labels) == 0 and user_email:
                result = send_alert_email(user_email, detection_type="live")
                if result.get("success"):
                    logger.info(f"Alert email sent: No objects detected in final live detection to {user_email}")
                else:
                    logger.warning(f"Failed to send alert email: {result.get('error')}")
            
            # Clean up
            try:
                if os.path.exists(final_snapshot_path):
                    os.remove(final_snapshot_path)
            except Exception as e:
                logger.warning(f"Failed to clean up final snapshot: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to save final live detection snapshot: {str(e)}", exc_info=True)


@app.post("/live/start")
def start_live(request: Request):
    global is_live_running, _live_thread, _live_user_email
    if not is_live_running:
        # Get user email for saving snapshots
        user_info = get_user_info_from_cookie(request)
        _live_user_email = user_info.get("email") if user_info else None
        
        is_live_running = True
        _live_thread = threading.Thread(target=_run_live_detection, args=(0, _live_user_email), daemon=True)
        _live_thread.start()
    return {"message": "Live detection started"}


@app.post("/live/stop")
def stop_live(request: Request):
    global is_live_running, _live_user_email
    is_live_running = False
    # Wait a bit for the thread to finish saving final snapshot
    if _live_thread and _live_thread.is_alive():
        _live_thread.join(timeout=2)
    _live_user_email = None
    return {"message": "Live detection stopped"}


@app.get("/live/stream")
def live_stream():
    def generate():
        live_path = os.path.join(Config.RESULT_FOLDER, "live", "latest.jpg")
        while is_live_running:
            if os.path.exists(live_path):
                with open(live_path, "rb") as f:
                    frame = f.read()
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.05)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


# -------------------- AUTH (Register/Login + JWT) --------------------

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def create_jwt(user_id: str, username: str, email: Optional[str] = None) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")


@app.post("/auth/register")
def register(req: RegisterRequest, response: Response):
    if users_collection.find_one({"email": req.email}):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_pw = generate_password_hash(req.password)
    users_collection.insert_one({
        "username": req.username,
        "email": req.email,
        "password": hashed_pw,
        "provider": "local",
        "createdAt": datetime.datetime.utcnow(),
        "lastLogin": datetime.datetime.utcnow()
    })
    logger.info(f"[REGISTER] User registered: {req.email}")
    response.set_cookie(
        key="username",
        value=req.email,
        httponly=True,
        samesite="none",
        secure=True,
    )
    logger.info(f"[REGISTER] Username cookie set: {req.email}")
    return {"msg": "Registered successfully"}


@app.post("/auth/login")
def login(req: LoginRequest, response: Response):
    """Manual login with email/password"""
    logger.info(f"[LOGIN] Attempting login for email: {req.email}")
    user = users_collection.find_one({"email": req.email})
    if not user or not user.get("password") or not check_password_hash(user["password"], req.password):
        logger.warning(f"[LOGIN] Invalid credentials for: {req.email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    logger.info(f"[LOGIN] User found: {user.get('username')}, Email: {user.get('email')}")
    
    # Update lastLogin timestamp
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"lastLogin": datetime.datetime.utcnow()}}
    )
    
    response.set_cookie(
        key="username",
        value=user.get("email"),
        httponly=True,
        samesite="none",
        secure=True,
    )
    logger.info(f"[LOGIN] Username cookie set: {user.get('email')}")
    return {"msg": "Login successful"}


@app.get("/auth/user")
def get_current_user(request: Request):
    """Get current user from cookie - returns username from DB"""
    logger.info(f"[AUTH_USER] Checking for user cookie...")
    logger.info(f"[AUTH_USER] All cookies: {list(request.cookies.keys())}")
    
    email = request.cookies.get("username")  # Cookie stores email
    if not email:
        logger.warning(f"[AUTH_USER] No username cookie found, returning 401")
        return JSONResponse({"username": None}, status_code=401)
    
    # Lookup user in DB to get actual username
    user = users_collection.find_one({"email": email})
    if not user:
        logger.warning(f"[AUTH_USER] User not found in DB for email: {email}")
        return JSONResponse({"username": None}, status_code=401)
    
    username = user.get("username") or email.split("@")[0]  # Fallback to email prefix
    logger.info(f"[AUTH_USER] User authenticated: {username} (email: {email})")
    return {"username": username}


@app.post("/auth/logout")
def logout(response: Response):
    """Logout user by clearing username cookie"""
    logger.info(f"[LOGOUT] User logging out...")
    response.delete_cookie(
        key="username",
        path="/",
        samesite="none"
    )
    logger.info(f"[LOGOUT] Username cookie cleared successfully")
    return {"msg": "Logged out successfully"}


@app.get("/history")
def get_history(request: Request):
    user = get_user_info_from_cookie(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    email = user["email"]
    items = list(detections_collection.find({"email": email}).sort("timestamp", -1))
    def map_item(it):
        return {
            "download_id": str(it.get("_id")),
            "filename": it.get("filename"),
            "result_url": it.get("result_url"),  # Cloudinary URL (primary) - None if not available
            "result_path": it.get("result_path"),  # Local path (fallback for old records)
            "labels": it.get("labels", []),
            "detection_type": it.get("detection_type", "static"),
            "timestamp": it.get("timestamp").isoformat() if it.get("timestamp") else None
        }
    return [map_item(i) for i in items]

from bson import ObjectId
from fastapi.responses import FileResponse

@app.get("/download/{doc_id}")
def download_result(doc_id: str, request: Request):
    """Download detection result from Cloudinary or local file"""
    user = get_user_info_from_cookie(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        obj_id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = detections_collection.find_one({"_id": obj_id, "email": user["email"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Prefer Cloudinary URL, fallback to local file for backward compatibility
    result_url = doc.get("result_url")
    filename = doc.get("filename", "result")
    
    if result_url:
        # Fetch and proxy Cloudinary file
        try:
            response = requests.get(result_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determine content type from response headers or URL
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            
            # Extract file extension from filename or URL
            if filename and "." in filename:
                file_ext = filename.split(".")[-1]
            elif "." in result_url:
                file_ext = result_url.split(".")[-1].split("?")[0]
            else:
                file_ext = "jpg"
            
            # Determine content type from extension if not provided
            if content_type == "application/octet-stream":
                if file_ext.lower() in ["jpg", "jpeg"]:
                    content_type = "image/jpeg"
                elif file_ext.lower() == "png":
                    content_type = "image/png"
                elif file_ext.lower() in ["mp4", "avi", "mov"]:
                    content_type = "video/mp4"
            
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            return StreamingResponse(
                generate(),
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="detected_{filename}"'
                }
            )
        except Exception as e:
            logging.error(f"Failed to fetch from Cloudinary: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
    else:
        # Fallback to local file (backward compatibility)
        path = doc.get("result_path")
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File missing")
        return FileResponse(path, filename=f"detected_{filename}")


@app.delete("/history/{doc_id}")
def delete_history_item(doc_id: str, request: Request):
    """Delete a single detection history item for the current user"""
    user = get_user_info_from_cookie(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        obj_id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    
    # Find and verify the document belongs to the user
    doc = detections_collection.find_one({"_id": obj_id, "email": user["email"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Delete from Cloudinary if public_id exists
    cloudinary_public_id = doc.get("cloudinary_public_id")
    if cloudinary_public_id:
        detection_type = doc.get("detection_type", "static")
        resource_type = "video" if detection_type == "video" else "image"
        deleted = delete_from_cloudinary(cloudinary_public_id, resource_type)
        if deleted:
            logger.info(f"Deleted from Cloudinary: {cloudinary_public_id}")
        else:
            logger.warning(f"Failed to delete from Cloudinary: {cloudinary_public_id}")
    
    # Also try to delete local file if it exists (backward compatibility/cleanup)
    result_path = doc.get("result_path")
    if result_path:
        # Handle both absolute and relative paths
        if os.path.isabs(result_path):
            full_path = result_path
        else:
            # Remove leading slash if present and join with result folder
            clean_path = result_path.lstrip("/").replace("\\", "/")
            full_path = os.path.join(Config.RESULT_FOLDER, clean_path)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted local file: {full_path}")
        except Exception as e:
            logger.warning(f"Failed to delete local file: {str(e)}")
    
    # Delete the record from database
    detections_collection.delete_one({"_id": obj_id, "email": user["email"]})
    
    logger.info(f"Deleted detection record {doc_id} for user: {user['email']}")
    return {"message": "Detection record deleted successfully"}


@app.delete("/history/delete-all")
def delete_all_history(request: Request):
    """Delete all detection history for the current user"""
    user = get_user_info_from_cookie(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    email = user["email"]
    
    # Get all user's detection records to delete associated files
    user_detections = detections_collection.find({"email": email})
    deleted_count = 0
    
    for doc in user_detections:
        # Delete from Cloudinary if public_id exists
        cloudinary_public_id = doc.get("cloudinary_public_id")
        if cloudinary_public_id:
            detection_type = doc.get("detection_type", "static")
            resource_type = "video" if detection_type == "video" else "image"
            delete_from_cloudinary(cloudinary_public_id, resource_type)
        
        # Also try to delete local file if it exists (backward compatibility/cleanup)
        result_path = doc.get("result_path")
        if result_path:
            # Handle both absolute and relative paths
            if os.path.isabs(result_path):
                full_path = result_path
            else:
                # Remove leading slash if present and join with result folder
                clean_path = result_path.lstrip("/").replace("\\", "/")
                full_path = os.path.join(Config.RESULT_FOLDER, clean_path)
            
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
                    logger.info(f"Deleted local file: {full_path}")
            except Exception as e:
                logger.warning(f"Failed to delete local file {full_path}: {e}")
        deleted_count += 1
    
    # Delete all records from database
    result = detections_collection.delete_many({"email": email})
    
    logger.info(f"Deleted {result.deleted_count} detection records for user: {email}")
    return {"message": f"Deleted {result.deleted_count} detection records", "deleted_count": result.deleted_count}


# -------------------- Google OAuth --------------------

@app.get("/auth/google/login")
async def google_login(request: Request):
    """Step 1: Initiate Google OAuth login"""
    try:
        logger.info(f"[GOOGLE LOGIN] Starting OAuth flow")
        logger.info(f"[GOOGLE LOGIN] Redirect URI: {Config.GOOGLE_REDIRECT_URI}")
        logger.info(f"[GOOGLE LOGIN] Session exists: {'session' in request.scope}")
        logger.info(f"[GOOGLE LOGIN] Client ID: {Config.GOOGLE_CLIENT_ID[:20]}...")
        
        redirect_response = await oauth.google.authorize_redirect(request, Config.GOOGLE_REDIRECT_URI)
        logger.info(f"[GOOGLE LOGIN] Redirect response created successfully")
        return redirect_response
    except Exception as e:
        logger.error(f"[GOOGLE LOGIN] ERROR: {str(e)}", exc_info=True)
        return JSONResponse(
            {"error": "Failed to initiate Google login", "detail": str(e)},
            status_code=500
        )


@app.get("/auth/callback")
@app.get("/auth/google/callback")  # Keep both for compatibility
async def google_callback(request: Request):
    """Step 2: Handle Google OAuth callback"""
    error_msg = None
    
    # Step 2a: Check for error parameter from Google
    error_param = request.query_params.get("error")
    if error_param:
        error_msg = f"Google OAuth error: {error_param}"
        logger.error(f"[GOOGLE CALLBACK] {error_msg}")
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error={urllib.parse.quote(error_param)}")
    
    # Step 2b: Get authorization code
    code = request.query_params.get("code")
    if not code:
        error_msg = "Missing authorization code"
        logger.error(f"[GOOGLE CALLBACK] {error_msg}")
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=missing_code")
    
    logger.info(f"[GOOGLE CALLBACK] Received code: {code[:20]}...")
    logger.info(f"[GOOGLE CALLBACK] Session exists: {'session' in request.scope}")
    
    # Step 2c: Exchange code for token
    try:
        logger.info(f"[GOOGLE CALLBACK] Step 1: Exchanging code for token...")
        token = await oauth.google.authorize_access_token(request)
        logger.info(f"[GOOGLE CALLBACK] Step 1: Token exchange successful")
        logger.info(f"[GOOGLE CALLBACK] Token keys: {list(token.keys())}")
    except Exception as e:
        error_msg = f"Token exchange failed: {str(e)}"
        logger.error(f"[GOOGLE CALLBACK] Step 1 FAILED: {error_msg}", exc_info=True)
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=token_exchange_failed&detail={urllib.parse.quote(str(e))}")
    
    # Step 2d: Get user info
    info = None
    try:
        logger.info(f"[GOOGLE CALLBACK] Step 2: Fetching user info...")
        info = token.get("userinfo")
        if not info:
            logger.info(f"[GOOGLE CALLBACK] userinfo not in token, calling userinfo endpoint...")
            info = await oauth.google.userinfo(token=token)
        logger.info(f"[GOOGLE CALLBACK] Step 2: User info fetched successfully")
        logger.info(f"[GOOGLE CALLBACK] User info keys: {list(info.keys()) if info else 'None'}")
    except Exception as e:
        error_msg = f"Userinfo fetch failed: {str(e)}"
        logger.error(f"[GOOGLE CALLBACK] Step 2 FAILED: {error_msg}", exc_info=True)
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=userinfo_failed&detail={urllib.parse.quote(str(e))}")
    
    # Step 2e: Extract user information from Google
    email = info.get("email") if info else None
    name = info.get("name") or info.get("given_name") or "User"
    picture = info.get("picture")
    given_name = info.get("given_name")
    family_name = info.get("family_name")
    verified_email = info.get("verified_email", False)
    locale = info.get("locale")
    
    logger.info(f"[GOOGLE CALLBACK] Step 3: Extracted email: {email}, name: {name}")
    
    if not email:
        error_msg = "No email in user info"
        logger.error(f"[GOOGLE CALLBACK] Step 3 FAILED: {error_msg}")
        logger.error(f"[GOOGLE CALLBACK] Available keys: {list(info.keys()) if info else 'None'}")
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=no_email")
    
    # Step 2f: Upsert user in database with comprehensive profile data
    try:
        logger.info(f"[GOOGLE CALLBACK] Step 4: Looking up/creating user in DB...")
        user = users_collection.find_one({"email": email})
        if not user:
            logger.info(f"[GOOGLE CALLBACK] Creating new user...")
            users_collection.insert_one({
                "username": name,
                "email": email,
                "password": None,
                "provider": "google",
                "google_profile": {
                    "picture": picture,
                    "given_name": given_name,
                    "family_name": family_name,
                    "verified_email": verified_email,
                    "locale": locale
                },
                "createdAt": datetime.datetime.utcnow(),
                "lastLogin": datetime.datetime.utcnow()
            })
            user = users_collection.find_one({"email": email})
            logger.info(f"[GOOGLE CALLBACK] User created with ID: {str(user['_id'])}")
        else:
            logger.info(f"[GOOGLE CALLBACK] Existing user found with ID: {str(user['_id'])}")
            # Update profile data on each login
            google_profile = {
                "picture": picture,
                "given_name": given_name,
                "family_name": family_name,
                "verified_email": verified_email,
                "locale": locale
            }
            
            update_data = {
                "username": name,
                "lastLogin": datetime.datetime.utcnow(),
                "google_profile": google_profile
            }
            
            users_collection.update_one({"_id": user["_id"]}, {"$set": update_data})
            logger.info(f"[GOOGLE CALLBACK] User profile updated successfully")
    except Exception as e:
        error_msg = f"Database operation failed: {str(e)}"
        logger.error(f"[GOOGLE CALLBACK] Step 4 FAILED: {error_msg}", exc_info=True)
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=db_failed&detail={urllib.parse.quote(str(e))}")
    
    # Step 2g: Set cookie with email (username) and redirect
    try:
        logger.info(f"[GOOGLE CALLBACK] Step 5: Setting cookie and redirecting...")
        logger.info(f"[GOOGLE CALLBACK] Cookie settings: httponly=True, secure=True, samesite=none")
        logger.info(f"[GOOGLE CALLBACK] Setting username cookie with value: {email}")
        logger.info(f"[GOOGLE CALLBACK] Redirecting to: {Config.FRONTEND_BASE}")
        
        resp = RedirectResponse(f"{Config.FRONTEND_BASE}")
        resp.set_cookie(
            key="username",
            value=email,
            httponly=True,
            samesite="none",
            secure=True,
        )
        
        logger.info(f"[GOOGLE CALLBACK] Step 5: Cookie set successfully")
        logger.info(f"[GOOGLE CALLBACK] Cookie 'username' set with email: {email}")
        logger.info(f"[GOOGLE CALLBACK] Redirect response created")
        
        return resp
    except Exception as e:
        error_msg = f"Cookie setting failed: {str(e)}"
        logger.error(f"[GOOGLE CALLBACK] Step 5 FAILED: {error_msg}", exc_info=True)
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=cookie_failed&detail={urllib.parse.quote(str(e))}")

@app.post("/send-email")
def send_mail(request: Request):
    """API endpoint to send alert email - uses cookie for authentication"""
    email = request.cookies.get("username")
    if not email:
        raise HTTPException(status_code=401, detail="User not logged in")
    
    result = send_alert_email(email)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500, 
            detail=result.get("error", "Failed to send email")
        )
    
    return {"message": "Email sent successfully"}

@app.get("/test-email")
async def test_email(request: Request):
    """
    Test endpoint to diagnose email sending issues.
    Tests SMTP connection, authentication, and email sending.
    """
    test_results = {
        "step": "Starting email test",
        "email_user_configured": bool(Config.EMAIL_USER),
        "email_password_configured": bool(Config.EMAIL_PASSWORD),
        "smtp_server": Config.SMTP_SERVER,
        "smtp_port": Config.SMTP_PORT,
        "tests": []
    }
    
    # Test 1: Check if credentials are configured
    logger.info("[EMAIL TEST] Step 1: Checking configuration...")
    if not Config.EMAIL_USER:
        test_results["tests"].append({
            "test": "EMAIL_USER configuration",
            "status": "FAILED",
            "message": "EMAIL_USER is not set in environment variables"
        })
        return JSONResponse(status_code=400, content={
            **test_results,
            "error": "EMAIL_USER not configured. Add EMAIL_USER=your-email@gmail.com to .env file"
        })
    else:
        test_results["tests"].append({
            "test": "EMAIL_USER configuration",
            "status": "PASSED",
            "message": f"EMAIL_USER is set (showing first 3 chars: {Config.EMAIL_USER[:3]}...)"
        })
    
    if not Config.EMAIL_PASSWORD:
        test_results["tests"].append({
            "test": "EMAIL_PASSWORD configuration",
            "status": "FAILED",
            "message": "EMAIL_PASSWORD is not set in environment variables"
        })
        return JSONResponse(status_code=400, content={
            **test_results,
            "error": "EMAIL_PASSWORD not configured. Add EMAIL_PASSWORD=your-app-password to .env file"
        })
    else:
        test_results["tests"].append({
            "test": "EMAIL_PASSWORD configuration",
            "status": "PASSED",
            "message": "EMAIL_PASSWORD is set (length: " + str(len(Config.EMAIL_PASSWORD)) + " characters)"
        })
    
    # Test 2: Get recipient email from cookie or use test email
    recipient_email = request.cookies.get("username") or request.query_params.get("to")
    if not recipient_email:
        recipient_email = Config.EMAIL_USER  # Send to self if no recipient specified
        test_results["tests"].append({
            "test": "Recipient email",
            "status": "INFO",
            "message": f"No recipient specified, using EMAIL_USER: {recipient_email}"
        })
    else:
        test_results["tests"].append({
            "test": "Recipient email",
            "status": "PASSED",
            "message": f"Recipient: {recipient_email}"
        })
    
    # Test 3: Test SMTP connection
    logger.info("[EMAIL TEST] Step 2: Testing SMTP connection...")
    try:
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10)
        test_results["tests"].append({
            "test": "SMTP connection",
            "status": "PASSED",
            "message": f"Successfully connected to {Config.SMTP_SERVER}:{Config.SMTP_PORT}"
        })
    except Exception as e:
        test_results["tests"].append({
            "test": "SMTP connection",
            "status": "FAILED",
            "message": f"Failed to connect: {str(e)}"
        })
        return JSONResponse(status_code=500, content={
            **test_results,
            "error": f"SMTP connection failed: {str(e)}"
        })
    
    # Test 4: Test STARTTLS
    logger.info("[EMAIL TEST] Step 3: Testing STARTTLS...")
    try:
        server.starttls()
        test_results["tests"].append({
            "test": "STARTTLS encryption",
            "status": "PASSED",
            "message": "TLS encryption enabled successfully"
        })
    except Exception as e:
        server.quit()
        test_results["tests"].append({
            "test": "STARTTLS encryption",
            "status": "FAILED",
            "message": f"Failed to enable TLS: {str(e)}"
        })
        return JSONResponse(status_code=500, content={
            **test_results,
            "error": f"STARTTLS failed: {str(e)}"
        })
    
    # Test 5: Test authentication
    logger.info("[EMAIL TEST] Step 4: Testing authentication...")
    try:
        server.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
        test_results["tests"].append({
            "test": "SMTP authentication",
            "status": "PASSED",
            "message": "Successfully authenticated with Gmail"
        })
    except smtplib.SMTPAuthenticationError as e:
        server.quit()
        error_code = e.smtp_code if hasattr(e, 'smtp_code') else 'Unknown'
        error_msg = str(e)
        test_results["tests"].append({
            "test": "SMTP authentication",
            "status": "FAILED",
            "message": f"Authentication failed (Code: {error_code}): {error_msg}"
        })
        return JSONResponse(status_code=401, content={
            **test_results,
            "error": "Authentication failed. Common issues:\n"
                    "1. EMAIL_USER or EMAIL_PASSWORD is incorrect\n"
                    "2. You need to use an App Password, not your regular Gmail password\n"
                    "3. 2-Step Verification must be enabled in your Google Account\n"
                    "4. 'Less secure app access' might be disabled (if using regular password)\n"
                    f"Error details: {error_msg}"
        })
    except Exception as e:
        server.quit()
        test_results["tests"].append({
            "test": "SMTP authentication",
            "status": "FAILED",
            "message": f"Unexpected error during authentication: {str(e)}"
        })
        return JSONResponse(status_code=500, content={
            **test_results,
            "error": f"Authentication error: {str(e)}"
        })
    
    # Test 6: Test sending email
    logger.info("[EMAIL TEST] Step 5: Testing email sending...")
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "VisionGuard Email Test"
        msg['From'] = Config.EMAIL_USER
        msg['To'] = recipient_email
        
        text_content = "This is a test email from VisionGuard. If you receive this, your email configuration is working correctly!"
        html_content = """
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #4CAF50;">✅ VisionGuard Email Test</h2>
            <p>This is a <strong>test email</strong> from VisionGuard.</p>
            <p>If you receive this, your email configuration is working correctly!</p>
            <p><small>Sent at: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</small></p>
        </div>
        """
        
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        server.send_message(msg)
        test_results["tests"].append({
            "test": "Email sending",
            "status": "PASSED",
            "message": f"Test email sent successfully to {recipient_email}"
        })
        
        server.quit()
        
        test_results["step"] = "All tests passed!"
        test_results["summary"] = "✅ Email configuration is working correctly! Check your inbox."
        
        return JSONResponse(content=test_results)
        
    except smtplib.SMTPRecipientsRefused as e:
        server.quit()
        test_results["tests"].append({
            "test": "Email sending",
            "status": "FAILED",
            "message": f"Recipient email rejected: {str(e)}"
        })
        return JSONResponse(status_code=400, content={
            **test_results,
            "error": f"Invalid recipient email address: {recipient_email}"
        })
    except Exception as e:
        server.quit()
        test_results["tests"].append({
            "test": "Email sending",
            "status": "FAILED",
            "message": f"Failed to send email: {str(e)}"
        })
        return JSONResponse(status_code=500, content={
            **test_results,
            "error": f"Email sending failed: {str(e)}"
        })
        
import uvicorn

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000, reload=True)
