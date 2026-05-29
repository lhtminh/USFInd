"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const AI_SUGGESTIONS = [
  "Cobalt-blue insulated water bottle, ~1 L, sticker on the body, small dent on the lower rim.",
  "Black school backpack with a red logo on the front panel, padded laptop sleeve, slightly worn straps.",
  "Set of three brass keys on a green USF lanyard with a small enamel bull pin.",
  "White AirPods Pro 2 case with a small superficial scratch on the bottom edge.",
];

export default function PostPage() {
  const [preview, setPreview] = useState<string | null>(null);
  const [kind, setKind] = useState<"lost" | "found">("lost");
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    // Simulate Gemini Vision auto-description after a short delay.
    setAiSuggestion(null);
    setTimeout(() => {
      const next =
        AI_SUGGESTIONS[Math.floor(Math.random() * AI_SUGGESTIONS.length)];
      setAiSuggestion(next);
      if (!description.trim()) {
        setDescription(next);
      }
    }, 900);
  }

  function applySuggestion() {
    if (aiSuggestion) setDescription(aiSuggestion);
  }

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitted(true);
  }

  if (submitted) {
    return <Filed onReset={() => location.reload()} />;
  }

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-4 py-12 sm:gap-10 sm:px-6 sm:py-16">
        <header>
          <div className="usfind-label text-ink-soft mb-2">
            New entry · file a report
          </div>
          <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
            File a <em>report</em>.
          </h1>
          <p className="mt-3 max-w-xl text-lg text-ink-soft">
            Upload a photo and the Vision LLM will pre-fill the description.
            Edit anything you want before filing.
          </p>
        </header>

        <form onSubmit={onSubmit} className="flex flex-col gap-8">
          {/* lost / found switch */}
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

          {/* photo + preview */}
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

          {/* title */}
          <fieldset className="flex flex-col gap-2">
            <Label htmlFor="title" className="usfind-label text-ink-soft">
              Title
            </Label>
            <Input
              id="title"
              name="title"
              placeholder="e.g. Blue Hydro Flask with a turtle sticker"
              maxLength={200}
              required
              className="font-display text-lg"
            />
          </fieldset>

          {/* description with AI suggestion */}
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
              name="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={2000}
              rows={4}
              placeholder={
                preview
                  ? "We'll draft something from the photo in a moment…"
                  : "Color, brand, distinguishing marks…"
              }
              className="font-display text-base"
            />
            {aiSuggestion ? (
              <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                ✶ AI suggestion ready — feel free to edit or replace.
              </p>
            ) : preview ? (
              <p className="font-mono text-[0.72rem] uppercase tracking-wider text-ink-soft">
                ✶ Generating a description…
              </p>
            ) : null}
          </fieldset>

          {/* location */}
          <fieldset className="flex flex-col gap-2">
            <Label htmlFor="location" className="usfind-label text-ink-soft">
              Last seen / Found at
            </Label>
            <Input
              id="location"
              name="location"
              placeholder="Library 4th floor, MSC plaza, Cooper Hall 110…"
              maxLength={200}
              className="font-display text-lg"
            />
          </fieldset>

          <div className="flex flex-wrap items-center gap-3 border-t border-line pt-6">
            <Button
              type="submit"
              size="lg"
              className="font-mono uppercase tracking-wider"
            >
              File the report →
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

function Filed({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-start gap-6 px-4 py-16 sm:px-6 sm:py-24">
        <div className="usfind-label text-[var(--accent-strong)]">
          ✓ Filed · receipt #USF-08423
        </div>
        <h1 className="font-display text-4xl tracking-tight sm:text-5xl">
          Your report is <em>on the wire</em>.
        </h1>
        <p className="max-w-xl text-lg text-ink-soft">
          We embedded the photo + description and indexed it in Qdrant. If a
          counterpart shows up, you'll see it on the <em>matches</em> page —
          ranked, explained, and ready to confirm.
        </p>
        <div className="flex gap-3">
          <Button
            size="lg"
            render={<Link href="/browse" />}
            nativeButton={false}
            className="font-mono uppercase tracking-wider"
          >
            See the inventory →
          </Button>
          <Button
            size="lg"
            variant="outline"
            onClick={onReset}
            className="font-mono uppercase tracking-wider"
          >
            File another
          </Button>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
