import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const TECH = [
  "Next.js 16",
  "FastAPI",
  "Postgres / Neon",
  "Qdrant",
  "Redis",
  "Gemini Flash + Pro",
  "CLIP",
  "Cloudflare R2",
];

const FEATURES = [
  {
    title: "Auto-described from a photo",
    description:
      "Gemini Vision drafts a precise, factual description the moment you upload the photo. Edit it or accept it.",
    tag: "Vision LLM",
  },
  {
    title: "Conversational search",
    description:
      "“I lost a blue water bottle near the library yesterday” becomes typed filter chips plus a semantic search.",
    tag: "Flash + CLIP",
  },
  {
    title: "Explainable matches",
    description:
      "Two-stage retrieval: Qdrant HNSW recall → Gemini Pro re-rank. Every match comes with a one-sentence reason.",
    tag: "Recall → Rerank",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col flex-1">
      <header className="border-b">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="font-semibold tracking-tight">
            🎒 USFind
          </Link>
          <nav className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/browse" />}
              nativeButton={false}
            >
              Browse
            </Button>
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/search" />}
              nativeButton={false}
            >
              Search
            </Button>
            <Button
              variant="ghost"
              size="sm"
              render={<Link href="/stats" />}
              nativeButton={false}
            >
              Stats
            </Button>
            <Button
              size="sm"
              render={<Link href="/post" />}
              nativeButton={false}
            >
              Post an item
            </Button>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-16 px-6 py-16">
        <section className="flex flex-col items-start gap-6">
          <Badge variant="secondary" className="rounded-full">
            Built with a production-grade AI retrieval pipeline
          </Badge>
          <h1 className="text-balance text-5xl font-bold tracking-tight sm:text-6xl">
            Lost something on campus?
            <br />
            <span className="text-primary">Find it with AI.</span>
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            USFind matches lost &amp; found items at USF using multi-modal
            embeddings, a Qdrant vector index, and Gemini Pro re-ranking — so
            the matches come back ranked and explained, not just listed.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button
              size="lg"
              render={<Link href="/post" />}
              nativeButton={false}
            >
              Report an item
            </Button>
            <Button
              size="lg"
              variant="outline"
              render={<Link href="/search" />}
              nativeButton={false}
            >
              Try conversational search
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {TECH.map((tech) => (
              <Badge key={tech} variant="outline" className="font-medium">
                {tech}
              </Badge>
            ))}
          </div>
        </section>

        <Separator />

        <section className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <h2 className="text-3xl font-bold tracking-tight">
              Three AI features doing real work
            </h2>
            <p className="max-w-2xl text-muted-foreground">
              Not a chatbot bolted onto a CRUD app — every feature below is part
              of the matching loop and pays for itself in better recall.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {FEATURES.map((feature) => (
              <Card key={feature.title}>
                <CardHeader>
                  <Badge variant="secondary" className="mb-2 w-fit">
                    {feature.tag}
                  </Badge>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Read more on the{" "}
                  <Link
                    href="/stats"
                    className="font-medium text-foreground underline-offset-4 hover:underline"
                  >
                    engineering dashboard →
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <Separator />

        <section className="flex flex-col gap-4">
          <h2 className="text-3xl font-bold tracking-tight">
            The retrieval pipeline
          </h2>
          <Card>
            <CardContent className="pt-6">
              <pre className="overflow-x-auto whitespace-pre text-xs leading-relaxed text-muted-foreground sm:text-sm">
                {`Query item ─► CLIP image/text embeddings (cached, Redis)
            └► Qdrant HNSW: parallel image + text search, fused 0.7 / 0.3
                  └► top 50 candidates
                        └► Gemini 2.5 Pro re-rank with JSON schema
                              └► top 10 with explanations
                                    └► 24h rerank cache (keyed on
                                       query.updated_at + sorted ids)`}
              </pre>
            </CardContent>
          </Card>
        </section>
      </main>

      <footer className="border-t">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6 text-sm text-muted-foreground">
          <span>© USFind — built as a portfolio project.</span>
          <Link
            href="https://github.com/lhtminh/USFInd"
            className="hover:text-foreground"
          >
            GitHub →
          </Link>
        </div>
      </footer>
    </div>
  );
}
