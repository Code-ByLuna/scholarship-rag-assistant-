import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: process.env.PLAYWRIGHT_BROWSER_CHANNEL || "msedge",
    headless: true,
  },
  reporter: [["list"], ["json", { outputFile: "../var/browser-report.json" }]],
  webServer: [
    {
      command:
        "python ../backend/manage.py runserver 127.0.0.1:8000 --noreload",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      timeout: 60000,
      env: { DJANGO_DEBUG: "true", LLM_PROVIDER: "none" },
    },
    {
      command: "npm run dev -- --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
