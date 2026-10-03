import { useEffect, useMemo, useRef, useState } from "react";
import { computeIntGearSegments, parseEquipment } from "./core/equipment";
import { EQUIPMENT_TYPES, totalApr, type EquipmentItem, type HpMode, type OptimizeResult, type PolicyName, type ResumeFrom, type SimulateResult } from "./core/models";
import { getJobProfile } from "./core/jobs";
import { JobReference } from "./JobReference";
import { optimize } from "./core/optimizer";
import { simulate } from "./core/simulator";
import { downloadText, readJsonFile } from "./file/browser";
import { planCsv } from "./file/plan-csv";

type Tab = "guide" | "job-reference" | "equipment" | "optimize" | "simulate" | "actions";
type ResumeFields = { level: string; baseHp: string; baseMp: string; extraMp: string; baseInt: string; baseLuk: string; baseDex: string; baseStr: string; freshAp: string; intResetDone: boolean; baseIntPeak: string };
type CalculatorConfig = {
  job: string; policy: PolicyName; targetHp: number; targetMp: string; targetInt: number;
  resetLevel: number; mpWashEnd: number; questHp: number; hpMode: HpMode;
  mwPercent: number; mwFromLevel: number; gearAfterReset: number; autoMethod2: boolean;
  resumeEnabled: boolean; resume: ResumeFields;
};
type AppCache = { version: 1; tab: Tab; equipment: EquipmentItem[]; optimize: CalculatorConfig; simulate: CalculatorConfig };

