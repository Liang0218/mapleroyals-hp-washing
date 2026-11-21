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

test.beforeEach(async ({ page }, testInfo) => {
  // Most tests run on the default (all INT 0) gear, so they start past the one-time "compute with 0?" question.
  if (!testInfo.title.includes("[gear prompt]")) await page.addInitScript(() => sessionStorage.setItem("mapleroyals-hp-wash-zero-gear-ok", "1"));
  await page.goto("/");
});

test("simulate lists every policy with its explanation and picks one by click", async ({ page }) => {
  await openTab(page, "模擬");
  const options = page.locator(".policy-option");
  await expect(options).toHaveCount(4);
  for (const letter of ["A", "B", "C", "D"]) await expect(options.locator("b", { hasText: letter })).toBeVisible();
  await expect(options.locator(".policy-option-hint")).toHaveCount(4);
  await options.filter({ hasText: "Plain INT" }).click();
  await expect(page.locator(".policy-option:has(input:checked) .policy-option-name b")).toHaveText("D");
});

test("a running optimization stays on its own tab; the other calculator waits", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  const busyButton = page.locator(".run-button");
  await expect(busyButton).toHaveText(/計算中…/);
  await expect(page.locator(".run-actions").getByRole("button", { name: "取消" })).toBeVisible();

  await openTab(page, "模擬");
  const simulateButton = page.locator(".run-button");
  await expect(simulateButton).toHaveText("執行模擬");
  await expect(simulateButton).toBeDisabled();
  await expect(page.getByText("最佳化計算中，完成後才能執行模擬。")).toBeVisible();
  await expect(page.locator(".run-actions").getByRole("button", { name: "取消" })).toHaveCount(0);
  await expect(page.locator(".results-empty")).not.toContainText("正在");

  await openTab(page, "最佳化");
  await expect(page.locator(".specimen-tag")).toContainText("No.", { timeout: 90_000 });
  await openTab(page, "模擬");
  await expect(page.locator(".run-button")).toBeEnabled();
});

