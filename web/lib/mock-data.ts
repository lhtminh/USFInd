// Seeded mock data used by pages that aren't wired to FastAPI yet (/post, /me).
// Field names match ApiItem in lib/api.ts so ItemCard can render both.

export type ItemType = "lost" | "found";
export type ItemStatus = "open" | "matched" | "closed";

export type Item = {
  id: string;
  type: ItemType;
  status: ItemStatus;
  title: string;
  description: string | null;
  ai_description: string | null;
  location: string | null;
  image_url: string;
  poster_name: string | null;
  posted_at: string; // ISO
};

export type ConfirmedMatch = {
  id: string;
  query: Item;
  matched: Item;
  rerank_score: number;
  confirmed_at: string; // ISO
};

const day = 1000 * 60 * 60 * 24;
const hour = 1000 * 60 * 60;
const now = Date.now();
const iso = (ms: number) => new Date(ms).toISOString();
const img = (seed: string) => `https://picsum.photos/seed/${seed}/640/640`;

export const items: Item[] = [
  {
    id: "blu-hydro-001",
    type: "lost",
    status: "open",
    title: "Blue Hydro Flask, 32 oz",
    description:
      "Standard mouth, dented near the base, sticker of a tortoise on the side.",
    ai_description:
      "Cobalt blue insulated water bottle, ~1 L. Small white sticker of a sea turtle near the lower third. Visible dent on the bottom rim.",
    location: "Library, 4th floor",
    image_url: img("hydroflask-blue"),
    poster_name: "Mia",
    posted_at: iso(now - 14 * hour),
  },
  {
    id: "lost-backpack-003",
    type: "lost",
    status: "matched",
    title: "Brown bifold wallet",
    description: "Has USF student ID and a Publix card inside.",
    ai_description: "Brown leather bifold wallet, faint wear on the corners.",
    location: "Sun Dome lot",
    image_url: img("wallet-brown"),
    poster_name: "Mia",
    posted_at: iso(now - 6 * day),
  },
  {
    id: "fnd-wallet-012",
    type: "found",
    status: "matched",
    title: "Brown wallet on the curb",
    description: "Returned to the owner after confirmation.",
    ai_description: "Brown bifold leather wallet found in the parking lot.",
    location: "Sun Dome lot",
    image_url: img("wallet-brown-2"),
    poster_name: "Casey",
    posted_at: iso(now - 6 * day),
  },
];

export const currentUser = { id: "u-mock", email: "mia@usf.edu", name: "Mia" };
export const myItems: Item[] = [items[0], items[1]];
export const confirmedMatches: ConfirmedMatch[] = [
  {
    id: "match-001",
    query: items[1],
    matched: items[2],
    rerank_score: 88,
    confirmed_at: iso(now - 5 * day),
  },
];
