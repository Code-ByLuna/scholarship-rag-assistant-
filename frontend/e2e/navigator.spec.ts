import { test, expect } from "@playwright/test";

test("profile to rules to cited detail to persistent assistant", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your next chapter starts here" }),
  ).toBeVisible();
  await expect(page.locator(".scholar-card")).toHaveCount(4);
  await page.screenshot({ path: "../var/dashboard.png", fullPage: true });
  await page.getByRole("button", { name: "Build my profile" }).click();
  await page.getByLabel(/^State/).fill("Kerala");
  await page.getByLabel(/^Category/).selectOption("OBC");
  await page.getByLabel(/^Annual Family Income/).fill("250000");
  await page.getByLabel(/^Course Level/).selectOption("undergraduate");
  await page.getByLabel(/^Year Of Study/).fill("3");
  await page.getByLabel(/^Study Mode/).selectOption("regular");
  await expect(page.getByLabel("Gender", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Find my scholarships" }).click();
  await expect(page.locator(".scholar-card")).toHaveCount(16);
  const candidate = page
    .locator(".scholar-card")
    .filter({ hasText: "PM-YASASVI" });
  await expect(candidate.locator(".badge")).toContainText("NEEDS VERIFICATION");
  await candidate.getByRole("link", { name: "View details" }).click();
  await expect(
    page.getByRole("heading", { name: "What we know" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "What is missing" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "What you need to verify" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Required documents", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Source information unavailable in dataset").first(),
  ).toBeVisible();
  await page
    .getByLabel("Ask a scholarship question")
    .fill("What is the income limit?");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(1, {
    timeout: 60000,
  });
  await expect(page.locator(".message.assistant")).toContainText("250000");
  await page.reload();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  expect(failures).toEqual([]);
});

test("mobile overview fits the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".scholar-card")).toHaveCount(4);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "../var/mobile.png", fullPage: true });
});
