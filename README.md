# SkillQuix AI API

SkillQuix is a FastAPI-based backend for resume intelligence and gig matching.
It combines LLM-driven analysis with vector similarity search and MongoDB persistence.

The API supports:
- Resume parsing from text/PDF/DOCX
- AI reflection generation
- Skill recommendation and skill impact analysis
- Gig matching and mentor matching
- User skill-gap analysis
- Activity-based clarity scoring
- Vector DB maintenance and reindexing

## 1) Tech Stack

### Backend and API
- FastAPI
- Uvicorn
- Pydantic / pydantic-settings

### AI and NLP
- OpenAI API via `openai` (AsyncOpenAI)
- LangChain / langchain-openai (used in skill recommendation flow)
- SentenceTransformer model: `BAAI/bge-base-en-v1.5` for embeddings

### Datastores
- MongoDB (via `motor` async driver)
- Qdrant vector database (via `qdrant-client`)

### Document Parsing
- `pdfplumber`
- `PyMuPDF` (`fitz`) fallback
- `python-docx`

### Scheduling and Background Work
- APScheduler (`AsyncIOScheduler`)
- FastAPI BackgroundTasks

### Deployment/Runtime
- Docker + docker-compose
- Python 3.11
- Nixpacks config included for platform deployments

## 2) High-Level Architecture

1. Client calls `/v1/*` endpoints.
2. FastAPI routers dispatch to service classes in `app/Services/*`.
3. Services call:
   - OpenAI for structured generation/scoring/matching
   - MongoDB for durable records
   - Qdrant for semantic similarity retrieval
4. Startup lifecycle in `main.py`:
   - Verifies Qdrant collection dimensions
   - Creates/recreates collections if needed
   - Initializes matching singleton
   - Starts scheduler for periodic activity score recalculation

## 3) Code Structure (Detailed)

```text
.
|- main.py                         # FastAPI entrypoint, router wiring, lifespan startup
|- Dockerfile                      # Multi-stage image build
|- docker-compose.yml              # skillquix + qdrant services
|- requirements.txt                # Python dependencies
|- runtime.txt                     # Python runtime pin (3.11.0)
|- nixpacks.toml                   # Nixpacks start command
|- app/
|  |- config/
|  |  |- settings.py               # Environment config via BaseSettings
|  |
|  |- DB/
|  |  |- mongodb/
|  |  |  |- mongodb.py             # MongoDB client wrapper + data access methods
|  |  |  |- router.py              # Mongo helper endpoint(s)
|  |  |
|  |  |- vectorDB/
|  |     |- vectordb.py            # Qdrant client, collections, search/upsert helpers
|  |     |- router.py              # Upsert/debug/reset vector routes
|  |     |- schema.py              # Request schemas for vector endpoints
|  |
|  |- moduls/
|  |  |- auth/                     # Auth module placeholder/stub area
|  |
|  |- prompt/
|  |  |- prompt.py                 # LLM prompts for all AI features
|  |
|  |- Services/
|  |  |- resume_parse/             # Resume parse API + schema + service
|  |  |- refelection/              # Reflection API + schema + service
|  |  |- recommend_skill/          # Skill recommendation API + schema + service
|  |  |- skill_impact/             # Skill impact API + schema + service
|  |  |- match_gig/                # Gig matching engine + AI domain matcher + router
|  |  |- mentor_match/             # Mentor recommendation from skill-gap embedding
|  |  |- user_skillgap/            # User vs gig skill gap analysis
|  |  |- clearity_score/           # Monthly activity scoring and cache logic
|  |
|  |- utils/
|     |- file_handler.py           # PDF/DOCX extraction utilities
|     |- cron.py                   # Scheduler startup and periodic jobs
```

## 4) Core Functionalities

### 4.1 Resume Parsing
- Endpoint accepts either:
  - direct `resume_text`, or
  - uploaded file (`pdf`/`docx`)
- File parser extracts text (including table-friendly extraction path).
- OpenAI structured output maps content into the candidate schema.
- Domain/subdomain are inferred from resume context.

### 4.2 Reflection Generation
- Uses user resume context + supplied `work_text`, `reasoning_text`, `impact_text`.
- Returns structured reflection JSON via OpenAI.

### 4.3 Skill Recommendation
- Reads user resume data from MongoDB.
- Extracts domain/subdomain/skills/summary context.
- Uses LangChain ChatOpenAI pipeline.
- Post-processes and deduplicates output skills.

### 4.4 Skill Impact
- Caches skill impact response in MongoDB by normalized lowercase skill.
- If missing, generates via OpenAI and stores it.

### 4.5 Gig Matching
- Embedding model: `BAAI/bge-base-en-v1.5`.
- Flow:
  1. Fetch user resume embedding/domain from MongoDB.
  2. Query Qdrant for similar gigs.
  3. Apply AI domain+skill relevance filtering.
  4. Save recommendations into MongoDB.
  5. Return paginated active/non-expired gigs.
