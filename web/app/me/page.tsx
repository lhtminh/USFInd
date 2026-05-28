import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { ItemCard, StatusBadge } from "@/components/item-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { currentUser, myItems, confirmedMatches } from "@/lib/mock-data";
import { relativeTimeFromIso } from "@/lib/api";

export default function MePage() {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-12 px-6 py-16">
        <header className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <div className="usfind-label text-ink-soft mb-2">
              Personal ledger · vol. 01
            </div>
            <h1 className="font-display text-5xl tracking-tight">
              Your <em>filings</em>, {currentUser.name}.
            </h1>
            <p className="mt-2 max-w-xl text-ink-soft">
              Posted items, confirmed matches, and the addresses we shared with
              the other party.
            </p>
          </div>
          <Badge
            variant="secondary"
            className="self-start font-mono uppercase tracking-widest"
          >
            ✶ Signed in · {currentUser.email}
          </Badge>
        </header>

        <section className="flex flex-col gap-6">
          <header className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="usfind-label text-ink-soft mb-1">
                § I — Your posts
              </div>
              <h2 className="font-display text-3xl tracking-tight">
                Items you've <em>filed</em>.
              </h2>
            </div>
            <Button
              size="sm"
              render={<Link href="/post" />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              File a new report →
            </Button>
          </header>
          {myItems.length === 0 ? (
            <div className="usfind-card p-8 text-center">
              <span className="font-display text-2xl italic">
                Nothing on file yet.
              </span>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {myItems.map((item, i) => (
                <ItemCard key={item.id} item={item} index={i} showStatus />
              ))}
            </div>
          )}
        </section>

        <section className="flex flex-col gap-6">
          <header>
            <div className="usfind-label text-ink-soft mb-1">
              § II — Confirmed matches
            </div>
            <h2 className="font-display text-3xl tracking-tight">
              Cases <em>closed</em>.
            </h2>
          </header>
          {confirmedMatches.length === 0 ? (
            <div className="usfind-card p-8 text-center">
              <span className="font-display text-2xl italic">
                No matches yet.
              </span>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {confirmedMatches.map((match) => (
                <article
                  key={match.id}
                  className="usfind-card relative grid gap-5 p-5 sm:grid-cols-[1fr_auto_1fr_auto]"
                >
                  <span className="usfind-tape" aria-hidden />
                  <div className="flex items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={match.query.image_url}
                      alt={match.query.title}
                      className="h-20 w-20 rounded-sm object-cover"
                    />
                    <div>
                      <div className="usfind-label text-ink-soft">
                        Your post
                      </div>
                      <div className="font-display text-lg">
                        {match.query.title}
                      </div>
                    </div>
                  </div>
                  <div className="hidden sm:flex items-center font-mono text-ink-soft">
                    ↔
                  </div>
                  <div className="flex items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={match.matched.image_url}
                      alt={match.matched.title}
                      className="h-20 w-20 rounded-sm object-cover"
                    />
                    <div>
                      <div className="usfind-label text-ink-soft">
                        Other party
                      </div>
                      <div className="font-display text-lg">
                        {match.matched.title}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <StatusBadge status="matched" />
                    <span className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                      Score {match.rerank_score} ·{" "}
                      {relativeTimeFromIso(match.confirmed_at)}
                    </span>
                    <Link
                      href={`mailto:${(match.matched.poster_name ?? "owner").toLowerCase()}@usf.edu`}
                      className="font-mono text-[0.72rem] uppercase tracking-wider text-[var(--accent-strong)] hover:underline"
                    >
                      Email {match.matched.poster_name ?? "the poster"}
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
