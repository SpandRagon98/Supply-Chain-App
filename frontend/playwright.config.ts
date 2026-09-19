import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    { command: "node e2e/mock-api.mjs", port: 4010, reuseExistingServer: !process.env.CI },
    {
      command: "npm run start -- -p 3100",
      port: 3100,
      reuseExistingServer: !process.env.CI,
      env: { API_URL: "http://127.0.0.1:4010/api/v1" },
    },
  ],
});
