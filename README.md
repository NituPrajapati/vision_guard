# Vision Guard - Object Detection System

A full-stack object detection application with user authentication, static image detection, live webcam detection, and detection history management.

## Features

- 🔐 **User Authentication**: Register, login, and secure session management
- 📸 **Static Detection**: Upload images/videos for object detection
- 📹 **Live Detection**: Real-time webcam object detection
- 📊 **Detection History**: View and download your detection results
- 🎯 **Dual Models**: ID Card detection + COCO object detection
- 💾 **Download Results**: Download detection results with bounding boxes

## Tech Stack

### Backend
- **Flask**: Web framework
- **YOLO (Ultralytics)**: Object detection models
- **MongoDB**: Database for user data and detection history
- **JWT**: Authentication tokens
- **OpenCV**: Image/video processing

### Frontend
- **React**: UI framework
- **Vite**: Build tool
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB (local or cloud)

### 1. Clone and Setup Backend

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Create environment file (or run setup script)
python ../setup_env.py
```

### 2. Setup MongoDB

**Option A: Local MongoDB**
```bash
# Install MongoDB locally
# Start MongoDB service
mongod
```

**Option B: MongoDB Atlas (Cloud)**
- Create account at [MongoDB Atlas](https://www.mongodb.com/atlas)
- Create a cluster and get connection string
- Update `MONGO_URI` in `.env` file

### 3. Configure Environment

Create `backend/.env` file:
```env
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
MONGO_URI=mongodb://localhost:27017/
DB_NAME=visionguard
FLASK_ENV=development
```

### 4. Setup Frontend

```bash
# Navigate to react-app directory
cd react-app

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Start Backend

```bash
# From backend directory
python app.py
```

## Usage

1. **Register**: Create a new account
2. **Login**: Sign in with your credentials
3. **Static Detection**: Upload images/videos for detection
4. **Live Detection**: Start webcam detection
5. **View History**: Check your detection history
6. **Download Results**: Download detection results with bounding boxes

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login

### Detection
- `POST /detect` - Static image/video detection (requires auth)
- `POST /live/start` - Start live detection (requires auth)
- `POST /live/stop` - Stop live detection (requires auth)
- `GET /live/stream` - Live detection stream (requires auth)

### History & Downloads
- `GET /history` - Get user's detection history (requires auth)
- `GET /download/<download_id>` - Download detection result (requires auth)
- `GET /results/<filename>` - Serve result files (requires auth)

## File Structure

```
react-app-detection/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── auth_routes.py      # Authentication routes
│   ├── db.py              # Database configuration
│   ├── requirements.txt   # Python dependencies
│   ├── results/           # Detection results storage
│   └── runs/              # YOLO model files
├── react-app/
│   ├── src/
│   │   ├── App.jsx        # Main React component
│   │   └── components/    # React components
│   ├── package.json       # Node.js dependencies
│   └── vite.config.js     # Vite configuration
└── README.md
```

## Security Features

- JWT-based authentication
- User-specific data isolation
- File upload validation
- Input sanitization
- CORS configuration

## Troubleshooting

### Common Issues

1. **"Invalid credentials" error**
   - Check if MongoDB is running
   - Verify user exists in database
   - Check JWT secret configuration

2. **Model loading errors**
   - Ensure YOLO model files exist in `runs/detect/train3/weights/`
   - Check `yolov8n.pt` is in backend directory

3. **CORS errors**
   - Verify frontend is running on `http://localhost:5173`
   - Check CORS configuration in `app.py`

4. **File upload issues**
   - Check file size limits (16MB max)
   - Verify file extensions are allowed
   - Ensure `results/` directory exists

### Debug Mode

Enable debug mode by setting `FLASK_ENV=development` in `.env` file.

## Production Deployment

1. Change JWT secret to a secure random string
2. Use environment variables for all sensitive data
3. Set up proper MongoDB authentication
4. Configure reverse proxy (nginx)
5. Use HTTPS in production
6. Set up proper logging and monitoring

