# FinanceBuddy Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │   Frontend   │────▶│   Backend    │────▶│   Database   │   │
│   │   (Vercel)   │     │  (Railway)   │     │  (Supabase)  │   │
│   └──────────────┘     └──────────────┘     └──────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                     ┌──────────────┐                            │
│                     │  External    │                            │
│                     │  Services    │                            │
│                     │  - Teller    │                            │
│                     │  - Ntropy    │                            │
│                     │  - Gemini    │                            │
│                     └──────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Live URLs

| Component | URL |
|-----------|-----|
| **Frontend** | https://olivefinance.vercel.app |
| **Backend API** | https://financebuddy-backend-production.up.railway.app |
| **API Documentation** | https://financebuddy-backend-production.up.railway.app/docs |

## Platform Details

### Frontend (Vercel)
- **Framework:** Next.js 14.1.0
- **Auto-deploy:** Yes (on push to `main`)
- **Root directory:** `frontend/`

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_TELLER_APP_ID` | Teller application ID |
| `NEXT_PUBLIC_TELLER_ENV` | Teller environment (`development`) |

### Backend (Railway)
- **Framework:** FastAPI
- **Build:** Dockerfile
- **Auto-deploy:** Yes (on push to `main`)
- **Root directory:** `backend/`
- **Serverless:** Enabled (scales to zero)

**Environment Variables:**
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection (pooler) |
| `SECRET_KEY` | JWT signing key |
| `DEBUG` | Debug mode (`false` in production) |
| `TELLER_APP_ID` | Teller API app ID |
| `TELLER_ENV` | Teller environment (`development`) |
| `TELLER_CERT_PATH` | Path to Teller certificate |
| `TELLER_KEY_PATH` | Path to Teller private key |
| `NTROPY_API_KEY` | Ntropy ML enrichment API |
| `USE_NTROPY` | Enable Ntropy (`true`) |
| `GEMINI_API_KEY` | Google Gemini API |
| `USE_GEMINI` | Enable Gemini insights (`true`) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `TAVILY_API_KEY` | Tavily search API |

### Database (Supabase)
- **Type:** PostgreSQL 15
- **Connection:** Transaction pooler (port 6543)
- **Host:** `aws-0-us-west-2.pooler.supabase.com`

## Deployment Workflow

### Automatic Deployments
Both frontend and backend auto-deploy when you push to `main`:

```bash
# Make changes
git add .
git commit -m "Your changes"
git push origin main
# ✨ Both services auto-deploy
```

### Manual Deployment (if needed)

**Frontend:**
```bash
cd frontend
vercel --prod
```

**Backend:**
```bash
cd backend
railway up
```

## User Flow (New User Journey)

```
1. REGISTRATION
   └─▶ POST /api/auth/register
       └─▶ Creates user in database
       └─▶ Returns JWT tokens

2. BANK CONNECTION
   └─▶ User clicks "Connect Bank"
   └─▶ Teller Connect modal opens
   └─▶ User authenticates with bank
   └─▶ POST /institutions/teller/callback
       └─▶ Stores Teller access token
       └─▶ Syncs accounts
       └─▶ Syncs transactions

3. AUTO-ENRICHMENT (Background)
   └─▶ New transactions trigger enrichment
   └─▶ Ntropy: merchant & category detection
   └─▶ Transfer detection
   └─▶ Anomaly scoring

4. INSIGHTS GENERATION
   └─▶ GET /api/insights/daily
   └─▶ Gemini analyzes spending patterns
   └─▶ Returns personalized insights
```

## Configuration Files

### Backend

**`backend/Dockerfile`**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

**`backend/railway.json`**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Monitoring & Logs

### Railway (Backend)
- Dashboard: https://railway.com/project/d1bf5b0b-279d-4870-9b72-9de3a452d0c7
- View logs: Click service → Deployments → View logs

### Vercel (Frontend)
- Dashboard: https://vercel.com/renjialans-projects/frontend
- View logs: Functions → Select function → Logs

### Supabase (Database)
- Dashboard: https://supabase.com/dashboard (login required)
- Table editor, SQL editor, logs available

## Troubleshooting

### Backend Returns 502
1. Check Railway logs for errors
2. Common causes:
   - Database connection failed → Check `DATABASE_URL`
   - Missing env vars → Verify all required vars are set
   - Cold start (serverless) → Wait 5-10 seconds

### CORS Errors
- Ensure frontend URL is in backend's CORS allowed origins
- Check `backend/app/main.py` → `allow_origins` list

### Teller Connection Fails
- Verify `TELLER_ENV` matches on frontend and backend
- Check Teller certificate files are present in backend

### Database Connection Issues
- Use pooler connection (port 6543), not direct (port 5432)
- Check password URL encoding (`@` → `%40`)

## Security Notes

1. **Secrets:** All API keys stored as environment variables (not in code)
2. **CORS:** Restricted to specific frontend domains
3. **JWT:** Tokens expire in 30 minutes (access) / 7 days (refresh)
4. **Rate Limiting:** Enabled on auth endpoints
5. **Password Hashing:** bcrypt with 12 rounds

## Cost Estimates

| Service | Free Tier | Paid Usage |
|---------|-----------|------------|
| **Vercel** | 100GB bandwidth/month | Pay as you go |
| **Railway** | $5/month credits | ~$0.01/hour when running |
| **Supabase** | 500MB database | Pay as you go |
| **Teller** | 100 connections (dev) | Contact for pricing |
| **Ntropy** | Budget per user | ~$0.001/transaction |
| **Gemini** | 1,500 requests/day | Free |

## Useful Commands

```bash
# Check backend health
curl https://financebuddy-backend-production.up.railway.app/

# Check Railway variables
railway variables list --service <service-id>

# Check Vercel env vars
vercel env ls

# View Railway logs
railway logs --service <service-id>

# Redeploy backend
railway up --service <service-id>

# Redeploy frontend
vercel --prod
```

## Repository Structure

```
financebuddy/
├── frontend/              # Next.js frontend
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   └── lib/          # API client, utilities
│   └── package.json
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── models/       # SQLAlchemy models
│   │   └── core/         # Config, security, DB
│   ├── alembic/          # Database migrations
│   ├── Dockerfile
│   ├── railway.json
│   └── requirements.txt
└── docs/                  # Documentation
    └── DEPLOYMENT.md     # This file
```

---
*Last updated: January 15, 2026*
