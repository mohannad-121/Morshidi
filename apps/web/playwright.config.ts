import { defineConfig } from "@playwright/test";

const channel =
  process.env.PLAYWRIGHT_CHANNEL ??
  (process.platform === "win32" ? "msedge" : undefined);
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.pw.ts",
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: {
    baseURL,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...(channel ? { channel } : {}),
  },
  webServer: {
    command: "npm run dev -- --hostname localhost --port 3000",
    url: `${baseURL}/dev/voice-mascot-preview`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
