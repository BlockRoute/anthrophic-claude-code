/** Local-date helpers keyed as YYYY-MM-DD so logs are timezone-stable. */

export function dateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function todayKey(): string {
  return dateKey(new Date());
}

export function parseKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function shiftDate(key: string, deltaDays: number): string {
  const d = parseKey(key);
  d.setDate(d.getDate() + deltaDays);
  return dateKey(d);
}

export function daysBetween(a: string, b: string): number {
  const ms = parseKey(b).getTime() - parseKey(a).getTime();
  return Math.round(ms / 86_400_000);
}

const WEEKDAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function weekdayShort(key: string): string {
  return WEEKDAY[parseKey(key).getDay()];
}

export function prettyDate(key: string): string {
  const d = parseKey(key);
  return `${WEEKDAY[d.getDay()]}, ${MONTH[d.getMonth()]} ${d.getDate()}`;
}

export function lastNDays(n: number, end = todayKey()): string[] {
  return Array.from({ length: n }, (_, i) => shiftDate(end, -(n - 1 - i)));
}
