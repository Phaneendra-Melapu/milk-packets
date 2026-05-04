const { test, expect } = require("@playwright/test");

async function resetDay(request, date) {
  await request.put(`/api/milk/day/${date}/gold/0`);
  await request.put(`/api/milk/day/${date}/blue/0`);
  await request.put(`/api/milk/day/${date}/green/0`);
}

async function chooseDate(page, date) {
  const input = page.locator("#purchaseDate");
  await input.fill(date);
  await input.evaluate((element) => element.dispatchEvent(new Event("change", { bubbles: true })));
}

test("counts packet taps and updates the daily total", async ({ page }) => {
  const date = "2026-05-10";
  await resetDay(page.request, date);
  await page.goto("/");
  await chooseDate(page, date);

  await page.getByRole("button", { name: /Gold Rs 38 each/ }).click();
  await page.getByRole("button", { name: /Blue Rs 30 each/ }).click();
  await page.getByRole("button", { name: /Gold Rs 38 each/ }).click();

  await expect(page.locator("#totalPackets")).toHaveText("3");
  await expect(page.locator("#dailyTotal")).toHaveText("Rs 106");
  await expect(page.getByText("2 x Rs 38")).toBeVisible();
  await expect(page.getByText("1 x Rs 30")).toBeVisible();
});

test("cart controls can reduce a packet count", async ({ page }) => {
  const date = "2026-05-11";
  await resetDay(page.request, date);
  await page.goto("/");
  await chooseDate(page, date);

  await page.getByRole("button", { name: /Green Rs 33 each/ }).click();
  await page.getByRole("button", { name: /Green Rs 33 each/ }).click();
  await page.getByRole("button", { name: "Remove Green" }).click();

  await expect(page.locator("#totalPackets")).toHaveText("1");
  await expect(page.locator("#dailyTotal")).toHaveText("Rs 33");
});
