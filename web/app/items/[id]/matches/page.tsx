import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { TypeBadge } from "@/components/item-card";
import { getItem, mockMatchesFor } from "@/lib/mock-data";
import { MatchCard } from "./match-card";
import { Button } from "@/components/ui/button";

type Params = Promise<{ id: string }>;

export default async function MatchesPage({ params }: { params: Params }) {
  const { id } = await params;
  const query = getItem(id);
  if (!query) notFound();

  const candidates = mockMatchesFor(id);

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-16">
        <div className="usfind-label text-ink-soft">
          <Link href={`/items/${query.id}`} className="hover:text-ink">
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
              src={query.imageUrl}
              alt={query.title}
              className="h-16 w-16 rounded-sm object-cover"
            />
            <div className="flex flex-col gap-1">
              <TypeBadge type={query.type} />
              <span className="font-display text-base leading-snug">
                {query.title}
              </span>
            </div>
          </div>
        </header>

        {/* Pipeline footnote moved to a single engineering dossier */}
        <PipelineFootnote />

        {candidates.length === 0 ? (
          <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
            <span className="font-display text-3xl italic">
              Nothing yet.
            </span>
            <span className="usfind-label text-ink-soft">
              No likely matches on file. We'll keep looking as new items are filed.
            </span>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {candidates.map((c, index) => (
              <MatchCard
                key={c.item.id}
                candidate={{
                  ...c,
                  item: { ...c.item, postedAt: c.item.postedAt.toISOString() },
                }}
                index={index}
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

function PipelineFootnote() {
  return (
    <div className="border border-line bg-paper-soft/60 px-5 py-4 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
      <span className="text-ink">Pipeline ·</span> Qdrant HNSW recall (top 50)
      → Gemini 2.5 Pro re-rank (top 10) ·{" "}
      <span className="text-ink">stage 1</span> 42 ms ·{" "}
      <span className="text-ink">stage 2</span> 1.84 s ·{" "}
      <span className="text-ink">cache</span> hit
    </div>
  );
}
