# Viral Content Tracker

A SaaS application that automatically discovers trending TikTok and Instagram videos, transcribes them, and exports everything to Google Sheets.

## Features

- 🔍 **Automated Discovery**: Scrapes TikTok and Instagram for trending content by keyword
- 🎯 **Customizable Keywords**: Set your own keywords per industry/niche
- 📝 **AI Transcription**: Uses Faster-Whisper to transcribe video audio locally
- 📊 **Google Sheets Export**: Automatically populates your sheet with videos + transcripts
- 👥 **Multi-tenant**: Each client gets their own account, keywords, and connected sheet
- 📅 **Scheduled Runs**: Set up daily/weekly automated scraping

## Tech Stack

- **Backend**: Python + FastAPI
- **Database**: PostgreSQL
- **Transcription**: Faster-Whisper (local AI)
- **Scraping**: Apify (TikTok/Instagram actors)
- **Sheets**: Google Sheets API
- **Auth**: JWT tokens

---

## Quick Start (Local Development)

### 1. Prerequisites

- Python 3.10+
- PostgreSQL database
- Apify account (for scraping)
- Google Cloud service account (for Sheets)

### 2. Clone and Install

```bash
cd viral-content-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
```

Required environment variables:

```
DATABASE_URL=postgresql://user:password@localhost:5432/viral_tracker
SECRET_KEY=generate-a-random-secret-key-here
APIFY_API_TOKEN=your-apify-token
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
```

### 4. Database Setup

```bash
# Create PostgreSQL database
createdb viral_tracker

# Tables are created automatically on first run
```

### 5. Google Sheets Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Google Sheets API and Google Drive API
4. Create a Service Account
5. Download the JSON key file
6. Save as `service-account.json` in project root
7. Share your Google Sheet with the service account email

### 6. Apify Setup

1. Sign up at [apify.com](https://apify.com)
2. Get your API token from Settings
3. Add token to `.env`

### 7. Run the Server

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

---

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Get access token
- `GET /api/auth/me` - Get current user

### Keywords
- `GET /api/keywords` - List keywords
- `POST /api/keywords` - Add keyword
- `POST /api/keywords/bulk` - Add multiple keywords
- `POST /api/keywords/presets/{industry}` - Load preset keywords
- `DELETE /api/keywords/{id}` - Delete keyword

### Jobs
- `POST /api/jobs/scrape` - Start scraping job
- `GET /api/jobs` - List recent jobs
- `POST /api/jobs/transcribe-all` - Transcribe pending videos
- `GET /api/jobs/dashboard/stats` - Get dashboard stats

### Videos
- `GET /api/videos` - List videos
- `GET /api/videos/top` - Get top performing videos
- `GET /api/videos/search?q=` - Search transcripts
- `GET /api/videos/stats/by-platform` - Stats by platform

### Settings
- `GET /api/settings` - Get user settings
- `PUT /api/settings` - Update settings
- `POST /api/settings/connect-sheet` - Connect Google Sheet

---

## Deploying to Production

### Option 1: Railway (Recommended for you)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. Create new project from GitHub repo
4. Add PostgreSQL plugin
5. Set environment variables in Railway dashboard
6. Deploy automatically

### Option 2: Render

1. Go to [render.com](https://render.com)
2. Create Web Service from GitHub repo
3. Create PostgreSQL database
4. Set environment variables
5. Deploy

---

## Client Onboarding Flow

1. Client signs up at your app URL
2. They create a Google Sheet and share it with your service account email
3. They enter the Sheet ID in Settings
4. They choose preset keywords or add custom ones
5. System runs daily, populating their sheet

---

## Preset Keyword Industries

The app comes with preset keywords for common niches:

- **ai_automation**: AI, ChatGPT, Claude, N8N, Vibecoding, etc.
- **ecommerce**: Dropshipping, Shopify, Amazon FBA
- **real_estate**: Investing, flipping, rentals
- **fitness**: Workouts, nutrition, weight loss
- **finance**: Investing, crypto, passive income

Load via API:
```
POST /api/keywords/presets/ai_automation?platform=tiktok
```

---

## Monthly Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Apify | ~$49/mo | Handles ~10k scrapes |
| Railway/Render | ~$7-20/mo | Server hosting |
| PostgreSQL | ~$7-15/mo | Managed database |
| Whisper | Free | Runs on server |
| **Total** | **~$60-85/mo** | For unlimited clients |

---

## Pricing Suggestions for Your Clients

- **Starter**: $47/mo - 5 keywords, 1 platform
- **Pro**: $97/mo - 20 keywords, both platforms  
- **Agency**: $197/mo - Unlimited keywords, API access

**Example**: 10 clients on Pro = $970/mo revenue vs ~$80 costs = **$890 profit**

---

## Next Steps

1. Download and unzip this project
2. Set up accounts (Apify, Google Cloud)
3. Deploy to Railway or Render
4. Build the React frontend (I can help with this next)
5. Start onboarding clients!

---

## Need Help?

The frontend dashboard (React) can be built next. It will include:
- Login/Signup pages
- Dashboard with stats
- Keyword management
- Video browser with transcripts
- Settings page

Let me know when you're ready to build the frontend!
