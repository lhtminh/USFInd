import Link from "next/link";
import { Button } from "@/components/ui/button";

export function SiteHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex w-full max-w-6xl items-end justify-between gap-6 px-6 py-5">
        <Link href="/" className="flex items-baseline gap-3 leading-none">
          <span className="font-display text-3xl italic tracking-tight">
            USFind
          </span>
          <span className="usfind-label text-ink-soft hidden sm:inline">
            Dept. of Lost &amp; Found · USF · vol. 01
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            render={<Link href="/browse" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            Browse
          </Button>
          <Button
            variant="ghost"
            size="sm"
            render={<Link href="/search" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            Search
          </Button>
          <Button
            variant="ghost"
            size="sm"
            render={<Link href="/me" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            Me
          </Button>
          <Button
            variant="ghost"
            size="sm"
            render={<Link href="/stats" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            Stats
          </Button>
          <Button
            size="sm"
            render={<Link href="/post" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            File a report →
          </Button>
        </nav>
      </div>
    </header>
  );
}
