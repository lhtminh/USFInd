# USFind — resume bullets (drafts)

These are templated bullets keyed to the real architecture. Fill the `{…}`
slots from a production deploy + `scripts/benchmark.py` run (see
`docs/BENCHMARK.md`).

## Metrics you'll need before posting these

From `scripts/benchmark.py` against a populated production deploy:

- **Stage 1 p95 latency** (Qdrant recall) — target < 100 ms
- **End-to-end p95 latency** (recall + rerank, warm cache)
- **Warm rerank cache hit rate**
- **Total Gemini cost over a representative run** (and item count seeded)

From `app/pages/9_Stats.py` after some live use:

- Items posted, users, confirmed matches, match success rate

## Draft bullets

### 1. The retrieval pipeline (the lead)

> Designed and built a 2-stage AI retrieval pipeline (Qdrant HNSW vector recall
> + Gemini 2.5 Pro re-ranking with structured JSON output) achieving Stage 1
> p95 of **{X} ms** over **{N}** items and end-to-end p95 of **{Y} s** on warm
> cache, with per-match LLM-generated explanations.

### 2. Multi-modal embeddings + vector DB

> Implemented multi-modal CLIP embeddings (image + text in a shared 512-dim
> space) indexed in Qdrant with HNSW and payload filters, scoring fused
> 0.7 image / 0.3 text for parallel cross-modal recall in **{X} ms** p95.

### 3. Caching & cost infra

> Built a 3-layer Redis cache (image embeddings, text embeddings, LLM
> responses) plus a content-aware re-rank cache keyed on the query's
> `updated_at` and sorted candidate IDs (24h TTL); achieved a warm-cache
> rerank hit rate of **{Z} %** during benchmark replay and reduced per-query
> Gemini cost to **{$C}** average.

### 4. LLM product features

> Shipped three Gemini-powered features behind a structured-output schema:
> Vision auto-description for posts, conversational search that parses free
> text into typed filter chips, and re-rank explanations on match cards —
> all wrapped with retry, response_schema validation, and full token+cost
> telemetry into a Postgres `llm_usage` table for per-endpoint cost tracking.

## Likely follow-up interview questions (3 per bullet)

### Pipeline
1. Why two stages instead of one? What does each stage's failure mode look like?
2. How did you pick the 0.7 / 0.3 weights between image and text scores?
3. How does the system behave when Gemini is rate-limited or returns invalid JSON?

### Embeddings + vector DB
1. Why CLIP base over a fine-tuned variant?
2. Why Qdrant over pgvector, Pinecone, or FAISS for this scale?
3. How would you re-index on a CLIP model upgrade without downtime?

### Caching & cost
1. What's the cache key for re-rank, and what invalidates it?
2. How do you handle Redis being down (graceful degradation contract)?
3. How do you measure cache hit rate in a way that survives restarts?

### LLM features
1. How do you guarantee JSON output from Gemini, and what happens when it deviates?
2. Why was the search parser split out from the recall step?
3. How is per-endpoint cost attribution implemented?
