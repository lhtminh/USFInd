import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { ItemCard } from "@/components/item-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { api, type ApiItem } from "@/lib/api";

export const dynamic = "force-dynamic";

type SearchParams = Promise<{ filter?: string }>;
type ItemFilter = "lost" | "found" | "all";

export default async function BrowsePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { filter } = await searchParams;
  const current: ItemFilter =
    filter === "lost" || filter === "found" ? filter : "all";

  let items: ApiItem[] = [];
  let error: string | null = null;
  try {
    items = await api.listItems({
      type: current === "all" ? undefined : current,
      limit: 60,
    });
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8 px-4 py-12 sm:gap-10 sm:px-6 sm:py-16">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="usfind-label text-ink-soft mb-2">
              Inventory · open filings
            </div>
            <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
              Browse the <em>archive</em>.
            </h1>
          </div>
          <p className="usfind-label text-ink-soft max-w-xs">
            Every open item on campus. Filter by category, click to read the
            dossier.
          </p>
        </header>

        <Tabs defaultValue={current}>
          <TabsList className="font-mono uppercase tracking-wider bg-paper-soft border border-line">
            <TabsTrigger value="all" render={<Link href="/browse" />}>
              All
            </TabsTrigger>
            <TabsTrigger
              value="lost"
              render={<Link href="/browse?filter=lost" />}
            >
              Lost
            </TabsTrigger>
            <TabsTrigger
              value="found"
              render={<Link href="/browse?filter=found" />}
            >
              Found
            </TabsTrigger>
          </TabsList>
          <TabsContent value={current} className="mt-8">
            {error ? (
              <ApiDown message={error} />
            ) : items.length === 0 ? (
              <EmptyArchive />
            ) : (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((item, index) => (
                  <ItemCard key={item.id} item={item} index={index} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>

        <div className="flex items-center justify-between gap-3 border-t border-line pt-5 font-mono text-xs uppercase tracking-wider text-ink-soft">
          <span>
            <span className="text-ink">{items.length}</span> open items shown
          </span>
          <Button
            size="sm"
            variant="outline"
            render={<Link href="/post" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            File a new report →
          </Button>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}

function EmptyArchive() {
  return (
    <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
      <span className="font-display text-3xl italic">Nothing on file.</span>
      <span className="usfind-label text-ink-soft">
        No open items match this filter yet — try filing one.
      </span>
    </div>
  );
}

function ApiDown({ message }: { message: string }) {
  return (
    <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
      <span className="font-display text-3xl italic">
        The bureau is offline.
      </span>
      <p className="max-w-md text-ink-soft">
        Couldn&apos;t reach the API. Start the FastAPI server with{" "}
        <code className="font-mono">uvicorn api.main:app --port 8000</code>{" "}
        and reload.
      </p>
      <span className="font-mono text-[0.7rem] uppercase tracking-wider text-ink-soft">
        {message}
      </span>
    </div>
  );
}
