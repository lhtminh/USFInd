import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-line mt-24">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-8 font-mono text-xs uppercase tracking-wider text-ink-soft">
        <span>
          USFind / Dept. of Lost &amp; Found / Tampa, FL ·{" "}
          <span className="text-ink">
            Set in Newsreader &amp; JetBrains Mono
          </span>
        </span>
        <Link
          href="https://github.com/lhtminh/USFInd"
          className="hover:text-[var(--accent-strong)]"
        >
          → source on github
        </Link>
      </div>
    </footer>
  );
}