test("cancel stops the optimization and leaves no result", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  await page.locator(".run-actions").getByRole("button", { name: "取消" }).click();
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

test("the shown plan can be fine-tuned in place without leaving Optimize", async ({ page }) => {
  await runOptimizeToResult(page);
  const tuner = page.locator(".plan-tuner");
  await tuner.locator("> summary").click();
  const original = Number(await page.locator("#tune-int").inputValue());
  await page.locator("#tune-int").fill(String(original + 20));
  await page.locator("#tune-int").press("Enter");
  await expect(tuner.locator(".tuner-outcome")).toContainText("總 APR");
  // Only the difference shows; the full tuned plan stays folded until asked for.
  await expect(tuner.locator("#tuned-plan-view")).toBeHidden();
  await tuner.getByText("查看完整微調計畫與 CSV").click();
  await expect(tuner.locator("#tuned-plan-view")).toContainText(`base INT ${original + 20}`);
  await expect(page.getByRole("tab", { name: "最佳化", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".run-button")).toHaveText("執行最佳化");
});

test("a fine-tune that misses the goal leads with the shortfall, not the APR saved", async ({ page }) => {
  await runOptimizeToResult(page);
  const tuner = page.locator(".plan-tuner");
  await tuner.locator("> summary").click();
  await page.locator("#tune-end").fill("60");
  await tuner.getByRole("button", { name: "重算" }).click();
  const outcome = tuner.locator(".tuner-outcome");
  await expect(outcome).toHaveClass(/is-missed/);
  await expect(outcome.locator("b").first()).toHaveText("未達標");
  await expect(outcome).toContainText("HP 差");
});

test("a fine-tune can be reset to the original values", async ({ page }) => {
  await runOptimizeToResult(page);
  const tuner = page.locator(".plan-tuner");
  await tuner.locator("> summary").click();
  const original = await page.locator("#tune-int").inputValue();
  await page.locator("#tune-int").fill(String(Number(original) + 30));
  await tuner.getByRole("button", { name: "重算", exact: true }).click();
  await tuner.getByRole("button", { name: "回到原值" }).click();
  await expect(page.locator("#tune-int")).toHaveValue(original);
  await expect(tuner.locator(".tuner-result")).toHaveCount(0);
});

test("final HP is stated against its goal in words, with no bar", async ({ page }) => {
  await runOptimizeToResult(page);
  await expect(page.locator(".ruler")).toHaveCount(0);
  await expect(page.locator(".hp-versus")).toHaveText(/^最終 HP [\d,]+／目標 [\d,]+（(多|HP 差) [\d,]+）$/);
});

test("an unchanged fine-tune says so and adds no second plan", async ({ page }) => {
  await runOptimizeToResult(page);
  const tuner = page.locator(".plan-tuner");
  await tuner.locator("> summary").click();
  await tuner.getByRole("button", { name: "重算" }).click();
  await expect(tuner.locator(".tuner-outcome")).toContainText("結果與原計畫相同");
  await expect(tuner.locator("#tuned-plan-view")).toHaveCount(0);
});

test("the default simulation reaches its goal", async ({ page }) => {
  await openTab(page, "模擬");
  await page.getByRole("button", { name: "執行模擬" }).click();
  await expect(page.locator(".stamp")).toContainText("已達成目標", { timeout: 30_000 });
});

test("an empty Simulate tab offers the optimizer's recommendation", async ({ page }) => {
  await runOptimizeToResult(page);
  const code = (await page.locator(".specimen-tag").textContent())?.replace("No.", "").trim() ?? "";
  const [, int, washEnd] = code.split("·");
  await openTab(page, "模擬");
  await page.getByRole("button", { name: `帶入最佳化建議：${code}` }).click();
  await expect(page.locator("#field-targetInt")).toHaveValue(int);
  await expect(page.locator("#field-mpWashEnd")).toHaveValue(washEnd);
});

test("open in Simulate carries the policy and numbers over", async ({ page }) => {
  await runOptimizeToResult(page);
  const headline = await page.locator(".specimen-head h3").textContent();
  const [, letter, int, washEnd] = /Policy ([A-D]) · base INT (\d+) · MP wash 到 Lv (\d+)/.exec(headline ?? "") ?? [];
  await page.locator(".specimen-actions").getByRole("button", { name: "在模擬中開啟" }).click();
  await expect(page.getByRole("tab", { name: "模擬", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#field-targetInt")).toHaveValue(int);
  await expect(page.locator("#field-mpWashEnd")).toHaveValue(washEnd);
  await expect(page.locator(".policy-option:has(input:checked) .policy-option-name b")).toHaveText(letter);
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
  await expect(page.getByRole("alert")).toContainText("標紅的欄位");
  await expect(page.locator("#field-targetHp-error")).toContainText("目標 HP");
  await expect(page.locator("#field-targetHp")).toHaveAttribute("aria-invalid", "true");
  await expect(page.locator("#field-targetHp")).toBeFocused();

  // Fixing the value clears the error right away, before running again.
  await page.locator("#field-targetHp").fill("27000");
  await expect(page.locator("#field-targetHp-error")).toHaveCount(0);
  await expect(page.locator("#field-targetHp")).not.toHaveAttribute("aria-invalid", "true");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("an out-of-range value is flagged when leaving the field", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.locator("#field-resetLevel").fill("500");
  await page.locator("#field-targetHp").focus();
  await expect(page.locator("#field-resetLevel-error")).toContainText("超出範圍");
  await page.locator("#field-resetLevel").fill("155");
  await expect(page.locator("#field-resetLevel-error")).toHaveCount(0);
});

test("the run bar never covers the form", async ({ page }) => {
  await openTab(page, "最佳化");
  const position = await page.locator(".runbar").evaluate((element) => getComputedStyle(element).position);
  expect(position).toBe("static");
});

test("an opened plan band shows all its levels without an inner scroll box", async ({ page }) => {
  await runOptimizeToResult(page);
  const band = page.locator("#plan-view details.plan-step").nth(1);
  await band.locator("summary").click();
  const box = band.locator(".plan");
  const scrolls = await box.evaluate((element) => element.scrollHeight > element.clientHeight + 1);
  expect(scrolls).toBe(false);
});

test("[gear prompt] unset gear INT is asked about once before the first run", async ({ page }) => {
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  const prompt = page.locator(".gear-prompt");
  await expect(prompt).toContainText("還沒有設定裝備 INT");
  await expect(page.locator(".run-button")).toHaveCount(0);
  await prompt.getByRole("button", { name: "前往裝備頁設定" }).click();
  await expect(page.getByRole("tab", { name: "裝備", exact: true })).toHaveAttribute("aria-selected", "true");
  await openTab(page, "最佳化");
  await page.getByRole("button", { name: "執行最佳化" }).click();
  await page.locator(".gear-prompt").getByRole("button", { name: "仍以 0 計算" }).click();
  await expect(page.locator(".specimen-tag")).toContainText("No.", { timeout: 90_000 });
  // Answered once: the next run goes straight through.
  await openTab(page, "模擬");
  await page.getByRole("button", { name: "執行模擬" }).click();
  await expect(page.locator(".gear-prompt")).toHaveCount(0);
});

test("a result computed without gear INT says so on its label", async ({ page }) => {
  await runOptimizeToResult(page);
  await expect(page.locator(".specimen .extra-caution")).toContainText("未設定（以 0 計算）");
  await expect(page.locator(".calc-results .gear-warning")).toHaveCount(0);
  await page.locator(".extra-caution").getByRole("button", { name: "設定裝備後重算" }).click();
  await expect(page.getByRole("tab", { name: "裝備", exact: true })).toHaveAttribute("aria-selected", "true");
});

test("gear with INT is confirmed by the run button", async ({ page }) => {
  await openTab(page, "裝備");
  await page.getByLabel("裝備 3 INT", { exact: true }).fill("25");
  await openTab(page, "最佳化");
  await expect(page.locator(".runbar .gear-check")).toContainText("裝備 INT 已套用：1 件有 INT");
});

test("repeated levels merge into one line until show-all is on", async ({ page }) => {
  await runOptimizeToResult(page);
  const band = page.locator("#plan-view details.plan-step").first();
  await band.locator("summary").click();
  const levels = await band.locator(".plan-step-range-lead").textContent();
  const [, from, to] = /Lv (\d+)(?:–(\d+))?/.exec(levels ?? "") ?? [];
  const levelCount = Number(to ?? from) - Number(from) + 1;
  const merged = await band.locator("tbody tr").count();
  expect(merged).toBeLessThan(levelCount);
  await page.getByLabel("顯示全部等級").check();
  await expect(band.locator("tbody tr")).toHaveCount(levelCount);
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
    for (const name of ["使用指南", "最佳化", "模擬", "裝備", "職業數值", "策略說明"]) {
      await expect(page.getByRole("tab", { name, exact: true })).toBeInViewport();
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("a finished simulation brings its result into view and focuses it", async ({ page }) => {
    await openTab(page, "模擬");
    await page.getByRole("button", { name: "執行模擬" }).click();
    const heading = page.locator(".specimen-head h3");
    await expect(heading).toBeFocused({ timeout: 30_000 });
    await expect(heading).toBeInViewport();
    // The No. tag above the specimen's top edge lands in view too, not cut off.
    await expect.poll(() => page.locator(".specimen-tag").evaluate((element) => element.getBoundingClientRect().top)).toBeGreaterThanOrEqual(0);
  });
});
