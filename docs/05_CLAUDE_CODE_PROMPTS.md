# USFind — Claude Code Prompts (AI-Focused, Deployable)

Stack: Streamlit + Postgres + Qdrant + Redis + CLIP + Gemini, deployed on Railway + Neon + Cloudflare R2.

Copy-paste each prompt into Claude Code. Run sequentially. Commit after each.

---

## CLAUDE.md (drop in repo root before starting)

```markdown
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
```

---

## Setup

```
Scaffold the USFind project per CLAUDE.md:

- Create all directories per the structure above
- Empty __init__.py in each /app subdir
- requirements.txt with pinned versions: streamlit==1.39.0, qdrant-client==1.12.0, redis==5.1.0, transformers==4.45.0, torch==2.4.1, torchvision==0.19.1, pillow==10.4.0, google-generativeai==0.8.3, psycopg[binary,pool]==3.2.3, boto3==1.35.36, python-dotenv==1.0.1, numpy==1.26.4, pydantic==2.9.2, pytest==8.3.3, black==24.10.0, ruff==0.7.0
- .env.example with all variables: GEMINI_API_KEY, DATABASE_URL (Neon Postgres URL), QDRANT_URL=http://localhost:6333, QDRANT_API_KEY (empty for local), REDIS_URL=redis://localhost:6379, R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET=usfind-images, R2_PUBLIC_URL (for serving), LOG_LEVEL=INFO, ENVIRONMENT=local
- .gitignore covering Python, /data/, .env, .venv, __pycache__, .pytest_cache, .ruff_cache
- pyproject.toml with black + ruff config (line length 100, target-version py311)
- /app/core/config.py — Pydantic Settings model that loads env vars and validates at startup (raises clear errors for missing values)
- /app/core/logging_config.py — JSON-structured logging when ENVIRONMENT=production, human-readable when local
- README.md skeleton
- NOTES.md empty

Initialize git. Make initial commit.
```

---

## Docker setup (local dev only)

```
Create /docker/docker-compose.yml that runs Qdrant + Redis for local dev (Postgres lives on Neon, not in Docker):

services:
  qdrant:
    image: qdrant/qdrant:v1.12.0
    ports: ["6333:6333", "6334:6334"]
    volumes: ["./data/qdrant:/qdrant/storage"]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["./data/redis:/data"]
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    restart: unless-stopped

Add a Makefile at the repo root:
- make up        # docker compose -f docker/docker-compose.yml up -d
- make down      # docker compose -f docker/docker-compose.yml down
- make logs      # docker compose -f docker/docker-compose.yml logs -f
- make reset     # stop + delete volumes + restart
- make run       # streamlit run app/streamlit_app.py
- make test      # pytest
- make fmt       # black . && ruff check --fix .

Output the exact first-time setup commands in order, including how to create a Neon project + dev branch and grab the connection string.
```

---

# WEEK 1 — Core infrastructure

## 1.1 Postgres schema + migration runner

```
Create /app/migrations/001_initial.sql:

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('lost', 'found')),
  title TEXT NOT NULL CHECK (length(title) <= 200),
  description TEXT CHECK (length(description) <= 2000),
  ai_description TEXT,
  image_url TEXT NOT NULL,
  image_key TEXT NOT NULL,
  location TEXT CHECK (length(location) <= 200),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'matched', 'closed')),
  embedding_status TEXT NOT NULL DEFAULT 'pending' CHECK (embedding_status IN ('pending', 'ready', 'failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  item_a_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  item_b_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
  confirmed_by_user_id UUID NOT NULL REFERENCES users(id),
  combined_score REAL NOT NULL,
  rerank_score REAL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(item_a_id, item_b_id)
);

CREATE INDEX idx_items_user ON items(user_id);
CREATE INDEX idx_items_type_status ON items(type, status);
CREATE INDEX idx_items_created_at_desc ON items(created_at DESC);
CREATE INDEX idx_items_embedding_status ON items(embedding_status);
CREATE INDEX idx_matches_item_a ON matches(item_a_id);
CREATE INDEX idx_matches_item_b ON matches(item_b_id);

CREATE TABLE schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER items_updated_at BEFORE UPDATE ON items
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

Then create /app/core/db.py with psycopg 3:

- get_pool() returning a module-level psycopg_pool.ConnectionPool (min_size=2, max_size=10), reads DATABASE_URL from config
- @contextmanager get_conn() yielding a connection from the pool with autocommit=False
- run_migrations() — applies any .sql files in /app/migrations not yet in schema_migrations table, in filename order, each in its own transaction
- Typed helpers (return TypedDict or Pydantic models):
  - insert_item(user_id, type, title, description, image_url, image_key, location) -> Item
  - get_item(item_id) -> Item | None
  - list_items(type: Optional[str], status: str = 'open', limit: int = 20, offset: int = 0) -> list[Item]
  - update_item_status(item_id, status)
  - update_embedding_status(item_id, status)
  - upsert_user(email, name) -> User
  - insert_match(item_a_id, item_b_id, confirmed_by, combined_score, rerank_score) -> Match
  - list_user_items(user_id) -> list[Item]

All queries use $1, $2 parameterization. Add retry decorator (3 attempts) on connection errors. Add pytest tests using a test database (create/teardown schema per test class).
```

