"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { TypeBadge } from "@/components/item-card";
import { cn } from "@/lib/utils";
import { relativeTimeFromIso, type ApiCandidate } from "@/lib/api";

export function MatchCard({
  candidate,
  index,
  otherEmailHint,
}: {
  candidate: ApiCandidate;
  index: number;
  otherEmailHint: string;
}) {
  const [stage, setStage] = useState<"idle" | "confirming" | "done">("idle");
  const tilt = ["-rotate-[0.3deg]", "rotate-[0.2deg]"][index % 2];
  const rerank = Math.round(candidate.rerank_score ?? 0);

  return (
    <article className={cn("usfind-card relative p-5", tilt)}>
      <span className="usfind-tape" aria-hidden />
      <div className="absolute top-3 right-4 usfind-label text-ink-soft">
        Rank #{(index + 1).toString().padStart(2, "0")}
      </div>

      <div className="grid gap-5 sm:grid-cols-[180px_1fr]">
        <Link
          href={`/items/${candidate.item.id}`}
          className="overflow-hidden rounded-sm border border-line bg-paper-soft"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={candidate.item.image_url}
            alt={candidate.item.title}
            className="aspect-square w-full object-cover"
          />
        </Link>

        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <TypeBadge type={candidate.item.type} />
            <span className="usfind-label text-ink-soft">
              {candidate.item.location ?? "—"} ·{" "}
              {relativeTimeFromIso(candidate.item.posted_at)}
            </span>
          </div>
          <h3 className="font-display text-2xl leading-snug">
            {candidate.item.title}
          </h3>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
              <span>Match confidence</span>
              <span className="text-ink">{rerank}%</span>
            </div>
            <Progress value={rerank} className="h-2 bg-paper-soft" />
          </div>

          {candidate.explanation ? (
            <blockquote className="border-l-2 border-[var(--accent-strong)] pl-3 font-display text-base italic leading-relaxed text-ink-soft">
              “{candidate.explanation}”
            </blockquote>
          ) : null}

          <details className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
            <summary className="cursor-pointer text-ink-soft hover:text-ink">
              ✶ Technical scores
            </summary>
            <dl className="mt-2 grid grid-cols-3 gap-2 border border-line bg-paper-soft p-3">
              <KV k="combined" v={candidate.combined_score.toFixed(2)} />
              <KV k="image" v={candidate.image_score.toFixed(2)} />
              <KV k="text" v={candidate.text_score.toFixed(2)} />
            </dl>
          </details>

          <div className="mt-1 flex flex-wrap gap-2">
            {stage === "idle" ? (
              <>
                <Button
                  size="sm"
                  onClick={() => setStage("confirming")}
                  className="font-mono uppercase tracking-wider"
                >
                  ✶ This is mine!
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  render={<Link href={`/items/${candidate.item.id}`} />}
                  nativeButton={false}
                  className="font-mono uppercase tracking-wider"
                >
                  Read filing
                </Button>
              </>
            ) : stage === "confirming" ? (
              <div className="flex w-full flex-col gap-3 border border-[var(--accent-strong)] bg-paper-soft/70 p-3">
                <p className="font-display text-base">
                  Confirm? The poster&apos;s email will be shared with you.
                  <br />
                  <span className="font-mono text-[0.7rem] uppercase tracking-wider text-ink-soft">
                    (Confirmation endpoint wires up in the next pass.)
                  </span>
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => setStage("done")}
                    className="font-mono uppercase tracking-wider"
                  >
                    Yes, confirm
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setStage("idle")}
                    className="font-mono uppercase tracking-wider"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="w-full border border-[var(--accent-strong)] bg-paper-soft p-3 font-mono text-xs uppercase tracking-wider text-[var(--accent-strong)]">
                ✓ Match confirmed · contact:{" "}
                <span className="text-ink">{otherEmailHint}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-ink-soft">{k}</dt>
      <dd className="text-ink">{v}</dd>
    </div>
  );
}
