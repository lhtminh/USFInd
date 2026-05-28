CREATE TABLE llm_usage (
  id BIGSERIAL PRIMARY KEY,
  called_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  model TEXT NOT NULL,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  cost_usd REAL NOT NULL,
  latency_ms INTEGER NOT NULL,
  cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
  endpoint TEXT NOT NULL
);

CREATE INDEX idx_llm_usage_called_at ON llm_usage(called_at DESC);
CREATE INDEX idx_llm_usage_endpoint_date ON llm_usage(endpoint, called_at DESC);
