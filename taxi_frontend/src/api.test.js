jest.mock("axios", () => {
  const get = jest.fn((url) => Promise.resolve({ data: { url } }));
  return { create: jest.fn(() => ({ get })) };
});

const loadApi = (demo) => {
  let api;
  process.env.REACT_APP_DEMO_MODE = demo ? "true" : "false";
  jest.isolateModules(() => {
    api = require("./api");
  });
  return api;
};

afterEach(() => {
  delete process.env.REACT_APP_DEMO_MODE;
});

test("live mode calls the REST API", async () => {
  const api = loadApi(false);
  expect(api.DEMO_MODE).toBe(false);
  expect((await api.getAnalytics("t1")).url).toBe("/analytics/t1/");
  expect(api.dailyCsvUrl("t1")).toBe("http://localhost:8000/api/analytics/t1/daily.csv");
});

test("demo mode reads the static snapshot files", async () => {
  const api = loadApi(true);
  expect(api.DEMO_MODE).toBe(true);
  expect((await api.getAnalytics("t1")).url).toBe("/analytics/t1.json");
  expect((await api.getTables()).url).toBe("/tables.json");
  expect(api.dailyCsvUrl("t1")).toBe("/demo-data/analytics/t1/daily.csv");
  expect(api.describeError({ response: { status: 404 } })).toMatch(/not included in the demo/);
});
