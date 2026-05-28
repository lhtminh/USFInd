export function relativeTime(date: Date | string | number): string {
  const moment = new Date(date).getTime();
  const seconds = Math.max(0, (Date.now() - moment) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return `${Math.floor(seconds / 86400)} d ago`;
}

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}
