# Project: USFind

A lost-and-found platform for USF students with a production-grade AI retrieval pipeline:
2-stage retrieval (Qdrant vector recall → LLM re-ranking), multi-modal embeddings, cached inference.

## Stack
- Frontend: Next.js 16 (App Router, TypeScript) + Tailwind v4 + shadcn (base-ui)
- API: FastAPI (Python 3.11) — thin REST bridge over /app/core/*
- Relational DB: PostgreSQL 15 on Neon (with psycopg 3)
- Vector DB: Qdrant (Docker, port 6333)
- Cache: Redis 7 (Docker, port 6379)
- Object storage: Cloudflare R2 (S3-compatible) for item images
- Embeddings: CLIP (clip-vit-base-patch32 via HuggingFace transformers)
- LLM: OpenRouter (OpenAI-compatible) — flash model for cheap calls, vision model for re-ranking
- Deploy: Vercel (Next.js), Railway (FastAPI + Qdrant + Redis), Neon (Postgres), R2 (images)

## Project structure
- /web                       # Next.js frontend (App Router)
  - app/                     # pages
  - components/              # shadcn + custom components
  - lib/                     # api client, formatters, mock data
- /api                       # FastAPI bridge
  - main.py                  # app + CORS + static images + lifespan
  - routers/                 # items, matches, search, stats
  - schemas.py               # API response shapes
- /app                       # Reusable Python core (consumed by api/ and scripts/)
  - core/
    - db.py                  # Postgres helpers (psycopg 3)
    - vectors.py             # Qdrant client + ops
    - embeddings.py          # CLIP image + text encoders
    - cache.py               # Redis helpers
    - llm.py                 # OpenRouter (OpenAI-compatible) client
    - storage.py             # R2 / local image storage abstraction
    - retrieval.py           # 2-stage retrieval pipeline
    - items.py               # create_item + confirm_match + backfill
    - auto_description.py    # Gemini Vision auto-describe
    - metrics.py             # in-process latency window
    - cost_tracking.py       # aggregations over llm_usage
    - config.py              # Pydantic Settings (validated at startup)
    - logging_config.py      # JSON / human-readable formatters
  - prompts/                 # LLM prompts as .txt files
  - migrations/              # SQL migration files (psycopg applies them)
- /scripts                   # benchmarks, seeders, backfills
- /tests                     # pytest
- /docker
  - docker-compose.yml       # local dev (qdrant + redis)
  - Dockerfile               # for FastAPI deploy on Railway
- /data                      # local dev only (gitignored)
- requirements.txt
- README.md, NOTES.md, .env.example

## Conventions
- Python 3.11, type hints on every function
- Format with black, lint with ruff, line length 100
- Production-grade code only — no placeholders, stubs, or TODO comments
- All secrets via env vars, validated at startup via /app/core/config.py
- All external I/O (Postgres, Qdrant, Redis, LLM, R2) wrapped with retry + descriptive errors
- Structured logging via Python logging with JSON formatter in production
- SQL: parameterized queries only, snake_case, raw SQL via psycopg (no ORM)
- pathlib.Path for filesystem paths

## Performance targets
- Vector recall (Qdrant): p95 < 100ms for top-50 over ~1000 items
- Embedding generation: p95 < 1.5s per image, < 200ms per text
- End-to-end retrieval (recall + rerank): p95 < 4s
- Redis cache hit rate: > 80% on warm workload

## Environments
- Local: docker-compose for Qdrant + Redis, Neon dev branch for Postgres, local filesystem for images
- Production: Railway containers, Neon main branch, Cloudflare R2 for images

## History
The project was first prototyped in Streamlit (commits `2da3162` … `a8c2343`), then
rewritten on Next.js + shadcn with a FastAPI bridge over the same /app/core/* modules.
The Streamlit prototype is preserved in git history.
