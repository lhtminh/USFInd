# USFind — production deployment checklist

Run-through for shipping USFind. Recommended split: **Vercel** for the
Next.js frontend (free tier covers it), **Railway** for the FastAPI bridge +
Qdrant + Redis, **Neon** for Postgres, **Cloudflare R2** for images.

## 1. External services

### Neon Postgres
- Create a project in Neon → use the `main` branch for production.
- Copy the pooled connection string (looks like
  `postgresql://USER:PASSWORD@HOST.neon.tech/DB?sslmode=require`).

### Cloudflare R2
- Create a bucket named `usfind-images`.
- Enable public access (R2.dev subdomain *or* a custom domain). Note the public base URL.
- Generate an API token with R2 read/write. Note the **endpoint URL**,
  **Access Key ID**, and **Secret Access Key**.

### OpenRouter
- Sign up at <https://openrouter.ai/keys> and create a key. Free vision models
  exist today; you can override the per-tier model via env later.

## 2. Railway project (FastAPI + Qdrant + Redis)

Create a new Railway project, then add **three services**:

### a. `api` (FastAPI)
- Source: this repo.
- Builder: Dockerfile at `docker/Dockerfile` (context = repo root).
- Port: `8000` (uvicorn binds 0.0.0.0:8000 inside the container).
- Environment variables (Service → Variables):

  | Name | Value |
  |---|---|
  | `ENVIRONMENT` | `production` |
  | `LOG_LEVEL` | `INFO` |
  | `DATABASE_URL` | Neon main-branch connection string |
  | `QDRANT_URL` | `http://qdrant.railway.internal:6333` |
  | `QDRANT_API_KEY` | *(leave empty for internal use)* |
  | `REDIS_URL` | `redis://redis.railway.internal:6379` |
  | `OPENROUTER_API_KEY` | from Step 1 |
  | `OPENROUTER_BASE_URL` | *(default `https://openrouter.ai/api/v1`)* |
  | `OPENROUTER_FLASH_MODEL` | *(optional override)* |
  | `OPENROUTER_PRO_MODEL` | *(optional override)* |
  | `R2_ENDPOINT` | from R2 |
  | `R2_ACCESS_KEY_ID` | from R2 |
  | `R2_SECRET_ACCESS_KEY` | from R2 |
  | `R2_BUCKET` | `usfind-images` |
  | `R2_PUBLIC_URL` | R2.dev or custom public URL |
  | `API_CORS_ORIGINS` | your Vercel app domain, comma-separated |
  | `RUN_MIGRATIONS_ON_BOOT` | `true` (one-time, then remove) |

### b. `qdrant`
- Image: `qdrant/qdrant:v1.12.0`
- Add a volume mount for `/qdrant/storage`.
- Expose port `6333` on the internal network (no public domain).

### c. `redis`
- Image: `redis:7-alpine`
- Command override:
  `redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru`
- Add a volume mount for `/data`.
- Expose port `6379` on the internal network (no public domain).

## 3. Vercel project (Next.js)

1. **Import the repo** at https://vercel.com/new → pick this GitHub repo.
2. Set the **root directory** to `web/`.
3. Framework preset: **Next.js** (auto-detected).
4. Environment variables:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | the Railway `api` service public URL |

5. Deploy. Vercel gives you a public URL (e.g. `usfind.vercel.app`).
6. Back in Railway, set `API_CORS_ORIGINS` to that URL.

## 4. First deploy verification

1. Trigger a Railway build of the `api` service. The Dockerfile pre-downloads
   CLIP during the build, so the first request is fast.
2. After the first successful boot, remove `RUN_MIGRATIONS_ON_BOOT` (it ran
   once via the FastAPI lifespan and inserted rows into `schema_migrations`).
3. Hit the Vercel URL.
4. Walk the flow: **browse** → **item detail** → **show possible matches**
   (exercises the LLM rerank) → **search** (exercises the parse step) →
   **stats** (system counts + cache + cost + Qdrant vitals).

## 5. Optional: seed and benchmark

Run once from a local shell against production (`DATABASE_URL` etc. set to the
production values):

```bash
python -m scripts.seed_data --num-items 80 --plant-matches 8
python -m scripts.benchmark --num-queries 50                # warm
python -m scripts.benchmark --num-queries 50 --flush-cache  # cold
```

The benchmark writes `docs/BENCHMARK.md` locally — commit it back so the
README can link to real numbers.

## 6. Day-2 operations

- **Logs:** Railway → service → Deployments → Logs (JSON via `configure_logging`).
- **Cost:** the `/stats` page in Vercel surfaces daily and monthly LLM cost.
- **Backfill failed embeddings:** if any items show `embedding_status='failed'`,
  run `python -m scripts.backfill_embeddings` against production credentials.
- **Auto-generated API docs:** `https://<api-domain>/docs` (FastAPI's Swagger UI).
