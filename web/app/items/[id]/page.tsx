import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import { TypeBadge, StatusBadge } from "@/components/item-card";
import { getItem } from "@/lib/mock-data";
import { relativeTime } from "@/lib/format";

type Params = Promise<{ id: string }>;

export default async function ItemDetailPage({ params }: { params: Params }) {
  const { id } = await params;
  const item = getItem(id);
  if (!item) {
    notFound();
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-6 py-16">
        <div className="usfind-label text-ink-soft">
          <Link href="/browse" className="hover:text-ink">
            ← back to the archive
          </Link>
        </div>

        <article className="grid gap-10 md:grid-cols-[1.1fr_1fr]">
          <div className="usfind-card relative overflow-hidden">
            <span className="usfind-tape" aria-hidden />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.imageUrl}
              alt={item.title}
              className="aspect-square w-full object-cover"
            />
          </div>

          <div className="flex flex-col gap-5">
            <div className="flex flex-wrap items-center gap-2">
              <TypeBadge type={item.type} />
              <StatusBadge status={item.status} />
              <span className="usfind-label text-ink-soft">
                Filed {relativeTime(item.postedAt)}
              </span>
            </div>
            <h1 className="font-display text-5xl leading-tight tracking-tight">
              {item.title}
            </h1>
            <div className="border-y border-line py-5">
              <div className="usfind-label text-ink-soft mb-2">
                ✶ As told by the poster
              </div>
              <p className="font-display text-lg leading-relaxed">
                {item.description}
              </p>
            </div>
            {item.aiDescription ? (
              <div>
                <div className="usfind-label text-[var(--accent-strong)] mb-2">
                  ✶ AI-described from the photo
                </div>
                <p className="font-display text-base italic leading-relaxed text-ink-soft">
                  “{item.aiDescription}”
                </p>
              </div>
            ) : null}

            <dl className="grid grid-cols-2 gap-4 border-t border-line pt-5 font-mono text-xs uppercase tracking-wider">
              <div>
                <dt className="text-ink-soft">Location</dt>
                <dd className="text-ink">{item.location}</dd>
              </div>
              <div>
                <dt className="text-ink-soft">Posted by</dt>
                <dd className="text-ink">{item.poster}</dd>
              </div>
              <div>
                <dt className="text-ink-soft">Filing #</dt>
                <dd className="text-ink">{item.id}</dd>
              </div>
              <div>
                <dt className="text-ink-soft">Status</dt>
                <dd className="text-ink">{item.status}</dd>
              </div>
            </dl>

            <div className="flex flex-wrap gap-3 pt-2">
              <Button
                size="lg"
                render={<Link href={`/items/${item.id}/matches`} />}
                nativeButton={false}
                className="font-mono uppercase tracking-wider"
              >
                ✶ Show possible matches →
              </Button>
              <Button
                size="lg"
                variant="outline"
                render={<Link href="/browse" />}
                nativeButton={false}
                className="font-mono uppercase tracking-wider"
              >
                Back to archive
              </Button>
            </div>
          </div>
        </article>
      </main>
      <SiteFooter />
    </div>
  );
}