const CACHE_KEY = "mapleroyals-hp-wash-web-cache-v1";
const tabs: Array<{ id: Tab; label: string }> = [
  { id: "guide", label: "使用指南 Guide" }, { id: "job-reference", label: "職業數值 Job reference" }, { id: "equipment", label: "裝備 Equipment" },
  { id: "optimize", label: "最佳化 Optimize" }, { id: "simulate", label: "模擬 Simulate" },
  { id: "actions", label: "說明 Actions" },
];
const jobs = [
  ["fighter", "英雄 Hero"], ["page", "聖騎士 Paladin"], ["spearman", "黑騎士 Dark Knight"],
  ["bowman", "弓箭手 Bowmaster／Marksman"], ["thief", "盜賊 Night Lord／Shadower"],
  ["brawler", "拳霸 Buccaneer"], ["gunslinger", "槍神 Corsair"], ["beginner", "初心者 Beginner"],
] as const;
const policyLabels: Record<PolicyName, string> = {
  mp_wash_shortfall: "A — MP wash shortfall", int_dump_shortfall: "B — INT dump shortfall",
  mp_wash_hardcore: "C — Hardcore greedy", int_only_plain: "D — Plain INT",
};
const initialEquipment: EquipmentItem[] = [
  ["Green Bandana", "Hat", 10], ["Talking Witch Hat", "Hat", 20], ["Zakum Helmet", "Hat", 50],
  ["Rudolph's Shiny Nose", "Face Accessory", 30], ["White Raccoon Mask", "Eye Accessory", 45],
  ["Single Earring", "Earring", 15], ["Element Pierce", "Earring", 110], ["Spiegelmann's Necklace", "Pendant", 30],
  ["Horntail Necklace", "Pendant", 120], ["3rd Job Medal", "Medal", 70], ["4th Job Medal", "Medal", 120],
  ["Balrog Shoulder", "Shoulder", 75], ["Bathrobe for Women", "Overall", 20], ["Old Raggedy Cape", "Cape", 25],
  ["Ragged Red Cape", "Cape", 25], ["Crimsonheart Cloak", "Cape", 90], ["White Belt", "Belt", 50],
  ["red maker", "Glove", 20], ["Flamekeeper Cordon", "Glove", 50], ["Wooden Wand", "Weapon", 10],
  ["BroomStick", "Weapon", 20], ["Maple Shield", "Shield", 20], ["Ring of Alchemist", "Ring", 10],
  ["Ring of Alchemist", "Ring", 10], ["Ring of Alchemist", "Ring", 10], ["Ring of Alchemist", "Ring", 10],
  ["Circle Of Ancient Thought", "Ring", 20], ["Almighty Ring", "Ring", 70], ["white Snowshoes", "Shoe", 10],
].map(([name, type, equip_level]) => ({ name: String(name), type: type as EquipmentItem["type"], int: 0, equip_level: Number(equip_level) }));
const emptyResume: ResumeFields = { level: "", baseHp: "", baseMp: "", extraMp: "", baseInt: "", baseLuk: "4", baseDex: "25", baseStr: "4", freshAp: "5", intResetDone: false, baseIntPeak: "" };
function defaultConfig(): CalculatorConfig {
  return { job: "thief", policy: "mp_wash_shortfall", targetHp: 27000, targetMp: "", targetInt: 350, resetLevel: 155, mpWashEnd: 100, questHp: 0, hpMode: "avg", mwPercent: 0.1, mwFromLevel: 10, gearAfterReset: 50, autoMethod2: true, resumeEnabled: false, resume: { ...emptyResume } };
}
function readCache(): AppCache {
  const fallback: AppCache = { version: 1, tab: "guide", equipment: initialEquipment, optimize: defaultConfig(), simulate: defaultConfig() };
  try {
    const raw = JSON.parse(localStorage.getItem(CACHE_KEY) ?? "null") as Partial<AppCache> | null;
    if (!raw || raw.version !== 1) return fallback;
    const tabsAllowed = tabs.some((item) => item.id === raw.tab);
    return {
      version: 1, tab: tabsAllowed ? raw.tab! : fallback.tab,
      equipment: Array.isArray(raw.equipment) ? parseEquipment(raw.equipment) : fallback.equipment,
      optimize: { ...fallback.optimize, ...(raw.optimize ?? {}), resume: { ...emptyResume, ...(raw.optimize?.resume ?? {}) } },
      simulate: { ...fallback.simulate, ...(raw.simulate ?? {}), resume: { ...emptyResume, ...(raw.simulate?.resume ?? {}) } },
    };
  } catch { return fallback; }
}
const optionalNumber = (value: string): number | undefined => value.trim() === "" ? undefined : Number(value);
function Field({ label, value, onChange, type = "number", step }: { label: string; value: string | number; onChange: (value: string) => void; type?: string; step?: number | string }) {
  return <label>{label}<input type={type} step={step} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

export function App() {
  const [cache, setCache] = useState<AppCache>(readCache);
  const [result, setResult] = useState<SimulateResult>();
  const [optimized, setOptimized] = useState<OptimizeResult>();
  const [error, setError] = useState<string>();
  const equipmentInput = useRef<HTMLInputElement>(null);
  const { tab, equipment, optimize: optimizeConfig, simulate: simulateConfig } = cache;
  const config = tab === "simulate" ? simulateConfig : optimizeConfig;
  const profile = getJobProfile(config.job);
  const effectivePolicy = profile.policies.includes(config.policy) ? config.policy : profile.policies[0];
  const gearPreview = useMemo(() => {
    try { return computeIntGearSegments(equipment, Math.max(1, optimizeConfig.resetLevel - 1)); }
    catch { return []; }
  }, [equipment, optimizeConfig.resetLevel]);

  useEffect(() => {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); }
    catch { /* Browser storage may be unavailable or full. */ }
  }, [cache]);

  function updateConfig(patch: Partial<CalculatorConfig>) {
    setCache((previous) => tab === "simulate"
      ? { ...previous, simulate: { ...previous.simulate, ...patch } }
      : { ...previous, optimize: { ...previous.optimize, ...patch } });
  }
  function updateResume(patch: Partial<ResumeFields>) { updateConfig({ resume: { ...config.resume, ...patch } }); }
  function changeTab(next: Tab) { setCache((previous) => ({ ...previous, tab: next })); setError(undefined); }
  function buildResume(current: CalculatorConfig): ResumeFrom | undefined {
    if (!current.resumeEnabled) return undefined;
    const level = optionalNumber(current.resume.level); const base_hp = optionalNumber(current.resume.baseHp); const base_int = optionalNumber(current.resume.baseInt);
    if (level === undefined || base_hp === undefined || base_int === undefined) throw new Error("接續計算請填寫目前等級、base HP 與 base INT。");
    const base_mp = optionalNumber(current.resume.baseMp) ?? (() => {
      const extra = optionalNumber(current.resume.extraMp);
      if (extra === undefined) throw new Error("base MP 與 Extra MP 請至少填一項。");
      return profile.minMp(level) + extra;
    })();
    return { level, base_hp, base_mp, base_int, base_luk: Number(current.resume.baseLuk), base_dex: Number(current.resume.baseDex), base_str: Number(current.resume.baseStr), fresh_ap: optionalNumber(current.resume.freshAp), int_reset_done: current.resume.intResetDone, base_int_peak: optionalNumber(current.resume.baseIntPeak) };
  }
  function sharedConfig(current: CalculatorConfig) {
    const intGear = computeIntGearSegments(equipment, Math.max(1, current.resetLevel - 1));
    return { target_hp: current.targetHp, target_mp: optionalNumber(current.targetMp), int_reset_level: current.resetLevel, int_gear: intGear, job: current.job, int_gear_after_reset: current.gearAfterReset, quest_equip_hp: current.questHp, hp_mode: current.hpMode, mw_percent: current.mwPercent, mw_from_level: current.mwFromLevel, resume_from: buildResume(current) };
  }
  function runSimulate() {
    try {
      const activeProfile = getJobProfile(simulateConfig.job);
      const policy = activeProfile.policies.includes(simulateConfig.policy) ? simulateConfig.policy : activeProfile.policies[0];
      setError(undefined); setOptimized(undefined);
      setResult(simulate({ ...sharedConfig(simulateConfig), policy, target_base_int: simulateConfig.targetInt, mp_wash_end: simulateConfig.mpWashEnd, auto_method2: simulateConfig.autoMethod2 }));
    } catch (caught) { setResult(undefined); setError(caught instanceof Error ? caught.message : "模擬失敗"); }
  }
  function runOptimize() {
    try {
      const activeProfile = getJobProfile(optimizeConfig.job);
      setError(undefined); setResult(undefined);
      setOptimized(optimize({
        ...sharedConfig(optimizeConfig), policies: [...activeProfile.policies],
        target_base_int_min: 100, target_base_int_max: 500, target_base_int_step: 10,
        mp_wash_end_min: 31, top_n: 5,
      }));
    } catch (caught) { setOptimized(undefined); setError(caught instanceof Error ? caught.message : "最佳化失敗"); }
  }
  async function importEquipment(file?: File) {
    if (!file) return;
    try { const items = parseEquipment(await readJsonFile(file)); setCache((previous) => ({ ...previous, equipment: items })); setError(undefined); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "裝備設定載入失敗"); }
  }
  function addEquipment() { setCache((previous) => ({ ...previous, equipment: [...previous.equipment, { name: "", type: "Hat", int: 0, equip_level: 10 }] })); }
  function updateEquipment(index: number, patch: Partial<EquipmentItem>) {
    setCache((previous) => ({ ...previous, equipment: previous.equipment.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }));
  }
  function removeEquipment(index: number) { setCache((previous) => ({ ...previous, equipment: previous.equipment.filter((_, itemIndex) => itemIndex !== index) })); }
  function restoreDefaults() { setCache((previous) => ({ ...previous, equipment: initialEquipment.map((item) => ({ ...item })) })); }

  return <main className="app-shell">
    <header className="app-header"><div><p className="eyebrow">MapleRoyals</p><h1>HP Washing APR Optimizer</h1></div></header>
    <nav className="tabbar" aria-label="Calculator sections">{tabs.map((item) => <button key={item.id} type="button" className={tab === item.id ? "tab active" : "tab"} onClick={() => changeTab(item.id)}>{item.label}</button>)}</nav>
    {error && <p className="error global-error" role="alert">{error}</p>}

    {tab === "guide" && <section className="page-card"><div className="section-heading"><div><p className="eyebrow">Guide</p><h2>使用指南</h2></div><button type="button" onClick={() => changeTab("equipment")}>先設定裝備 →</button></div><ol className="guide-steps"><li><b>選擇職業</b><span>Thief 可比較 A／B／C／D 策略；其他職業使用 Policy D。</span></li><li><b>設定 INT 裝備</b><span>到「裝備 Equipment」頁編輯各等級可穿戴裝備，檢查 INT 區間預覽。</span></li><li><b>執行最佳化</b><span>輸入 HP／MP 目標與 INT reset 條件，搜尋低 APR 計畫。</span></li><li><b>執行模擬</b><span>指定 base INT 與 MP wash 結束等級，檢查單一計畫的逐級行動。</span></li><li><b>保留操作</b><span>此瀏覽器會自動記住上次的裝備及各分頁設定。</span></li></ol><div className="guide-note"><b>計算提示</b><p>最佳化與模擬會依目前裝備清單及各自的 INT reset level 即時更新 INT 裝備區間。</p></div></section>}

    {tab === "equipment" && <section className="page-card equipment-page"><div className="section-heading"><div><p className="eyebrow">Equipment</p><h2>裝備設定</h2><p className="subheading">每種裝備槽取最高 INT；Ring 最多計入四件。下表會即時預覽各等級可用的總 INT。</p></div><div className="button-row"><input ref={equipmentInput} className="visually-hidden" type="file" accept="application/json,.json" onChange={(event) => void importEquipment(event.target.files?.[0])} /><button className="quiet" type="button" onClick={restoreDefaults}>還原預設</button><button className="quiet" type="button" onClick={() => equipmentInput.current?.click()}>載入智力裝備設定</button><button className="quiet" type="button" onClick={() => downloadText("int-equipment-settings.json", `${JSON.stringify(equipment, null, 2)}\n`, "application/json;charset=utf-8")}>儲存智力裝備設定</button></div></div>
      <div className="equipment-toolbar"><button type="button" onClick={addEquipment}>＋ 新增裝備</button><span className="equipment-auto-note">編輯裝備清單後，最佳化與模擬會依各自設定的 INT reset level 自動套用。</span></div>
      <div className="equipment-layout"><div className="equipment-table-wrap"><table className="equipment-table"><thead><tr><th>Equipment Name</th><th>Type</th><th>INT</th><th>Level to Equip</th><th></th></tr></thead><tbody>{equipment.map((item, index) => <tr key={`${index}-${item.name}`}><td><input aria-label={`Equipment ${index + 1} name`} value={item.name} onChange={(event) => updateEquipment(index, { name: event.target.value })} /></td><td><select aria-label={`Equipment ${index + 1} type`} value={item.type} onChange={(event) => updateEquipment(index, { type: event.target.value as EquipmentItem["type"] })}>{EQUIPMENT_TYPES.map((type) => <option key={type}>{type}</option>)}</select></td><td><input aria-label={`Equipment ${index + 1} INT`} type="number" min="0" value={item.int} onChange={(event) => updateEquipment(index, { int: Number(event.target.value) })} /></td><td><input aria-label={`Equipment ${index + 1} level`} type="number" min="1" value={item.equip_level} onChange={(event) => updateEquipment(index, { equip_level: Number(event.target.value) })} /></td><td><button className="remove" type="button" aria-label={`Remove equipment ${index + 1}`} onClick={() => removeEquipment(index)}>移除</button></td></tr>)}</tbody></table></div>
        <aside className="gear-preview"><h3>INT gear preview</h3><p>Reset 後裝備 INT：{optimizeConfig.gearAfterReset}</p>{gearPreview.length ? <table><thead><tr><th>等級</th><th>裝備 INT</th></tr></thead><tbody>{gearPreview.map((segment) => <tr key={segment.from_level}><td>{segment.from_level}–{segment.to_level}</td><td>{segment.int_gear}</td></tr>)}</tbody></table> : <p className="error">請檢查裝備名稱、INT 與裝備等級。</p>}</aside></div>
    </section>}

    {tab === "job-reference" && <JobReference />}

    {(tab === "optimize" || tab === "simulate") && <section className="calculator-page">
      <div className="page-title"><div><p className="eyebrow">{tab === "optimize" ? "Optimize" : "Simulate"}</p><h2>{tab === "optimize" ? "最佳化計畫" : "單一計畫模擬"}</h2><p className="subheading">{tab === "optimize" ? "搜尋最佳 base INT 與 MP wash 結束等級，並比較適用策略。" : "固定 base INT 與 MP wash 結束等級，模擬每一級的 AP／APR 行動。"}</p></div></div>
      <div className="form-section"><h3>角色與目標 <span>此分頁專屬設定</span></h3><div className="fields">
        <label>職業<select value={config.job} onChange={(event) => updateConfig({ job: event.target.value })}>{jobs.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <Field label="目標 HP" value={config.targetHp} onChange={(value) => updateConfig({ targetHp: Number(value) })} />
        <Field label="目標 base MP（可空）" value={config.targetMp} onChange={(value) => updateConfig({ targetMp: value })} />
        <Field label="INT reset level" value={config.resetLevel} onChange={(value) => updateConfig({ resetLevel: Number(value) })} />
        <Field label="reset 後裝備 INT" value={config.gearAfterReset} onChange={(value) => updateConfig({ gearAfterReset: Number(value) })} />
        <Field label="任務／裝備 HP" value={config.questHp} onChange={(value) => updateConfig({ questHp: Number(value) })} />
        <label>HP 模式<select value={config.hpMode} onChange={(event) => updateConfig({ hpMode: event.target.value as HpMode })}><option value="avg">平均 avg</option><option value="min">最低 min</option><option value="max">最高 max</option></select></label>
        <Field label="Maple Warrior 比例" value={config.mwPercent} step="0.01" onChange={(value) => updateConfig({ mwPercent: Number(value) })} />
        <Field label="Maple Warrior 起始等級" value={config.mwFromLevel} onChange={(value) => updateConfig({ mwFromLevel: Number(value) })} />
      </div><p className="field-note">裝備 INT 會從「裝備 Equipment」分頁的裝備清單計算。</p></div>

      {tab === "optimize" ? <p className="field-note">最佳化會使用桌面版預設搜尋策略與範圍。</p> : <div className="form-section"><h3>模擬參數 <span>只用於 Simulate</span></h3><div className="fields">
        <label>Policy<select value={effectivePolicy} onChange={(event) => updateConfig({ policy: event.target.value as PolicyName })}>{profile.policies.map((value) => <option key={value} value={value}>{policyLabels[value]}</option>)}</select></label>
        <Field label="目標 base INT" value={config.targetInt} onChange={(value) => updateConfig({ targetInt: Number(value) })} />
        <Field label="MP wash 結束等級" value={config.mpWashEnd} onChange={(value) => updateConfig({ mpWashEnd: Number(value) })} />
        <label className="checkbox-field"><input type="checkbox" checked={config.autoMethod2} onChange={(event) => updateConfig({ autoMethod2: event.target.checked })} />自動以 Method 2 補足目標 HP</label>
      </div></div>}

      <details className="resume-section"><summary>中途接續 Resume</summary><label className="checkbox-field resume-toggle"><input type="checkbox" checked={config.resumeEnabled} onChange={(event) => updateConfig({ resumeEnabled: event.target.checked })} />從目前角色狀態接續計算，APR 只統計接下來使用的 APR</label>{config.resumeEnabled && <div className="fields resume-fields">
        <Field label="目前等級" value={config.resume.level} onChange={(level) => updateResume({ level })} /><Field label="base HP" value={config.resume.baseHp} onChange={(baseHp) => updateResume({ baseHp })} />
        <Field label="base MP（擇一）" value={config.resume.baseMp} onChange={(baseMp) => updateResume({ baseMp })} /><Field label="Extra MP（擇一）" value={config.resume.extraMp} onChange={(extraMp) => updateResume({ extraMp })} />
        <Field label="base INT" value={config.resume.baseInt} onChange={(baseInt) => updateResume({ baseInt })} /><Field label="base STR" value={config.resume.baseStr} onChange={(baseStr) => updateResume({ baseStr })} />
        <Field label="base DEX" value={config.resume.baseDex} onChange={(baseDex) => updateResume({ baseDex })} /><Field label="base LUK" value={config.resume.baseLuk} onChange={(baseLuk) => updateResume({ baseLuk })} />
        <Field label="本等尚未點的 AP" value={config.resume.freshAp} onChange={(freshAp) => updateResume({ freshAp })} /><Field label="base INT peak（可空）" value={config.resume.baseIntPeak} onChange={(baseIntPeak) => updateResume({ baseIntPeak })} />
        <label className="checkbox-field"><input type="checkbox" checked={config.resume.intResetDone} onChange={(event) => updateResume({ intResetDone: event.target.checked })} />已完成 INT reset（base INT = 4）</label>
      </div>}</details>
      <div className="runbar"><div><b>CSV 計畫輸出</b><span>完成計算後可下載逐級計畫</span></div><button type="button" onClick={tab === "optimize" ? runOptimize : runSimulate}>{tab === "optimize" ? "執行最佳化" : "執行模擬"}</button></div>
      {tab === "simulate" && result && <SimulationResult result={result} />}{tab === "optimize" && optimized && <OptimizationResult result={optimized} />}
    </section>}

    {tab === "actions" && <section className="page-card"><p className="eyebrow">Actions</p><h2>策略、洗法與計畫動作說明</h2><div className="action-grid"><article><h3>Policy A — MP wash shortfall</h3><p>31 等級起進入 INT 目標階段。Extra MP 達 threshold 時用 Method 1 洗 HP；不足時先 MP wash。</p></article><article><h3>Policy B — INT dump shortfall</h3><p>Extra MP 足夠時用 Method 1；不足時把本等 AP 點入 INT，該列不增加洗血 APR。</p></article><article><h3>Policy C — Hardcore greedy</h3><p>10 等起逐 AP 檢查：Extra MP 足夠就 HP1；30 等起可嘗試 MP1；剩餘 AP 投入 INT／主屬性。</p></article><article><h3>Policy D — Plain INT</h3><p>先集中 INT，達標後進行 MP wash、Method 1／Method 2 與 INT reset。非 Thief 職業使用此策略。</p></article><article><h3>Method 1</h3><p>使用當等級新鮮 AP 加 HP，再以 APR 扣除職業對應 MP；新鮮 AP 回到 INT 或主屬性。</p></article><article><h3>Method 2</h3><p>使用 APR 扣 Extra MP 換取 HP，沒有新鮮 AP 限制；計算會遵守設定的目標 base MP 下限。</p></article><article><h3>計畫動作</h3><p><code>BUILD</code> 建立初始能力值；<code>HP1–HP5</code>／<code>MP1–MP5</code> 表示本等洗血／洗 MP；<code>M2</code> 為 Method 2；<code>RESET_INT</code> 為 INT 洗回；<code>RESUME</code> 標示接續起點。</p></article></div></section>}
  </main>;
}