## 1.2 Qdrant client wrapper

```
Create /app/core/vectors.py:

- Lazy singleton qdrant_client.QdrantClient connecting to QDRANT_URL with optional QDRANT_API_KEY (for Qdrant Cloud later if needed)
- On import / first use, ensure collections exist (idempotent):
  - "items_image": vectors size 512, distance Cosine, on_disk_payload=True
  - "items_text": same shape
- HNSW config: m=16, ef_construct=128, full_scan_threshold=10000
- Payload indexes on both: type (keyword), status (keyword), created_at_ts (integer)
- Use UUID point IDs matching items.id

Functions:
- upsert_image_embedding(item_id: UUID, vector: np.ndarray, payload: dict)
- upsert_text_embedding(item_id: UUID, vector: np.ndarray, payload: dict)
- get_embeddings(item_id: UUID) -> tuple[np.ndarray | None, np.ndarray | None]  # (image, text)
- search_image(query_vector, qdrant_filter, limit) -> list[ScoredPoint]
- search_text(query_vector, qdrant_filter, limit) -> list[ScoredPoint]
- delete_item(item_id: UUID)
- build_filter(item_type=None, status=None, created_after_ts=None, exclude_item_id=None) -> qdrant_client.models.Filter
- collection_stats() -> dict (point counts, indexed status, used in /stats page)

All operations include retry (3x exponential backoff) on connection errors. Add pytest tests using qdrant in-memory mode (:memory: location).
```

## 1.3 CLIP embedding module

```
Create /app/core/embeddings.py:

- Load openai/clip-vit-base-patch32 model + processor ONCE on first call (thread-safe singleton with threading.Lock)
- Auto-detect CUDA, fall back to CPU; log device on first load
- model.eval(), torch.inference_mode() for all forward passes

Functions:
- embed_image(image: PIL.Image | bytes | Path) -> np.ndarray (float32, shape (512,), L2-normalized)
- embed_text(text: str) -> np.ndarray (float32, shape (512,), L2-normalized)
- embed_image_batch(images: list, batch_size: int = 8) -> np.ndarray (shape (N, 512))
- embed_text_batch(texts: list, batch_size: int = 32) -> np.ndarray (shape (N, 512))

For text: truncate to 77 tokens silently (CLIP limit), log warning if truncation happens.
For image: convert to RGB if needed, resize via processor's image_processor.

All errors raise EmbeddingError(BaseException) with descriptive messages.
Log inference latency at DEBUG level. Add a module-level counter for total inferences (visible in stats page).

Add pytest tests:
- Output shape (512,), dtype float32
- L2 norm is ~1.0 within tolerance
- Identical inputs produce bit-identical outputs (with deterministic seed)
- Batch outputs match individual calls
```

## 1.4 Redis cache layer

```
Create /app/core/cache.py:

- Lazy singleton redis.Redis client from REDIS_URL, decode_responses=False (we store binary)
- Cache key conventions:
  - emb:img:{sha256_of_image_bytes_hex} → pickled np.ndarray
  - emb:txt:{sha256_of_text_hex} → pickled np.ndarray
  - llm:{sha256_of_prompt_payload_hex} → JSON-encoded response dict
- TTLs (constants at top of file): EMB_TTL = 30 days, LLM_TTL = 7 days

Functions:
- get_cached_image_embedding(image_bytes: bytes) -> np.ndarray | None
- set_cached_image_embedding(image_bytes: bytes, vector: np.ndarray)
- get_cached_text_embedding(text: str) -> np.ndarray | None
- set_cached_text_embedding(text: str, vector: np.ndarray)
- get_cached_llm(prompt_payload: dict) -> dict | None
- set_cached_llm(prompt_payload: dict, response: dict)
- cache_stats() -> dict {image_hits, image_misses, text_hits, text_misses, llm_hits, llm_misses}

All Redis ops wrapped in try/except — on Redis failure, log warning at WARNING level and return None (graceful degradation, app keeps working without cache). Track hit/miss counters in-process (module-level dict, thread-safe with Lock).

Wire cache into embeddings.py: embed_image() and embed_text() check cache first by content hash, populate on miss.

Add pytest tests using fakeredis.
```

