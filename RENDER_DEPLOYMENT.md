# Deploying Gym Bro to Render

This guide will walk you through deploying your Gym Bro backend API to Render.

## Prerequisites

- GitHub account (to connect your repository)
- Render account (sign up at https://render.com)
- Your OpenAI API key

## Step-by-Step Deployment Guide

### 1. Push Your Code to GitHub

First, make sure all your changes are committed and pushed:

```bash
cd ai-gym-bro
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

### 2. Sign Up for Render

1. Go to https://render.com
2. Click "Get Started" or "Sign Up"
3. Sign up with your GitHub account (recommended)
4. Authorize Render to access your GitHub repositories

### 3. Create a PostgreSQL Database

1. From your Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Fill in the details:
   - **Name**: `gym-bro-db`
   - **Database**: `workout_tracker`
   - **User**: (auto-generated)
   - **Region**: Choose closest to you (e.g., Oregon USA)
   - **Plan**: **Free** (for now)
3. Click **"Create Database"**
4. **IMPORTANT**: Copy the **Internal Database URL** - you'll need this later
5. Wait for the database to provision (takes ~1-2 minutes)

### 4. Set Up Database Schema

After your database is created:

1. Click on your database in the Render dashboard
2. Go to the **"Shell"** tab (or use **"Connect"** button)
3. Run the following SQL commands to create tables:

```sql
-- Copy the contents of database/schema.sql here
-- Or connect via psql and run:
-- \i database/schema.sql
```

**Alternatively**, you can connect from your local machine:

```bash
# Get the External Database URL from Render dashboard
psql <EXTERNAL_DATABASE_URL>

# Then run:
\i database/schema.sql
\q
```

### 5. Create the Web Service

1. From Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository:
   - Click **"Connect account"** if needed
   - Select **"ai-gym-bro"** repository
   - Click **"Connect"**

3. Configure the service:
   - **Name**: `gym-bro-api`
   - **Region**: Same as your database (e.g., Oregon USA)
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave blank (or enter `backend` if needed)
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT backend.api_server:app`
   - **Plan**: **Free**

4. Click **"Advanced"** and add **Environment Variables**:

   | Key | Value |
   |-----|-------|
   | `PYTHON_VERSION` | `3.11.0` |
   | `OPENAI_API_KEY` | `your-openai-api-key-here` |
   | `DATABASE_URL` | Paste the Internal Database URL from step 3 |
   | `DEBUG` | `False` |

   **IMPORTANT**: For `DATABASE_URL`:
   - Go to your PostgreSQL database page
   - Copy the **Internal Database URL**
   - Paste it as the value for `DATABASE_URL`

5. Click **"Create Web Service"**

### 6. Wait for Deployment

1. Render will now:
   - Clone your repository
   - Install dependencies
   - Start your Flask app with Gunicorn
2. This takes 2-5 minutes for the first deploy
3. Watch the logs in the **"Logs"** tab

### 7. Verify Deployment

Once deployed, you'll get a URL like: `https://gym-bro-api.onrender.com`

Test your API:

1. Visit: `https://gym-bro-api.onrender.com/health`
2. You should see:
   ```json
   {
     "status": "healthy",
     "message": "AI Gym Bro API is running! 💪"
   }
   ```

### 8. Update Your Mobile App

Update the mobile app's `.env` file with your production URL:

```bash
# mobile/.env
API_BASE_URL=https://gym-bro-api.onrender.com
ENVIRONMENT=production
```

## Environment Variables Reference

Your Render service should have these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-proj-...` |
| `DATABASE_URL` | PostgreSQL connection URL (from Render) | `postgresql://user:pass@host/db` |
| `DEBUG` | Enable debug mode (use False in production) | `False` |
| `PYTHON_VERSION` | Python version to use | `3.11.0` |

## Troubleshooting

### Build Fails

**Issue**: Dependencies fail to install

**Solution**:
- Check that `requirements.txt` is in the root directory
- Make sure all package versions are compatible
- Check build logs for specific errors

### Database Connection Errors

**Issue**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
- Verify `DATABASE_URL` is set correctly
- Use the **Internal Database URL**, not External
- Make sure database and web service are in the same region

### App Won't Start

**Issue**: Service keeps restarting or shows "Service Unavailable"

**Solution**:
- Check logs for errors: Render Dashboard → Your Service → Logs
- Verify the start command is correct: `gunicorn --bind 0.0.0.0:$PORT backend.api_server:app`
- Make sure `OPENAI_API_KEY` is set

### 500 Internal Server Error

**Issue**: API returns 500 errors

**Solution**:
- Check application logs in Render dashboard
- Verify database schema is created (run `schema.sql`)
- Check that all environment variables are set

## Free Tier Limitations

Render's free tier has some limitations:

- **Web Service**:
  - 750 hours/month (enough for one app)
  - Spins down after 15 minutes of inactivity
  - Cold start takes 30-60 seconds

- **PostgreSQL**:
  - 1GB storage
  - 90 days of data retention
  - Expires after 90 days (you'll need to upgrade or migrate)

## Keeping Your Service Awake (Optional)

To prevent cold starts, you can:

1. **Upgrade to paid plan** ($7/month for web service)
2. **Use a ping service** (e.g., UptimeRobot) to ping your API every 14 minutes
3. **Accept the cold start** - first request takes 30-60s after inactivity

## Monitoring Your Deployment

### View Logs
```
Render Dashboard → gym-bro-api → Logs
```

### Check Metrics
```
Render Dashboard → gym-bro-api → Metrics
```

### Database Access
```
Render Dashboard → gym-bro-db → Connect
```

## Updating Your Deployment

When you push new code to GitHub:

1. Commit and push changes:
   ```bash
   git add .
   git commit -m "Update feature"
   git push origin main
   ```

2. Render automatically detects the push and redeploys
3. Watch the deploy in the Render dashboard
4. No manual intervention needed!

## Custom Domain (Optional)

To use your own domain:

1. Go to your web service in Render
2. Click **"Settings"** → **"Custom Domain"**
3. Add your domain (e.g., `api.gymbro.app`)
4. Update your DNS records as instructed
5. Render provides free SSL certificates automatically

## Next Steps

After successful deployment:

1. ✅ Update mobile app's `.env` with production URL
2. ✅ Test all API endpoints
3. ✅ Create test user account
4. ✅ Log some test workouts
5. ✅ Deploy mobile app to TestFlight / App Store

## Support

- Render Docs: https://render.com/docs
- Render Community: https://community.render.com
- Your API logs: Check Render dashboard

---

**Your Production API URL**: `https://gym-bro-api.onrender.com`

**Database Dashboard**: Render → gym-bro-db

Good luck with deployment! 💪
