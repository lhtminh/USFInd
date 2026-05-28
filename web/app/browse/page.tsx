import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { ItemCard } from "@/components/item-card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { listItems, type ItemType } from "@/lib/mock-data";

type SearchParams = Promise<{ filter?: string }>;

export default async function BrowsePage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { filter } = await searchParams;
  const current: ItemType | "all" =
    filter === "lost" || filter === "found" ? filter : "all";

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-6 py-16">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="usfind-label text-ink-soft mb-2">
              Inventory · open filings
            </div>
            <h1 className="font-display text-5xl tracking-tight">
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
            <TabsTrigger value="lost" render={<Link href="/browse?filter=lost" />}>
              Lost
            </TabsTrigger>
            <TabsTrigger value="found" render={<Link href="/browse?filter=found" />}>
              Found
            </TabsTrigger>
          </TabsList>
          <TabsContent value={current} className="mt-8">
            <FilterGrid filter={current} />
          </TabsContent>
        </Tabs>

        <div className="flex items-center justify-between gap-3 border-t border-line pt-5 font-mono text-xs uppercase tracking-wider text-ink-soft">
          <span>
            <span className="text-ink">{listItems(current).length}</span> open
            items shown
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

function FilterGrid({ filter }: { filter: ItemType | "all" }) {
  const rows = listItems(filter);
  if (rows.length === 0) {
    return (
      <div className="usfind-card flex flex-col items-center gap-3 p-10 text-center">
        <span className="font-display text-3xl italic">Nothing on file.</span>
        <span className="usfind-label text-ink-soft">
          No open items match this filter yet.
        </span>
      </div>
    );
  }
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {rows.map((item, index) => (
        <ItemCard key={item.id} item={item} index={index} />
      ))}
    </div>
  );
}