## 1.5 R2 / image storage abstraction

```
Create /app/core/storage.py with an interface that swaps between local filesystem and Cloudflare R2 based on config.ENVIRONMENT:

class ImageStorage(Protocol):
    def upload(self, key: str, image_bytes: bytes, content_type: str) -> str: ...  # returns public URL
    def delete(self, key: str) -> None: ...
    def get_url(self, key: str) -> str: ...

Implementations:
- LocalImageStorage: saves under ./data/images/{key}, serves via Streamlit static files
- R2ImageStorage: uses boto3 with R2 endpoint, uploads to R2_BUCKET, returns f"{R2_PUBLIC_URL}/{key}"

Factory: get_storage() returns LocalImageStorage if ENVIRONMENT=local else R2ImageStorage.

Helper: process_uploaded_image(uploaded_file, user_id, item_id) -> (image_bytes, key, content_type):
- Validate: max 5MB, content types image/jpeg, image/png, image/webp
- Resize images larger than 1600px on longest side via Pillow LANCZOS, preserve aspect ratio
- Re-encode: JPEG quality 88 if RGB, PNG if RGBA
- Generate key: f"items/{user_id}/{item_id}.{ext}"
- Return processed bytes, key, content type

Add pytest tests for both implementations (moto for R2 mock, tmpdir for local).
```

## 1.6 Gemini LLM client

```
Create /app/core/llm.py:

- Configure google.generativeai with GEMINI_API_KEY at module load
- Two model wrappers (both accept text + PIL.Image inputs):
  - call_flash(parts: list, system_instruction: str | None, response_schema: dict | None = None, max_output_tokens: int = 1024) -> dict
    Uses gemini-2.0-flash
  - call_pro(parts: list, system_instruction: str | None, response_schema: dict | None = None, max_output_tokens: int = 2048) -> dict
    Uses gemini-2.5-pro

Both:
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s) on rate limit (429) and 5xx errors
- Timeout 60s
- When response_schema provided, use Gemini's response_mime_type='application/json' with response_schema
- Log every call: model, prompt token count, output token count, latency, estimated cost (USD)
- Return parsed JSON if response_schema, else raw text in {"text": ...}

Cached variants:
- cached_call_flash(...) and cached_call_pro(...) check Redis llm cache before calling

Helpers:
- estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float
  Use current Gemini pricing: flash $0.075/1M input, $0.30/1M output; pro $1.25/1M input, $5.00/1M output

All errors raise LLMError. Add pytest tests with mocked SDK.
```

---

# WEEK 2 — Item posting + embedding pipeline

## 2.1 Item creation pipeline

```
Create /app/core/items.py with create_item(user_id, type, title, description, location, uploaded_file) -> Item:

Pipeline:
1. Generate UUID for item_id
2. Process image via storage.process_uploaded_image → (image_bytes, key, content_type)
3. Upload image to storage backend → public URL
4. INSERT into Postgres items table with embedding_status='pending'
5. Generate image_embedding via embeddings.embed_image(image_bytes) (cached)
6. Generate text_embedding from f"{title}. {description or ''}" via embeddings.embed_text (cached)
7. Build Qdrant payload: {item_id: str, type, status: 'open', created_at_ts: int(created_at.timestamp())}
8. Upsert both embeddings into Qdrant (image into items_image, text into items_text)
9. UPDATE items SET embedding_status='ready'
10. Return the full Item dict

On any failure after step 4 (item is in DB):
- Log error with full stack trace
- UPDATE embedding_status='failed'
- Do NOT delete the item — user retains their post, embeddings can be backfilled
- Re-raise the exception so caller can show a clear error in UI

Add backfill_failed_embeddings() that retries all items with embedding_status='failed'.

Add /scripts/backfill_embeddings.py CLI entry point that calls it.

Add pytest test for the full pipeline using a small test image.
```

## 2.2 Streamlit app entry + auth (simple email-based)