- Includes admin endpoints for reindexing gig/resume/mentor vectors.

### 4.6 Mentor Matching
- Depends on existing user skill-gap analysis.
- Uses skill-gap embedding to search mentor vectors in Qdrant.
- Uses AI to select best mentor candidates.
- Enriches mentor metadata from MongoDB and stores results.

### 4.7 User Skill Gap
- Compares user resume profile against a target gig.
- Generates structured skill-gap output with OpenAI.
- Background task stores result and generated embedding in MongoDB.

### 4.8 Clarity Score (Activity Score)
- Computes current and previous month activity quality score.
- Uses OpenAI scoring with fallback heuristic logic.
- Cached with TTL (24h).
- Scheduled refresh job runs periodically via APScheduler.

### 4.9 Vector DB Operations
- Upsert embeddings for gigs/resumes/mentors.
- Reset Qdrant collections.
- Debug routes for embedding retrieval and collection inspection.

## 5) API Routes (Grouped)

All routes are mounted under `/v1`.

### Resume Parse
- `POST /v1/resume-parse`

### Reflection
- `POST /v1/refelection`

### Recommend Skill
- `POST /v1/recommend-skill/{user_id}`

### Skill Impact
- `POST /v1/skill-impact`

### Match Gig
- `POST /v1/get-embedding`
- `GET /v1/user-this-month-match-gig/{user_id}`
- `GET /v1/gigs/similar`
- `GET /v1/debug/similar/{user_id}`
- `POST /v1/admin/reindex-gigs`
- `POST /v1/admin/reindex-resume`
- `POST /v1/admin/reindex-mentor`
- `DELETE /v1/qdrant-delete/{gig_id}`
- `DELETE /v1/qdrant-delete-mentor/{mentor_id}`
- `DELETE /v1/qdrant-delete-resume/{resume_id}`
- `DELETE /v1/delete_previous_match_gig/{user_id}`

### Vector DB
- `POST /v1/upsert_gig_embedding`
- `POST /v1/upsert_resume_embedding`
- `POST /v1/upsert_mentor_embedding`
- `POST /v1/admin/reset-qdrant`
- `GET /v1/debug/qdrant-embedding/{collection}/{mongo_id}`
- `GET /v1/debug/qdrant-full/{user_id}`

### Clarity Score
- `GET /v1/clearity-score/{user_id}`
- `GET /v1/debug/clearity-logs/{user_id}`

### User Skill Gap
- `GET /v1/user_skillgap`
- `POST /v1/get_resume_by_user_id`

### Mentor Match
- `GET /v1/mentor_match`

### MongoDB Utility
- `GET /v1/get_match_score/{user_id}/{gig_id}`

## 6) Environment Variables

Create a `.env` file in repo root with:

```env
SECRET_KEY=your_secret
OPENAI_API_KEY=your_openai_api_key
MONGODB_URL=mongodb://localhost:27017
DB_NAME=skillquix
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

Notes:
- `settings.py` requires all variables above.
- Current vector DB service code also uses hardcoded defaults (`qdrant:6333`), which aligns with Docker compose networking.

## 7) Setup and Run

## Option A: Local Development (without Docker)

### Prerequisites
- Python 3.11+
- Running MongoDB instance
- Running Qdrant instance (default `localhost:6333` unless network aliasing is configured)

### Steps

1. Create and activate virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Add `.env` file as shown above.

4. Start API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

5. Open docs:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Option B: Docker Compose

### Prerequisites
- Docker Desktop

### Steps

1. Ensure `.env` exists in project root.
2. Build and run:

```bash
docker compose up --build
```

3. API will be exposed on:
- `http://localhost:8888/docs`

4. Qdrant will be exposed on:
- `http://localhost:6333`

## 8) Startup Lifecycle Details

On startup (`lifespan` in `main.py`):
- Checks Qdrant `gigs` collection dimension.
- Recreates collections if dimension mismatch is detected.
- Ensures required collections exist.
- Initializes match engine singleton.
- Starts scheduler for periodic score updates.

## 9) Important Implementation Notes

- Many routes use async execution and background tasks for non-blocking writes.
- Matching pipelines combine vector similarity and LLM-based semantic/domain filtering.
- Gig/mentor/resume vectors share a fixed vector size (768).
- Data is spread across several MongoDB collections (resume, gig, matches, skill gap, mentor match, activity log, score cache).

## 10) Known Naming and Consistency Notes

These names are currently in code and kept as-is:
- `refelection` (service/router name)
- `clearity` (score module/route naming)

You can rename later for consistency, but doing so will require route and import updates.

## 11) Quick Health Check

After startup, verify:
- `GET /` returns welcome message.
- `GET /docs` loads.
- Qdrant collections are created (`gigs`, `resumes`, `mentors`).
- One sample flow works end-to-end (resume parse -> upsert embedding -> gigs similar).
