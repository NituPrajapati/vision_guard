# Deployment Guide - Alternative Platforms

This guide covers deployment options for your React + FastAPI application (excluding AWS, GCP, Azure).

## Quick Comparison

| Platform | Best For | Cost | Difficulty | Recommended |
|----------|----------|------|------------|-------------|
| **Railway** | Quick deployment | $5+/mo | Easy | ⭐⭐⭐⭐⭐ |
| **Render** | Budget-friendly | Free-$7+/mo | Easy | ⭐⭐⭐⭐ |
| **DigitalOcean** | Production-ready | $12+/mo | Medium | ⭐⭐⭐⭐ |
| **Fly.io** | Global distribution | $2+/mo | Medium | ⭐⭐⭐ |
| **Vercel + Backend** | Frontend optimization | Free-$20/mo | Medium | ⭐⭐⭐⭐ |

---

## Recommended: Railway (Easiest)

### Setup Steps:

1. **Sign up** at [railway.app](https://railway.app)

2. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

3. **Deploy Backend:**
   ```bash
   cd backend
   railway login
   railway init
   railway up
   ```

4. **Add MongoDB:**
   - In Railway dashboard → New → Add Database → MongoDB
   - Copy connection string to environment variables

5. **Set Environment Variables** in Railway:
   ```
   JWT_SECRET=your-secret-key
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-secret
   MONGO_URI=mongodb://... (from MongoDB service)
   FRONTEND_BASE=https://your-frontend-url
   GOOGLE_REDIRECT_URI=https://your-frontend-url/auth/callback
   ```

6. **Deploy Frontend:**
   - Build React app: `npm run build` in `react-app/`
   - Railway supports static sites, or use Vercel/Netlify for frontend

### Railway Configuration File (`railway.json`):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## Option 2: Render

### Backend Deployment:

1. **Create account** at [render.com](render.com)

2. **New Web Service:**
   - Connect GitHub repo
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT`

3. **Add MongoDB:**
   - New → MongoDB
   - Copy connection string

4. **Environment Variables:**
   ```
   JWT_SECRET=your-secret
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-secret
   MONGO_URI=mongodb+srv://...
   FRONTEND_BASE=https://your-app.onrender.com
   PORT=10000
   ```

5. **Frontend on Render:**
   - New → Static Site
   - Build Command: `cd react-app && npm install && npm run build`
   - Publish Directory: `react-app/dist`

### Render Limitations:
- Free tier spins down after 15 min inactivity
- Cold starts can be slow
- Upgrade to paid plan for production

---

## Option 3: DigitalOcean App Platform

### Setup:

1. **Create account** at [digitalocean.com](https://digitalocean.com)

2. **Deploy Backend:**
   - Create App → GitHub repo
   - Component Type: Web Service
   - Build Command: `cd backend && pip install -r requirements.txt`
   - Run Command: `cd backend && uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT`
   - Resource: Basic ($5/mo) or Pro ($12/mo)

3. **Add MongoDB:**
   - New Component → Database → MongoDB
   - Or use managed MongoDB Atlas (free tier available)

4. **Deploy Frontend:**
   - New Component → Static Site
   - Build Command: `cd react-app && npm install && npm run build`
   - Output Directory: `react-app/dist`

---

## Option 4: Fly.io (Container-based)

### Setup:

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Create `backend/Dockerfile`:**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   EXPOSE 8080

   CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8080"]
   ```

3. **Deploy:**
   ```bash
   cd backend
   fly launch
   fly secrets set JWT_SECRET=... GOOGLE_CLIENT_ID=... etc.
   fly deploy
   ```

4. **Add MongoDB:**
   - Use MongoDB Atlas (free tier) or Fly Postgres with adapter

---

## Option 5: Vercel (Frontend) + Railway/Render (Backend)

### Frontend on Vercel:

1. **Connect GitHub** to [vercel.com](https://vercel.com)

2. **Import Project:**
   - Root Directory: `react-app`
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Framework Preset: Vite

3. **Environment Variables:**
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```

### Backend on Railway/Render:
Follow backend deployment steps above.

**Update `fastapi_app.py` CORS:**
```python
allow_origins=["https://your-frontend.vercel.app"]
```

---

## Environment Variables Checklist

Set these on your deployment platform:

### Backend:
- `JWT_SECRET` - Random secret key (use `openssl rand -hex 32`)
- `GOOGLE_CLIENT_ID` - From Google Cloud Console
- `GOOGLE_CLIENT_SECRET` - From Google Cloud Console
- `MONGO_URI` - MongoDB connection string
- `DB_NAME` - Database name (default: visionguard)
- `FRONTEND_BASE` - Your frontend URL
- `GOOGLE_REDIRECT_URI` - `{FRONTEND_BASE}/auth/callback`
- `PORT` - Usually auto-set by platform

### Frontend (if using build-time env):
- `VITE_API_URL` - Backend API URL

---

## Important Notes

### File Storage:
- Your app stores results in `results/` folder
- Most platforms have ephemeral storage (files deleted on restart)
- **Solutions:**
  1. Use cloud storage (Cloudinary, Backblaze B2 - free tier)
  2. Use platform storage (Railway volumes, DigitalOcean Spaces)
  3. Store in MongoDB GridFS

### ML Model Files:
- `yolov8n.pt` and trained models should be:
  1. Committed to repo (if < 100MB)
  2. Downloaded on build (from cloud storage)
  3. Stored in persistent volume

### MongoDB Options:
1. **MongoDB Atlas** (free tier) - Recommended
2. Platform-managed MongoDB
3. Self-hosted on VPS

---

## Recommended Architecture

**For Production:**
- **Frontend:** Vercel or Netlify (free, excellent CDN)
- **Backend:** Railway or DigitalOcean App Platform
- **Database:** MongoDB Atlas (free tier available)
- **File Storage:** Backblaze B2 or Cloudinary (free tiers)

**For Budget/Testing:**
- **Everything:** Render (free tier) or Railway ($5/mo)

---

## Deployment Checklist

- [ ] Update CORS origins in `fastapi_app.py`
- [ ] Set all environment variables
- [ ] Update Google OAuth redirect URIs in Google Cloud Console
- [ ] Configure file storage (if needed)
- [ ] Test API endpoints
- [ ] Test OAuth flow
- [ ] Monitor logs for errors
- [ ] Set up custom domain (optional)
- [ ] Enable SSL/HTTPS (usually automatic)

---

## Support & Documentation

- Railway: [docs.railway.app](https://docs.railway.app)
- Render: [render.com/docs](https://render.com/docs)
- DigitalOcean: [docs.digitalocean.com](https://docs.digitalocean.com)
- Fly.io: [fly.io/docs](https://fly.io/docs)
- Vercel: [vercel.com/docs](https://vercel.com/docs)

