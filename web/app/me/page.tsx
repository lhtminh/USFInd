"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { ItemCard, StatusBadge } from "@/components/item-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/components/auth-provider";
import { SignInSheet } from "@/components/sign-in-sheet";
import {
  api,
  relativeTimeFromIso,
  type ApiItem,
  type ApiMyMatch,
} from "@/lib/api";

export default function MePage() {
  const { user, loading } = useAuth();
  const [items, setItems] = useState<ApiItem[] | null>(null);
  const [matches, setMatches] = useState<ApiMyMatch[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setError(null);
    Promise.all([api.myItems(), api.myMatches()])
      .then(([its, ms]) => {
        if (cancelled) return;
        setItems(its);
        setMatches(ms);
      })
      .catch((exc) => {
        if (cancelled) return;
        setError(exc instanceof Error ? exc.message : "Couldn't load");
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  if (loading) {
    return <Shell>{null}</Shell>;
  }

  if (!user) {
    return (
      <Shell>
        <div className="usfind-card flex flex-col items-start gap-4 p-8">
          <div className="usfind-label text-ink-soft">
            Restricted · sign-in required
          </div>
          <h2 className="font-display text-3xl tracking-tight">
            Sign in to see your <em>ledger</em>.
          </h2>
          <p className="max-w-prose text-ink-soft">
            Your posts and confirmed matches are scoped to your email. Sign
            in to view them.
          </p>
          <SignInSheet
            trigger={
              <Button size="lg" className="font-mono uppercase tracking-wider">
                Sign in →
              </Button>
            }
          />
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <header className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <div className="usfind-label text-ink-soft mb-2">
            Personal ledger · vol. 01
          </div>
          <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
            Your <em>filings</em>, {user.name ?? user.email}.
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
          ✶ Signed in · {user.email}
        </Badge>
      </header>

      {error ? (
        <div className="border border-line bg-paper-soft p-4 font-mono text-xs uppercase tracking-wider text-ink-soft">
          {error}
        </div>
      ) : null}

      <section className="flex flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="usfind-label text-ink-soft mb-1">
              § I — Your posts
            </div>
            <h2 className="font-display text-3xl tracking-tight">
              Items you&apos;ve <em>filed</em>.
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
        {items === null ? (
          <SkeletonCards count={3} />
        ) : items.length === 0 ? (
          <div className="usfind-card p-8 text-center">
            <span className="font-display text-2xl italic">
              Nothing on file yet.
            </span>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item, i) => (
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
        {matches === null ? (
          <SkeletonCards count={1} />
        ) : matches.length === 0 ? (
          <div className="usfind-card p-8 text-center">
            <span className="font-display text-2xl italic">
              No matches yet.
            </span>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {matches.map((match) => (
              <article
                key={match.id}
                className="usfind-card relative flex flex-col gap-5 p-5"
              >
                <span className="usfind-tape" aria-hidden />
                <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
                  <Side
                    side={match.query}
                    fallbackLabel={match.query.is_mine ? "Your post" : "Other party"}
                  />
                  <div className="hidden font-mono text-2xl text-ink-soft sm:block">
                    ↔
                  </div>
                  <Side
                    side={match.matched}
                    fallbackLabel={match.matched.is_mine ? "Your post" : "Other party"}
                  />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-4 font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status="matched" />
                    <span>
                      Score {match.rerank_score ?? "—"} ·{" "}
                      {relativeTimeFromIso(match.confirmed_at)}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </Shell>
  );
}

function Side({
  side,
  fallbackLabel,
}: {
  side: ApiMyMatch["query"];
  fallbackLabel: string;
}) {
  return (
    <div className="flex items-center gap-3 border-t border-line pt-4 sm:border-none sm:pt-0">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={side.image_url}
        alt={side.title}
        className="h-20 w-20 flex-none rounded-sm object-cover"
      />
      <div className="min-w-0">
        <div className="usfind-label text-ink-soft">{fallbackLabel}</div>
        <div className="font-display text-lg leading-snug">{side.title}</div>
      </div>
    </div>
  );
}

function SkeletonCards({ count }: { count: number }) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="usfind-card h-64 animate-pulse bg-paper-soft"
          aria-hidden
        />
      ))}
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-10 px-4 py-12 sm:gap-12 sm:px-6 sm:py-16">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
