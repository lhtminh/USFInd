# USFind 🎒

> Lost & Found for USF students, powered by a production-grade 2-stage AI retrieval pipeline.

## 🔗 Live demo

- **App:** _(deploy the Next.js frontend to Vercel and add the URL — see [`docs/DEPLOY.md`](docs/DEPLOY.md))_
- **Demo video:** _(record a 60–90s Loom and paste here)_
- **GitHub:** this repo

## 🎯 What it does

Students post photos of items they've **lost** or **found**. The system embeds
each item with multi-modal CLIP, then for any query item runs a two-stage
retrieval pipeline that surfaces the most likely matches with plain-language
explanations:

1. **Stage 1 — Vector recall** (Qdrant HNSW): parallel image + text search,
   weighted fusion (0.7 / 0.3), top 50 in under a tenth of a second.
2. **Stage 2 — LLM re-ranking** (vision-language model via OpenRouter): the
   top 20 go to a vision model with both query and candidate images. It
   returns a 0–100 score and a one-sentence justification per candidate.

A conversational search mode parses free text ("I lost a blue water bottle near
the library yesterday") into structured filters and runs the same rerank on
text-only candidates. A Vision auto-description pre-fills the post form from
the photo. All LLM calls flow through a 3-layer Redis cache.

## 🏗️ Architecture

```
Next.js 16 (App Router)  ──→  FastAPI  ──→  Postgres (Neon)
       (Vercel)                 (Railway)   ├──→  Qdrant (HNSW vector search)
                                            ├──→  Redis (3-layer cache)
                                            ├──→  OpenRouter (vision LLM rerank)
                                            └──→  Cloudflare R2 (image storage)
```

## 🧠 The AI pipeline (the heart of this project)

**Stage 1 — Vector recall.**
CLIP image and text embeddings (512-dim, L2-normalized) sit in two Qdrant
collections with HNSW (`m=16`, `ef_construct=128`). Each query item triggers
two parallel cosine searches; the per-source scores are fused
`0.7 * image + 0.3 * text` and the top 50 after a 0.45 threshold proceed.

**Stage 2 — LLM re-ranking.**
The top 20 candidates go to a vision/reasoning LLM (default
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` via OpenRouter) with the
query image, candidate images, and metadata. A JSON response schema returns
`{candidate_index, rerank_score 0-100, explanation}`. Anything under 40 is
dropped; the final top 10 are returned sorted by score.

**Why this architecture?**
Recall-then-rerank is the standard pattern for YouTube, Spotify, and modern
retrieval systems. Vector search is fast but imprecise; LLM rerank is precise
but slow and expensive. Combining them gives both speed and quality, and the
24-hour rerank cache (keyed on the query's `updated_at` + sorted candidate ids)
makes repeat lookups near-instant.

## ⚡ Performance

_Numbers below are filled in by `python -m scripts.benchmark`; see
[`docs/BENCHMARK.md`](docs/BENCHMARK.md) for the report._

| Metric | Target | Latest |
|---|---:|---:|
| Stage 1 p95 (Qdrant recall) | < 100 ms | _TBD_ |
| Stage 2 p95 (LLM rerank) | — | _TBD_ |
| End-to-end p95 | < 4 s | _TBD_ |
| Rerank cache hit rate (warm) | ≥ 80 % | _TBD_ |

## ✨ AI features

1. **Auto-description from photo** (vision LLM) — pre-fills item
   descriptions on upload; original AI output preserved in `items.ai_description`.
2. **Conversational search** (LLM + CLIP) — `"I lost a blue water bottle
   near the library yesterday"` → structured filter chips + semantic search +
   LLM rerank with explanations.
3. **2-stage retrieval with explanations** (CLIP + Qdrant + LLM) —
   the matches page shows confidence bars and a one-sentence reason per match.

## 📦 Tech stack

| Component | Choice | Why |
|---|---|---|
| Frontend | Next.js 16 + Tailwind v4 + shadcn (base-ui) | Modern App Router, polished components, fast iteration |
| Frontend host | Vercel | Native Next.js deployment, edge network |
| API | FastAPI | Type-safe, fast, auto-generated OpenAPI |
| Relational DB | Postgres on Neon | Free dev branches, scales, raw SQL via psycopg 3 |
| Vector DB | Qdrant | HNSW, payload filters, scales to millions |
| Cache | Redis | Sub-ms reads for embedding + LLM + rerank caches |
| Image storage | Cloudflare R2 | S3-compatible, zero egress fees |
| Embeddings | CLIP (HuggingFace) | Multi-modal (image + text in the same space), local inference |
| LLM | OpenRouter | Unified gateway: free vision models today, swap to paid via env var |
| Backend host | Railway | Multi-service Docker, internal networking |

## 🚀 Local development

```bash
# Prereqs: Docker, Python 3.11, Node 20+, a Neon connection string, an OpenRouter key
cp .env.example .env                  # fill in DATABASE_URL, OPENROUTER_API_KEY, R2_* (placeholders fine for dev)
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # Windows; use source ./venv/bin/activate on macOS/Linux
pip install -r requirements.txt -r requirements-dev.txt
cd web && npm install && cd ..        # install web/ once

make up                               # bring up Qdrant + Redis
make api                              # uvicorn api.main:app --reload → http://localhost:8000
make web                              # next dev (in another shell) → http://localhost:3000
make seed                             # optional: seed demo data + planted match pairs
make benchmark                        # optional: write docs/BENCHMARK.md
make test                             # full pytest (db tests skip without Postgres reachable)
make fmt                              # black + ruff --fix
```

## 🧪 Testing

The full pytest suite covers each `/app/core` module (db, vectors, embeddings,
cache, storage, llm, retrieval, items, auto-description, cost tracking). Most
tests run offline (in-memory Qdrant, fakeredis, moto, mocked OpenRouter
client); the db/item/retrieval pipelines run against a real Neon dev branch
(skipped gracefully without one). The Next.js side type-checks via
`npm run build`.

## 🗂️ Project structure

```
web/
  app/                   Next.js routes (App Router)
  components/            shadcn + site-header / site-footer / item-card
  lib/                   typed API client, mock-data (for /post + /me until auth)

api/
  main.py                FastAPI app, CORS, static images, lifespan
  routers/               items, matches, search, stats
  schemas.py             API response shapes

app/
  core/
    db.py                Postgres helpers (psycopg 3, pool, migrations, typed queries)
    vectors.py           Qdrant client + collections + filters
    embeddings.py        CLIP image + text encoders
    cache.py             Redis 3-layer cache
    storage.py           Local + R2 image storage
    llm.py               OpenRouter (OpenAI-compatible) wrappers with retry, cost logging
    retrieval.py         2-stage retrieval, rerank cache, conversational search
    items.py             create_item + confirm_match + backfill
    auto_description.py  Vision LLM auto-describe
    metrics.py           in-process latency window
    cost_tracking.py     aggregations over llm_usage
    config.py            Pydantic Settings (validated at startup)
    logging_config.py    JSON / human-readable formatters
  prompts/               LLM prompts as .txt
  migrations/            .sql migrations applied by db.run_migrations
scripts/                 seed_data, benchmark, backfill_embeddings
tests/                   pytest
docker/                  Dockerfile, docker-compose.yml
docs/                    DEPLOY.md, BENCHMARK.md, CLAUDE.md, prompt sequence, RESUME.md
```

## 🕰️ Project history

USFind was first prototyped end-to-end in **Streamlit** (commits `2da3162` …
`a8c2343` in git history) — full pages for posting, browsing, matches, search,
and an observability dashboard, on top of the same `app/core/*` modules. It
was later rewritten on **Next.js 16 + shadcn** with a thin **FastAPI bridge**
over the same Python core, so the AI retrieval logic was reused verbatim. The
Streamlit prototype is preserved in git history; only the FastAPI + Next.js
stack ships today.

## 🔮 Future work

- Auth (NextAuth magic link) + write endpoints (`POST /api/items`, confirm match).
- More expressive match confirmation (in-app messaging instead of email exchange).
- Multi-image items.
- A periodic re-index job for items whose embeddings drift after model updates.

## 📜 License

MIT
