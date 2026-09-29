import { defineConfig } from "@playwright/test";
import { outputs } from "./helpers/outputs";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["allure-playwright", { resultsDir: "../../build/allure-results/e2e" }],
  ],
  use: {
    baseURL: outputs.api_url,
    extraHTTPHeaders: { "content-type": "application/json" },
  },
});
