# Email Setup Guide

## Quick Fix for Email Not Working

If your email is not working even with correct credentials, follow these steps:

### 1. Create `.env` file in `backend` directory

Create a file named `.env` in the `backend` folder with the following content:

```env
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password-here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### 2. Important Notes:

- **EMAIL_USER**: Your Gmail address (e.g., `yourname@gmail.com`)
- **EMAIL_PASSWORD**: Must be an **App Password**, NOT your regular Gmail password
- **SMTP_SERVER**: Default is `smtp.gmail.com` (can be omitted)
- **SMTP_PORT**: Default is `587` (can be omitted)

### 3. How to Get Gmail App Password:

1. Go to your Google Account: https://myaccount.google.com/
2. Enable **2-Step Verification** (required for App Passwords)
3. Go to: https://myaccount.google.com/apppasswords
4. Select "Mail" and "Other (Custom name)" → Enter "VisionGuard"
5. Click "Generate"
6. Copy the 16-character password (no spaces)
7. Use this password as `EMAIL_PASSWORD` in your `.env` file

### 4. Verify Setup:

1. Restart your FastAPI server after creating/updating `.env` file
2. Test email endpoint: `GET http://localhost:5000/test-email`
3. Check server logs for detailed error messages

### 5. Common Issues:

**Issue**: "Email credentials not configured"
- **Solution**: Make sure `.env` file is in the `backend` directory (same folder as `config.py`)
- **Solution**: Restart the server after creating/updating `.env` file

**Issue**: "SMTP Authentication failed"
- **Solution**: Make sure you're using an App Password, not your regular password
- **Solution**: Verify 2-Step Verification is enabled
- **Solution**: Check that EMAIL_USER is your full Gmail address

**Issue**: "Connection timeout"
- **Solution**: Check your internet connection
- **Solution**: Verify firewall isn't blocking port 587
- **Solution**: Try using port 465 with SSL instead (requires code change)

### 6. Example `.env` file location:

```
vision_guard/
└── backend/
    ├── .env          ← Create this file here
    ├── config.py
    └── fastapi_app.py
```

### 7. Test Your Configuration:

Visit: `http://localhost:5000/test-email` in your browser or use curl:

```bash
curl http://localhost:5000/test-email
```

This will show detailed diagnostics about your email configuration.

