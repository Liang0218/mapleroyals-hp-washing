import { expect, test, type Page } from "@playwright/test";

// Each test starts from a fresh browser profile, so localStorage defaults apply (Thief, 27,000 HP, Chinese, auto theme).

async function openTab(page: Page, name: string) {
  await page.getByRole("tab", { name, exact: true }).click();
  await expect(page.getByRole("tab", { name, exact: true })).toHaveAttribute("aria-selected", "true");
}

async function runOptimizeToResult(page: Page) {
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  await expect(page.locator(".specimen-tag")).toContainText("No.", { timeout: 90_000 });
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("a running optimization stays on its own tab; the other calculator waits", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  const busyButton = page.locator(".run-button");
  await expect(busyButton).toHaveText(/計算中…/);
  await expect(page.getByRole("button", { name: "取消" })).toBeVisible();

  await openTab(page, "模擬");
  const simulateButton = page.locator(".run-button");
  await expect(simulateButton).toHaveText("執行模擬");
  await expect(simulateButton).toBeDisabled();
  await expect(page.getByText("最佳化計算中，完成後才能執行模擬。")).toBeVisible();
  await expect(page.getByRole("button", { name: "取消" })).toHaveCount(0);
  await expect(page.locator(".results-empty")).not.toContainText("正在");

  await openTab(page, "最佳化");
  await expect(page.locator(".specimen-tag")).toContainText("No.", { timeout: 90_000 });
  await openTab(page, "模擬");
  await expect(page.locator(".run-button")).toBeEnabled();
});

test("cancel stops the optimization and leaves no result", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  await page.getByRole("button", { name: "取消" }).click();
  await expect(page.locator(".run-button")).toHaveText("執行最佳化");
  await expect(page.locator(".run-button")).toBeEnabled();
  await expect(page.locator(".specimen")).toHaveCount(0);
});

test("selecting a policy card shows that policy's plan and CSV below", async ({ page }) => {
  await runOptimizeToResult(page);
  const cards = page.locator(".card-select");
  const count = await cards.count();
  expect(count).toBeGreaterThan(1);
  const pressed = await cards.evaluateAll((items) => items.map((item) => item.getAttribute("aria-pressed")));
  const target = cards.nth(pressed.findIndex((value) => value !== "true"));
  const label = (await target.locator(".policy-name").textContent())?.trim() ?? "";
  await target.click();
  await expect(target).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#plan-view .section-plate")).toContainText(`${label} 計畫`);

  const letter = /Policy ([A-D])/.exec(label)?.[1]?.toLowerCase();
  const download = page.waitForEvent("download");
  await page.locator("#plan-view").getByRole("button", { name: "下載 CSV" }).click();
  expect((await download).suggestedFilename()).toBe(`plan-policy-${letter}.csv`);
});

test("plan bands are continuous level ranges for every policy", async ({ page }) => {
  await runOptimizeToResult(page);
  const cards = page.locator(".card-select");
  for (let index = 0; index < await cards.count(); index += 1) {
    await cards.nth(index).click();
    const ranges = await page.locator("#plan-view .plan-step-range-lead").allTextContents();
    expect(ranges.length).toBeGreaterThan(0);
    let expected = 1;
    for (const text of ranges) {
      const match = /Lv (\d+)(?:–(\d+))?/.exec(text);
      expect(match, `unreadable range "${text}"`).not.toBeNull();
      const from = Number(match![1]);
      const to = Number(match![2] ?? match![1]);
      expect(from, `gap or overlap before "${text}"`).toBe(expected);
      expect(to).toBeGreaterThanOrEqual(from);
      expected = to + 1;
    }
    expect(expected - 1).toBe(200);
  }
});

test("open in Simulate carries the policy and numbers over", async ({ page }) => {
  await runOptimizeToResult(page);
  const headline = await page.locator(".specimen-head h3").textContent();
  const [, letter, int, washEnd] = /Policy ([A-D]) · base INT (\d+) · MP wash 到 Lv (\d+)/.exec(headline ?? "") ?? [];
  await page.locator(".specimen-actions").getByRole("button", { name: "在模擬中開啟" }).click();
  await expect(page.getByRole("tab", { name: "模擬", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#field-targetInt")).toHaveValue(int);
  await expect(page.locator("#field-mpWashEnd")).toHaveValue(washEnd);
  await expect(page.locator("#field-policy option:checked")).toContainText(`${letter} —`);
});

test("in English the whole result panel is English", async ({ page }) => {
  await runOptimizeToResult(page);
  await page.getByRole("button", { name: "EN" }).click();
  await expect(page.getByRole("tab", { name: "Optimize", exact: true })).toBeVisible();
  await page.locator("#plan-view details.plan-step").first().evaluate((element) => { (element as HTMLDetailsElement).open = true; });
  const text = await page.locator(".result-panel").innerText();
  const cjk = text.match(/[㐀-鿿（-？、。]+/g) ?? [];
  expect(cjk, `Chinese left in the English result: ${cjk.slice(0, 10).join(" | ")}`).toEqual([]);
});

test("each calculator keeps its own result", async ({ page }) => {
  await openTab(page, "模擬");
  await page.getByRole("button", { name: "執行模擬" }).click();
  await expect(page.locator(".specimen-tag")).toContainText("No.", { timeout: 90_000 });
  const simulated = await page.locator(".specimen-head h3").textContent();
  await runOptimizeToResult(page);
  await openTab(page, "模擬");
  await expect(page.locator(".specimen-head h3")).toHaveText(simulated ?? "");
});

test("an invalid input is reported on its field and focused", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.locator("#field-targetHp").fill("0");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  await expect(page.getByRole("alert")).toContainText("目標 HP");
  await expect(page.locator("#field-targetHp")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#field-targetHp")).toBeFocused();
});

test("tabs move with the arrow keys", async ({ page }) => {
  await page.getByRole("tab", { name: "使用指南", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "最佳化", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tab", { name: "最佳化", exact: true })).toBeFocused();
});

test("theme and language switches apply and persist", async ({ page }) => {
  await page.getByRole("button", { name: "深色" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "EN" }).click();
  await expect(page.getByRole("tab", { name: "Optimize", exact: true })).toBeVisible();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.screenshot({ path: "test-results/screens/guide-dark-en.png", fullPage: true });
});

test.describe("phone", () => {
  test.use({ viewport: { width: 390, height: 844 } });
  test("all tabs are reachable without horizontal scrolling", async ({ page }) => {
    for (const name of ["使用指南", "最佳化", "模擬", "裝備", "職業數值", "策略說明", "聯絡作者"]) {
      await expect(page.getByRole("tab", { name, exact: true })).toBeInViewport();
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
});
