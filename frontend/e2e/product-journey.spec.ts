import { expect, test } from "@playwright/test";

test("decision-to-execution journey remains navigable and governed", async ({ page }) => {
  await page.goto("/decisions/scenarios");
  await expect(page.getByRole("heading", { name: "Scenario comparison" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Activate alternate source" })).toBeVisible();

  await page.goto("/decisions/recommendations");
  await expect(page.getByText("Protects the most revenue within budget.")).toBeVisible();

  await page.goto("/approvals");
  await page.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Approval approved and audit event recorded.")).toBeVisible();

  await page.goto("/executions");
  await expect(page.getByRole("heading", { name: "SWITCH SUPPLIER" })).toBeVisible();

  await page.goto("/workflows/version-1");
  await expect(page.getByLabel("Visual workflow graph")).toBeVisible();
  await expect(page.getByText("Published versions are immutable.")).toBeVisible();

  await page.goto("/simulations");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByText("Simulation completed with persisted stage lineage.")).toBeVisible();
  await expect(page.getByText("Verify outcome", { exact: true }).first()).toBeVisible();
});

test("primary screens do not overflow the viewport", async ({ page }) => {
  for (const path of ["/approvals", "/workflows", "/settings/integrations", "/audit"]) {
    await page.goto(path);
    const width = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: window.innerWidth }));
    expect(width.body).toBeLessThanOrEqual(width.viewport + 1);
  }
});

test("empty and failed API states remain explicit", async ({ page }) => {
  await page.goto("/disruptions");
  await expect(page.getByRole("heading", { name: "No incident feed is connected yet" })).toBeVisible();
  await page.goto("/suppliers");
  await expect(page.getByRole("heading", { name: "Supplier records will appear here" })).toBeVisible();
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "No audit events have been recorded" })).toBeVisible();
});
