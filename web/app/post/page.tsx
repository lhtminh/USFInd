"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/components/auth-provider";
import { SignInSheet } from "@/components/sign-in-sheet";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function PostPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [kind, setKind] = useState<"lost" | "found">("lost");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
            Sign in to <em>file a report</em>.
          </h2>
          <p className="max-w-prose text-ink-soft">
            We need to know who&apos;s posting so the other party can reach you
            once a match is confirmed. Email only — no password.
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

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setPhoto(file);
    setAiSuggestion(null);
    if (!file) {
      setPreview(null);
      return;
    }
    setPreview(URL.createObjectURL(file));
    setAiBusy(true);
    try {
      const form = new FormData();
      form.append("photo", file);
      const { description: ai } = await api.autoDescribe(form);
      setAiSuggestion(ai);
      if (!description.trim()) {
        setDescription(ai);
      }
    } catch {
      // Silent: auto-describe is a nice-to-have, the user can type their own.
    } finally {
      setAiBusy(false);
    }
  }

  function applySuggestion() {
    if (aiSuggestion) setDescription(aiSuggestion);
  }

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!photo) {
      setError("A photo is required.");
      return;
    }
    if (!title.trim()) {
      setError("A title is required.");
      return;
    }
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("type", kind);
      form.append("title", title.trim());
      if (description.trim()) form.append("description", description.trim());
      if (location.trim()) form.append("location", location.trim());
      if (aiSuggestion) form.append("ai_description", aiSuggestion);
      form.append("photo", photo);
      const item = await api.createItem(form);
      router.push(`/items/${item.id}`);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Submit failed");
      setSubmitting(false);
    }
  }

  return (
    <Shell>
      <header>
        <div className="usfind-label text-ink-soft mb-2">
          New entry · file a report
        </div>
        <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
          File a <em>report</em>.
        </h1>
        <p className="mt-3 max-w-xl text-lg text-ink-soft">
          Upload a photo and the vision LLM will pre-fill the description. Edit
          anything before filing.
        </p>
      </header>

      <form onSubmit={onSubmit} className="flex flex-col gap-8">
        <fieldset className="flex flex-col gap-3">
          <Label className="usfind-label text-ink-soft">
            I am reporting
          </Label>
          <div className="flex gap-2 self-start rounded-md border border-line bg-paper-soft p-1">
            <KindToggle
              value="lost"
              current={kind}
              onSelect={setKind}
              label="Something I lost"
            />
            <KindToggle
              value="found"
              current={kind}
              onSelect={setKind}
              label="Something I found"
            />
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-3">
          <Label className="usfind-label text-ink-soft">Photo</Label>
          <div className="usfind-card relative grid gap-4 p-5 sm:grid-cols-[200px_1fr]">
            <span className="usfind-tape" aria-hidden />
            <div className="flex aspect-square items-center justify-center overflow-hidden rounded-sm border border-line bg-paper-soft">
              {preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={preview}
                  alt="Preview"
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="font-display text-xs uppercase tracking-widest text-ink-soft">
                  Add a photo
                </span>
              )}
            </div>
            <div className="flex flex-col justify-center gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={onFile}
                className="hidden"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                className="w-fit font-mono uppercase tracking-wider"
              >
                {preview ? "Replace photo" : "Choose a photo"}
              </Button>
              <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                JPEG / PNG / WEBP · max 5 MB · resized to 1600 px
              </p>
            </div>
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <Label htmlFor="title" className="usfind-label text-ink-soft">
            Title
          </Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Blue Hydro Flask with a turtle sticker"
            maxLength={200}
            required
            className="font-display text-lg"
          />
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Label
              htmlFor="description"
              className="usfind-label text-ink-soft"
            >
              Description
            </Label>
            {aiSuggestion ? (
              <button
                type="button"
                onClick={applySuggestion}
                className="font-mono text-[0.72rem] uppercase tracking-wider text-[var(--accent-strong)] underline-offset-4 hover:underline"
              >
                ✶ Apply AI suggestion
              </button>
            ) : null}
          </div>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={2000}
            rows={4}
            placeholder={
              preview
                ? aiBusy
                  ? "Drafting a description from the photo…"
                  : "Color, brand, distinguishing marks…"
                : "Color, brand, distinguishing marks…"
            }
            className="font-display text-base"
          />
          {aiBusy ? (
            <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
              ✶ Generating a description…
            </p>
          ) : aiSuggestion ? (
            <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
              ✶ AI suggestion ready — feel free to edit or replace.
            </p>
          ) : null}
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <Label htmlFor="location" className="usfind-label text-ink-soft">
            Last seen / Found at
          </Label>
          <Input
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Library 4th floor, MSC plaza, Cooper Hall 110…"
            maxLength={200}
            className="font-display text-lg"
          />
        </fieldset>

        {error ? (
          <div className="border border-[oklch(0.55_0.2_28)] bg-paper-soft p-3 font-mono text-xs uppercase tracking-wider text-[oklch(0.5_0.2_28)]">
            {error}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-3 border-t border-line pt-6">
          <Button
            type="submit"
            size="lg"
            disabled={submitting}
            className="font-mono uppercase tracking-wider"
          >
            {submitting ? "Filing…" : "File the report →"}
          </Button>
          <Button
            type="button"
            size="lg"
            variant="outline"
            render={<Link href="/browse" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            Cancel
          </Button>
          <Badge
            variant="secondary"
            className="ml-auto font-mono uppercase tracking-widest"
          >
            ✶ AI auto-description · enabled
          </Badge>
        </div>
      </form>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-4 py-12 sm:gap-10 sm:px-6 sm:py-16">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

function KindToggle({
  value,
  current,
  onSelect,
  label,
}: {
  value: "lost" | "found";
  current: "lost" | "found";
  onSelect: (v: "lost" | "found") => void;
  label: string;
}) {
  const active = current === value;
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={cn(
        "rounded-sm px-3 py-1.5 font-mono text-xs uppercase tracking-widest transition-colors",
        active
          ? "bg-paper text-ink shadow-[0_1px_0_oklch(0.20_0.01_55_/_0.06)]"
          : "text-ink-soft hover:text-ink",
      )}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}
