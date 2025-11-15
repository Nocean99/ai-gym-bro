# Render Deployment - Quick Start

## TL;DR - Deploy in 10 Minutes

### 1. Create PostgreSQL Database (2 min)
1. Go to https://render.com → New → PostgreSQL
2. Name: `gym-bro-db`, Plan: Free
3. **Copy the Internal Database URL**

### 2. Set Up Database Schema (2 min)
```bash
# Connect to database
psql <EXTERNAL_DATABASE_URL>

# Run schema
\i database/schema.sql
\q
```

### 3. Create Web Service (5 min)
1. Render Dashboard → New → Web Service
2. Connect your GitHub repo: `ai-gym-bro`
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT backend.api_server:app`
   - **Plan**: Free

4. Environment Variables:
   ```
   OPENAI_API_KEY = sk-proj-your-key-here
   DATABASE_URL = <paste Internal Database URL>
   DEBUG = False
   PYTHON_VERSION = 3.11.0
   ```

5. Click **"Create Web Service"**

### 4. Test Deployment (1 min)
Visit: `https://your-service.onrender.com/health`

Should return:
```json
{"status": "healthy", "message": "AI Gym Bro API is running! 💪"}
```

### 5. Update Mobile App
```bash
# mobile/.env
API_BASE_URL=https://your-service.onrender.com
ENVIRONMENT=production
```

## Done! 🎉

Your production URL: **https://[your-service-name].onrender.com**

---

**Important Notes:**
- Free tier spins down after 15 min inactivity (30-60s cold start)
- Database expires after 90 days on free tier
- Auto-deploys when you push to GitHub

**Full Documentation**: See RENDER_DEPLOYMENT.md