```
Build /app/streamlit_app.py as the entry point:

- Sets page_config (page_title="USFind", page_icon="🎒", layout="wide")
- Initializes config, runs migrations on startup (only if ENVIRONMENT != production OR if env var RUN_MIGRATIONS_ON_BOOT=true)
- Warms up CLIP model in a background thread
- Sidebar: shows current user (if signed in) + sign in / out

Simple identity model (no full OAuth for v1):
- Sidebar has a "Sign in" expander with email + name inputs and a "Continue" button
- On click: upsert user in Postgres, store user_id and name in st.session_state.user
- "Sign out" button clears session_state.user
- A helper require_login() that st.stop()s if not signed in (used on /post and /me pages)

Landing content on the main page (when not signed in):
- Title "USFind 🎒 — AI-powered lost & found for USF"
- One-paragraph pitch
- Tech badges: Streamlit · Postgres · Qdrant · Redis · CLIP · Gemini
- Sign-in prompt
```

## 2.3 Streamlit page: post item

```
Build /app/pages/1_📤_Post_Item.py:

- require_login() at top
- Header: "Report a Lost or Found Item"

Form (st.form):
- Radio: "I... [Lost something | Found something]"
- File uploader: "Upload a photo" (jpg/png/webp, max 5MB)
- After upload, show image preview at 300px width
- Text input: "Title" (required, max 200 chars)
- Text area: "Description" (optional, max 2000 chars) — will be AI-filled in Week 3
- Text input: "Location" (optional, max 200 chars)
- Submit button

On submit:
- Validate fields (all required ones present, file size, file type)
- Show spinner "Posting and indexing your item..."
- Call items.create_item(...)
- On success: success toast "Item posted!" + auto-redirect via st.switch_page to /pages/3_📋_Item_Detail.py?id={new_id}
- On error: error toast with sanitized message

Live status during processing: stream-like UI showing "Uploading image..." → "Generating embeddings..." → "Indexing in vector DB..." → "Done!"
```

## 2.4 Streamlit page: browse feed

```
Build /app/pages/2_🔍_Browse.py:

- Header with filter tabs: All / Lost / Found (use st.tabs or radio buttons)
- Grid: st.columns(3) for desktop, fallback handled by Streamlit responsiveness
- Each card (custom HTML in st.markdown with unsafe_allow_html=True):
  - Square thumbnail (object-cover via inline CSS) from item.image_url
  - Colored type badge (red for lost, green for found)
  - Title (truncate to 60 chars with ellipsis)
  - Location · "X hours/days ago"
- Card click → navigate to detail page via st.query_params

Pagination:
- "Load more" button at bottom, paginates 20 per page, stored in session_state.feed_offset
- Reset offset to 0 when filter tab changes

Pure SQL fetch via db.list_items() — no vector search here.
```

## 2.5 Streamlit page: item detail

```
Build /app/pages/3_📋_Item_Detail.py:

- Read item_id from st.query_params['id']
- Fetch item from Postgres, fetch poster's name via JOIN (extend db.get_item to include poster_name)

Layout:
- Large image (max 600px wide, lazy-load via img tag)
- Type badge + title
- Description block — if item.ai_description was used as base, show small "✨ AI-described" label
- Location · Posted by {poster_name} · {relative_time}
- Big CTA button: "Show possible matches" → navigates to /pages/4_✨_Matches.py?id={item_id}

Handle:
- Item not found → "This item doesn't exist or was removed" + back to browse
- Image URL broken → placeholder + warning log
```

---

# WEEK 3 — The retrieval pipeline (the hardcore part)

## 3.1 Stage 1: Qdrant recall

```
Create /app/core/retrieval.py with stage1_recall(query_item_id: UUID, top_k: int = 50) -> list[Candidate]:

Candidate is a Pydantic model: { item_id: UUID, combined_score: float, image_score: float, text_score: float, item: ItemDict, stage1_rank: int }

Logic:
1. Fetch query item from Postgres
2. Fetch its image_embedding + text_embedding from Qdrant via vectors.get_embeddings()
   (If either is missing, raise RetrievalError)
3. Build Qdrant filter: opposite type, status='open', created_at_ts >= (now - 60 days), exclude query item
4. Run both searches in parallel via concurrent.futures.ThreadPoolExecutor(2):
   - vectors.search_image(query.image_embedding, filter, limit=top_k)
   - vectors.search_text(query.text_embedding, filter, limit=top_k)
5. Merge by item_id:
   - For each item appearing in either result, take its scores (0 if missing from one list)
   - combined_score = 0.7 * image_score + 0.3 * text_score
6. Filter: combined_score >= 0.45
7. Sort DESC by combined_score
8. Take top top_k
9. Hydrate item details from Postgres (single SELECT WHERE id IN (...))
10. Return Candidate list

Log stage 1 latency at INFO level.
Performance target: p95 < 100ms with 1000 items in collection.

Add pytest test with seeded data verifying ordering, filters, and threshold.
```

## 3.2 Stage 2: Gemini Pro re-ranking

