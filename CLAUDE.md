# Project: USFind

A lost-and-found platform for USF students with a production-grade AI retrieval pipeline:
2-stage retrieval (Qdrant vector recall → Gemini LLM re-ranking), multi-modal embeddings, cached inference.

## Stack
- UI: Streamlit (Python 3.11)
- Relational DB: PostgreSQL 15 on Neon (with psycopg 3)
- Vector DB: Qdrant (Docker, port 6333)
- Cache: Redis 7 (Docker, port 6379)
- Object storage: Cloudflare R2 (S3-compatible) for item images
- Embeddings: CLIP (clip-vit-base-patch32 via HuggingFace transformers)
- LLM: Google Gemini (gemini-2.0-flash for cheap calls, gemini-2.5-pro for re-ranking)
- Deploy: Railway (Streamlit + Qdrant + Redis containers), Neon (Postgres), R2 (images)

## Project structure
- /app
  - streamlit_app.py        # entry point
  - pages/                  # Streamlit pages
  - core/
    - db.py                 # Postgres helpers (psycopg 3)
    - vectors.py            # Qdrant client + ops
    - embeddings.py         # CLIP image + text encoders
    - cache.py              # Redis helpers
    - llm.py                # Gemini client
    - storage.py            # R2 / local image storage abstraction
    - retrieval.py          # 2-stage retrieval pipeline
  - prompts/                # Gemini prompts as .txt files
  - migrations/             # SQL migration files (psycopg applies them)
- /scripts                  # benchmarks, seeders, backfills
- /tests                    # pytest
- /docker
  - docker-compose.yml      # local dev (qdrant + redis)
  - Dockerfile              # for Streamlit deploy on Railway
- /data                     # local dev only (gitignored)
- requirements.txt
- README.md, NOTES.md, .env.example

## Conventions
- Python 3.11, type hints on every function
- Format with black, lint with ruff, line length 100
- Production-grade code only — no placeholders, stubs, or TODO comments
- All secrets via env vars, validated at startup via /app/core/config.py
- All external I/O (Postgres, Qdrant, Redis, Gemini, R2) wrapped with retry + descriptive errors
- Structured logging via Python logging with JSON formatter in production
- SQL: parameterized queries only, snake_case, raw SQL via psycopg (no ORM)
- pathlib.Path for filesystem paths

## Performance targets
- Vector recall (Qdrant): p95 < 100ms for top-50 over ~1000 items
- Embedding generation: p95 < 1.5s per image, < 200ms per text
- End-to-end retrieval (recall + rerank): p95 < 4s
- Redis cache hit rate: > 80% on warm workload
- Streamlit page load (cold): < 3s

## Environments
- Local: docker-compose for Qdrant + Redis, Neon dev branch for Postgres, local filesystem for images
- Production: Railway containers, Neon main branch, Cloudflare R2 for images