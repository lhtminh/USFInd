import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { relativeTimeFromIso } from "@/lib/api";

export type ItemCardItem = {
  id: string;
  type: "lost" | "found";
  status: "open" | "matched" | "closed";
  title: string;
  location: string | null;
  image_url: string;
  poster_name: string | null;
  posted_at: string; // ISO
};

type Props = {
  item: ItemCardItem;
  index?: number;
  className?: string;
  hrefBase?: string;
  showStatus?: boolean;
};

export function ItemCard({
  item,
  index,
  className,
  hrefBase = "/items",
  showStatus,
}: Props) {
  const tilt =
    typeof index === "number"
      ? ["-rotate-[0.4deg]", "rotate-[0.3deg]", "-rotate-[0.25deg]"][index % 3]
      : "";
  return (
    <Link
      href={`${hrefBase}/${item.id}`}
      className={cn(
        "usfind-card group relative flex flex-col overflow-hidden no-underline",
        tilt,
        className,
      )}
    >
      <span className="usfind-tape" aria-hidden />
      <div className="aspect-[4/3] overflow-hidden border-b border-line bg-paper-soft">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={item.image_url}
          alt={item.title}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.015]"
        />
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4 pt-5">
        <div className="flex items-center gap-2">
          <TypeBadge type={item.type} />
          {showStatus && item.status !== "open" ? (
            <StatusBadge status={item.status} />
          ) : null}
          {typeof index === "number" ? (
            <span className="ml-auto usfind-label text-ink-soft">
              #{(index + 1).toString().padStart(2, "0")}
            </span>
          ) : null}
        </div>
        <h3 className="font-display text-xl leading-snug">{item.title}</h3>
        <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
          {item.location ?? "—"}
          {item.poster_name ? ` · ${item.poster_name}` : ""} ·{" "}
          {relativeTimeFromIso(item.posted_at)}
        </p>
      </div>
    </Link>
  );
}

export function TypeBadge({ type }: { type: "lost" | "found" }) {
  const isLost = type === "lost";
  return (
    <Badge
      variant="secondary"
      className={cn(
        "font-mono uppercase tracking-widest text-[10px] px-2 py-0.5",
        isLost
          ? "bg-[oklch(0.93_0.07_30)] text-[oklch(0.38_0.16_28)]"
          : "bg-[oklch(0.93_0.05_140)] text-[oklch(0.38_0.10_150)]",
      )}
    >
      {type}
    </Badge>
  );
}

export function StatusBadge({
  status,
}: {
  status: "open" | "matched" | "closed";
}) {
  const styles: Record<string, string> = {
    open: "bg-[oklch(0.93_0.04_240)] text-[oklch(0.38_0.13_240)]",
    matched: "bg-[oklch(0.93_0.05_40)] text-[oklch(0.40_0.15_35)]",
    closed: "bg-[oklch(0.90_0.005_60)] text-[oklch(0.38_0.005_60)]",
  };
  return (
    <Badge
      variant="secondary"
      className={cn(
        "font-mono uppercase tracking-widest text-[10px] px-2 py-0.5",
        styles[status],
      )}
    >
      {status}
    </Badge>
  );
}
