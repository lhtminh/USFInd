"use client";

import { useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { TypeBadge } from "@/components/item-card";
import { cn } from "@/lib/utils";
import {
  api,
  relativeTimeFromIso,
  type ApiSearch,
  type ApiParsedSearch,
} from "@/lib/api";

const EXAMPLES = [
  "I lost my blue water bottle near the library yesterday",
  "Found a black backpack with a red logo at MSC this morning",
  "Looking for white AirPods Pro 2 case with a scratch on the bottom",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [parsed, setParsed] = useState<ApiParsedSearch | null>(null);
  const [result, setResult] = useState<ApiSearch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setBusy(true);
    setParsed(null);
    setResult(null);
    setError(null);
    try {
      const res = await api.search(trimmed);
      setParsed(res.parsed);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-4 py-12 sm:gap-10 sm:px-6 sm:py-16">
        <header>
          <div className="usfind-label text-ink-soft mb-2">
            Section · talk to the archive
          </div>
          <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
            Describe what&apos;s <em>missing</em>.
          </h1>
          <p className="mt-3 max-w-xl text-lg text-ink-soft">
            A reasoning LLM parses your sentence into filters, CLIP embeds the
            cleaned query, and the same LLM re-ranks the candidates with
            reasons.
          </p>
        </header>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(query);
          }}
          className="flex flex-col gap-3"
        >
          <div className="flex flex-wrap gap-3">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="I lost my blue water bottle near the library yesterday…"
              className="font-display text-lg h-12"
            />
            <Button
              size="lg"
              type="submit"
              className="font-mono uppercase tracking-wider"
              disabled={busy}
            >
              {busy ? "Searching…" : "Search →"}
            </Button>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
            <span>Try:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => {
                  setQuery(ex);
                  run(ex);
                }}
                className="rounded-full border border-line bg-paper-soft px-3 py-1 hover:border-[var(--accent-strong)] hover:text-ink"
              >
                {ex.length > 36 ? ex.slice(0, 36) + "…" : ex}
              </button>
            ))}
          </div>
        </form>

        {(busy || parsed || result) && (
          <section className="flex flex-col gap-5">
            <ol className="grid gap-3 sm:grid-cols-3">
              <Step
                idx="01"
                title="Parsing your query"
                done={!!parsed}
                active={busy && !parsed}
              />
              <Step
                idx="02"
                title="Vector recall + rerank"
                done={!!result}
                active={busy && !!parsed && !result}
              />
              <Step idx="03" title="Ranked results" done={!!result} />
            </ol>

            {parsed ? (
              <div className="usfind-card p-4">
                <div className="usfind-label text-ink-soft mb-2">
                  ✶ Understood as
                </div>
                <div className="flex flex-wrap gap-2">
                  {parsed.item_type ? <Chip label={`🏷️ ${parsed.item_type}`} /> : null}
                  {parsed.color ? <Chip label={`🎨 ${parsed.color}`} /> : null}
                  {parsed.location ? (
                    <Chip label={`📍 ${parsed.location}`} />
                  ) : null}
                  {parsed.time_window_hours ? (
                    <Chip label={`⏰ last ${parsed.time_window_hours}h`} />
                  ) : null}
                  <Chip label={`🔎 ${parsed.search_type}`} accent />
                </div>
                <p className="mt-2 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                  Semantic query ·{" "}
                  <span className="text-ink">{parsed.semantic_query}</span>
                </p>
              </div>
            ) : null}

            {result ? (
              <div className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                <span className="text-ink">Stage 1</span>{" "}
                {result.stage1_ms.toFixed(0)} ms ·{" "}
                <span className="text-ink">Stage 2</span>{" "}
                {result.stage2_ms.toFixed(0)} ms ·{" "}
                <span className="text-ink">Total</span>{" "}
                {result.total_ms.toFixed(0)} ms ·{" "}
                <span className="text-ink">{result.stage1_count}</span>{" "}
                stage-1 candidates
              </div>
            ) : null}
          </section>
        )}

        {error ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">
              The search desk is closed.
            </span>
            <p className="max-w-md text-ink-soft">
              The API didn&apos;t answer. Confirm{" "}
              <code className="font-mono">uvicorn api.main:app --port 8000</code>{" "}
              is running and that <code className="font-mono">GEMINI_API_KEY</code>{" "}
              is set in <code className="font-mono">.env</code>.
            </p>
            <span className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
              {error}
            </span>
          </div>
        ) : null}

        {result && result.candidates.length === 0 ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">No matches yet.</span>
            <span className="usfind-label text-ink-soft">
              Try broadening the description or check back as new items are filed.
            </span>
          </div>
        ) : null}

        {result && result.candidates.length > 0 ? (
          <section className="flex flex-col gap-4">
            <div className="usfind-label text-ink-soft">
              Top {result.candidates.length} results
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {result.candidates.map((c, i) => (
                <ResultCard
                  key={c.item.id}
                  result={{
                    id: c.item.id,
                    title: c.item.title,
                    imageUrl: c.item.image_url,
                    location: c.item.location ?? "—",
                    postedAtIso: c.item.posted_at,
                    type: c.item.type,
                    rerankScore: Math.round(c.rerank_score ?? 0),
                    explanation: c.explanation ?? "",
                  }}
                  index={i}
                />
              ))}
            </div>
          </section>
        ) : null}
      </main>
      <SiteFooter />
    </div>
  );
}

function Step({
  idx,
  title,
  done,
  active,
}: {
  idx: string;
  title: string;
  done?: boolean;
  active?: boolean;
}) {
  return (
    <li
      className={cn(
        "border border-line p-3 font-mono text-xs uppercase tracking-wider",
        done && "border-[var(--accent-strong)] text-[var(--accent-strong)]",
        active && "animate-pulse",
      )}
    >
      <div className="text-ink-soft">§ {idx}</div>
      <div className="text-ink">{title}</div>
    </li>
  );
}

function Chip({ label, accent }: { label: string; accent?: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full border px-3 py-1 font-mono text-xs uppercase tracking-wider",
        accent
          ? "border-[var(--accent-strong)] text-[var(--accent-strong)]"
          : "border-line bg-paper-soft text-ink",
      )}
    >
      {label}
    </span>
  );
}

function ResultCard({
  result,
  index,
}: {
  result: {
    id: string;
    title: string;
    imageUrl: string;
    location: string;
    postedAtIso: string;
    type: "lost" | "found";
    rerankScore: number;
    explanation: string;
  };
  index: number;
}) {
  const tilt = ["-rotate-[0.25deg]", "rotate-[0.2deg]"][index % 2];
  return (
    <Link
      href={`/items/${result.id}`}
      className={cn("usfind-card relative flex gap-4 p-4 no-underline", tilt)}
    >
      <span className="usfind-tape" aria-hidden />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={result.imageUrl}
        alt={result.title}
        className="h-28 w-28 flex-none rounded-sm border border-line object-cover"
      />
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex items-center gap-2">
          <TypeBadge type={result.type} />
          <span className="usfind-label text-ink-soft">
            {result.location} · {relativeTimeFromIso(result.postedAtIso)}
          </span>
        </div>
        <h3 className="font-display text-xl leading-snug">{result.title}</h3>
        <div className="flex items-baseline justify-between font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
          <span>Match confidence</span>
          <span className="text-ink">{result.rerankScore}%</span>
        </div>
        <Progress value={result.rerankScore} className="h-1.5 bg-paper-soft" />
        {result.explanation ? (
          <p className="font-display text-sm italic leading-relaxed text-ink-soft">
            “{result.explanation}”
          </p>
        ) : null}
      </div>
    </Link>
  );
}
