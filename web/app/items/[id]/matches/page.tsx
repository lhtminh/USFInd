import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { TypeBadge } from "@/components/item-card";
import { api, ApiError, type ApiCandidate, type ApiItem } from "@/lib/api";
import { MatchCard } from "./match-card";
import { Button } from "@/components/ui/button";

export const dynamic = "force-dynamic";

type Params = Promise<{ id: string }>;

export default async function MatchesPage({ params }: { params: Params }) {
  const { id } = await params;

  let queryItem: ApiItem;
  let candidates: ApiCandidate[] = [];
  let stage1Ms = 0;
  let stage2Ms = 0;
  let totalMs = 0;
  let cacheHit = false;
  let runError: string | null = null;

  try {
    queryItem = await api.getItem(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  try {
    const matches = await api.getMatches(id);
    candidates = matches.candidates;
    stage1Ms = matches.stage1_ms;
    stage2Ms = matches.stage2_ms;
    totalMs = matches.total_ms;
    cacheHit = matches.cache_hit;
  } catch (err) {
    runError = err instanceof Error ? err.message : "matching failed";
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-16">
        <div className="usfind-label text-ink-soft">
          <Link href={`/items/${queryItem.id}`} className="hover:text-ink">
            ← back to the filing
          </Link>
        </div>

        <header className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <div className="usfind-label text-ink-soft mb-2">
              ✶ Matching against
            </div>
            <h1 className="font-display text-5xl tracking-tight">
              Possible <em>matches</em>.
            </h1>
          </div>
          <div className="usfind-card flex items-center gap-4 p-3 pr-5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={queryItem.image_url}
              alt={queryItem.title}
              className="h-16 w-16 rounded-sm object-cover"
            />
            <div className="flex flex-col gap-1">
              <TypeBadge type={queryItem.type} />
              <span className="font-display text-base leading-snug">
                {queryItem.title}
              </span>
            </div>
          </div>
        </header>

        <div className="border border-line bg-paper-soft/60 px-5 py-4 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
          <span className="text-ink">Pipeline ·</span> Qdrant HNSW recall (top
          50) → Gemini 2.5 Pro re-rank (top 10) ·{" "}
          <span className="text-ink">stage 1</span> {stage1Ms.toFixed(0)} ms ·{" "}
          <span className="text-ink">stage 2</span> {stage2Ms.toFixed(0)} ms ·{" "}
          <span className="text-ink">total</span> {totalMs.toFixed(0)} ms ·{" "}
          <span className="text-ink">cache</span> {cacheHit ? "hit" : "miss"}
        </div>

        {runError ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">
              Couldn&apos;t run the pipeline.
            </span>
            <p className="max-w-xl text-ink-soft">
              The retrieval failed. Either the query item is still indexing,
              Qdrant isn&apos;t up, or the Gemini key is missing.
            </p>
            <span className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
              {runError}
            </span>
          </div>
        ) : candidates.length === 0 ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">Nothing yet.</span>
            <span className="usfind-label text-ink-soft">
              No likely matches on file. We&apos;ll keep looking as new items are
              filed.
            </span>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {candidates.map((c, index) => (
              <MatchCard
                key={c.item.id}
                candidate={c}
                index={index}
                otherEmailHint={`${(c.item.poster_name ?? "owner").toLowerCase()}@usf.edu`}
              />
            ))}
          </div>
        )}

        <div className="border-t border-line pt-6">
          <Button
            size="lg"
            variant="outline"
            render={<Link href="/search" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            Try conversational search →
          </Button>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
