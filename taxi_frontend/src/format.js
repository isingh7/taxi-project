// All figures are USD for a New York business, so formatting is pinned to en-US
// rather than the browser locale (en-IN would print $3,64,154.82).
const LOCALE = "en-US";
const DASH = "–";

const isMissing = (v) => v === null || v === undefined || Number.isNaN(Number(v));

export const money = (v, digits = 2) =>
  isMissing(v)
    ? DASH
    : Number(v).toLocaleString(LOCALE, {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

/** $364,154 -> "$364.2K"; used where space is tight (KPI cards, axes). */
export const moneyCompact = (v) =>
  isMissing(v)
    ? DASH
    : Number(v).toLocaleString(LOCALE, {
        style: "currency",
        currency: "USD",
        notation: "compact",
        maximumFractionDigits: 1,
      });

export const num = (v, digits = 0) =>
  isMissing(v)
    ? DASH
    : Number(v).toLocaleString(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const pct = (v, digits = 1) => (isMissing(v) ? DASH : `${Number(v).toFixed(digits)}%`);

export const minutes = (v, digits = 1) => (isMissing(v) ? DASH : `${Number(v).toFixed(digits)} min`);

export const hourRange = (hour) => {
  if (isMissing(hour)) return DASH;
  const pad = (h) => String(h).padStart(2, "0");
  return `${pad(hour)}:00–${pad((Number(hour) + 1) % 24)}:00`;
};

export const tableLabel = (table) => {
  // "tlc_yellow_trips_2015" -> "Yellow cab · 2015"
  const match = /^tlc_(green|yellow)_trips_(\d{4})$/.exec(table || "");
  if (!match) return table || DASH;
  const [, color, year] = match;
  return `${color === "green" ? "Green" : "Yellow"} cab · ${year}`;
};

export const shortDate = (iso) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString(LOCALE, { month: "short", day: "numeric", timeZone: "UTC" });

export const dateTime = (iso) =>
  isMissing(Date.parse(iso))
    ? DASH
    : new Date(iso).toLocaleString(LOCALE, { dateStyle: "medium", timeStyle: "short" });