```
Add stage2_rerank(query_item: ItemDict, candidates: list[Candidate], top_k: int = 10) -> list[Candidate]:

Logic:
1. Cap input to top 20 from stage 1 (Gemini Pro can handle ~20 images per request safely)
2. Build a structured prompt:
   - System instruction loaded from /app/prompts/rerank.txt
   - User message parts:
     - "QUERY ITEM:" + query metadata + query image
     - "CANDIDATES (numbered 1-20):" + for each candidate: index, metadata, image
     - "Rank each candidate by likelihood of being the same physical item."
3. Define response_schema:
   {
     "type": "object",
     "properties": {
       "rankings": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "candidate_index": {"type": "integer"},
             "rerank_score": {"type": "integer", "minimum": 0, "maximum": 100},
             "explanation": {"type": "string"}
           },
           "required": ["candidate_index", "rerank_score", "explanation"]
         }
       }
     },
     "required": ["rankings"]
   }
4. Call llm.cached_call_pro(parts, system_instruction, response_schema)
5. Parse response, attach rerank_score + explanation to each candidate
6. Filter: rerank_score >= 40
7. Sort DESC by rerank_score
8. Return top top_k

Save /app/prompts/rerank.txt with explicit guidance:
- Focus on visual identity (color, shape, brand, distinguishing features) above all
- Then text coherence (does the description match what's in the image?)
- Light weight on location/time proximity (helpful but not decisive)
- Reject obvious non-matches even if vector similarity was high
- Score scale: 0-30 unlikely, 30-60 possible, 60-85 likely, 85-100 very likely
- Be conservative — false positives hurt user trust more than false negatives
- Each explanation: one factual sentence about visual/textual evidence, not speculation

Add full_retrieval(query_item_id: UUID, final_k: int = 10) -> RetrievalResult:
- Calls stage1_recall, then stage2_rerank
- Returns RetrievalResult: { candidates: list[Candidate], stage1_count: int, stage1_ms: float, stage2_ms: float, total_ms: float, cache_hit: bool }
```

## 3.3 Aggressive caching for re-ranking

```
Add re-rank cache layer in retrieval.py:

Cache key: rerank:v1:{query_item_id}:{updated_at_unix}:{candidate_ids_sorted_hash}

Where candidate_ids_sorted_hash = sha256 of sorted candidate UUIDs concatenated.

TTL: 24 hours.

Logic:
- Before calling stage2_rerank, build the cache key
- Check Redis (use the generic llm cache namespace OR a dedicated rerank: namespace — use the dedicated one for clearer stats)
- On hit: return parsed cached result, set cache_hit=True
- On miss: run stage 2, cache the result, set cache_hit=False

Edge case: query item updated → updated_at in key changes → cache miss naturally. Same for any candidate update would NOT invalidate (cache is keyed on snapshot of candidate IDs, not their content) — acceptable since matches are about identity, not metadata.

Add to cache_stats(): rerank_hits, rerank_misses counters.
```

## 3.4 Streamlit page: matches with explanations

```
Build /app/pages/4_✨_Matches.py:

- Read query_item_id from st.query_params['id']
- Fetch query item, show small "query" badge at top with thumbnail + title
- Run full_retrieval(query_item_id) with spinner showing live progress:
  - "🔍 Stage 1: Searching vector indexes..." (during stage 1)
  - "🧠 Stage 2: Re-ranking with Gemini Pro..." (during stage 2)
  - On done: "✅ Found N matches in Xms"

For each match:
- Card layout: thumbnail (200px), title, location, posted by, posted-at
- "Match confidence" progress bar with rerank_score percentage
- "Why this might match" — italic, explanation from Gemini
- Small expander "🔬 Technical scores" showing: combined_score, image_score, text_score, rerank_score (great for the demo)
- "This is mine!" button (wire up in Week 4)

Footer bar with technical details (this is a portfolio piece — show off):
- "Stage 1: Xms | Stage 2: Yms | Total: Zms"
- "Cache: HIT/MISS"
- "🧠 Pipeline: Qdrant HNSW recall (top 50) → Gemini 2.5 Pro re-ranking (top 10)"

Empty state: "No likely matches yet. We'll keep looking as new items are posted. Try the conversational search if you want to broaden the criteria."
```

## 3.5 Auto-description with Gemini Vision

