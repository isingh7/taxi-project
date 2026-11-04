import { hourRange, minutes, money, moneyCompact, num, pct, shortDate, tableLabel } from "./format";
import { mapCenter } from "./components/LocationMap";

jest.mock("google-map-react", () => () => null);
jest.mock("./api", () => ({ DEMO_MODE: false }));

test("money uses US grouping regardless of browser locale", () => {
  expect(money(364154.82)).toBe("$364,154.82");
  expect(money(1234.5, 0)).toBe("$1,235");
  expect(moneyCompact(364154.82)).toBe("$364.2K");
});

test("missing values render as a dash, not NaN or a crash", () => {
  for (const f of [money, moneyCompact, num, pct, minutes, hourRange]) {
    expect(f(null)).toBe("–");
    expect(f(undefined)).toBe("–");
  }
});

test("number helpers", () => {
  expect(num(14073)).toBe("14,073");
  expect(num(2.414, 1)).toBe("2.4");
  expect(pct(92.888)).toBe("92.9%");
  expect(minutes(12.15)).toBe("12.2 min");
});

test("hourRange wraps at midnight", () => {
  expect(hourRange(23)).toBe("23:00–00:00");
  expect(hourRange(7)).toBe("07:00–08:00");
});

test("tableLabel turns table ids into readable names", () => {
  expect(tableLabel("tlc_yellow_trips_2015")).toBe("Yellow cab · 2015");
  expect(tableLabel("tlc_green_trips_2013")).toBe("Green cab · 2013");
  expect(tableLabel("something_else")).toBe("something_else");
});

test("shortDate is timezone-safe", () => {
  expect(shortDate("2015-01-01")).toBe("Jan 1");
});

test("mapCenter falls back to NYC when coordinates are missing", () => {
  expect(mapCenter({}, {})).toEqual({ lat: 40.7484, lng: -73.9857 });
  expect(mapCenter({ latitude: 40, longitude: -74 }, { latitude: 41, longitude: -73 })).toEqual({ lat: 40.5, lng: -73.5 });
});
