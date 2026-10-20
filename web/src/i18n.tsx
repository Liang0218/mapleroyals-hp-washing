import React from "react";

export type Language = "zh" | "en";

// Keep translations next to the rendering helper so all text nodes, including
// text inside shared components, follow the selected language.
const translations: Array<[string, string]> = [
  ["使用指南 Guide", "Guide"], ["職業數值 Job reference", "Job reference"], ["裝備 Equipment", "Equipment"],
  ["最佳化 Optimize", "Optimize"], ["模擬 Simulate", "Simulate"], ["策略說明 Actions", "Strategy guide"], ["聯絡作者 Contact Author", "Contact"],
  ["洗血涉及多項職業公式、能力值與遊戲機制，計算過程較為複雜。程式提供的最佳化結果可能有誤，請將結果作為參考，並在遊戲中操作前自行確認。", "HP washing uses job formulas, stats, and game mechanics. Treat optimizer results as estimates and verify them in game before acting."],
  ["使用指南", "Getting started"], ["先設定裝備 →", "Set up equipment →"], ["選擇職業", "Choose a job"], ["Thief 可比較 A／B／C／D 策略；其他職業使用 Policy D。", "Thieves can compare policies A, B, C, and D. Other jobs use Policy D."],
  ["設定 INT 裝備", "Set INT gear"], ["到「裝備 Equipment」頁編輯各等級可穿戴裝備，檢查 INT 區間預覽。", "Edit gear by equip level on the Equipment page, then review the INT preview."],
  ["執行最佳化", "Optimize"], ["輸入 HP／MP 目標與洗回 INT 條件，搜尋低 APR 計畫。", "Enter HP and MP goals and the INT reset level to find a low APR plan."],
  ["執行模擬", "Simulate"], ["指定 base INT 與 MP wash 結束等級，檢查單一計畫的逐級行動。", "Set base INT and the MP wash end level to inspect a plan level by level."],
  ["保留操作", "Your settings"], ["此瀏覽器會自動記住上次的裝備及各分頁設定。", "This browser saves your equipment and settings automatically."],
  ["計算提示", "Calculation note"], ["最佳化與模擬會依目前裝備清單及各自設定的洗回 INT 等級，即時更新 INT 裝備區間。", "The INT gear preview updates using your equipment list and the selected INT reset level."],
  ["裝備設定", "Equipment settings"], ["每種裝備槽取最高 INT；Ring 最多計入四件。下表會即時預覽各等級可用的總 INT。", "The highest INT item is used for each slot, with up to four rings. The table previews total available INT by level."],
  ["還原預設", "Restore defaults"], ["載入智力裝備設定", "Load INT gear"], ["儲存智力裝備設定", "Save INT gear"], ["新增裝備", "Add equipment"],
  ["整理裝備清單後，最佳化與模擬會依各自設定的洗回 INT 等級自動更新裝備 INT。", "Optimizer and simulator use this gear list and update available INT for their selected reset levels."],
  ["移除", "Remove"], ["重設後可用裝備 INT：", "Available gear INT after reset: "], ["等級", "Level"], ["裝備 INT", "Gear INT"],
  ["找不到有效的裝備資料；請確認 INT 與裝備等級。", "No valid equipment found. Check INT and equip levels."],
  ["最佳化計畫", "Optimization plan"], ["單一計畫模擬", "Plan simulation"],
  ["搜尋最佳 base INT 與 MP wash 結束等級，並比較適用策略。", "Search for an efficient base INT and MP wash end level, and compare applicable policies."],
  ["固定 base INT 與 MP wash 結束等級，模擬每一級的 AP／APR 行動。", "Simulate each level's AP and APR actions with a fixed base INT and MP wash end level."],
  ["基本參數與目標", "Core settings and goals"], ["以下設定只用於目前分頁", "These settings apply to this tab"], ["職業", "Job"], ["目標 HP", "Target HP"],
  ["目標 MP（留空表示不設定）", "Target MP (leave blank for none)"], ["目標等級（留空預設 200）", "Target level (defaults to 200)"],
  ["洗回 INT 等級", "INT reset level"], ["洗回後裝備 INT", "Gear INT after reset"], ["任務／裝備 HP", "Quest / gear HP"],
  ["HP 計算方式", "HP calculation"], ["平均 avg", "Average"], ["最低 min", "Minimum"], ["最高 max", "Maximum"],
  ["Maple Warrior 加成", "Maple Warrior bonus"], ["Maple Warrior 起始等級", "Maple Warrior start level"],
  ["裝備 INT 會從「裝備 Equipment」頁的裝備清單計算。", "Gear INT is calculated from the Equipment page."],
  ["最佳化比較策略", "Policies to compare"], ["只用於 Optimize", "Optimize only"], ["比較 Policy C（Hardcore greedy）", "Compare Policy C (Hardcore greedy)"],
  ["Policy C 會逐 AP 嘗試洗血與洗 MP，策略較繁瑣，搜尋也較耗時。關閉後只比較 A／B／D，可縮短最佳化時間。", "Policy C checks HP and MP washing for each AP, which makes the search slower. Turn it off to compare A, B, and D."],
  ["模擬參數", "Simulation settings"], ["只用於 Simulate", "Simulate only"], ["目標 base INT", "Target base INT"],
  ["MP wash 結束等級", "MP wash end level"], ["自動使用 Method 2 補足目標 HP", "Use Method 2 automatically to reach target HP"],
  ["接續既有角色 Resume", "Continue an existing character"], ["使用目前角色數值接續計算；APR 只統計此處輸入的 APR", "Continue from current character stats. APR counts only resets entered here."],
  ["目前等級", "Current level"], ["本等級尚未使用的 AP", "Unused AP at this level"], ["尚未洗回的 HP／MP AP", "Unwashed HP / MP AP"],
  ["INT 已洗回 4，角色不再有額外 INT", "INT has been reset to 4; no extra INT remains"],
  ["CSV 計畫輸出", "CSV plan export"], ["完成計算後可下載逐級計畫", "Download the level-by-level plan after calculation"],
  ["執行最佳化", "Run optimizer"], ["執行模擬", "Run simulation"], ["策略、洗法與計畫動作說明", "Policies, washing methods, and plan actions"],
  ["聯絡作者 Contact Author", "Contact the author"], ["若發現問題或有任何疑問，歡迎聯絡作者：", "For issues or questions, contact the author:"],
  ["最佳化結果", "Optimization result"], ["模擬結果", "Simulation result"], ["已達標", "Goal reached"], ["未達標", "Goal not reached"],
  ["目標 HP", "Target HP"], ["最終 HP", "Final HP"], ["最終 base MP", "Final base MP"], ["總 APR", "Total APR"], ["最佳 base INT", "Best base INT"],
  ["最佳策略", "Best policy"], ["MP wash 結束等級", "MP wash end level"], ["策略比較", "Policy comparison"], ["計畫步驟", "Plan steps"],
  ["下載 CSV", "Download CSV"], ["目標等級", "Target level"], ["繼續到 200 等最高 HP", "HP at level 200"], ["Action", "Action"],
  ["超過 30,000；建議提早做 Method 2", "Over 30,000; consider using Method 2 earlier"],
  ["抵達目標", "Target reached"], ["無法滿足目標：HP 已達標，但 MP 未達標", "Goal not met: HP reached, but MP did not"], ["無法達成目標：最接近結果", "Goal not met; showing the closest result"],
  ["未設定 MP 目標", "No MP goal set"], ["已達標", "Reached"], ["尚未達標", "Not reached"], ["結束", "end"],
  ["HP 目標", "HP goal"], ["MP 目標", "MP goal"], ["達標", "reached"], ["未達標", "not reached"],
  ["匯出 CSV", "Export CSV"],
  ["使用指南 Guide", "Guide"], ["職業數值 Job reference", "Job reference"], ["裝備 Equipment", "Equipment"],
  ["最佳化 Optimize", "Optimize"], ["模擬 Simulate", "Simulate"], ["說明 Actions", "Strategy guide"],
  ["英雄 Hero", "Hero"], ["聖騎士 Paladin", "Paladin"], ["黑騎士 Dark Knight", "Dark Knight"], ["弓箭手 Bowmaster／Marksman", "Bowmaster / Marksman"],
  ["盜賊 Night Lord／Shadower", "Night Lord / Shadower"], ["拳霸 Buccaneer", "Buccaneer"], ["槍神 Corsair", "Corsair"], ["初心者 Beginner", "Beginner"],
  ["目標 MP（留空則洗到最低）", "Target MP (leave blank to wash to minimum)"], ["目標等級（留空則表示 200 等）", "Target level (defaults to 200)"],
  ["角色與目標", "Character and goals"], ["此分頁專屬設定", "Tab-specific settings"], ["HP 模式", "HP mode"],
  ["洗回後升等裝備 INT", "Gear INT after reset level-up"], ["逐級計畫", "Level-by-level plan"], ["優勝計畫", "Winning plan"], ["備註", "Notes"],
  ["已達成目標", "Goal reached"], ["無法同時達標 — HP 已達標，MP 未達標", "Goals differ: HP reached, MP not reached"], ["無法達成 — 最接近結果", "Goal not reached; closest result"],
  ["實際", "actual"], ["每 APR 增加 HP 怎麼看", "How to read HP gained per APR"],
  ["職業洗血與成長數值", "Job HP washing and level-up values"],
  ["數值直接取自計算器使用的職業公式。範圍依 HP 模式不同而變；平均值模式會取範圍中點。", "Values come from the job formulas used by the calculator. Ranges depend on HP mode; Average uses the midpoint."],
  ["Method 1：先用 Fresh AP 加 HP，再用 APR 洗血，把 AP 點回其他能力值；表格列出這次操作增加的 HP。Method 2：不需要 Fresh AP，直接用 APR 扣 MP 換 HP。兩種方式都會消耗 1 APR，扣除該職業表列的 MP。", "Method 1 uses fresh AP for HP, then spends APR to remove the job's listed MP and returns AP to another stat. Method 2 spends APR to trade MP for HP without fresh AP. Both cost 1 APR."],
  ["MP wash 是消耗 1 APR 將 AP 點入 MP；每點增加的 MP 為表列職業範圍，再加上 ⌊base INT ÷ 10⌋。最小 MP 是洗血時不可低於的 base MP。", "MP washing spends 1 APR to add AP to MP. MP gained per point is the job range plus ⌊base INT ÷ 10⌋. Minimum MP is the base MP floor during HP washing."],
  ["轉職時額外增加", "Job advancement bonuses"], ["此表顯示計算器目前採用的轉職 HP／MP 固定值；3、4 轉的 AP 加成已列入。", "This table shows the fixed HP / MP job advancement bonuses used by the calculator, including AP bonuses for 3rd and 4th job."],
  ["升級 MP 的實際增加量 = 表列職業基礎範圍 + ⌊總 INT ÷ 10⌋；總 INT 會計入裝備 INT 與 Maple Warrior。Improve MaxHP 技能效果會依技能等級套用，升級 HP 加成與洗血 HP 加成分別列出。", "MP gained on level-up is the job's base range plus ⌊total INT ÷ 10⌋, including gear INT and Maple Warrior. Improve MaxHP scales by skill level; level-up and HP washing bonuses are listed separately."],
  ["無轉職加成", "No job advancement bonus"], ["Skill level × ", "Skill level × "], [" 等（", " (job "], [" 轉）：", "): "], ["、MP +", ", MP +"], ["、AP +", ", AP +"], ["；", "; "],
  [" × 等級 ", " × level "], ["技能：", " skill: "], ["每等級", "per level"], ["最高等級", "Max level"], ["（前置 SP ", " (requires SP "],
  ["中途接續 Resume", "Resume a character"],
  ["從目前角色狀態接續計算，APR 只統計接下來使用的 APR", "Continue from current character stats. APR counts only resets used from this point on."],
  ["本等尚未點的 AP", "Unspent AP at the current level"],
  ["INT 已洗回 4，之後不再點 INT", "INT has been reset to 4; do not add INT afterward"],
  ["沒有可用候選計畫", "No candidate plans available"], ["優勝策略", "Winning policy"],
  ["Method 1：用 Fresh AP 加 HP 後洗血", "Method 1: Use fresh AP for HP, then wash HP"],
  ["Method 2：直接用 APR 洗血換 HP", "Method 2: Spend APR to trade MP for HP"],
  ["轉職等級與額外 HP／MP／AP", "Job advancement level and bonus HP / MP / AP"],
  ["編輯裝備清單後，最佳化與模擬會依各自設定的 INT reset level 自動套用。", "After editing the gear list, Optimize and Simulate apply gear based on each tab's INT reset level."],
  ["編輯裝備清單後，最佳化與模擬會依各自設定的洗回 INT 等級自動套用。", "After editing the gear list, Optimize and Simulate apply gear based on each tab's INT reset level."],
  ["裝備 INT 會從「裝備 Equipment」分頁的裝備清單計算。", "Gear INT is calculated from the equipment list on the Equipment tab."],
  ["接續 Lv", "Resume at Lv"], ["接續乾淨 AP：", "Resume fresh AP: "], ["初始 AP 分配：", "Starting AP allocation: "], ["本等 AP 分配：", "AP allocation this level: "],
  ["本等剩餘 AP ", "Remaining AP this level "], [" 點由下一列分配", " points allocated on the next row"], ["待洗回 AP ", "AP pending reset "],
  [" 點 → ", " points → "], ["、", ", "], ["乾淨 AP ", "Fresh AP "], [" 點 → HP +", " points → HP +"], [" 點 → MP", " points → MP"],
  ["洗回 ", "Reset "], [" 點 AP（MP -", " AP (MP -"], ["）→ ", ") → "], ["剩餘 AP → ", "Remaining AP → "],
  ["洗回 AP 點入 INT ", "Reset AP into INT "], ["剩餘 AP 點入 ", "Remaining AP into "], ["MP 淨增加", "net MP gained"], ["MP 淨減少", "net MP lost"],
  ["洗回 AP → ", "Reset AP → "], ["Method 2：", "Method 2: "], ["技能等級 × ", "Skill level × "], ["：", ": "], ["，", ", "],
  ["混合 early：", "Mixed early: "], [" AP，MP ", " AP, MP "], ["Method 1 ", "Method 1 "], [" AP，HP +", " AP, HP +"], ["、MP -", ", MP -"],
  ["洗血：乾淨 AP ", "HP wash: Fresh AP "], [" 點 → HP （HP +", " points → HP (HP +"], ["（MP 淨增加 ", " (net MP gained "], ["）", ")"],
  ["注意：base MP 超過 30,000，建議提早做 Method 2", "Warning: base MP exceeds 30,000; consider using Method 2 earlier"],
  ["也可選擇在此提早做 Method 2：最多 ", "Optional early Method 2 here: up to "], [" 次（原計畫 200 等 ", " times (original plan: "], [" 次），當下 HP ", " times), HP at this point "], ["；繼續洗到 200 等可達 ", "; continuing to level 200 can reach "],
  ["31 等級起進入 INT 目標階段。Extra MP 達 threshold 時用 Method 1 洗 HP；不足時先 MP wash。", "Build INT from level 31. When Extra MP reaches the threshold, use Method 1 for HP; otherwise MP wash first."],
  ["Extra MP 足夠時用 Method 1；不足時把本等 AP 點入 INT，該列不增加洗血 APR。", "Use Method 1 when Extra MP is sufficient. Otherwise put this level's AP into INT without spending HP washing APR."],
  ["10 等起逐 AP 檢查：Extra MP 足夠就 HP1；30 等起可嘗試 MP1；剩餘 AP 投入 INT／主屬性。", "Check each AP from level 10: use HP1 when Extra MP allows; try MP1 from level 30; put remaining AP into INT or the main stat."],
  ["先集中 INT，達標後進行 MP wash、Method 1／Method 2 與 INT reset。非 Thief 職業使用此策略。", "Build INT first, then MP wash, Method 1 / Method 2, and reset INT. Non-Thief jobs use this policy."],
  ["使用當等級新鮮 AP 加 HP，再以 APR 扣除職業對應 MP；新鮮 AP 回到 INT 或主屬性。", "Use fresh AP to add HP, then spend APR to remove the job's corresponding MP. Fresh AP returns to INT or the main stat."],
  ["使用 APR 扣 Extra MP 換取 HP，沒有新鮮 AP 限制；計算會遵守設定的目標 base MP 下限。", "Spend APR to trade Extra MP for HP. This has no fresh AP limit and respects the target base MP floor."],
  ["計畫動作", "Plan actions"], ["建立初始能力值", "Build initial stats"], ["表示本等洗血／洗 MP", "means HP / MP washing at this level"], ["為 Method 2", "is Method 2"], ["為 INT 洗回", "is an INT reset"], ["標示接續起點", "marks the resume point"],
  ["最小 MP 公式", "Minimum MP formula"], ["200 等最小 MP", "Minimum MP at level 200"], ["每 APR 扣 MP", "MP removed per APR"],
  ["每 APR 增加 HP", "HP gained per APR"], ["MP wash 每點 AP 增加 MP", "MP gained per MP wash AP"], ["升級 HP（1–10 等）", "Level-up HP (levels 1–10)"],
  ["升級 HP（11 等起）", "Level-up HP (level 11+)"], ["升級 MP（11 等起）", "Level-up MP (level 11+)"], ["技能加成", "Skill bonus"], ["平均", "average"],
  ["HP 目標 ", "HP goal "], ["MP 目標 ", "MP goal "], ["，實際 ", ", actual "], ["（", " ("], ["）", ")"], ["。", "."],
];

export function translateText(value: string, language: Language): string {
  if (language === "zh") return value;
  let translated = value;
  for (const [source, target] of [...translations].sort((a, b) => b[0].length - a[0].length)) {
    translated = translated.replaceAll(source, target);
  }
  return translated;
}

export function translateTree(node: React.ReactNode, language: Language): React.ReactNode {
  if (typeof node === "string") return translateText(node, language);
  if (typeof node === "number" || node == null || typeof node === "boolean") return node;
  if (Array.isArray(node)) return node.map((child) => translateTree(child, language));
  if (!React.isValidElement(node)) return node;
  const props = node.props as Record<string, unknown>;
  const next: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(props)) {
    if (key === "children") next.children = translateTree(value as React.ReactNode, language);
    else if (typeof value === "string" && ["label", "title", "placeholder", "aria-label"].includes(key)) next[key] = translateText(value, language);
  }
  return React.cloneElement(node, next);
}