```
Add /app/core/auto_description.py with auto_describe(image_bytes: bytes) -> str:

- Open as PIL.Image
- Load system instruction from /app/prompts/auto_describe.txt
- Schema: {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}
- Call llm.cached_call_flash(parts=[image, "Describe this item for a lost-and-found post."], system_instruction, response_schema)
- Return description string

Save /app/prompts/auto_describe.txt:
"You are helping describe items posted to a lost-and-found platform. Look at the image and write a single 1-2 sentence factual description focused on:
- Object type (e.g., backpack, water bottle, keys)
- Color(s)
- Brand or text if clearly visible
- Distinguishing features (stickers, damage, accessories, condition)

Be specific and useful for matching. Do not speculate beyond what is clearly visible. Avoid filler words. Example good: 'Black Nike backpack with red logo, side mesh water-bottle pocket, small white sticker on top flap.' Example bad: 'A nice backpack that someone lost.'"

Integrate into /pages/1_📤_Post_Item.py:
- After file upload but before form submit, run auto_describe in the background
- Pre-fill the description text area with the AI result (via session_state)
- Show small "✨ AI suggestion — feel free to edit" caption below
- If user has already typed something, do NOT overwrite — show "Apply AI suggestion" button instead
- On error: silent fail, user types their own

Save the AI-generated text to items.ai_description column when item is created (even if user edits the final description, we keep the original AI output for debugging / metrics).
```

## 3.6 Conversational search

```
Add /app/pages/5_💬_Search.py:

UI:
- Big text input: "Describe what you're looking for"
- Placeholder: "e.g., 'I lost a blue water bottle near the library yesterday'"
- Search button

On submit:
1. Spinner: "🧠 Understanding your search..."
2. Call llm.cached_call_flash with prompt from /app/prompts/parse_search.txt and response_schema:
   {
     "item_type": "string | null",
     "color": "string | null",
     "location": "string | null",
     "time_window_hours": "integer | null (null means no time filter)",
     "search_type": "lost | found | either",
     "semantic_query": "string (cleaned-up query for embedding search)"
   }
3. Display parsed filters as colored chips below the search bar so the user sees what was understood
4. Build retrieval:
   - Generate text embedding for semantic_query via embeddings.embed_text
   - Build Qdrant filter from extracted structured fields:
     - type filter: 'found' if search_type=='lost', 'lost' if 'found', else None
     - status: 'open'
     - time window: if time_window_hours, created_at_ts >= now - hours
   - Run vectors.search_text only (no query image)
   - Take top 30 candidates
5. Spinner: "🎯 Re-ranking results..."
6. Build a "virtual query item" for stage 2 with title=semantic_query, description="", no image
7. Run a slightly modified stage2_rerank that handles missing image gracefully (still effective for text-heavy queries)
8. Show top 10 with explanations

Save /app/prompts/parse_search.txt with 5+ few-shot examples covering:
- Lost with time + location: "I lost my blue water bottle near the library yesterday around 3pm"
- Found, casual: "Found a black backpack with red patch this morning at MSC"
- Vague: "Has anyone found my keys?"
- Very specific: "Looking for white AirPods Pro 2 case with a small scratch on the bottom"
- Non-English mixed in: "lost cây bút màu xanh in the engineering building"
```

---

# WEEK 4 — Polish + ship

## 4.1 Match confirmation flow

```
Wire up "This is mine!" button on /pages/4_✨_Matches.py:

On click:
1. st.modal: "Confirm this is your item? The poster's contact email will be shared with you."
2. On confirm:
   - INSERT into matches table (item_a_id=query, item_b_id=matched, confirmed_by=current_user.id, combined_score, rerank_score)
   - UPDATE both items SET status='matched'
   - DELETE both items from Qdrant collections (no longer searchable)
   - Show: "✅ Match confirmed! The poster's email: {other_user.email} — reach out to coordinate."
3. After confirmation, st.rerun() to refresh the matches page

Add /app/pages/6_👤_Me.py:
- "My posted items" section: list with status badges
- "My confirmed matches" section: shows both as finder and as loser, with the matched item details
- Sign out button
```

## 4.2 Stats / observability page (the demo killer)

```
Build /app/pages/9_⚙️_Stats.py — engineering observability dashboard, public access:

Sections with st.metric tiles + small charts:

System scale:
- Total items (lost / found / matched)
- Total users
- Total confirmed matches
- Match success rate (matched_lost / total_lost)

AI pipeline performance (rolling 100-request window, in-memory deque):
- Stage 1 (Qdrant recall) p50 / p95 / p99 latency
- Stage 2 (Gemini rerank) p50 / p95 / p99 latency
- End-to-end p50 / p95 / p99 latency

Cache performance:
- Image embedding cache: hit rate %
- Text embedding cache: hit rate %
- LLM cache: hit rate %
- Re-rank cache: hit rate %

Cost tracking (from llm_usage table — add migration 002_llm_usage.sql):
- Gemini cost today (USD)
- Gemini cost this month (USD)
- Average cost per retrieval

Vector DB stats:
- items_image collection: point count, indexed status
- items_text collection: point count, indexed status

Architecture diagram (markdown, ASCII or embedded image):
- Streamlit → Postgres + Qdrant + Redis + Gemini

Make this page beautiful. It IS the portfolio piece. Use st.columns, st.metric with deltas, small line charts for latency over time. Recruiters and engineers will love this.
```

