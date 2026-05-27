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
