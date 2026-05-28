// Seeded mock data. Replace with FastAPI calls once the backend bridge lands.

export type ItemType = "lost" | "found";
export type ItemStatus = "open" | "matched" | "closed";

export type Item = {
  id: string;
  type: ItemType;
  status: ItemStatus;
  title: string;
  description: string;
  aiDescription?: string;
  location: string;
  imageUrl: string;
  poster: string;
  postedAt: Date;
};

export type Candidate = {
  item: Item;
  combinedScore: number;
  imageScore: number;
  textScore: number;
  rerankScore: number;
  explanation: string;
};

export type ConfirmedMatch = {
  id: string;
  query: Item;
  matched: Item;
  rerankScore: number;
  confirmedAt: Date;
};

const day = 1000 * 60 * 60 * 24;
const hour = 1000 * 60 * 60;
const now = Date.now();

const img = (seed: string) => `https://picsum.photos/seed/${seed}/640/640`;

export const items: Item[] = [
  {
    id: "blu-hydro-001",
    type: "lost",
    status: "open",
    title: "Blue Hydro Flask, 32 oz",
    description:
      "Standard mouth, dented near the base, sticker of a tortoise on the side.",
    aiDescription:
      "Cobalt blue insulated water bottle, ~1 L. Small white sticker of a sea turtle near the lower third. Visible dent on the bottom rim.",
    location: "Library, 4th floor",
    imageUrl: img("hydroflask-blue"),
    poster: "Mia",
    postedAt: new Date(now - 14 * hour),
  },
  {
    id: "fnd-hydro-002",
    type: "found",
    status: "open",
    title: "Blue water bottle on a study desk",
    description: "Left behind near the printers. No name.",
    aiDescription:
      "Blue stainless water bottle, large size, sticker on the body. Slight dent on the bottom edge.",
    location: "Library, 4th floor",
    imageUrl: img("hydroflask-blue-2"),
    poster: "Devon",
    postedAt: new Date(now - 6 * hour),
  },
  {
    id: "lost-backpack-003",
    type: "lost",
    status: "open",
    title: "Black Nike backpack with red logo",
    description: "Has a calculus textbook and a USB-C charger inside.",
    aiDescription:
      "Black backpack, Nike swoosh in red on the front panel, mesh side pocket. Slightly worn straps.",
    location: "Cooper Hall",
    imageUrl: img("backpack-black"),
    poster: "Alex",
    postedAt: new Date(now - 2 * day),
  },
  {
    id: "fnd-backpack-004",
    type: "found",
    status: "open",
    title: "Backpack left on a bench",
    description: "Black, looks new, with a red brand mark.",
    aiDescription:
      "Black school backpack, red logo on front, padded laptop sleeve inside. Visible wear on straps.",
    location: "MSC plaza",
    imageUrl: img("backpack-black-2"),
    poster: "Sam",
    postedAt: new Date(now - 1 * day),
  },
  {
    id: "fnd-keys-005",
    type: "found",
    status: "open",
    title: "Keychain with three keys and a USF lanyard",
    description: "Found on the lawn near the Marshall Center.",
    aiDescription:
      "Set of three brass keys on a green USF-branded lanyard with a small enamel bull pin.",
    location: "Marshall Center lawn",
    imageUrl: img("keys-lanyard"),
    poster: "Jordan",
    postedAt: new Date(now - 30 * hour),
  },
  {
    id: "lost-airpods-006",
    type: "lost",
    status: "open",
    title: "AirPods Pro case (white, small scratch)",
    description: "Lost during the morning lecture. Has a small scratch on the underside.",
    aiDescription:
      "White AirPods Pro 2 charging case, small superficial scratch on the bottom edge, otherwise clean.",
    location: "Cooper Hall, lecture 110",
    imageUrl: img("airpods-case"),
    poster: "Riley",
    postedAt: new Date(now - 5 * hour),
  },
  {
    id: "fnd-glasses-007",
    type: "found",
    status: "open",
    title: "Tortoise-shell reading glasses",
    description: "Found at the engineering library help desk.",
    aiDescription:
      "Brown tortoise-shell frame reading glasses, thin metal arms, no case.",
    location: "Engineering Library",
    imageUrl: img("glasses-tortoise"),
    poster: "Pat",
    postedAt: new Date(now - 3 * day),
  },
  {
    id: "lost-umbrella-008",
    type: "lost",
    status: "open",
    title: "Black compact umbrella, broken rib",
    description: "Probably left in a cafe. Has a small broken rib.",
    aiDescription:
      "Compact black telescoping umbrella, one broken rib on the back-left, soft grip handle.",
    location: "Argo Tea, MSC",
    imageUrl: img("umbrella-black"),
    poster: "Kiana",
    postedAt: new Date(now - 4 * day),
  },
  {
    id: "fnd-notebook-009",
    type: "found",
    status: "open",
    title: "Spiral notebook with calculus notes",
    description: "Left on a chair in the third-floor study area.",
    aiDescription:
      "Top-bound spiral notebook, 1-subject, light blue cover, handwritten calculus notes inside.",
    location: "Library, 3rd floor",
    imageUrl: img("notebook-calc"),
    poster: "Han",
    postedAt: new Date(now - 8 * hour),
  },
  {
    id: "lost-charger-010",
    type: "lost",
    status: "open",
    title: "USB-C 65W charger",
    description: "Black Anker brick with a braided cable.",
    aiDescription:
      "Black Anker 65 W USB-C wall charger and a braided black cable, about 1.8 m.",
    location: "Engineering Building 211",
    imageUrl: img("charger-anker"),
    poster: "Mira",
    postedAt: new Date(now - 26 * hour),
  },
  {
    id: "lost-wallet-011",
    type: "lost",
    status: "matched",
    title: "Brown bifold wallet",
    description: "Has USF student ID and a Publix card inside.",
    aiDescription:
      "Brown leather bifold wallet, faint wear on the corners, slot card layout.",
    location: "Sun Dome lot",
    imageUrl: img("wallet-brown"),
    poster: "Theo",
    postedAt: new Date(now - 6 * day),
  },
  {
    id: "fnd-wallet-012",
    type: "found",
    status: "matched",
    title: "Brown wallet on the curb",
    description: "Returned to the owner after confirmation.",
    aiDescription:
      "Brown bifold leather wallet found in the parking lot, contents intact.",
    location: "Sun Dome lot",
    imageUrl: img("wallet-brown-2"),
    poster: "Casey",
    postedAt: new Date(now - 6 * day),
  },
];