## 4.3 LLM usage logging

```
Add /app/migrations/002_llm_usage.sql:

CREATE TABLE llm_usage (
  id BIGSERIAL PRIMARY KEY,
  called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  model TEXT NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  cost_usd REAL NOT NULL,
  latency_ms INTEGER NOT NULL,
  cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
  endpoint TEXT NOT NULL  -- 'auto_describe', 'parse_search', 'rerank'
);

CREATE INDEX idx_llm_usage_called_at ON llm_usage(called_at DESC);
CREATE INDEX idx_llm_usage_endpoint_date ON llm_usage(endpoint, called_at DESC);

Update /app/core/llm.py:
- After every Gemini call (cached or not), INSERT into llm_usage (cache_hit=True if served from cache, with zero tokens/cost)
- Wrap inserts in try/except so logging failure never breaks user flow

Add /app/core/cost_tracking.py with:
- get_daily_cost() -> float
- get_monthly_cost() -> float
- get_cost_by_endpoint(days: int = 7) -> dict
```

## 4.4 Performance benchmarking script

```
Create /scripts/benchmark.py:

CLI: python -m scripts.benchmark --num-items 200 --num-queries 50

Pipeline:
1. Seed N synthetic items into the system using realistic test data from /scripts/seed_data.py (next prompt)
2. Wait for all embeddings to be ready
3. Run M retrievals (random query item each time) through full_retrieval
4. Collect timings for: stage1_ms, stage2_ms, total_ms, cache_hit
5. Compute p50, p95, p99 for each
6. Print Redis cache hit rates before and after the benchmark
7. Print Qdrant collection stats
8. Compute average Gemini cost per retrieval
9. Output a markdown report to /docs/BENCHMARK.md with timestamp, parameters, full results table

Run twice and report both: cold cache (after Redis flush) and warm cache. The diff is impressive to show in interviews.
```

## 4.5 Demo data seeder

```
Create /scripts/seed_data.py:

CLI: python -m scripts.seed_data --num-items 80 --plant-matches 8

Plants 80 realistic items with embeddings. Uses curated free image URLs (Unsplash, public CDN) covering:
- Backpacks (various colors)
- Water bottles (various colors, brands)
- Keys / keychains
- Phones / cases
- Headphones / AirPods
- Laptops / laptop sleeves
- Wallets
- Notebooks / planners
- Eyewear / glasses
- Clothing items

Plants 8 obvious matching pairs:
- Each pair: one item marked 'lost', a near-identical item marked 'found'
- Use slightly different photos of similar items (e.g., two blue Hydro Flask water bottles)
- Pairs should be discoverable through your retrieval pipeline — this validates the system works end-to-end

Also generates 5 test user accounts so items aren't all owned by user 1.

Run via Makefile: make seed
```

## 4.6 Deploy to Railway

```
Set up production deployment.

Create /docker/Dockerfile (used for Streamlit container on Railway):
- Base: python:3.11-slim
- Install system deps for Pillow + torch: libpq-dev, gcc, libgl1
- Copy requirements.txt, pip install (use --no-cache-dir)
- Pre-download CLIP model at build time so cold starts are fast:
  RUN python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32')"
- Copy app source
- EXPOSE 8501
- CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

Create /docker/railway.toml or use Railway's config UI:

Three Railway services in one project:
1. streamlit: builds from /docker/Dockerfile, port 8501, env vars from production
2. qdrant: uses qdrant/qdrant:v1.12.0 image, port 6333, volume mount for storage
3. redis: uses redis:7-alpine, port 6379, volume mount

Internal networking: Streamlit reaches Qdrant via railway internal DNS (qdrant.railway.internal:6333), Redis via redis.railway.internal:6379.

Postgres: separate Neon project's main branch, connection string via env var.

R2 setup:
- Create Cloudflare account + R2 bucket "usfind-images"
- Enable public access via R2.dev subdomain OR custom domain
- Generate API token with R2 read/write
- Add credentials as env vars in Railway

Output the full deploy checklist:
1. Create Railway project
2. Add three services (Streamlit from repo, Qdrant from image, Redis from image)
3. Configure env vars on streamlit service (DATABASE_URL, QDRANT_URL=http://qdrant.railway.internal:6333, REDIS_URL=redis://redis.railway.internal:6379, R2 vars, GEMINI_API_KEY, ENVIRONMENT=production)
4. Trigger deploy
5. Once running, generate public domain on streamlit service
6. Test the full sign-in + post + search + matches flow on production
7. Run /scripts/seed_data.py against production (one-time setup)
```

