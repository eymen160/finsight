# FinSight — Deployment Guide (3 Steps)

## Step 1 — Deploy Backend to Render

1. Go to: https://render.com/deploy?repo=https://github.com/eymen160/finsight
   OR manually: render.com → New → Web Service → eymen160/finsight
2. Settings:
   - Environment: Docker
   - Dockerfile Path: ./Dockerfile
   - Instance Type: Free
3. Add ONE environment variable manually:
   - Key:   ANTHROPIC_API_KEY
   - Value: sk-ant-... (your key)
4. Click Deploy → wait for: https://finsight-api.onrender.com/health → {"status":"ok"}

## Step 2 — Deploy Frontend to Vercel

1. Go to: https://vercel.com/new
2. Import: eymen160/finsight
3. ROOT DIRECTORY: finsight-web  ← CRITICAL
4. Add environment variable:
   - Key:   NEXT_PUBLIC_API_URL
   - Value: https://YOUR-RENDER-URL.onrender.com
5. Deploy → get URL: https://finsight-eymen160.vercel.app

## Step 3 — Connect them (CORS update)

1. Go to Render Dashboard → finsight-api → Environment
2. Update: CORS_ALLOWED_ORIGINS = https://finsight-eymen160.vercel.app
3. Click "Save Changes" → Manual Deploy

## Done! Test with:
- https://YOUR-RENDER-URL.onrender.com/health
- https://finsight-eymen160.vercel.app

## Keep Render alive (Free Tier):
- Go to: https://uptimerobot.com
- Create monitor → HTTP → URL: https://YOUR-RENDER-URL.onrender.com/health
- Interval: 5 minutes
