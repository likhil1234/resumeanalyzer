# Resume Analyzer & Job Matcher

A full-stack Flask application that analyzes PDF/DOCX resumes, optionally matches them against a job description, stores resume versions in **PostgreSQL** (client-server database), and provides an AI Resume Assistant.

## Features
- PDF and DOCX upload
- Resume text extraction
- Section detection: summary, skills, education, projects, experience, certifications
- Skill extraction and ATS-style checks
- Optional job description
- TF-IDF + cosine similarity match score
- Matching/missing skills and keywords
- Role/project suggestions
- **PostgreSQL resume storage** (works with free hosted databases)
- Resume version history
- Context-aware AI Resume Assistant
- AI rewrite actions for summary/projects/skills/experience
- Works without an AI API for core analysis
- Optional Ollama local AI (free and local)
- Optional OpenAI-compatible cloud API

## Requirements
- Python 3.10+
- A free PostgreSQL database (see below)
- Optional: Ollama for the AI assistant

## Free PostgreSQL options (recommended)

You need a real client-server database that can be accessed from the internet. These are free:

### 1. Neon (recommended – easiest)
1. Go to https://neon.tech and create a free account
2. Create a new project
3. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Paste it into `DATABASE_URL` in your `.env`

### 2. Supabase
1. Go to https://supabase.com → New project
2. Project Settings → Database → Connection string (URI)
3. Use the “Connection pooling” or direct connection string
4. Put it in `DATABASE_URL`

### 3. Render Postgres
1. On Render, create a new PostgreSQL service (free tier available)
2. Copy the **External Database URL**
3. Put it in `DATABASE_URL`

## Backend setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and set DATABASE_URL to your free Postgres URL
python app.py
```

Backend runs at `http://127.0.0.1:5000`.

The `resumes` table is created automatically on first successful connection.

## Frontend

Open `frontend/index.html` directly, or serve it:

```bash
cd frontend
python -m http.server 5500
```

Then open `http://127.0.0.1:5500`.

## Environment variables

```env
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
PORT=5000
AI_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
CORS_ORIGINS=*
```

## AI assistant

### Option A: Ollama (recommended for free/local use)
```bash
ollama pull llama3.2
```
```env
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

### Option B: OpenAI-compatible endpoint
```env
AI_PROVIDER=openai_compatible
AI_API_KEY=your_key
AI_BASE_URL=https://your-provider.example/v1
AI_MODEL=your-model
```

## API endpoints
- `GET /api/health`
- `POST /api/resumes/analyze`
- `GET /api/resumes`
- `GET /api/resumes/<id>`
- `DELETE /api/resumes/<id>`
- `POST /api/match`
- `POST /api/chat`
- `POST /api/rewrite`

## Production notes
- Keep `DATABASE_URL` and AI keys only in server environment variables.
- Restrict CORS to your frontend domain.
- Store uploads in object storage rather than local disk.
- Add authentication before making stored resumes private.
- Add rate limiting to AI endpoints.

## Deploying the API
Works well on Render, Railway, Fly.io, etc.
Just set the `DATABASE_URL` environment variable to your free Postgres connection string.