export function listItems(filter?: ItemType | "all"): Item[] {
  if (!filter || filter === "all") {
    return items.filter((i) => i.status === "open");
  }
  return items.filter((i) => i.type === filter && i.status === "open");
}

export function getItem(id: string): Item | undefined {
  return items.find((i) => i.id === id);
}

export function mockMatchesFor(id: string): Candidate[] {
  const query = getItem(id);
  if (!query) return [];
  const opposite = query.type === "lost" ? "found" : "lost";
  const pool = items.filter(
    (i) => i.type === opposite && i.status === "open" && i.id !== id,
  );
  // Deterministic-ish mock scoring based on string overlap.
  return pool
    .map((item) => {
      const overlap = sharedWords(query.title, item.title);
      const imageScore = clamp(0.55 + overlap * 0.12, 0, 1);
      const textScore = clamp(0.5 + overlap * 0.1, 0, 1);
      const combined = imageScore * 0.7 + textScore * 0.3;
      const rerank = Math.round(45 + overlap * 12 + (imageScore - 0.6) * 60);
      return {
        item,
        imageScore,
        textScore,
        combinedScore: combined,
        rerankScore: clamp(rerank, 25, 96),
        explanation: synthExplanation(query, item, overlap),
      };
    })
    .sort((a, b) => b.rerankScore - a.rerankScore)
    .slice(0, 6);
}

export const currentUser = { id: "u-mock", email: "mia@usf.edu", name: "Mia" };

export const myItems: Item[] = [items[0], items[10]];

export const confirmedMatches: ConfirmedMatch[] = [
  {
    id: "match-001",
    query: items[10],
    matched: items[11],
    rerankScore: 88,
    confirmedAt: new Date(now - 5 * day),
  },
];

export const mockStats = {
  users: 184,
  openItems: items.filter((i) => i.status === "open").length,
  lost: items.filter((i) => i.type === "lost").length,
  found: items.filter((i) => i.type === "found").length,
  matches: 24,
  matchSuccessRate: 0.42,
  latency: {
    stage1: { p50: 38, p95: 81, p99: 112 },
    stage2: { p50: 1820, p95: 3120, p99: 4400 },
    total: { p50: 1880, p95: 3210, p99: 4490 },
  },
  cacheRates: {
    imageEmb: 0.94,
    textEmb: 0.81,
    llm: 0.62,
    rerank: 0.83,
  },
  cost: {
    today: 0.42,
    last30: 8.91,
    perRetrieval: 0.0173,
    byEndpoint: {
      rerank: 6.4,
      auto_describe: 1.8,
      parse_search: 0.71,
    },
  },
  qdrant: {
    items_image: { points: 184, status: "green" },
    items_text: { points: 184, status: "green" },
  },
};

function sharedWords(a: string, b: string): number {
  const norm = (s: string) =>
    new Set(s.toLowerCase().replace(/[^a-z0-9 ]/g, "").split(/\s+/));
  const A = norm(a);
  const B = norm(b);
  let overlap = 0;
  for (const w of A) if (B.has(w) && w.length > 2) overlap += 1;
  return overlap;
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

function synthExplanation(q: Item, c: Item, overlap: number): string {
  if (overlap >= 2) {
    return `Strong color and shape agreement; both descriptions mention ${overlap} matching attributes. Locations are consistent.`;
  }
  if (overlap === 1) {
    return `Category matches and one descriptive attribute overlaps. Locations differ but are within campus.`;
  }
  return `Visually similar at first glance but distinguishing features differ; recommend a careful look in person.`;
}
