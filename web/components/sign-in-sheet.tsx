"use client";

import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { useAuth } from "@/components/auth-provider";

type Props = {
  trigger: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export function SignInSheet({ trigger, open, onOpenChange }: Props) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!email.includes("@")) {
      setError("Enter a valid email");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), name.trim() || undefined);
      onOpenChange?.(false);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetTrigger render={trigger as React.ReactElement} />
      <SheetContent side="right" className="w-80 sm:w-96">
        <SheetHeader className="text-left">
          <SheetTitle className="font-display text-2xl italic">
            Sign in
          </SheetTitle>
          <SheetDescription>
            Email-only. We just upsert a user record so you can post and
            confirm matches. No password.
          </SheetDescription>
        </SheetHeader>
        <form onSubmit={onSubmit} className="flex flex-col gap-4 px-4 pb-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="signin-email" className="usfind-label text-ink-soft">
              Email
            </Label>
            <Input
              id="signin-email"
              type="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@usf.edu"
              className="font-display text-base"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="signin-name" className="usfind-label text-ink-soft">
              Name (optional)
            </Label>
            <Input
              id="signin-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Mia"
              className="font-display text-base"
            />
          </div>
          {error ? (
            <p className="font-mono text-xs uppercase tracking-wider text-[oklch(0.5_0.2_28)]">
              {error}
            </p>
          ) : null}
          <Button
            type="submit"
            disabled={busy}
            className="mt-2 font-mono uppercase tracking-wider"
          >
            {busy ? "Signing in…" : "Continue →"}
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  );
}
