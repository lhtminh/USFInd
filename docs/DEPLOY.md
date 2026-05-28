# USFind — production deployment checklist

Run-through for shipping USFind to **Railway** (containers) + **Neon**
(Postgres) + **Cloudflare R2** (images).

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

### Gemini API key
- Create a key at <https://aistudio.google.com/app/apikey> (or Cloud Console).

## 2. Railway project

Create a new Railway project, then add **three services**:

### a. `streamlit` (the app)
- Source: this repo.
- Builder: Dockerfile at `docker/Dockerfile` (context = repo root).
- Port: `8501` (Streamlit binds 0.0.0.0:8501 inside the container).
- Environment variables (Service → Variables):

  | Name | Value |
  |---|---|
  | `ENVIRONMENT` | `production` |
  | `LOG_LEVEL` | `INFO` |
  | `DATABASE_URL` | Neon main-branch connection string |
  | `QDRANT_URL` | `http://qdrant.railway.internal:6333` |
  | `QDRANT_API_KEY` | *(leave empty for internal use)* |
  | `REDIS_URL` | `redis://redis.railway.internal:6379` |
  | `GEMINI_API_KEY` | from Step 1 |
  | `R2_ENDPOINT` | from R2 |
  | `R2_ACCESS_KEY_ID` | from R2 |
  | `R2_SECRET_ACCESS_KEY` | from R2 |
  | `R2_BUCKET` | `usfind-images` |
  | `R2_PUBLIC_URL` | R2.dev or custom public URL |
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

## 3. First deploy

1. Trigger a Railway build of the `streamlit` service.
2. Wait for the Dockerfile to finish (CLIP pre-download runs once during build).
3. Generate a **public domain** on the streamlit service.
4. Visit the URL. On first request, migrations run against Neon
   (`RUN_MIGRATIONS_ON_BOOT=true`); after that succeeds once, remove the flag and redeploy.

## 4. Smoke test the live app

1. **Sign in** with an email from the sidebar.
2. **Post an item** with a photo (you should see the AI auto-description).
3. **Browse** to verify the item appears with its thumbnail (served from R2).
4. **Search** with a free-text query and confirm filter chips appear.
5. Open an item and click **Show possible matches** to exercise the 2-stage pipeline.
6. Visit **Stats** — confirm system scale, cache, and cost tiles populate.

## 5. Optional: seed and benchmark

Run once from a local shell against production (`DATABASE_URL` etc. set to the
production values):

```bash
python -m scripts.seed_data --num-items 80 --plant-matches 8
python -m scripts.benchmark --num-queries 50            # warm
python -m scripts.benchmark --num-queries 50 --flush-cache  # cold
```

The benchmark writes `docs/BENCHMARK.md` locally — commit it back so the
README can link to real numbers.

## 6. Day-2 operations

- **Logs:** Railway → service → Deployments → Logs (JSON via `configure_logging`).
- **Cost:** the `/Stats` page surfaces daily and monthly Gemini cost; aggregated from `llm_usage`.
- **Backfill failed embeddings:** if any items show `embedding_status='failed'`,
  run `python -m scripts.backfill_embeddings` against production credentials.
