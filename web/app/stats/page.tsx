import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { api, type ApiStats } from "@/lib/api";

export const dynamic = "force-dynamic";

const ZERO = { p50: 0, p95: 0, p99: 0 };

export default async function StatsPage() {
  let s: ApiStats | null = null;
  let error: string | null = null;
  try {
    s = await api.getStats();
  } catch (err) {
    error = err instanceof Error ? err.message : "Stats API unavailable";
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-4 py-12 sm:gap-14 sm:px-6 sm:py-16">
        <header>
          <div className="usfind-label text-ink-soft mb-2">
            Engineering dossier · public observability
          </div>
          <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
            How the bureau is <em>running</em>.
          </h1>
          <p className="mt-2 max-w-xl text-ink-soft">
            Latency percentiles, cache hit rates, LLM cost, and Qdrant
            vitals — refreshed live from{" "}
            <code className="font-mono">llm_usage</code> and an in-process
            rolling window.
          </p>
        </header>

        {error ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">
              The bureau is offline.
            </span>
            <span className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
              {error}
            </span>
          </div>
        ) : null}

        {s ? (
          <>
            <Section label="§ I — Scale" title="The size of the archive.">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Tile k="users" v={String(s.users)} sub="registered" />
                <Tile
                  k="open items"
                  v={String(s.open_total)}
                  sub={`${s.lost_total} lost · ${s.found_total} found`}
                />
                <Tile
                  k="confirmed matches"
                  v={String(s.matches)}
                  sub="all time"
                />
                <Tile
                  k="match success rate"
                  v={`${Math.round((s.match_success_rate || 0) * 100)}%`}
                  sub="lost → matched"
                  accent
                />
              </div>
            </Section>

            <Section
              label="§ II — Latency"
              title="Pipeline percentiles (last 100 retrievals)."
            >
              <div className="overflow-x-auto border border-line">
                <table className="w-full min-w-[480px] font-mono text-sm">
                  <thead className="bg-paper-soft text-left uppercase tracking-wider text-[0.72rem] text-ink-soft">
                    <tr>
                      <th className="px-4 py-3">Stage</th>
                      <th className="px-4 py-3 text-right">p50 (ms)</th>
                      <th className="px-4 py-3 text-right">p95 (ms)</th>
                      <th className="px-4 py-3 text-right">p99 (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <Row
                      name="Stage 1 · Qdrant recall"
                      p={{ ...ZERO, ...s.latency.stage1 }}
                      highlight
                    />
                    <Row
                      name="Stage 2 · Nemotron rerank"
                      p={{ ...ZERO, ...s.latency.stage2 }}
                    />
                    <Row
                      name="End-to-end"
                      p={{ ...ZERO, ...s.latency.total }}
                    />
                  </tbody>
                </table>
              </div>
              <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                {s.latency_samples} samples in the rolling window · Targets:
                Stage 1 p95 &lt; 100 ms · E2E p95 &lt; 4 s warm
              </p>
            </Section>

            <Section label="§ III — Cache" title="Three layers, all hot.">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <CacheTile
                  name="Image embeddings"
                  hits={s.cache.image_hits ?? 0}
                  misses={s.cache.image_misses ?? 0}
                />
                <CacheTile
                  name="Text embeddings"
                  hits={s.cache.text_hits ?? 0}
                  misses={s.cache.text_misses ?? 0}
                />
                <CacheTile
                  name="LLM responses"
                  hits={s.cache.llm_hits ?? 0}
                  misses={s.cache.llm_misses ?? 0}
                />
                <CacheTile
                  name="Rerank (24h)"
                  hits={s.cache.rerank_hits ?? 0}
                  misses={s.cache.rerank_misses ?? 0}
                  accent
                />
              </div>
            </Section>

            <Section label="§ IV — Cost" title="LLM spend, watched.">
              <div className="grid gap-4 sm:grid-cols-3">
                <Tile
                  k="today"
                  v={`$${(s.cost.today ?? 0).toFixed(4)}`}
                  sub="rolling 24h"
                />
                <Tile
                  k="last 30 days"
                  v={`$${(s.cost.last30 ?? 0).toFixed(4)}`}
                  sub="rolling 30d"
                />
                <Tile
                  k="endpoints (7d)"
                  v={String(Object.keys(s.cost.by_endpoint ?? {}).length)}
                  sub="touched"
                  accent
                />
              </div>
              {Object.keys(s.cost.by_endpoint ?? {}).length > 0 ? (
                <div className="usfind-card p-5">
                  <div className="usfind-label text-ink-soft mb-3">
                    By endpoint · last 7 days
                  </div>
                  <ul className="flex flex-col gap-2 font-mono text-sm">
                    {Object.entries(s.cost.by_endpoint).map(([endpoint, cost]) => (
                      <li
                        key={endpoint}
                        className="flex items-baseline justify-between border-b border-line/70 pb-2 last:border-none last:pb-0"
                      >
                        <span className="text-ink-soft uppercase tracking-wider text-xs">
                          {endpoint}
                        </span>
                        <span className="text-ink">${cost.toFixed(4)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </Section>

            <Section label="§ V — Vector store" title="Qdrant vitals.">
              {Object.keys(s.qdrant ?? {}).length === 0 ? (
                <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                  Qdrant offline or no collections yet.
                </p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {Object.entries(s.qdrant).map(([name, info]) => (
                    <div key={name} className="usfind-card p-5">
                      <div className="usfind-label text-ink-soft mb-2">
                        Collection · {name}
                      </div>
                      <div className="flex items-baseline justify-between">
                        <span className="font-display text-3xl">
                          {info.points_count ?? 0}
                        </span>
                        <span className="font-mono text-[0.72rem] uppercase tracking-wider text-[var(--accent-strong)]">
                          ● {info.status ?? "—"}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                        HNSW · m=16 · ef_construct=128 · cosine
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Section>

            <Section label="§ VI — Architecture" title="What talks to what.">
              <div className="usfind-card p-6">
                <pre className="overflow-x-auto whitespace-pre font-mono text-[0.78rem] leading-relaxed text-ink sm:text-sm">
                  {`Streamlit (legacy ops)   ┐
Next.js 16 (app)         │
                         ▼
                    FastAPI bridge ──► Postgres / Neon  (psycopg 3, raw SQL)
                         │            └► users, items, matches, llm_usage
                         ├──► Qdrant   (vector recall + payload filters)
                         ├──► Redis    (3-layer cache + rerank cache)
                         ├──► OpenRouter (Nemotron 3 Nano Omni — describe + parse + rerank)
                         └──► R2       (image storage, signed upload URLs)`}
                </pre>
              </div>
            </Section>
          </>
        ) : null}
      </main>
      <SiteFooter />
    </div>
  );
}

function Section({
  label,
  title,
  children,
}: {
  label: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-5">
      <header>
        <div className="usfind-label text-ink-soft mb-1">{label}</div>
        <h2 className="font-display text-3xl tracking-tight">{title}</h2>
      </header>
      {children}
    </section>
  );
}

function Tile({
  k,
  v,
  sub,
  accent,
}: {
  k: string;
  v: string;
  sub: string;
  accent?: boolean;
}) {
  return (
    <div className="usfind-card flex flex-col gap-2 p-5">
      <div className="usfind-label text-ink-soft">{k}</div>
      <div
        className={
          accent
            ? "font-display text-4xl text-[var(--accent-strong)]"
            : "font-display text-4xl"
        }
      >
        {v}
      </div>
      <div className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
        {sub}
      </div>
    </div>
  );
}

function CacheTile({
  name,
  hits,
  misses,
  accent,
}: {
  name: string;
  hits: number;
  misses: number;
  accent?: boolean;
}) {
  const total = hits + misses;
  const pct = total === 0 ? 0 : Math.round((hits / total) * 100);
  return (
    <div className="usfind-card flex flex-col gap-3 p-5">
      <div className="usfind-label text-ink-soft">{name}</div>
      <div
        className={
          accent
            ? "font-display text-4xl text-[var(--accent-strong)]"
            : "font-display text-4xl"
        }
      >
        {total === 0 ? "—" : `${pct}%`}
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-paper-soft">
        <div
          className={
            accent
              ? "h-full bg-[var(--accent-strong)]"
              : "h-full bg-[oklch(0.55_0.05_60)]"
          }
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
        {hits} / {total} hit rate
      </div>
    </div>
  );
}

function Row({
  name,
  p,
  highlight,
}: {
  name: string;
  p: { p50: number; p95: number; p99: number };
  highlight?: boolean;
}) {
  return (
    <tr
      className={
        highlight
          ? "border-t border-line bg-paper-soft/40"
          : "border-t border-line"
      }
    >
      <td className="px-4 py-3 text-ink">{name}</td>
      <td className="px-4 py-3 text-right text-ink">{p.p50.toFixed(0)}</td>
      <td className="px-4 py-3 text-right text-ink">{p.p95.toFixed(0)}</td>
      <td className="px-4 py-3 text-right text-ink">{p.p99.toFixed(0)}</td>
    </tr>
  );
}