function SimulationResult({ result }: { result: SimulateResult }) {
  const hpReached = result.final_display_hp >= result.target_hp;
  const mpReached = result.target_mp === undefined || result.final_base_mp >= result.target_mp;
  const outcome = result.reached_target ? "已達成目標" : hpReached && !mpReached ? "無法同時達標 — HP 已達標，MP 未達標" : "無法達成 — 最接近結果";
  const mpDetail = result.target_mp === undefined ? "未設定 MP 目標" : `MP 目標 ${result.target_mp}，實際 ${result.final_base_mp}${mpReached ? "（達標）" : "（未達標）"}`;
  return <section className="result-panel"><div className="result-heading"><div><p className="eyebrow">Simulation result</p><h3>模擬結果</h3></div></div><div className={`goal-outcome ${result.reached_target ? "success" : "failure"}`} role="status"><strong>{outcome}</strong><span>HP 目標 {result.target_hp}，實際 {result.final_display_hp}（{hpReached ? "達標" : "未達標"}）；{mpDetail}；APR {totalApr(result.apr)}。</span></div><Metrics items={[[result.final_display_hp.toLocaleString(), "最終 HP"], [result.final_base_mp.toLocaleString(), "最終 base MP"], [totalApr(result.apr).toLocaleString(), "總 APR"], [String(result.int_reached_level || "—"), "INT 達標等級"]]} /><div className="result-heading"><h4>逐級計畫（{result.plan.length} 列）</h4><button type="button" className="quiet" onClick={() => downloadText("plan.csv", planCsv(result.plan), "text/csv;charset=utf-8")}>下載 CSV</button></div><PlanTable rows={result.plan} /></section>;
}
function OptimizationResult({ result }: { result: OptimizeResult }) {
  const winner = result.winner;
  if (!winner) return <section className="result-panel"><h3>沒有可用候選計畫</h3></section>;
  const policies: Array<[string, OptimizeResult["comparison"]["policy_a"]]> = [["A", result.comparison.policy_a], ["B", result.comparison.policy_b], ["C", result.comparison.policy_c], ["D", result.comparison.policy_d]];
  const hpReached = winner.final_display_hp >= winner.target_hp;
  const mpReached = winner.target_mp === undefined || winner.final_base_mp >= winner.target_mp;
  const outcome = winner.reached_target ? "已達成目標" : hpReached && !mpReached ? "無法同時達標 — HP 已達標，MP 未達標" : "無法達成 — 最接近結果";
  const mpDetail = winner.target_mp === undefined ? "未設定 MP 目標" : `MP 目標 ${winner.target_mp}，實際 ${winner.final_base_mp}${mpReached ? "（達標）" : "（未達標）"}`;
  return <section className="result-panel"><div className="result-heading"><div><p className="eyebrow">Optimization result</p><h3>最佳化結果</h3></div></div><div className={`goal-outcome ${winner.reached_target ? "success" : "failure"}`} role="status"><strong>{outcome}</strong><span>HP 目標 {winner.target_hp}，實際 {winner.final_display_hp}（{hpReached ? "達標" : "未達標"}）；{mpDetail}；APR {totalApr(winner.apr)}。</span></div><Metrics items={[[policyLabels[winner.policy], "優勝策略"], [totalApr(winner.apr).toLocaleString(), "總 APR"], [String(winner.target_base_int), "最佳 base INT"], [String(winner.mp_wash_end), "MP wash 結束等級"], [winner.final_display_hp.toLocaleString(), "最終 HP"], [winner.final_base_mp.toLocaleString(), "最終 base MP"]]} /><h4>策略比較</h4><div className="comparison-grid">{policies.filter((item): item is [string, NonNullable<typeof item[1]>] => item[1] !== undefined).map(([letter, candidate]) => <article key={letter}><span>Policy {letter}</span><b>{totalApr(candidate.apr).toLocaleString()} APR</b><small>INT {candidate.target_base_int} · MP 結束 {candidate.mp_wash_end} · HP {candidate.final_display_hp.toLocaleString()}</small></article>)}</div><div className="result-heading"><h4>優勝計畫（{winner.plan.length} 列）</h4><button type="button" className="quiet" onClick={() => downloadText("optimized-plan.csv", planCsv(winner.plan), "text/csv;charset=utf-8")}>下載 CSV</button></div><PlanTable rows={winner.plan} /></section>;
}
function Metrics({ items }: { items: Array<[string, string]> }) { return <div className="metrics">{items.map(([value, label]) => <span key={label}><b>{value}</b>{label}</span>)}</div>; }
function PlanTable({ rows }: { rows: SimulateResult["plan"] }) { return <div className="plan"><table><thead><tr><th>Lv</th><th>Action</th><th>base INT</th><th>base LUK</th><th>base HP</th><th>base MP</th><th>Extra MP</th><th>AP</th><th>APR</th><th>備註</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.level}-${row.action}-${index}`}><td>{row.level}</td><td>{row.action}</td><td>{row.base_int}</td><td>{row.base_luk}</td><td>{row.base_hp}</td><td>{row.base_mp}</td><td>{row.extra_mp}</td><td>INT {row.fresh_ap_int} · HP {row.fresh_ap_hp} · MP {row.fresh_ap_mp}</td><td>{row.apr_spent}</td><td>{row.notes}</td></tr>)}</tbody></table></div>; }
