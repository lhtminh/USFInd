import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

const TECH = [
  "Next.js 16",
  "FastAPI",
  "Postgres / Neon",
  "Qdrant",
  "Redis",
  "Gemini Flash + Pro",
  "CLIP ViT-B/32",
  "Cloudflare R2",
];

const FEATURES = [
  {
    code: "I.",
    tag: "Vision LLM",
    title: "Auto-described from a photo",
    body: "Gemini Vision drafts a precise, factual description the moment you upload the photo. Edit it or accept it.",
    rotate: "-rotate-[0.7deg]",
  },
  {
    code: "II.",
    tag: "Flash + CLIP",
    title: "Conversational search",
    body: "“I lost a blue water bottle near the library yesterday” becomes typed filter chips plus semantic search.",
    rotate: "rotate-[0.4deg]",
  },
  {
    code: "III.",
    tag: "Recall → Rerank",
    title: "Explainable matches",
    body: "Qdrant HNSW recall fused 0.7 / 0.3, then Gemini Pro re-rank. Every match comes with a one-sentence reason.",
    rotate: "-rotate-[0.3deg]",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col">
      {/* Newspaper-style masthead */}
      <header className="border-b border-line">
        <div className="mx-auto flex w-full max-w-6xl items-end justify-between gap-6 px-6 py-5">
          <Link
            href="/"
            className="flex items-baseline gap-3 leading-none"
          >
            <span className="font-display text-3xl italic tracking-tight">
              USFind
            </span>
            <span className="usfind-label text-ink-soft hidden sm:inline">
              Dept. of Lost &amp; Found · USF · vol. 01
            </span>
          </Link>
          <nav className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/browse" />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              Browse
            </Button>
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/search" />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              Search
            </Button>
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/stats" />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              Stats
            </Button>
            <Button
              size="sm"
              render={<Link href="/post" />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              File a report →
            </Button>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-24 px-6 py-20">
        {/* Hero */}
        <section className="grid gap-10 md:grid-cols-12">
          <div className="md:col-span-8 usfind-reveal">
            <div className="usfind-label text-ink-soft mb-4">
              Issue 01 · Spring 2026 · Established this week
            </div>
            <h1 className="usfind-headline font-display text-[5.5rem] sm:text-[7.5rem]">
              Lost?
              <br />
              <em className="text-[var(--accent-strong)]">found.</em>
            </h1>
            <p className="mt-10 max-w-xl text-xl leading-relaxed text-ink-soft">
              The Department of Lost &amp; Found at the University of South
              Florida. Powered by multi-modal embeddings, a Qdrant vector
              index, and Gemini Pro re-ranking — so missing things come back{" "}
              <em>ranked and explained</em>, not just listed.
            </p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Button
                size="lg"
                render={<Link href="/post" />}
                nativeButton={false}
                className="font-mono uppercase tracking-wider"
              >
                File a report →
              </Button>
              <Button
                size="lg"
                variant="outline"
                render={<Link href="/search" />}
                nativeButton={false}
                className="font-mono uppercase tracking-wider"
              >
                Search the inventory
              </Button>
            </div>
          </div>

          {/* Right column: a vertical "ledger" */}
          <aside className="md:col-span-4 md:pl-8 md:border-l md:border-line usfind-reveal">
            <div className="usfind-label text-ink-soft mb-3">Filed under</div>
            <dl className="font-mono text-sm">
              {TECH.map((tech, index) => (
                <div
                  key={tech}
                  className="flex items-baseline justify-between border-b border-line/70 py-2"
                >
                  <dt className="text-ink-soft">
                    {String(index + 1).padStart(2, "0")}
                  </dt>
                  <dd className="text-ink">{tech}</dd>
                </div>
              ))}
            </dl>
          </aside>
        </section>

        {/* Features as filed cards */}
        <section className="flex flex-col gap-8">
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="usfind-label text-ink-soft mb-2">
                § II — Capabilities
              </div>
              <h2 className="font-display text-5xl tracking-tight">
                Three things <em>doing real work</em>.
              </h2>
            </div>
            <p className="usfind-label text-ink-soft max-w-xs">
              Not a chatbot bolted onto a CRUD app. Every feature pays for
              itself in better recall.
            </p>
          </header>
          <div className="grid gap-8 md:grid-cols-3">
            {FEATURES.map((feature) => (
              <Card
                key={feature.code}
                className={cn(
                  "usfind-card relative pt-7",
                  feature.rotate,
                )}
              >
                <span className="usfind-tape" aria-hidden />
                <div className="absolute top-3 right-4 usfind-label text-ink-soft">
                  Card {feature.code}
                </div>
                <CardHeader className="gap-3">
                  <Badge
                    variant="secondary"
                    className="w-fit font-mono uppercase tracking-wider"
                  >
                    {feature.tag}
                  </Badge>
                  <CardTitle className="font-display text-2xl italic">
                    {feature.title}
                  </CardTitle>
                  <CardDescription className="font-display text-base leading-relaxed">
                    {feature.body}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Link
                    href="/stats"
                    className="usfind-label text-ink-soft underline decoration-line decoration-2 underline-offset-4 hover:text-[var(--accent-strong)] hover:decoration-[var(--accent-strong)]"
                  >
                    Read the dossier →
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Pipeline as a typed schematic */}
        <section className="flex flex-col gap-6">
          <header>
            <div className="usfind-label text-ink-soft mb-2">
              § III — The retrieval pipeline
            </div>
            <h2 className="font-display text-5xl tracking-tight">
              How the matching <em>actually</em> works.
            </h2>
          </header>
          <div className="usfind-card relative p-8">
            <pre className="overflow-x-auto whitespace-pre font-mono text-[0.78rem] leading-relaxed text-ink sm:text-sm">
              {`QUERY ITEM ─► CLIP image / text embeddings (cached, Redis 30d TTL)
                  │
                  ▼
            QDRANT HNSW (m=16, ef_construct=128)
              parallel  ─► image search  ─┐
                        ─► text search   ─┤  fused 0.7 / 0.3, threshold ≥ 0.45
                                          │
                                          ▼
                                  TOP 50 CANDIDATES
                                          │
                                          ▼
                          GEMINI 2.5 PRO  re-rank with response_schema
                                          │   { rerank_score 0–100, explanation }
                                          ▼
                                  TOP 10 with reasons
                                          │
                                          ▼
                      24 h re-rank cache  (key:  rerank:v1:{id}:{updated_at}:{sha})`}
            </pre>
            <div className="mt-6 grid gap-2 font-mono text-xs uppercase tracking-wider text-ink-soft sm:grid-cols-3">
              <div>
                <span className="text-ink">p95 Stage 1 ·</span> &lt; 100 ms
              </div>
              <div>
                <span className="text-ink">p95 E2E ·</span> &lt; 4 s warm
              </div>
              <div>
                <span className="text-ink">Cache hit warm ·</span> ≥ 80 %
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Colophon footer */}
      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-8 font-mono text-xs uppercase tracking-wider text-ink-soft">
          <span>
            USFind / Dept. of Lost &amp; Found / Tampa, FL ·{" "}
            <span className="text-ink">Set in Newsreader &amp; JetBrains Mono</span>
          </span>
          <Link
            href="https://github.com/lhtminh/USFInd"
            className="hover:text-[var(--accent-strong)]"
          >
            → source on github
          </Link>
        </div>
      </footer>
    </div>
  );
}
