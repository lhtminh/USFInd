"use client";

import { useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { TypeBadge } from "@/components/item-card";
import { items as MOCK_ITEMS } from "@/lib/mock-data";
import { relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

type Parsed = {
  semanticQuery: string;
  searchType: "lost" | "found" | "either";
  itemType: string | null;
  color: string | null;
  location: string | null;
  timeWindowHours: number | null;
};

type Result = {
  id: string;
  title: string;
  imageUrl: string;
  location: string;
  poster: string;
  postedAt: Date;
  type: "lost" | "found";
  rerankScore: number;
  explanation: string;
};

const EXAMPLES = [
  "I lost my blue water bottle near the library yesterday",
  "Found a black backpack with a red logo at MSC this morning",
  "Looking for white AirPods Pro 2 case with a scratch on the bottom",
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [parsed, setParsed] = useState<Parsed | null>(null);
  const [results, setResults] = useState<Result[] | null>(null);
  const [busy, setBusy] = useState(false);

  function run(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setBusy(true);
    setParsed(null);
    setResults(null);
    setTimeout(() => {
      const p = mockParse(trimmed);
      setParsed(p);
      setTimeout(() => {
        setResults(mockSearch(p));
        setBusy(false);
      }, 600);
    }, 500);
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-16">
        <header>
          <div className="usfind-label text-ink-soft mb-2">
            Section · talk to the archive
          </div>
          <h1 className="font-display text-5xl tracking-tight">
            Describe what's <em>missing</em>.
          </h1>
          <p className="mt-3 max-w-xl text-lg text-ink-soft">
            Gemini Flash parses your sentence into filters, CLIP embeds the
            cleaned query, and Pro re-ranks the candidates with reasons.
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

        {/* Status / steps */}
        {(busy || parsed || results) && (
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
                done={!!results}
                active={busy && !!parsed && !results}
              />
              <Step idx="03" title="Ranked results" done={!!results} />
            </ol>

            {parsed ? (
              <div className="usfind-card p-4">
                <div className="usfind-label text-ink-soft mb-2">
                  ✶ Understood as
                </div>
                <div className="flex flex-wrap gap-2">
                  {parsed.itemType ? <Chip label={`🏷️ ${parsed.itemType}`} /> : null}
                  {parsed.color ? <Chip label={`🎨 ${parsed.color}`} /> : null}
                  {parsed.location ? <Chip label={`📍 ${parsed.location}`} /> : null}
                  {parsed.timeWindowHours ? (
                    <Chip label={`⏰ last ${parsed.timeWindowHours}h`} />
                  ) : null}
                  <Chip label={`🔎 ${parsed.searchType}`} accent />
                </div>
                <p className="mt-2 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                  Semantic query · <span className="text-ink">{parsed.semanticQuery}</span>
                </p>
              </div>
            ) : null}
          </section>
        )}

        {results !== null && results.length === 0 ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">No matches yet.</span>
            <span className="usfind-label text-ink-soft">
              Try broadening the description or check back as new items are filed.
            </span>
          </div>
        ) : null}

        {results && results.length > 0 ? (
          <section className="flex flex-col gap-4">
            <div className="usfind-label text-ink-soft">
              Top {results.length} results
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {results.map((r, i) => (
                <ResultCard key={r.id} result={r} index={i} />
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

function ResultCard({ result, index }: { result: Result; index: number }) {
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
            {result.location} · {relativeTime(result.postedAt)}
          </span>
        </div>
        <h3 className="font-display text-xl leading-snug">{result.title}</h3>
        <div className="flex items-baseline justify-between font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
          <span>Match confidence</span>
          <span className="text-ink">{result.rerankScore}%</span>
        </div>
        <Progress value={result.rerankScore} className="h-1.5 bg-paper-soft" />
        <p className="font-display text-sm italic leading-relaxed text-ink-soft">
          “{result.explanation}”
        </p>
      </div>
    </Link>
  );
}

// ---- mock parsing + search ------------------------------------------------

function mockParse(text: string): Parsed {
  const lower = text.toLowerCase();
  const isLost = /\b(i lost|lost my|missing|looking for|can't find)\b/.test(lower);
  const isFound = /\b(found|i found|picked up)\b/.test(lower);
  const searchType: Parsed["searchType"] = isLost
    ? "lost"
    : isFound
      ? "found"
      : "either";
  const color = ["blue", "black", "red", "white", "brown", "green", "silver"].find(
    (c) => lower.includes(c),
  );
  const itemType = [
    "water bottle",
    "backpack",
    "keys",
    "phone",
    "headphones",
    "airpods",
    "laptop",
    "wallet",
    "notebook",
    "glasses",
    "umbrella",
    "charger",
  ].find((c) => lower.includes(c));
  const locationMatch = /\b(?:near|at|in)\s+(?:the\s+)?([a-z][a-z\s]{2,32})/i.exec(
    text,
  );
  const location = locationMatch ? locationMatch[1].trim() : null;
  const timeWindowHours = /yesterday/.test(lower)
    ? 24
    : /this morning/.test(lower)
      ? 12
      : /last week/.test(lower)
        ? 168
        : null;
  const cleaned = [color, itemType].filter(Boolean).join(" ") || text;
  return {
    semanticQuery: cleaned,
    searchType,
    itemType: itemType ?? null,
    color: color ?? null,
    location,
    timeWindowHours,
  };
}

function mockSearch(parsed: Parsed): Result[] {
  const opposite =
    parsed.searchType === "lost"
      ? "found"
      : parsed.searchType === "found"
        ? "lost"
        : null;
  const pool = MOCK_ITEMS.filter(
    (i) => i.status === "open" && (opposite ? i.type === opposite : true),
  );
  const lowered = parsed.semanticQuery.toLowerCase();
  return pool
    .map((item, i) => {
      const haystack = (item.title + " " + (item.aiDescription ?? "")).toLowerCase();
      const tokens = lowered.split(/\s+/).filter(Boolean);
      const hits = tokens.filter((t) => haystack.includes(t)).length;
      const base = 40 + hits * 14 + (i % 3);
      const score = Math.max(28, Math.min(95, base));
      return {
        id: item.id,
        title: item.title,
        imageUrl: item.imageUrl,
        location: item.location,
        poster: item.poster,
        postedAt: item.postedAt,
        type: item.type,
        rerankScore: score,
        explanation:
          hits >= 2
            ? "Strong color and category match; visual evidence aligns with the description."
            : hits === 1
              ? "Category and one attribute overlap; worth a closer look."
              : "Loosely related; included because vector similarity was non-trivial.",
      };
    })
    .sort((a, b) => b.rerankScore - a.rerankScore)
    .slice(0, 6);
}
