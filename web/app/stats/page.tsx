import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { mockStats } from "@/lib/mock-data";

export default function StatsPage() {
  const s = mockStats;

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-14 px-6 py-16">
        <header>
          <div className="usfind-label text-ink-soft mb-2">
            Engineering dossier · public observability
          </div>
          <h1 className="font-display text-5xl tracking-tight">
            How the bureau is <em>running</em>.
          </h1>
          <p className="mt-2 max-w-xl text-ink-soft">
            Latency percentiles, cache hit rates, Gemini cost, and Qdrant
            vitals — refreshed live from <code className="font-mono">llm_usage</code>{" "}
            and an in-process rolling window.
          </p>
        </header>

        {/* Scale */}
        <Section label="§ I — Scale" title="The size of the archive.">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Tile k="users" v={s.users.toString()} sub="active accounts" />
            <Tile
              k="open items"
              v={s.openItems.toString()}
              sub={`${s.lost} lost · ${s.found} found`}
            />
            <Tile k="confirmed matches" v={s.matches.toString()} sub="all time" />
            <Tile
              k="match success rate"
              v={`${Math.round(s.matchSuccessRate * 100)}%`}
              sub="lost → matched"
              accent
            />
          </div>
        </Section>

        {/* Latency */}
        <Section
          label="§ II — Latency"
          title="Pipeline percentiles (last 100 retrievals)."
        >
          <div className="overflow-hidden border border-line">
            <table className="w-full font-mono text-sm">
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
                  p={s.latency.stage1}
                  highlight
                />
                <Row name="Stage 2 · Gemini rerank" p={s.latency.stage2} />
                <Row name="End-to-end" p={s.latency.total} />
              </tbody>
            </table>
          </div>
          <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
            Target: Stage 1 p95 &lt; 100 ms · E2E p95 &lt; 4 s warm
          </p>
        </Section>

        {/* Cache */}
        <Section label="§ III — Cache" title="Three layers, all hot.">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <CacheTile name="Image embeddings" rate={s.cacheRates.imageEmb} />
            <CacheTile name="Text embeddings" rate={s.cacheRates.textEmb} />
            <CacheTile name="LLM responses" rate={s.cacheRates.llm} />
            <CacheTile name="Rerank (24h)" rate={s.cacheRates.rerank} accent />
          </div>
        </Section>

        {/* Cost */}
        <Section label="§ IV — Cost" title="Gemini spend, watched.">
          <div className="grid gap-4 sm:grid-cols-3">
            <Tile k="today" v={`$${s.cost.today.toFixed(2)}`} sub="rolling 24h" />
            <Tile
              k="last 30 days"
              v={`$${s.cost.last30.toFixed(2)}`}
              sub="rolling 30d"
            />
            <Tile
              k="avg / retrieval"
              v={`$${s.cost.perRetrieval.toFixed(4)}`}
              sub="warm cache"
              accent
            />
          </div>
          <div className="usfind-card p-5">
            <div className="usfind-label text-ink-soft mb-3">
              By endpoint · last 7 days
            </div>
            <ul className="flex flex-col gap-2 font-mono text-sm">
              {Object.entries(s.cost.byEndpoint).map(([endpoint, cost]) => (
                <li
                  key={endpoint}
                  className="flex items-baseline justify-between border-b border-line/70 pb-2 last:border-none last:pb-0"
                >
                  <span className="text-ink-soft uppercase tracking-wider text-xs">
                    {endpoint}
                  </span>
                  <span className="text-ink">${cost.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* Qdrant */}
        <Section label="§ V — Vector store" title="Qdrant vitals.">
          <div className="grid gap-4 sm:grid-cols-2">
            {Object.entries(s.qdrant).map(([name, info]) => (
              <div key={name} className="usfind-card p-5">
                <div className="usfind-label text-ink-soft mb-2">
                  Collection · {name}
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="font-display text-3xl">{info.points}</span>
                  <span className="font-mono text-[0.72rem] uppercase tracking-wider text-[var(--accent-strong)]">
                    ● {info.status}
                  </span>
                </div>
                <p className="mt-1 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                  HNSW · m=16 · ef_construct=128 · cosine
                </p>
              </div>
            ))}
          </div>
        </Section>

        {/* Architecture */}
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
                         ├──► Gemini   (Flash for parse + describe; Pro for rerank)
                         └──► R2       (image storage, signed upload URLs)`}
            </pre>
          </div>
        </Section>
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
        <h2 className="font-display text-3xl tracking-tight">
          {title.replace("running", "running")}
        </h2>
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
  rate,
  accent,
}: {
  name: string;
  rate: number;
  accent?: boolean;
}) {
  const pct = Math.round(rate * 100);
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
        {pct}%
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
        hit rate
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
      <td className="px-4 py-3 text-right text-ink">{p.p50}</td>
      <td className="px-4 py-3 text-right text-ink">{p.p95}</td>
      <td className="px-4 py-3 text-right text-ink">{p.p99}</td>
    </tr>
  );
}
