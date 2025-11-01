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
import jwt
from pydantic import BaseModel
from typing import Optional
from db import users_collection, detections_collection
from werkzeug.security import generate_password_hash, check_password_hash
import urllib.parse
import requests
import logging
from authlib.integrations.starlette_client import OAuth

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Required for Authlib (stores OAuth state in server-side session)
app.add_middleware(SessionMiddleware, secret_key=Config.JWT_SECRET_KEY)
# Mount results static dir (equivalent of Flask send_from_directory)
app.mount("/results", StaticFiles(directory=Config.RESULT_FOLDER), name="results")

@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


idcard_model = None
coco_model = None


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
    client_kwargs={"scope": "openid email profile"},
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


@app.on_event("startup")
def on_startup():
    global idcard_model, coco_model
    os.makedirs(Config.RESULT_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(Config.RESULT_FOLDER, "predictions"), exist_ok=True)
    # Lazy load models at startup to avoid import-time issues with reload on Windows
    idcard_model = YOLO(Config.IDCARD_MODEL_PATH)
    coco_model = YOLO(Config.COCO_MODEL_PATH)


@app.post("/detect")
async def detect(file: UploadFile = File(...), request: Request = None):
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

    # Save detection history tied to user
    user_info = get_user_info_from_cookie(request) if request else None
    detections_collection.insert_one({
        "email": user_info.get("email") if user_info else None,
        "filename": filename,
        "result_path": out_path.replace("\\", "/"),
        "labels": list(detected_labels),
        "detection_type": "video" if is_video else "static",
        "timestamp": datetime.datetime.utcnow()
    })

    return {"result_paths": [out_path.replace("\\", "/")], "labels": list(detected_labels), "type": "video" if is_video else "image"}


# Live detection state
is_live_running = False
_live_thread = None


def _run_live_detection(cam_index: int = 0):
    global is_live_running
    if idcard_model is None or coco_model is None:
        return
    cap = cv2.VideoCapture(cam_index)
    save_dir = os.path.join(Config.RESULT_FOLDER, "live")
    os.makedirs(save_dir, exist_ok=True)

    while is_live_running and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        idcard_results = idcard_model.predict(frame, conf=0.5, verbose=False)
        coco_results = coco_model.predict(frame, conf=0.5, verbose=False)

        for r in idcard_results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                label = f"IDCard {box.conf[0]:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        for r in coco_results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                label = f"{coco_model.names[cls]} {box.conf[0]:.2f}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        out_path = os.path.join(save_dir, "latest.jpg")
        cv2.imwrite(out_path, frame)

    cap.release()


@app.post("/live/start")
def start_live():
    global is_live_running, _live_thread
    if not is_live_running:
        is_live_running = True
        _live_thread = threading.Thread(target=_run_live_detection, daemon=True)
        _live_thread.start()
    return {"message": "Live detection started"}


@app.post("/live/stop")
def stop_live():
    global is_live_running
    is_live_running = False
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
        "createdAt": datetime.datetime.utcnow()
    })
    logger.info(f"[REGISTER] User registered: {req.email}")
    response.set_cookie(
        key="username",
        value=req.email,
        httponly=True,
        samesite="lax",
        secure=False,
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
    
    response.set_cookie(
        key="username",
        value=user.get("email"),
        httponly=True,
        samesite="lax",
        secure=False,
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
        samesite="lax"
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
            "result_path": it.get("result_path"),
            "labels": it.get("labels", []),
            "detection_type": it.get("detection_type", "static"),
            "timestamp": it.get("timestamp").isoformat() if it.get("timestamp") else None
        }
    return [map_item(i) for i in items]

from bson import ObjectId
from fastapi.responses import FileResponse

@app.get("/download/{doc_id}")
def download_result(doc_id: str, request: Request):
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
    path = doc.get("result_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(path, filename=f"detected_{doc.get('filename','result')}")


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
    
    # Delete the result file from filesystem
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
                logger.info(f"Deleted file: {full_path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {full_path}: {e}")
    
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
        # Delete the result file from filesystem
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
                    logger.info(f"Deleted file: {full_path}")
            except Exception as e:
                logger.warning(f"Failed to delete file {full_path}: {e}")
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
    
    # Step 2e: Extract email and name
    email = info.get("email") if info else None
    name = info.get("name") or info.get("given_name") or "User"
    
    logger.info(f"[GOOGLE CALLBACK] Step 3: Extracted email: {email}, name: {name}")
    
    if not email:
        error_msg = "No email in user info"
        logger.error(f"[GOOGLE CALLBACK] Step 3 FAILED: {error_msg}")
        logger.error(f"[GOOGLE CALLBACK] Available keys: {list(info.keys()) if info else 'None'}")
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=no_email")
    
    # Step 2f: Upsert user in database
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
                "createdAt": datetime.datetime.utcnow()
            })
            user = users_collection.find_one({"email": email})
            logger.info(f"[GOOGLE CALLBACK] User created with ID: {str(user['_id'])}")
        else:
            logger.info(f"[GOOGLE CALLBACK] Existing user found with ID: {str(user['_id'])}")
            if not user.get("username"):
                logger.info(f"[GOOGLE CALLBACK] Updating username...")
                users_collection.update_one({"_id": user["_id"]}, {"$set": {"username": name}})
    except Exception as e:
        error_msg = f"Database operation failed: {str(e)}"
        logger.error(f"[GOOGLE CALLBACK] Step 4 FAILED: {error_msg}", exc_info=True)
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=db_failed&detail={urllib.parse.quote(str(e))}")
    
    # Step 2g: Set cookie with email (username) and redirect
    try:
        logger.info(f"[GOOGLE CALLBACK] Step 5: Setting cookie and redirecting...")
        logger.info(f"[GOOGLE CALLBACK] Cookie settings: httponly=True, secure=False, samesite=lax")
        logger.info(f"[GOOGLE CALLBACK] Setting username cookie with value: {email}")
        logger.info(f"[GOOGLE CALLBACK] Redirecting to: {Config.FRONTEND_BASE}")
        
        resp = RedirectResponse(f"{Config.FRONTEND_BASE}")
        resp.set_cookie(
            key="username",
            value=email,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        
        logger.info(f"[GOOGLE CALLBACK] Step 5: Cookie set successfully")
        logger.info(f"[GOOGLE CALLBACK] Cookie 'username' set with email: {email}")
        logger.info(f"[GOOGLE CALLBACK] Redirect response created")
        
        return resp
    except Exception as e:
        error_msg = f"Cookie setting failed: {str(e)}"
        logger.error(f"[GOOGLE CALLBACK] Step 5 FAILED: {error_msg}", exc_info=True)
        return RedirectResponse(f"{Config.FRONTEND_BASE}/auth/callback?error=cookie_failed&detail={urllib.parse.quote(str(e))}")

import uvicorn

if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000, reload=True)
