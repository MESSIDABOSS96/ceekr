interface DateGroup<T> {
  group: string;
  items: T[];
}

export function groupByDate<T>(
  items: T[],
  getDate: (item: T) => string,
): DateGroup<T>[] {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86_400_000;
  const weekStart = todayStart - 7 * 86_400_000;

  const buckets: Record<string, T[]> = {
    Today: [],
    Yesterday: [],
    "Previous 7 days": [],
    Older: [],
  };

  for (const item of items) {
    const ts = new Date(getDate(item)).getTime();
    if (ts >= todayStart) buckets.Today.push(item);
    else if (ts >= yesterdayStart) buckets.Yesterday.push(item);
    else if (ts >= weekStart) buckets["Previous 7 days"].push(item);
    else buckets.Older.push(item);
  }

  const order = ["Today", "Yesterday", "Previous 7 days", "Older"];
  return order
    .filter((g) => buckets[g].length > 0)
    .map((g) => ({ group: g, items: buckets[g] }));
}

export function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);

  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;

  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
