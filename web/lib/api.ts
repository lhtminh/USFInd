// Thin typed fetch client for the FastAPI bridge.
// Override the base URL with NEXT_PUBLIC_API_BASE in .env.local.

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type ApiItem = {
  id: string;
  type: "lost" | "found";
  status: "open" | "matched" | "closed";
  title: string;
  description: string | null;
  ai_description: string | null;
  location: string | null;
  image_url: string;
  poster_name: string | null;
  posted_at: string;
  embedding_status: string;
};

export type ApiCandidate = {
  item: ApiItem;
  combined_score: number;
  image_score: number;
  text_score: number;
  rerank_score: number | null;
  explanation: string | null;
  stage1_rank: number;
};

export type ApiMatches = {
  query: ApiItem;
  candidates: ApiCandidate[];
  stage1_count: number;
  stage1_ms: number;
  stage2_ms: number;
  total_ms: number;
  cache_hit: boolean;
};

export type ApiParsedSearch = {
  semantic_query: string;
  search_type: "lost" | "found" | "either";
  item_type: string | null;
  color: string | null;
  location: string | null;
  time_window_hours: number | null;
};

export type ApiSearch = {
  parsed: ApiParsedSearch;
  candidates: ApiCandidate[];
  stage1_count: number;
  stage1_ms: number;
  stage2_ms: number;
  total_ms: number;
};

export type ApiStats = {
  users: number;
  open_total: number;
  lost_total: number;
  found_total: number;
  matched_total: number;
  matches: number;
  match_success_rate: number;
  cache: Record<string, number>;
  latency_samples: number;
  latency: {
    stage1: { p50?: number; p95?: number; p99?: number };
    stage2: { p50?: number; p95?: number; p99?: number };
    total: { p50?: number; p95?: number; p99?: number };
  };
  cost: {
    today: number;
    last30: number;
    by_endpoint: Record<string, number>;
  };
  qdrant: Record<
    string,
    { points_count?: number; indexed_vectors_count?: number; status?: string }
  >;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(
      `API ${path} → ${res.status}${text ? `: ${text.slice(0, 200)}` : ""}`,
      res.status,
    );
  }
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = {
  listItems(
    params: {
      type?: "lost" | "found" | "all";
      status?: "open" | "matched" | "closed";
      limit?: number;
      offset?: number;
    } = {},
  ): Promise<ApiItem[]> {
    const qs = new URLSearchParams();
    if (params.type && params.type !== "all") qs.set("type", params.type);
    if (params.status) qs.set("status", params.status);
    if (params.limit) qs.set("limit", String(params.limit));
    if (params.offset) qs.set("offset", String(params.offset));
    return request<ApiItem[]>(`/api/items${qs.size ? `?${qs}` : ""}`);
  },

  getItem(id: string): Promise<ApiItem> {
    return request<ApiItem>(`/api/items/${id}`);
  },

  getMatches(id: string): Promise<ApiMatches> {
    return request<ApiMatches>(`/api/items/${id}/matches`, { method: "POST" });
  },

  search(query: string): Promise<ApiSearch> {
    return request<ApiSearch>(`/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
  },

  getStats(): Promise<ApiStats> {
    return request<ApiStats>("/api/stats");
  },
};

export function relativeTimeFromIso(iso: string): string {
  const t = new Date(iso).getTime();
  const seconds = Math.max(0, (Date.now() - t) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}
