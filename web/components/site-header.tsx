"use client";

import Link from "next/link";
import { useState } from "react";
import { MenuIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useAuth } from "@/components/auth-provider";
import { SignInSheet } from "@/components/sign-in-sheet";

const NAV = [
  { href: "/browse", label: "Browse" },
  { href: "/search", label: "Search" },
  { href: "/me", label: "Me" },
  { href: "/stats", label: "Stats" },
];

export function SiteHeader() {
  const { user, signOut, loading } = useAuth();
  const [signInOpen, setSignInOpen] = useState(false);

  return (
    <header className="border-b border-line">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 sm:py-5">
        <Link href="/" className="flex items-baseline gap-3 leading-none">
          <span className="font-display text-2xl italic tracking-tight sm:text-3xl">
            USFind
          </span>
          <span className="usfind-label text-ink-soft hidden md:inline">
            Dept. of Lost &amp; Found · USF · vol. 01
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <Button
              key={item.href}
              variant="ghost"
              size="sm"
              render={<Link href={item.href} />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              {item.label}
            </Button>
          ))}
          {loading ? null : user ? (
            <>
              <span className="usfind-label ml-2 hidden text-ink-soft lg:inline">
                {user.name ?? user.email}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => signOut()}
                className="font-mono uppercase tracking-wider"
              >
                Sign out
              </Button>
              <Button
                size="sm"
                render={<Link href="/post" />}
                nativeButton={false}
                className="font-mono uppercase tracking-wider"
              >
                File a report →
              </Button>
            </>
          ) : (
            <SignInSheet
              open={signInOpen}
              onOpenChange={setSignInOpen}
              trigger={
                <Button
                  size="sm"
                  className="font-mono uppercase tracking-wider"
                >
                  Sign in
                </Button>
              }
            />
          )}
        </nav>

        {/* Mobile: condensed actions + hamburger */}
        <div className="flex items-center gap-2 md:hidden">
          {!loading && !user ? (
            <SignInSheet
              open={signInOpen}
              onOpenChange={setSignInOpen}
              trigger={
                <Button
                  size="sm"
                  className="font-mono uppercase tracking-wider"
                >
                  Sign in
                </Button>
              }
            />
          ) : null}
          {!loading && user ? (
            <Button
              size="sm"
              render={<Link href="/post" />}
              nativeButton={false}
              className="font-mono uppercase tracking-wider"
            >
              File →
            </Button>
          ) : null}
          <Sheet>
            <SheetTrigger
              render={
                <Button
                  variant="outline"
                  size="icon"
                  aria-label="Open navigation menu"
                />
              }
            >
              <MenuIcon />
            </SheetTrigger>
            <SheetContent side="right" className="w-72">
              <SheetHeader>
                <SheetTitle className="font-display text-2xl italic">
                  USFind
                </SheetTitle>
              </SheetHeader>
              <nav className="flex flex-col gap-1 px-3 pb-6">
                {NAV.map((item) => (
                  <SheetClose
                    key={item.href}
                    render={
                      <Link
                        href={item.href}
                        className="rounded-md px-3 py-3 font-mono text-sm uppercase tracking-wider text-ink hover:bg-paper-soft"
                      >
                        {item.label}
                      </Link>
                    }
                  />
                ))}
                <div className="mt-3 flex flex-col gap-2 border-t border-line pt-3">
                  {user ? (
                    <>
                      <SheetClose
                        render={
                          <Link
                            href="/post"
                            className="block rounded-md bg-primary px-3 py-3 text-center font-mono text-sm uppercase tracking-wider text-primary-foreground"
                          >
                            File a report →
                          </Link>
                        }
                      />
                      <span className="px-3 font-mono text-[0.7rem] uppercase tracking-wider text-ink-soft">
                        Signed in as {user.name ?? user.email}
                      </span>
                      <SheetClose
                        render={
                          <button
                            type="button"
                            onClick={() => signOut()}
                            className="rounded-md border border-line px-3 py-3 font-mono text-sm uppercase tracking-wider text-ink hover:bg-paper-soft"
                          >
                            Sign out
                          </button>
                        }
                      />
                    </>
                  ) : null}
                </div>
              </nav>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