## 4.7 Production README

```
Write /README.md as a portfolio-quality document:

# USFind 🎒

> Lost & Found for USF students, powered by a production-grade 2-stage AI retrieval pipeline

## 🔗 Live demo
- App: [Railway URL]
- Demo video: [Loom URL]
- GitHub: [repo URL]

## 🎯 What it does
Students post photos of items they've lost or found. The system uses image + text embeddings to surface possible matches, then re-ranks them with a vision-language model for high-precision results.

## 🏗️ Architecture

[ASCII diagram]
Streamlit (UI) ──→ Postgres (relational data)
            ├──→ Qdrant (vector search, HNSW)
            ├──→ Redis (3-layer cache)
            ├──→ Gemini Flash + Pro (LLM features)
            └──→ Cloudflare R2 (image storage)

## 🧠 The AI pipeline (the heart of this project)

**Stage 1 — Vector recall (Qdrant)**
CLIP embeddings (512-dim, image + text) stored in two Qdrant collections with HNSW indexing. For a query item, runs parallel image-vector and text-vector searches, fuses results with weighted scoring (0.7 image + 0.3 text), returns top 50 in <100ms.

**Stage 2 — LLM re-ranking (Gemini 2.5 Pro)**
Top 20 candidates from stage 1 go to Gemini Pro with both query and candidate images + metadata. Gemini scores each 0-100 with structured output, produces match explanations. Final top-10 ranked by Gemini score.

**Why this architecture?**
This is the same recall+rerank pattern used by YouTube, Spotify, and modern search engines. Vector search is fast but imprecise; LLM rerank is precise but slow and expensive. Combining them gives both speed and quality.

## ⚡ Performance
[Pull real numbers from /docs/BENCHMARK.md]
- Stage 1 p95: Xms
- Stage 2 p95: Yms
- End-to-end p95: Zms
- Cache hit rate (warm): N%

## ✨ AI features
1. **Auto-description from photo** (Gemini Flash Vision) — pre-fills item descriptions on upload
2. **Conversational search** (Gemini Flash + CLIP) — "I lost a blue water bottle near the library" → structured filters + semantic search
3. **2-stage retrieval with explanations** (CLIP + Qdrant + Gemini Pro) — finds and explains matches

## 📦 Tech stack
| Component | Choice | Why |
|---|---|---|
| UI | Streamlit | Fast iteration on AI prototypes |
| Relational DB | Postgres on Neon | Standard, scalable |
| Vector DB | Qdrant | HNSW indexing, payload filters, scales to millions |
| Cache | Redis | Sub-ms reads, perfect for embedding + LLM cache |
| Image storage | Cloudflare R2 | S3-compatible, zero egress fees |
| Embeddings | CLIP (HuggingFace) | Multi-modal (image + text in same space), free, local inference |
| LLM | Gemini 2.0 Flash + 2.5 Pro | Strong vision, structured output, cost-effective |
| Deploy | Railway | Multi-service Docker, simple ops |

## 🚀 Local development

```bash
# Prereqs: Docker, Python 3.11, a Neon Postgres URL, Gemini API key
cp .env.example .env  # fill in values
make up               # start Qdrant + Redis
pip install -r requirements.txt
make run              # streamlit run app/streamlit_app.py
make seed             # optional: seed demo data
```

## 🔍 What I learned
[3-5 honest items]

## 🛣️ Future work
- [3-5 honest items]

## 📜 License
MIT
```

## 4.8 Resume bullets

```
Based on what actually shipped, draft 4 resume bullets for USFind. Tell me what metrics you need from me first (from /docs/BENCHMARK.md and the live deployment), then write them.

Constraints:
- Each bullet must be defensible in a 2-minute interview question
- Lead with the most impressive ACCURATE metric
- One bullet about the 2-stage retrieval pipeline (the standout)
- One about multi-modal embeddings + vector DB
- One about caching / cost / performance infra
- One about LLM features (auto-description, conversational search, re-ranking)
- Use action verbs: built, designed, architected, deployed, achieved
- 1-2 lines per bullet
- No marketing language, just engineering substance

After drafting, list 3 likely interview follow-up questions per bullet so I can prep answers.
```
