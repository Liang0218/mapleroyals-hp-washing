import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { computeIntGearSegments, parseEquipment } from "./core/equipment";
import { EQUIPMENT_TYPES, totalApr, type EquipmentItem, type HpMode, type OptimizeResult, type PolicyName, type ResumeFrom, type SimulateResult } from "./core/models";
import { getJobProfile } from "./core/jobs";
import { simulate } from "./core/simulator";
import { JobReference } from "./JobReference";
import type { CalcRequest, CalcResponse } from "./calc.worker";
import { downloadText, readJsonFile } from "./file/browser";
import { planCsv } from "./file/plan-csv";
import { describeUserError, type ErrorField } from "./user-errors";
import { translateTree, type Language } from "./i18n";

type Tab = "guide" | "job-reference" | "equipment" | "optimize" | "simulate" | "actions";
type ResumeFields = { level: string; baseHp: string; baseMp: string; baseInt: string; baseLuk: string; baseDex: string; baseStr: string; freshAp: string; unwashedAp: string; intResetDone: boolean };
type CalculatorConfig = {
  job: string; policy: PolicyName; targetHp: number; targetMp: string; targetLevel: string; targetInt: number;
  resetLevel: number; mpWashEnd: number; questHp: number; hpMode: HpMode;
  mwPercent: number; mwFromLevel: number; gearAfterReset: number; autoMethod2: boolean;
  compareThiefPolicyC: boolean;
  resumeEnabled: boolean; resume: ResumeFields;
};
type AppCache = { version: 1; tab: Tab; equipment: EquipmentItem[]; optimize: CalculatorConfig; simulate: CalculatorConfig };
type Failure = { error: unknown; tab: Tab };
type Undo = { message: string; equipment: EquipmentItem[] };

const CACHE_KEY = "mapleroyals-hp-wash-web-cache-v1";
const GEAR_ACK_KEY = "mapleroyals-hp-wash-zero-gear-ok";
// Ordered by task: the calculators and their gear come first; reference pages sit apart at the end.
const tabs: Array<{ id: Tab; label: string; reference?: boolean }> = [
  { id: "guide", label: "使用指南" }, { id: "optimize", label: "最佳化" }, { id: "simulate", label: "模擬" },
  { id: "equipment", label: "裝備" }, { id: "job-reference", label: "職業數值", reference: true },
  { id: "actions", label: "策略說明", reference: true },
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
const policyHints: Record<PolicyName, string> = {
  mp_wash_shortfall: "Extra MP 不足時先 MP wash，足夠時用 Method 1 洗血。",
  int_dump_shortfall: "Extra MP 不足時把 AP 點入 INT，該等不花洗血 APR。",
  mp_wash_hardcore: "逐 AP 嘗試洗血與洗 MP，最省 APR 但操作最繁瑣。",
  int_only_plain: "先把 INT 點滿，再 MP wash、洗血並洗回 INT。",
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
const emptyResume: ResumeFields = { level: "", baseHp: "", baseMp: "", baseInt: "", baseLuk: "4", baseDex: "25", baseStr: "4", freshAp: "5", unwashedAp: "0", intResetDone: false };
const advancedFields: ErrorField[] = ["gearAfterReset"];
function defaultConfig(): CalculatorConfig {
  // The simulate defaults match the plan the optimizer finds for the default goal, so a first simulation reaches its target.
  return { job: "thief", policy: "mp_wash_shortfall", targetHp: 27000, targetMp: "", targetLevel: "200", targetInt: 350, resetLevel: 155, mpWashEnd: 108, questHp: 0, hpMode: "avg", mwPercent: 0.1, mwFromLevel: 10, gearAfterReset: 50, autoMethod2: true, compareThiefPolicyC: true, resumeEnabled: false, resume: { ...emptyResume } };
}
function cachedResume(value?: Partial<ResumeFields> & { unwashedHpAp?: string; unwashedMpAp?: string }): ResumeFields {
  const legacyCount = Number(value?.unwashedHpAp ?? 0) + Number(value?.unwashedMpAp ?? 0);
  return { ...emptyResume, ...(value ?? {}), unwashedAp: value?.unwashedAp ?? String(legacyCount) };
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
      optimize: { ...fallback.optimize, ...(raw.optimize ?? {}), targetLevel: String(raw.optimize?.targetLevel ?? fallback.optimize.targetLevel), resume: cachedResume(raw.optimize?.resume as (Partial<ResumeFields> & { unwashedHpAp?: string; unwashedMpAp?: string }) | undefined) },
      simulate: { ...fallback.simulate, ...(raw.simulate ?? {}), targetLevel: String(raw.simulate?.targetLevel ?? fallback.simulate.targetLevel), resume: cachedResume(raw.simulate?.resume as (Partial<ResumeFields> & { unwashedHpAp?: string; unwashedMpAp?: string }) | undefined) },
    };
  } catch { return fallback; }
}
type Theme = "system" | "light" | "dark";
function readTheme(): Theme {
  try { const value = localStorage.getItem("mapleroyals-hp-wash-theme"); return value === "light" || value === "dark" ? value : "system"; }
  catch { return "system"; }
}
function readLanguage(): Language {
  try { return localStorage.getItem("mapleroyals-hp-wash-language") === "en" ? "en" : "zh"; }
  catch { return "zh"; }
}
const optionalNumber = (value: string): number | undefined => value.trim() === "" ? undefined : Number(value);
const fieldId = (field: ErrorField) => `field-${field.replace(".", "-")}`;

type FieldProps = {
  name: ErrorField | string; label: string; value: string | number; onChange: (value: string) => void;
  invalid?: ErrorField; message?: string; min?: number; max?: number; step?: number | string; hint?: string;
};
function Field({ name, label, value, onChange, invalid, message, min, max, step, hint }: FieldProps) {
  const id = fieldId(name as ErrorField);
  // Range check on leaving the field, so a bad value shows before Run is pressed.
  const [outOfRange, setOutOfRange] = useState(false);
  const isInvalid = invalid === name;
  const rangeText = min !== undefined && max !== undefined ? `${min}–${max}` : min !== undefined ? `≥ ${min}` : `≤ ${max}`;
  const shown = isInvalid ? message : outOfRange ? `超出範圍（${rangeText}）` : undefined;
  const describedBy = [hint ? `${id}-hint` : "", shown ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined;
  return <label>{label}<input id={id} type="number" inputMode="decimal" min={min} max={max} step={step} value={value} aria-invalid={isInvalid || outOfRange || undefined} aria-describedby={describedBy}
    onChange={(event) => { if (outOfRange && event.target.validity.valid) setOutOfRange(false); onChange(event.target.value); }}
    onBlur={(event) => setOutOfRange(event.target.validity.rangeUnderflow || event.target.validity.rangeOverflow)} />
    {hint && <small id={`${id}-hint`} className="field-hint">{hint}</small>}
    {shown && <small id={`${id}-error`} className="field-error">{shown}</small>}</label>;
}

export function App() {
  const [cache, setCache] = useState<AppCache>(readCache);
  const [language, setLanguage] = useState<Language>(readLanguage);
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [ranWith, setRanWith] = useState<Partial<Record<"optimize" | "simulate", string>>>({});
  const [result, setResult] = useState<SimulateResult>();
  const [optimized, setOptimized] = useState<OptimizeResult>();
  const [failure, setFailure] = useState<Failure>();
  const [running, setRunning] = useState<"optimize" | "simulate">();
  const [elapsed, setElapsed] = useState(0);
  const [revealTick, setRevealTick] = useState(0);
  const [gearAck, setGearAck] = useState(() => { try { return sessionStorage.getItem(GEAR_ACK_KEY) === "1"; } catch { return false; } });
  const [gearPrompt, setGearPrompt] = useState(false);
  const [lastDuration, setLastDuration] = useState<Partial<Record<"optimize" | "simulate", number>>>({});
  const cancelRun = useRef<(() => void) | undefined>(undefined);
  useEffect(() => () => cancelRun.current?.(), []);
  const [undo, setUndo] = useState<Undo>();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [resumeOpen, setResumeOpen] = useState(false);
  const equipmentInput = useRef<HTMLInputElement>(null);
  const { tab, equipment, optimize: optimizeConfig, simulate: simulateConfig } = cache;
  // Busy belongs to the tab whose calculation is running; the other calculator tab only waits for it.
  const busy = running !== undefined && running === (tab === "optimize" ? "optimize" : "simulate");
  const otherRunning = running !== undefined && !busy;
  const config = tab === "simulate" ? simulateConfig : optimizeConfig;
  const profile = getJobProfile(config.job);
  const effectivePolicy = profile.policies.includes(config.policy) ? config.policy : profile.policies[0];
  const userError = failure && failure.tab === tab ? describeUserError(failure.error, language) : undefined;
  const invalid = userError?.field;
  const gearPreview = useMemo(() => {
    try { return computeIntGearSegments(equipment, Math.max(1, optimizeConfig.resetLevel - 1)); }
    catch { return []; }
  }, [equipment, optimizeConfig.resetLevel]);
  const formGear = useMemo(() => {
    try { return computeIntGearSegments(equipment, Math.max(1, config.resetLevel - 1)); }
    catch { return []; }
  }, [equipment, config.resetLevel]);
  const gearUnset = formGear.every((segment) => segment.int_gear === 0);
  const gearItemsWithInt = equipment.filter((item) => item.int > 0).length;

  useEffect(() => {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); }
    catch { /* Browser storage may be unavailable or full. */ }
  }, [cache]);

  useEffect(() => {
    try { localStorage.setItem("mapleroyals-hp-wash-language", language); }
    catch { /* Browser storage may be unavailable. */ }
    document.documentElement.lang = language === "en" ? "en" : "zh-Hant";
  }, [language]);

  useEffect(() => {
    try { localStorage.setItem("mapleroyals-hp-wash-theme", theme); }
    catch { /* Browser storage may be unavailable. */ }
    if (theme === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
  }, [theme]);

  // A result is stale once the inputs it was computed from change.
  const inputSignature = JSON.stringify([tab, config, equipment]);
  const calcKind = tab === "simulate" ? "simulate" : "optimize";
  const stale = ranWith[calcKind] !== undefined && ranWith[calcKind] !== inputSignature;

  // Move focus to the field an error points at, opening its group first.
  useEffect(() => {
    if (!failure) return;
    const field = describeUserError(failure.error).field;
    if (!field || field === "equipment") { document.getElementById("form-error")?.focus(); return; }
    if (field.startsWith("resume.")) setResumeOpen(true);
    if (advancedFields.includes(field)) setAdvancedOpen(true);
    requestAnimationFrame(() => (document.getElementById(fieldId(field)) ?? document.getElementById("form-error"))?.focus());
  }, [failure]);

  // Editing the field an error points at clears that error.
  function clearErrorFor(fields: string[]) { if (invalid && fields.includes(invalid)) setFailure(undefined); }
  function updateConfig(patch: Partial<CalculatorConfig>) {
    if (!("resume" in patch)) clearErrorFor(Object.keys(patch));
    setCache((previous) => tab === "simulate"
      ? { ...previous, simulate: { ...previous.simulate, ...patch } }
      : { ...previous, optimize: { ...previous.optimize, ...patch } });
  }
  function updateResume(patch: Partial<ResumeFields>) { clearErrorFor(Object.keys(patch).map((key) => `resume.${key}`)); updateConfig({ resume: { ...config.resume, ...patch } }); }
  function openInSimulate(request: SimulateRequest) {
    setCache((previous) => ({ ...previous, tab: "simulate", simulate: { ...previous.optimize, autoMethod2: previous.simulate.autoMethod2, policy: request.policy, targetInt: request.targetInt, mpWashEnd: request.mpWashEnd } }));
    setFailure(undefined); setResult(undefined);
    window.scrollTo({ top: 0 });
  }
  // Re-runs one plan of the optimizer's result with a different base INT / MP wash end, using the Optimize settings.
  // A single simulation is fast enough for the main thread, and it never touches the Simulate tab's own settings.
  function tunePlan(request: SimulateRequest): SimulateResult {
    return simulate({ ...sharedConfig(optimizeConfig), policy: request.policy, target_base_int: request.targetInt, mp_wash_end: request.mpWashEnd, auto_method2: true });
  }
  function changeTab(next: Tab) { setCache((previous) => ({ ...previous, tab: next })); setFailure(undefined); setGearPrompt(false); }
  function onTabKey(event: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex((item) => item.id === tab);
    const moves: Record<string, number> = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 };
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = tabs[(moves[event.key] + tabs.length) % tabs.length].id;
    changeTab(next);
    requestAnimationFrame(() => document.getElementById(`tab-${next}`)?.focus());
  }
  function buildResume(current: CalculatorConfig): ResumeFrom | undefined {
    if (!current.resumeEnabled) return undefined;
    const level = optionalNumber(current.resume.level); const base_hp = optionalNumber(current.resume.baseHp); const base_int = optionalNumber(current.resume.baseInt);
    if (level === undefined || base_hp === undefined || base_int === undefined) throw new Error("resume missing required stats");
    const base_mp = optionalNumber(current.resume.baseMp);
    if (base_mp === undefined) throw new Error("resume missing base_mp");
    return { level, base_hp, base_mp, base_int, base_luk: Number(current.resume.baseLuk), base_dex: Number(current.resume.baseDex), base_str: Number(current.resume.baseStr), fresh_ap: optionalNumber(current.resume.freshAp), unwashed_ap: Number(current.resume.unwashedAp || 0), int_reset_done: current.resume.intResetDone };
  }
  function sharedConfig(current: CalculatorConfig) {
    const levelInput = String(current.targetLevel ?? "");
    const targetLevel = levelInput.trim() === "" ? 200 : Number(levelInput);
    if (!Number.isInteger(targetLevel) || targetLevel < 31 || targetLevel > 200) throw new Error("target_level out of range");
    const intGear = computeIntGearSegments(equipment, Math.max(1, current.resetLevel - 1));
    return { target_hp: current.targetHp, target_mp: optionalNumber(current.targetMp), max_level: targetLevel, int_reset_level: current.resetLevel, int_gear: intGear, job: current.job, int_gear_after_reset: current.gearAfterReset, quest_equip_hp: current.questHp, hp_mode: current.hpMode, mw_percent: current.mwPercent, mw_from_level: current.mwFromLevel, resume_from: buildResume(current) };
  }
  function simulateParams() {
    const activeProfile = getJobProfile(simulateConfig.job);
    const policy = activeProfile.policies.includes(simulateConfig.policy) ? simulateConfig.policy : activeProfile.policies[0];
    return { ...sharedConfig(simulateConfig), policy, target_base_int: simulateConfig.targetInt, mp_wash_end: simulateConfig.mpWashEnd, auto_method2: simulateConfig.autoMethod2 };
  }
  function optimizeParams() {
    const activeProfile = getJobProfile(optimizeConfig.job);
    return {
      ...sharedConfig(optimizeConfig), policies: activeProfile.policies.filter((policy) => optimizeConfig.job !== "thief" || optimizeConfig.compareThiefPolicyC || policy !== "mp_wash_hardcore"),
      target_base_int_min: 4, target_base_int_max: 999, target_base_int_step: 10,
      mp_wash_end_min: 31, top_n: 5,
    };
  }
  // Validate on the main thread, then search in a worker so the page stays responsive and cancellable.
  function run() {
    if (running) return;
    if (gearUnset && !gearAck) { setGearPrompt(true); return; }
    calculate();
  }
  // Chosen once per browser session: after "compute with 0" the prompt stays away until the tab is reopened.
  function acceptZeroGear() {
    setGearAck(true); setGearPrompt(false);
    try { sessionStorage.setItem(GEAR_ACK_KEY, "1"); } catch { /* Session storage may be unavailable. */ }
    calculate();
  }
  function calculate() {
    const kind = tab === "optimize" ? "optimize" : "simulate";
    let request: CalcRequest;
    try { request = kind === "optimize" ? { kind, params: optimizeParams() } : { kind, params: simulateParams() }; }
    catch (caught) { if (kind === "optimize") setOptimized(undefined); else setResult(undefined); setFailure({ error: caught, tab: kind }); return; }
    setFailure(undefined);
    const signature = inputSignature;
    const started = performance.now();
    setElapsed(0); setRunning(kind);
    const timer = window.setInterval(() => setElapsed(Math.floor((performance.now() - started) / 1000)), 250);
    const worker = new Worker(new URL("./calc.worker.ts", import.meta.url), { type: "module" });
    const finish = () => { window.clearInterval(timer); worker.terminate(); cancelRun.current = undefined; setRunning(undefined); };
    cancelRun.current = finish;
    worker.onmessage = (event: MessageEvent<CalcResponse>) => {
      finish();
      const data = event.data;
      if (!data.ok) { if (kind === "optimize") setOptimized(undefined); else setResult(undefined); setFailure({ error: new Error(data.message), tab: kind }); return; }
      // Each calculator keeps its own last result; running one never clears the other.
      setLastDuration((previous) => ({ ...previous, [kind]: Math.max(1, Math.round((performance.now() - started) / 1000)) }));
      if (kind === "optimize") setOptimized(data.result as OptimizeResult);
      else setResult(data.result as SimulateResult);
      setRanWith((previous) => ({ ...previous, [kind]: signature }));
      setRevealTick((tick) => tick + 1);
    };
    worker.onerror = (event) => { event.preventDefault(); finish(); setFailure({ error: new Error(event.message), tab: kind }); };
    worker.postMessage(request);
  }
  // Once a new result has rendered: if it landed out of view (a stacked layout on narrow screens), bring it in, then move focus to its heading.
  useEffect(() => {
    if (!revealTick) return;
    // Scroll the whole specimen (its scroll-margin keeps the No. tag in view); focus only its heading.
    const specimen = document.querySelector<HTMLElement>(".calc-results .specimen");
    const heading = specimen?.querySelector<HTMLElement>(".specimen-head h3");
    if (!specimen || !heading) return;
    const top = specimen.getBoundingClientRect().top;
    const inView = top >= 16 && top < window.innerHeight * 0.7;
    if (!inView) specimen.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    heading.focus({ preventScroll: true });
  }, [revealTick]);
  async function importEquipment(file?: File) {
    if (!file) return;
    try { const items = parseEquipment(await readJsonFile(file)); setUndo({ message: "已載入裝備設定。", equipment }); setCache((previous) => ({ ...previous, equipment: items })); setFailure(undefined); }
    catch (caught) { setFailure({ error: caught, tab: "equipment" }); }
  }
  function addEquipment() { setUndo(undefined); setCache((previous) => ({ ...previous, equipment: [...previous.equipment, { name: "", type: "Hat", int: 0, equip_level: 10 }] })); }
  function updateEquipment(index: number, patch: Partial<EquipmentItem>) {
    setCache((previous) => ({ ...previous, equipment: previous.equipment.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item) }));
  }
  function removeEquipment(index: number) {
    const name = equipment[index]?.name.trim();
    setUndo({ message: name ? `已移除「${name}」。` : "已移除一件裝備。", equipment });
    setCache((previous) => ({ ...previous, equipment: previous.equipment.filter((_, itemIndex) => itemIndex !== index) }));
  }
  function restoreDefaults() {
    setUndo({ message: "已還原預設裝備。", equipment });
    setCache((previous) => ({ ...previous, equipment: initialEquipment.map((item) => ({ ...item })) }));
  }
  function revertEquipment() {
    if (!undo) return;
    const previousEquipment = undo.equipment;
    setCache((previous) => ({ ...previous, equipment: previousEquipment }));
    setUndo(undefined);
  }

  const errorBox = userError && <div className="error-box" id="form-error" role="alert" tabIndex={-1}>
    <p>{userError.message}</p>
    {userError.field === "equipment" && tab !== "equipment" && <button type="button" className="quiet" onClick={() => changeTab("equipment")}>前往裝備頁</button>}
  </div>;

  const panels: Record<Tab, () => ReactNode> = {
    guide: () => <section className="page-card">
      <div className="section-heading"><div><h2>使用指南</h2><p className="subheading">五個步驟算出低 APR 的洗血計畫。</p></div><div className="button-row"><button type="button" onClick={() => changeTab("optimize")}>開始最佳化</button><button type="button" className="quiet" onClick={() => changeTab("equipment")}>設定裝備</button></div></div>
      <ol className="guide-steps"><li><b>選擇職業</b><span>Thief 可比較 A／B／C／D 策略；其他職業使用 Policy D。</span></li><li><b>設定 INT 裝備</b><span>到「裝備 Equipment」頁編輯各等級可穿戴裝備，檢查 INT 區間預覽。</span></li><li><b>執行最佳化</b><span>輸入 HP／MP 目標與洗回 INT 條件，搜尋低 APR 計畫。</span></li><li><b>執行模擬</b><span>指定 base INT 與 MP wash 結束等級，檢查單一計畫的逐級行動。</span></li><li><b>保留操作</b><span>此瀏覽器會自動記住上次的裝備及各分頁設定。</span></li></ol>
      <div className="notice-row"><div className="notice notice-tip"><b>計算提示</b><p>最佳化與模擬會依目前裝備清單及各自設定的洗回 INT 等級，即時更新 INT 裝備區間。</p></div><div className="notice notice-caution"><b>結果不保證完全正確</b><p>洗血涉及多項職業公式、能力值與遊戲機制，計算過程較為複雜，程式算出的結果不保證完全正確，可能有誤差。有疑問歡迎聯絡作者：Discord fuhuo。</p></div></div>
    </section>,

    equipment: () => <section className="page-card equipment-page">
      <div className="section-heading"><div><h2>裝備設定</h2><p className="subheading">每種裝備槽取最高 INT；Ring 最多計入四件。下表會即時預覽各等級可用的總 INT。</p></div><div className="button-row"><input ref={equipmentInput} className="visually-hidden" type="file" accept="application/json,.json" tabIndex={-1} aria-hidden="true" onChange={(event) => { void importEquipment(event.target.files?.[0]); event.target.value = ""; }} /><button className="link-button" type="button" onClick={restoreDefaults}>還原預設</button><button className="quiet" type="button" onClick={() => equipmentInput.current?.click()}>載入智力裝備設定</button><button className="quiet" type="button" onClick={() => downloadText("int-equipment-settings.json", `${JSON.stringify(equipment, null, 2)}\n`, "application/json;charset=utf-8")}>儲存智力裝備設定</button></div></div>
      {errorBox}
      <div className="equipment-toolbar"><button type="button" className="quiet" onClick={addEquipment}>新增裝備</button><span className="equipment-auto-note">編輯裝備清單後，最佳化與模擬會依各自設定的洗回 INT 等級自動套用。</span></div>
      {undo && <div className="undo-bar" role="status"><span>{undo.message}</span><button type="button" className="quiet" onClick={revertEquipment}>復原</button></div>}
      <div className="equipment-layout"><div className="equipment-table-wrap"><table className="equipment-table"><thead><tr><th scope="col">裝備名稱</th><th scope="col">類型</th><th scope="col">INT</th><th scope="col">穿戴等級</th><th scope="col"><span className="visually-hidden">移除</span></th></tr></thead><tbody>{equipment.map((item, index) => <tr key={index}><td><input aria-label={`裝備 ${index + 1} 名稱`} value={item.name} onChange={(event) => updateEquipment(index, { name: event.target.value })} /></td><td><select aria-label={`裝備 ${index + 1} 類型`} value={item.type} onChange={(event) => updateEquipment(index, { type: event.target.value as EquipmentItem["type"] })}>{EQUIPMENT_TYPES.map((type) => <option key={type}>{type}</option>)}</select></td><td><input aria-label={`裝備 ${index + 1} INT`} type="number" min="0" value={item.int} onChange={(event) => updateEquipment(index, { int: Number(event.target.value) })} /></td><td><input aria-label={`裝備 ${index + 1} 穿戴等級`} type="number" min="1" max="200" value={item.equip_level} onChange={(event) => updateEquipment(index, { equip_level: Number(event.target.value) })} /></td><td><button className="remove" type="button" aria-label={`移除裝備 ${index + 1}${item.name ? ` (${item.name})` : ""}`} onClick={() => removeEquipment(index)}>移除</button></td></tr>)}</tbody></table></div>
        <aside className="gear-preview"><h3>INT 裝備預覽</h3><p>洗回 INT 前：依左邊裝備表，各等級如下。</p><p>洗回 INT 後：{optimizeConfig.gearAfterReset}（在最佳化的「進階設定」修改）</p>{gearPreview.length ? <table><thead><tr><th scope="col">等級</th><th scope="col">裝備 INT</th></tr></thead><tbody>{gearPreview.map((segment) => <tr key={segment.from_level}><td>{segment.from_level}–{segment.to_level}</td><td>{segment.int_gear}</td></tr>)}</tbody></table> : <p className="error">請檢查裝備名稱、INT 與裝備等級。</p>}</aside></div>
    </section>,

    "job-reference": () => <JobReference language={language} />,
    optimize: () => calculator(),
    simulate: () => calculator(),

    actions: () => <section className="page-card"><h2>策略、洗法與計畫動作說明</h2><div className="action-grid"><article><h3>Policy A — MP wash shortfall</h3><p>31 等級起進入 INT 目標階段。Extra MP 達 threshold 時用 Method 1 洗 HP；不足時先 MP wash。</p></article><article><h3>Policy B — INT dump shortfall</h3><p>Extra MP 足夠時用 Method 1；不足時把本等 AP 點入 INT，該列不增加洗血 APR。</p></article><article><h3>Policy C — Hardcore greedy</h3><p>10 等起逐 AP 檢查：Extra MP 足夠就 HP1；30 等起可嘗試 MP1；剩餘 AP 投入 INT／主屬性。</p></article><article><h3>Policy D — Plain INT</h3><p>先集中 INT，達標後進行 MP wash、Method 1／Method 2 與 INT reset。非 Thief 職業使用此策略。</p></article><article><h3>Method 1</h3><p>使用當等級新鮮 AP 加 HP，再以 APR 扣除職業對應 MP；新鮮 AP 回到 INT 或主屬性。</p></article><article><h3>Method 2</h3><p>使用 APR 扣 Extra MP 換取 HP，沒有新鮮 AP 限制；計算會遵守設定的目標 base MP 下限。</p></article><article><h3>計畫動作</h3><p><code>BUILD</code> 建立初始能力值；<code>HP1–HP5</code>／<code>MP1–MP5</code> 表示本等洗血／洗 MP；<code>M2</code> 為 Method 2；<code>RESET_INT</code> 為 INT 洗回；<code>RESUME</code> 標示接續起點。</p></article></div></section>,
  };

  function calculator() {
    const isOptimize = tab === "optimize";
    const suggestion = optimized ? recommendedPlan(optimized)?.[1] : undefined;
    return <form className="calculator-page" noValidate onSubmit={(event) => { event.preventDefault(); run(); }}>
      <div className="page-title"><div><h2>{isOptimize ? "最佳化計畫" : "單一計畫模擬"}</h2><p className="subheading">{isOptimize ? "搜尋最佳 base INT 與 MP wash 結束等級，並比較適用策略。" : "固定 base INT 與 MP wash 結束等級，模擬每一級的 AP／APR 行動。"}</p></div></div>
      <div className="calc-layout"><div className="calc-form" id="calc-form">

      <fieldset className="form-section"><legend>目標與職業</legend><div className="fields">
        <label>職業<select id={fieldId("job")} value={config.job} aria-invalid={invalid === "job" || undefined} onChange={(event) => updateConfig({ job: event.target.value })}>{jobs.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>{invalid === "job" && <small className="field-error">{userError?.message}</small>}</label>
        <Field name="targetHp" invalid={invalid} message={userError?.message} min={1} step={1} label="目標 HP" value={config.targetHp} onChange={(value) => updateConfig({ targetHp: Number(value) })} />
        <label>目標 MP（留空則洗到最低）<input id={fieldId("targetMp")} type="number" inputMode="numeric" min={0} step={1} value={config.targetMp} aria-invalid={invalid === "targetMp" || undefined} onChange={(event) => updateConfig({ targetMp: event.target.value })} />{invalid === "targetMp" && <small className="field-error">{userError?.message}</small>}</label>
        <label>目標等級（留空＝200）<input id={fieldId("targetLevel")} type="number" inputMode="numeric" min={31} max={200} step={1} value={config.targetLevel} aria-invalid={invalid === "targetLevel" || undefined} onChange={(event) => updateConfig({ targetLevel: event.target.value })} />{invalid === "targetLevel" && <small className="field-error">{userError?.message}</small>}</label>
        <Field name="resetLevel" invalid={invalid} message={userError?.message} min={2} max={200} step={1} label="洗回 INT 等級" value={config.resetLevel} onChange={(value) => updateConfig({ resetLevel: Number(value) })} />
      </div><p className="field-note gear-summary"><span className="gear-chips"><span className="gear-label">裝備 INT</span>{formGear.length ? formGear.map((segment) => <span className="gear-chip" key={segment.from_level}>Lv {segment.from_level}–{segment.to_level} INT <b>+{segment.int_gear}</b></span>) : <span>尚未設定</span>}</span><button type="button" className="link-button" onClick={() => changeTab("equipment")}>編輯裝備</button></p></fieldset>

      {isOptimize
        ? null
        : <fieldset className="form-section"><legend>模擬參數</legend>
          <fieldset className="policy-choice" aria-invalid={invalid === "policy" || undefined}><legend>Policy</legend>
            {profile.policies.map((value) => <label key={value} className="policy-option"><input type="radio" name="simulate-policy" id={value === effectivePolicy ? fieldId("policy") : undefined} value={value} checked={value === effectivePolicy} onChange={() => updateConfig({ policy: value })} /><span className="policy-option-name"><b>{policyLetter(value)}</b>{policyLabels[value].split("— ")[1]}</span><small className="policy-option-hint">{policyHints[value]}</small></label>)}
            {invalid === "policy" && <small className="field-error">{userError?.message}</small>}
          </fieldset><div className="fields">
          <Field name="targetInt" invalid={invalid} message={userError?.message} min={4} step={1} label="目標 base INT" value={config.targetInt} onChange={(value) => updateConfig({ targetInt: Number(value) })} />
          <Field name="mpWashEnd" invalid={invalid} message={userError?.message} min={31} max={200} step={1} label="MP wash 結束等級" value={config.mpWashEnd} onChange={(value) => updateConfig({ mpWashEnd: Number(value) })} />
          <label className="checkbox-field"><input type="checkbox" checked={config.autoMethod2} onChange={(event) => updateConfig({ autoMethod2: event.target.checked })} />自動以 Method 2 補足目標 HP</label>
        </div></fieldset>}

      <details className="disclosure" open={advancedOpen} onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}><summary>進階設定<span>{isOptimize && optimizeConfig.job === "thief" ? "比較 Policy C、" : ""}裝備 INT、HP 計算方式與 Maple Warrior</span></summary>
        {isOptimize && optimizeConfig.job === "thief" && <div className="disclosure-body advanced-compare"><label className="checkbox-field"><input type="checkbox" checked={optimizeConfig.compareThiefPolicyC} onChange={(event) => updateConfig({ compareThiefPolicyC: event.target.checked })} />比較 Policy C（Hardcore greedy）</label><p className="field-note">Policy C 會逐 AP 嘗試洗血與洗 MP，策略較繁瑣，搜尋也較耗時。關閉後只比較 A／B／D，可縮短最佳化時間。</p></div>}
        <div className="fields disclosure-body">
        <Field name="gearAfterReset" invalid={invalid} message={userError?.message} min={0} step={1} label="洗回後升等裝備 INT" value={config.gearAfterReset} onChange={(value) => updateConfig({ gearAfterReset: Number(value) })} />
        <Field name="questHp" min={0} step={1} label="任務／裝備 HP" value={config.questHp} onChange={(value) => updateConfig({ questHp: Number(value) })} />
        <label>HP 模式<select value={config.hpMode} onChange={(event) => updateConfig({ hpMode: event.target.value as HpMode })}><option value="avg">平均 avg</option><option value="min">最低 min</option><option value="max">最高 max</option></select></label>
        <Field name="mwPercent" min={0} max={1} step="0.01" label="Maple Warrior 比例" hint="填 0.1 代表 10%" value={config.mwPercent} onChange={(value) => updateConfig({ mwPercent: Number(value) })} />
        <Field name="mwFromLevel" min={1} max={200} step={1} label="Maple Warrior 起始等級" value={config.mwFromLevel} onChange={(value) => updateConfig({ mwFromLevel: Number(value) })} />
      </div></details>

      <details className="disclosure" open={resumeOpen} onToggle={(event) => setResumeOpen(event.currentTarget.open)}><summary>中途接續 Resume<span>從已經在練的角色接著算</span></summary><div className="disclosure-body"><label className="checkbox-field resume-toggle"><input type="checkbox" checked={config.resumeEnabled} onChange={(event) => updateConfig({ resumeEnabled: event.target.checked })} />從目前角色狀態接續計算，APR 只統計接下來使用的 APR</label>{config.resumeEnabled && <div className="fields resume-fields">
        <Field name="resume.level" invalid={invalid} message={userError?.message} min={1} max={200} step={1} label="目前等級" value={config.resume.level} onChange={(level) => updateResume({ level })} /><Field name="resume.baseHp" invalid={invalid} message={userError?.message} min={1} step={1} label="base HP" value={config.resume.baseHp} onChange={(baseHp) => updateResume({ baseHp })} />
        <Field name="resume.baseMp" invalid={invalid} message={userError?.message} min={0} step={1} label="base MP" value={config.resume.baseMp} onChange={(baseMp) => updateResume({ baseMp })} />
        <Field name="resume.baseInt" invalid={invalid} message={userError?.message} min={4} step={1} label="base INT" value={config.resume.baseInt} onChange={(baseInt) => updateResume({ baseInt })} /><Field name="baseStr" min={4} step={1} label="base STR" value={config.resume.baseStr} onChange={(baseStr) => updateResume({ baseStr })} />
        <Field name="baseDex" min={4} step={1} label="base DEX" value={config.resume.baseDex} onChange={(baseDex) => updateResume({ baseDex })} /><Field name="baseLuk" min={4} step={1} label="base LUK" value={config.resume.baseLuk} onChange={(baseLuk) => updateResume({ baseLuk })} />
        <Field name="freshAp" min={0} step={1} label="本等尚未點的 AP" value={config.resume.freshAp} onChange={(freshAp) => updateResume({ freshAp })} />
        <Field name="unwashedAp" min={0} step={1} label="尚未洗回的 HP／MP AP" value={config.resume.unwashedAp} onChange={(unwashedAp) => updateResume({ unwashedAp })} />
        <label className="checkbox-field"><input type="checkbox" checked={config.resume.intResetDone} onChange={(event) => updateResume({ intResetDone: event.target.checked })} />INT 已洗回 4，之後不再點 INT</label>
      </div>}</div></details>

      <div className="runbar">
        {!gearUnset && <p className="gear-check"><span className="mark mark-filled" aria-hidden="true" />裝備 INT 已套用：{gearItemsWithInt} 件有 INT</p>}
        {!busy && !gearPrompt && <p className="runbar-note">{otherRunning ? (running === "optimize" ? "最佳化計算中，完成後才能執行模擬。" : "模擬計算中，完成後才能執行最佳化。") : "完成後可在結果區下載逐級計畫 CSV。"}</p>}
        {gearPrompt
          // First run with no gear INT at all: ask once, in place of the run button, before computing a plan that will overstate APR.
          ? <div className="gear-prompt" role="group" aria-labelledby="gear-prompt-title">
            <p id="gear-prompt-title"><b>還沒有設定裝備 INT。</b>現在計算會當作沒有任何 INT 裝備，需要的 APR 會偏高。要先設定裝備嗎？</p>
            <div className="run-actions"><button type="button" className="quiet" onClick={() => changeTab("equipment")}>前往裝備頁設定</button><button type="button" onClick={acceptZeroGear}>仍以 0 計算</button></div>
          </div>
          : <div className="run-actions">
            <button type="submit" className="run-button" disabled={busy || otherRunning} aria-busy={busy}>{busy ? `計算中… ${elapsed} 秒` : isOptimize ? "執行最佳化" : "執行模擬"}</button>
            {busy && <button type="button" className="quiet" onClick={() => cancelRun.current?.()}>取消</button>}
          </div>}
      </div>
      </div>
      <div className="calc-results" aria-live="polite">
        {userError && <div className="error-box" id="form-error" role="alert" tabIndex={-1}><p>{userError.field && userError.field !== "equipment" ? "請修正左邊標紅的欄位後再執行。" : userError.message}</p>{userError.field === "equipment" && <button type="button" className="quiet" onClick={() => changeTab("equipment")}>前往裝備頁</button>}</div>}
        {busy ? <div className="results-empty results-busy"><p>{isOptimize ? "正在搜尋 base INT 與 MP wash 組合，請稍候。" : "正在逐級模擬，請稍候。"}</p><p className="elapsed" aria-live="off">已經過 {elapsed} 秒{lastDuration[calcKind] !== undefined && `（上次約 ${lastDuration[calcKind]} 秒）`}</p><button type="button" className="quiet" onClick={() => cancelRun.current?.()}>取消</button></div>
          : tab === "simulate" && result ? <SimulationResult result={result} language={language} stale={stale} onEditGear={gearUnset ? () => changeTab("equipment") : undefined} />
          : isOptimize && optimized ? <OptimizationResult result={optimized} language={language} stale={stale} onEditGear={gearUnset ? () => changeTab("equipment") : undefined} onSimulate={openInSimulate} onTune={tunePlan} />
          : <div className="results-empty"><p>{isOptimize ? "填好目標後按「執行最佳化」，結果會顯示在這裡。" : "填好設定後按「執行模擬」，結果會顯示在這裡。"}</p>
            {!isOptimize && suggestion && <button type="button" className="quiet" onClick={() => openInSimulate({ policy: suggestion.policy, targetInt: suggestion.target_base_int, mpWashEnd: suggestion.mp_wash_end })}>帶入最佳化建議：{codeFor(suggestion)}</button>}</div>}
      </div></div>
    </form>;
  }

  const themes: Array<[Theme, string]> = [["light", "淺色"], ["dark", "深色"], ["system", "自動"]];
  return <>{translateTree(<>
    <header className="app-bar"><div className="app-bar-inner">
      <div className="app-bar-row"><h1><span className="brand">MapleRoyals</span> HP Washing APR Optimizer</h1>
        <div className="switches"><div className="segmented" role="group" aria-label="語言"><button type="button" aria-pressed={language === "zh"} onClick={() => setLanguage("zh")}>中文</button><button type="button" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>EN</button></div>
          <div className="segmented" role="group" aria-label="外觀">{themes.map(([value, label]) => <button key={value} type="button" aria-pressed={theme === value} onClick={() => setTheme(value)}>{label}</button>)}</div></div></div>
      <div className="tabbar" role="tablist" aria-label="計算器分頁" onKeyDown={onTabKey}>{tabs.map((item) => <button key={item.id} id={`tab-${item.id}`} type="button" role="tab" aria-selected={tab === item.id} aria-controls="tab-panel" tabIndex={tab === item.id ? 0 : -1} className={`tab${tab === item.id ? " active" : ""}${item.reference && !tabs[tabs.indexOf(item) - 1]?.reference ? " tab-reference-start" : ""}`} onClick={() => changeTab(item.id)}>{item.label}</button>)}</div>
    </div></header>
    <main className="app-shell">
    <div id="tab-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
      {tab !== "optimize" && tab !== "simulate" && tab !== "equipment" && errorBox}
      {panels[tab]()}
    </div>
    <footer className="app-footer"><span className="footer-disclaimer">結果不保證完全正確，可能有誤差；有疑問請聯絡作者。</span><span>聯絡作者：Discord <b>fuhuo</b> · <a href="https://github.com/Liang0218/mapleroyals-hp-washing" target="_blank" rel="noreferrer">GitHub</a></span><span>v{__APP_VERSION__}</span></footer>
    </main>
  </>, language)}</>;
}

type PlanRow = SimulateResult["plan"][number];
type SpecimenProps = {
  code: string; headline: string; reached: boolean; hpReached: boolean; mpReached: boolean; stale: boolean;
  targetHp: number; finalHp: number; targetMp?: number; finalMp: number;
  figures: Array<[string, string]>; extras: Array<[string, string]>; note?: ReactNode; language: Language;
  /** Set when the plan was computed without any gear INT: the label then says so in the caution ink, with a way to fix it. */
  onEditGear?: () => void;
};

/** Drawn state mark: filled = reached, hollow = not reached. */
function Mark({ reached }: { reached: boolean }) { return <span className={`mark ${reached ? "mark-filled" : "mark-hollow"}`} aria-hidden="true" />; }

// Child components render their own copy, so each one runs it through translateTree itself:
// the caller's translateTree only sees the JSX it was handed, never what a component returns.

/** The result as a specimen label: the answer first, its proof underneath. */
function Specimen({ code, headline, reached, hpReached, mpReached, stale, targetHp, finalHp, targetMp, finalMp, figures, extras, note, language, onEditGear }: SpecimenProps) {
  const outcome = reached ? "已達成目標" : hpReached && !mpReached ? "無法同時達標 — HP 已達標，MP 未達標" : "無法達成 — 最接近結果";
  const mpDetail = targetMp === undefined ? "未設定 MP 目標" : `MP 目標 ${targetMp.toLocaleString()}，實際 ${finalMp.toLocaleString()}${mpReached ? "（達標）" : "（未達標）"}`;
  // HP against its goal as plain numbers: most plans reach it, so a bar would sit near full and say nothing.
  const hpMargin = finalHp - targetHp;
  return translateTree(<div className={`specimen ${stale ? "is-stale" : ""}`}>
    <span className="specimen-tag" title="編號：策略 · base INT · MP wash 結束等級">No. {code}</span>
    <div className="specimen-head">
      <h3 tabIndex={-1}>{headline}</h3>
      <span className={`stamp ${reached ? "stamp-reached" : "stamp-missed"}`} role="status"><Mark reached={reached} /> {outcome}</span>
    </div>
    {stale && <p className="stale-note">設定已變更，這是舊的結果；請重新執行。</p>}
    {note}
    <p className="hp-versus">最終 HP {finalHp.toLocaleString()}／目標 {targetHp.toLocaleString()}<span className={hpMargin >= 0 ? "hp-margin" : "hp-margin is-short"}>{hpMargin >= 0 ? `（多 ${hpMargin.toLocaleString()}）` : `（HP 差 ${(-hpMargin).toLocaleString()}）`}</span></p>
    <p className="capacity-caption">{mpDetail}</p>
    <dl className="figures">{figures.map(([value, label]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    {(extras.length > 0 || onEditGear) && <dl className="extras">{extras.map(([value, label]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
      {onEditGear && <div className="extra-caution"><dt>裝備 INT</dt><dd>未設定（以 0 計算）</dd><button type="button" className="link-button" onClick={onEditGear}>設定裝備後重算</button></div>}</dl>}
  </div>, language);
}

/** The moves a plan can make, in the player's words. Index -1 is AP allocation and other moves. */
const moves: Array<[(row: PlanRow) => boolean, string]> = [
  [(row) => /^HP[1-5]$/.test(row.action), "Method 1 洗血"],
  [(row) => /^MP[1-5]$/.test(row.action), "MP wash"],
  [(row) => row.action === "HARDCORE_GREEDY", "逐 AP 洗血或洗 MP"],
  [(row) => row.action === "M2", "Method 2 換 HP"],
  [(row) => row.action === "RESET_INT", "把 INT 洗回 4"],
];
const rowMove = (row: PlanRow) => moves.findIndex(([match]) => match(row));
const RESET_MOVE = 4;
const M2_MOVE = 3;
const PURE_RUN = 5;
const MAX_LEVEL = 200;
const levelRange = (from: number, to: number) => `Lv ${from === to ? from : `${from}–${to}`}`;

type PlanBand = { id: string; number: number; from: number; to: number; title: string; resets: number[]; rows: PlanRow[]; apr: number };
/**
 * Cuts the plan into continuous level bands by what each level actually does:
 * a run of one move lasting PURE_RUN+ levels stands alone, shorter alternating runs merge into one band,
 * Method 2 always stands alone, and a one-off INT reset is noted inside its band.
 */
function planBands(rows: PlanRow[]): PlanBand[] {
  if (!rows.length) return [];
  const sorted = [...rows].sort((a, b) => a.level - b.level);
  type Run = { moves: Set<number>; from: number; to: number; pure: boolean };
  const runs: Run[] = [];
  for (const row of sorted) {
    const move = rowMove(row);
    if (move === RESET_MOVE) continue;
    const last = runs.at(-1);
    if (last && last.moves.size === 1 && last.moves.has(move)) last.to = row.level;
    else runs.push({ moves: new Set([move]), from: row.level, to: row.level, pure: true });
  }
  const merged: Run[] = [];
  for (const run of runs) {
    const move = [...run.moves][0];
    const standsAlone = move === M2_MOVE || run.to - run.from + 1 >= PURE_RUN;
    const last = merged.at(-1);
    if (!standsAlone && last && !last.pure) { run.moves.forEach((value) => last.moves.add(value)); last.to = run.to; continue; }
    if (!standsAlone && last && last.pure && !last.moves.has(M2_MOVE) && last.to - last.from + 1 < PURE_RUN) {
      run.moves.forEach((value) => last.moves.add(value)); last.to = run.to; last.pure = false; continue;
    }
    merged.push({ ...run, moves: new Set(run.moves), pure: standsAlone || run.moves.size === 1 });
  }
  // A short pure run wedged between two others is not its own phase: fold it into an alternating band.
  for (let index = 1; index < merged.length; index += 1) {
    const band = merged[index];
    const isShort = band.to - band.from + 1 < PURE_RUN && band.pure && !band.moves.has(M2_MOVE);
    if (!isShort || index + 1 >= merged.length) continue;
    const previous = merged[index - 1];
    const next = merged[index + 1];
    if (previous.moves.has(M2_MOVE) || (previous.moves.has(-1) && previous.pure)) continue;
    band.moves.forEach((value) => previous.moves.add(value));
    previous.to = band.to; previous.pure = false;
    merged.splice(index, 1);
    const sameAsPrevious = [...next.moves].every((value) => previous.moves.has(value)) && !next.moves.has(M2_MOVE);
    if (sameAsPrevious && next.to - next.from + 1 < PURE_RUN * 3) { previous.to = next.to; merged.splice(index, 1); }
    index -= 1;
  }
  // Neighbouring alternating bands with the same moves read as one phase.
  for (let index = 1; index < merged.length; index += 1) {
    const previous = merged[index - 1];
    const band = merged[index];
    const sameMoves = band.moves.size === previous.moves.size && [...band.moves].every((value) => previous.moves.has(value));
    if (!previous.pure && !band.pure && sameMoves) { previous.to = band.to; merged.splice(index, 1); index -= 1; }
  }
  return merged.map((band, index) => {
    const from = index === 0 ? sorted[0].level : band.from;
    const to = index + 1 < merged.length ? merged[index + 1].from - 1 : sorted.at(-1)!.level;
    const bandRows = sorted.filter((row) => row.level >= from && row.level <= to);
    const named = [...band.moves].filter((move) => move !== -1).sort((a, b) => a - b).map((move) => moves[move][1]);
    if (band.moves.has(-1) && named.length) named.push("配點");
    const title = named.length === 0 ? "配點" : named.length === 1 ? named[0] : `${named.join("、")} 交替`;
    return { id: `band-${from}`, number: index + 1, from, to, title, resets: bandRows.filter((row) => rowMove(row) === RESET_MOVE).map((row) => row.level), rows: bandRows, apr: bandRows.reduce((sum, row) => sum + row.apr_spent, 0) };
  }).filter((band) => band.rows.length > 0);
}

/** The plan as a field-guide key: one row per continuous level band, drawn on a level track; each row opens to its levels. */
function PlanKey({ title, rows, file, language, summary, idPrefix = "" }: { title: string; rows: PlanRow[]; file: string; language: Language; summary?: string; idPrefix?: string }) {
  const bands = planBands(rows);
  const [showAll, setShowAll] = useState(false);
  return translateTree(<section className="plan-view" id={`${idPrefix}plan-view`}>
    <div className="result-heading"><div><h4 className="section-plate">{title}（{rows.length} 列）</h4>{summary && <p className="plan-summary">{summary}</p>}</div><button type="button" className="quiet" onClick={() => downloadText(file, planCsv(rows), "text/csv;charset=utf-8")}>下載 CSV</button></div>
    <div className="plan-hint-row"><p className="plan-hint">依等級順序照做；點一列展開該段的動作，連續做法相同的等級會合成一行。Extra MP 是目前 MP 超出洗血下限的量，負數表示還不能洗血。</p><label className="checkbox-field show-all"><input type="checkbox" checked={showAll} onChange={(event) => setShowAll(event.target.checked)} />顯示全部等級</label></div>
    <div className="plan-sections">
      <div className="plan-axis" aria-hidden="true"><span className="plan-axis-scale"><span>Lv 1</span><span style={{ left: `${(99 / (MAX_LEVEL - 1)) * 100}%` }}>Lv 100</span><span>Lv 200</span></span></div>
      {bands.map((band) => <details className="plan-step" id={`${idPrefix}${band.id}`} key={band.id}><summary>
        <span className="key-code">{band.number}</span>
        <span className="plan-step-range-lead">{levelRange(band.from, band.to)}</span>
        <span className="plan-step-text">{band.title}{band.resets.length > 0 && <span className="plan-step-events">Lv {band.resets.join("、")} 時把 INT 洗回 4</span>}</span>
        <span className="key-track" aria-hidden="true"><span className="key-band" style={{ left: `min(${((band.from - 1) / (MAX_LEVEL - 1)) * 100}%, calc(100% - 3px))`, width: `${(Math.max(band.to - band.from, 0.6) / (MAX_LEVEL - 1)) * 100}%` }} />{band.resets.map((level) => <span key={level} className="key-band is-point" style={{ left: `${((level - 1) / (MAX_LEVEL - 1)) * 100}%` }} />)}</span>
        <span className="plan-step-apr">{band.apr.toLocaleString()} APR</span>
      </summary><PlanTable language={language} rows={band.rows} compact={!showAll} /></details>)}
    </div>
  </section>, language);
}

const policyLetter = (policy: PolicyName) => policyLabels[policy].split(" ")[0];
const policyTitle = (policy: PolicyName) => `Policy ${policyLetter(policy)} · ${policyLabels[policy].split("— ")[1] ?? ""}`;
// How much in-game work a policy asks for: plain INT is simplest, per-AP greedy washing the most tedious.
const policyEffort: Record<PolicyName, number> = { int_only_plain: 1, int_dump_shortfall: 2, mp_wash_shortfall: 2, mp_wash_hardcore: 3 };
type SimulateRequest = { policy: PolicyName; targetInt: number; mpWashEnd: number };
const headlineFor = (candidate: { policy: PolicyName; target_base_int: number; mp_wash_end: number }) => `Policy ${policyLetter(candidate.policy)} · base INT ${candidate.target_base_int} · MP wash 到 Lv ${candidate.mp_wash_end}`;
const codeFor = (candidate: { policy: PolicyName; target_base_int: number; mp_wash_end: number }) => `${policyLetter(candidate.policy)}·${candidate.target_base_int}·${candidate.mp_wash_end}`;

/** Unset gear INT is stated as a plain fact on the label, not as another warning box. */
function SimulationResult({ result, language, stale, onEditGear }: { result: SimulateResult; language: Language; stale: boolean; onEditGear?: () => void }) {
  const hpReached = result.final_display_hp >= result.target_hp;
  const mpReached = result.target_mp === undefined || result.final_base_mp >= result.target_mp;
  return translateTree(<section className="result-panel"><h3 className="visually-hidden">模擬結果</h3>
    <div className="result-lead"><Specimen language={language} code={codeFor(result)} headline={headlineFor(result)} reached={result.reached_target} hpReached={hpReached} mpReached={mpReached} stale={stale} targetHp={result.target_hp} finalHp={result.final_display_hp} targetMp={result.target_mp} finalMp={result.final_base_mp}
      figures={[[totalApr(result.apr).toLocaleString(), "總 APR"], [result.final_display_hp.toLocaleString(), "最終 HP"], [result.final_base_mp.toLocaleString(), "最終 base MP"], [String(result.int_reached_level || "—"), "INT 達標等級"]]} extras={[[policyTitle(result.policy), "策略"]]} onEditGear={onEditGear}
      note={result.reached_target ? undefined : <p className="sim-hint">想達標可以：提高 base INT、延後 MP wash 結束等級，或先到「最佳化」找出可達成的組合。</p>} />
    <div className="specimen-actions back-only"><a className="back-to-form" href="#calc-form">回到設定</a></div>
    <PlanKey title="逐級計畫" rows={result.plan} file="plan.csv" language={language} /></div></section>, language);
}
type Candidate = NonNullable<OptimizeResult["comparison"]["policy_a"]>;
/** How far a plan falls short of its goals, in the units the player checks in game. */
function shortfall(plan: SimulateResult): string {
  const parts: string[] = [];
  if (plan.final_display_hp < plan.target_hp) parts.push(`HP 差 ${(plan.target_hp - plan.final_display_hp).toLocaleString()}`);
  if (plan.target_mp !== undefined && plan.final_base_mp < plan.target_mp) parts.push(`MP 差 ${(plan.target_mp - plan.final_base_mp).toLocaleString()}`);
  return parts.length ? parts.join("、") : "未達成目標";
}
const comparedPolicies = (result: OptimizeResult) => ([["A", result.comparison.policy_a], ["B", result.comparison.policy_b], ["C", result.comparison.policy_c], ["D", result.comparison.policy_d]] as Array<[string, OptimizeResult["comparison"]["policy_a"]]>)
  .filter((item): item is [string, Candidate] => item[1] !== undefined);
/** The plan to follow: a simpler policy that reaches the target within 1% (at least 10 APR) of the fewest-APR plan, else the fewest-APR plan. */
function recommendedPlan(result: OptimizeResult): [string, Candidate] | undefined {
  const winner = result.winner;
  if (!winner) return undefined;
  const fewestApr = totalApr(winner.apr);
  const tolerance = Math.max(10, Math.round(fewestApr * 0.01));
  const simpler = comparedPolicies(result)
    .filter(([, candidate]) => candidate.reached_target && policyEffort[candidate.policy] < policyEffort[winner.policy] && totalApr(candidate.apr) - fewestApr <= tolerance)
    .sort(([, a], [, b]) => policyEffort[a.policy] - policyEffort[b.policy] || totalApr(a.apr) - totalApr(b.apr))[0];
  return simpler ?? [policyLetter(winner.policy), winner as Candidate];
}
/** Fine-tune the shown plan in place: change base INT or the MP wash end level and re-simulate, without leaving Optimize. */
function PlanTuner({ base, letter, stale, language, onTune }: { base: Candidate; letter: string; stale: boolean; language: Language; onTune: (request: SimulateRequest) => SimulateResult }) {
  const [targetInt, setTargetInt] = useState(String(base.target_base_int));
  const [mpWashEnd, setMpWashEnd] = useState(String(base.mp_wash_end));
  const [tuned, setTuned] = useState<SimulateResult>();
  const [error, setError] = useState<string>();
  const baseApr = totalApr(base.apr);
  function recalc() {
    try { setTuned(onTune({ policy: base.policy, targetInt: Number(targetInt), mpWashEnd: Number(mpWashEnd) })); setError(undefined); }
    catch (caught) { setTuned(undefined); setError(describeUserError(caught, language).message); }
  }
  // The tuner sits inside the Optimize form: Enter re-calculates here instead of re-running the whole search.
  const onEnter = (event: KeyboardEvent<HTMLInputElement>) => { if (event.key === "Enter") { event.preventDefault(); if (!stale) recalc(); } };
  const tunedApr = tuned ? totalApr(tuned.apr) : 0;
  const delta = tunedApr - baseApr;
  const hpDelta = tuned ? tuned.final_display_hp - base.final_display_hp : 0;
  const mpDelta = tuned ? tuned.final_base_mp - base.final_base_mp : 0;
  const unchanged = tuned !== undefined && delta === 0 && hpDelta === 0 && mpDelta === 0 && tuned.reached_target === base.reached_target;
  const signed = (value: number) => `${value > 0 ? "+" : ""}${value.toLocaleString()}`;
  // Only the levels whose APR moved; the full tuned plan stays folded so the recommended plan above remains the one to follow.
  const changedBands = tuned ? planBands(tuned.plan).map((band) => {
    const before = base.plan.filter((row) => row.level >= band.from && row.level <= band.to).reduce((sum, row) => sum + row.apr_spent, 0);
    return { ...band, before };
  }).filter((band) => band.apr !== band.before) : [];
  return translateTree(<details className="disclosure plan-tuner"><summary>微調這份計畫<span>改 base INT 或 MP wash 結束等級，立即重算 Policy {letter}</span></summary><div className="disclosure-body">
    {stale && <p className="stale-note">設定已變更，請先重新執行最佳化再微調。</p>}
    <div className="tuner-fields">
      <label>base INT<input id="tune-int" type="number" inputMode="numeric" min={4} step={1} value={targetInt} disabled={stale} onKeyDown={onEnter} onChange={(event) => setTargetInt(event.target.value)} /></label>
      <label>MP wash 結束等級<input id="tune-end" type="number" inputMode="numeric" min={31} max={200} step={1} value={mpWashEnd} disabled={stale} onKeyDown={onEnter} onChange={(event) => setMpWashEnd(event.target.value)} /></label>
      <button type="button" className="quiet" disabled={stale} onClick={recalc}>重算</button>
      {(targetInt !== String(base.target_base_int) || mpWashEnd !== String(base.mp_wash_end)) && <button type="button" className="link-button" onClick={() => { setTargetInt(String(base.target_base_int)); setMpWashEnd(String(base.mp_wash_end)); setTuned(undefined); setError(undefined); }}>回到原值</button>}
    </div>
    <p className="field-hint">原計畫：base INT {base.target_base_int} · MP wash 到 Lv {base.mp_wash_end} · 總 APR {baseApr.toLocaleString()}。其他設定沿用左邊的最佳化表單。</p>
    {error && <p className="field-error" role="alert">{error}</p>}
    {tuned && <div className="tuner-result" role="status">
      {unchanged ? <p className="tuner-outcome">結果與原計畫相同，照上方的計畫做即可。</p> : <>
        {tuned.reached_target
          // Fewer APR only counts as better when the tuned plan still reaches the goal.
          ? <p className="tuner-outcome"><span className="status-success"><Mark reached /> 已達標</span>
            <b>總 APR {tunedApr.toLocaleString()}（{signed(delta)}）</b>
            <span>最終 HP {tuned.final_display_hp.toLocaleString()}（{signed(hpDelta)}）· 最終 base MP {tuned.final_base_mp.toLocaleString()}（{signed(mpDelta)}）</span></p>
          : <p className="tuner-outcome is-missed"><span className="status-failure"><Mark reached={false} /> <b>未達標</b></span>
            <b>{shortfall(tuned)}</b>
            <span className="tuner-secondary">這個組合不能照做。總 APR {tunedApr.toLocaleString()}（{signed(delta)}）只供參考。下表列出和原計畫相比 APR 有變動的等級段，可以從這裡看出差在哪一段；按「回到原值」可重新調整。</span></p>}
        {changedBands.length > 0 && <table className="tuner-diff"><caption>APR 有變動的等級段</caption><thead><tr><th scope="col">等級</th><th scope="col">做法</th><th scope="col">原計畫</th><th scope="col">微調後</th></tr></thead>
          <tbody>{changedBands.map((band) => <tr key={band.id}><td>{levelRange(band.from, band.to)}</td><td>{band.title}</td><td>{band.before.toLocaleString()} APR</td><td>{band.apr.toLocaleString()} APR</td></tr>)}</tbody></table>}
        <details className="tuner-full"><summary>查看完整微調計畫與 CSV</summary>
          <PlanKey idPrefix="tuned-" title={`微調計畫 · ${headlineFor(tuned)}`} rows={tuned.plan} file={`plan-policy-${letter.toLowerCase()}-tuned.csv`} language={language} /></details>
      </>}
    </div>}
  </div></details>, language);
}
function OptimizationResult({ result, language, stale, onEditGear, onSimulate, onTune }: { result: OptimizeResult; language: Language; stale: boolean; onEditGear?: () => void; onSimulate: (request: SimulateRequest) => void; onTune: (request: SimulateRequest) => SimulateResult }) {
  const [selected, setSelected] = useState<string>();
  const winner = result.winner;
  if (!winner) return translateTree(<section className="result-panel"><h3>沒有可用候選計畫</h3><p className="subheading">請放寬目標 HP／MP，或調整洗回 INT 等級後再試一次。</p></section>, language);
  const policies = comparedPolicies(result);
  const fewestLetter = policyLetter(winner.policy);
  const fewestApr = totalApr(winner.apr);
  const [recommendedLetter, recommended] = recommendedPlan(result) ?? [fewestLetter, winner];
  const recommendedIsFewest = recommendedLetter === fewestLetter;
  const recommendedApr = totalApr(recommended.apr);
  const hpReached = recommended.final_display_hp >= recommended.target_hp;
  const mpReached = recommended.target_mp === undefined || recommended.final_base_mp >= recommended.target_mp;
  const planFor = (itemLetter: string, candidate: typeof winner) => itemLetter === fewestLetter && result.continued_to_200_plan ? [...winner.plan, ...result.continued_to_200_plan] : candidate.plan;
  const shownLetter = selected && policies.some(([itemLetter]) => itemLetter === selected) ? selected : recommendedLetter;
  const shown = policies.find(([itemLetter]) => itemLetter === shownLetter)?.[1] ?? recommended;
  const showPolicy = (itemLetter: string) => { setSelected(itemLetter); requestAnimationFrame(() => document.getElementById("plan-view")?.scrollIntoView({ behavior: "smooth", block: "start" })); };
  const toSimulate = (candidate: { policy: PolicyName; target_base_int: number; mp_wash_end: number }) => onSimulate({ policy: candidate.policy, targetInt: candidate.target_base_int, mpWashEnd: candidate.mp_wash_end });
  const extras: Array<[string, string]> = [[policyTitle(recommended.policy), recommendedIsFewest ? "優勝策略" : "建議照做"]];
  if (recommendedIsFewest && result.continued_to_200_hp !== undefined && result.continued_to_200_hp !== winner.final_display_hp) extras.push([result.continued_to_200_hp.toLocaleString(), "繼續到 200 等最高 HP"]);
  return translateTree(<section className="result-panel"><h3 className="visually-hidden">最佳化結果</h3>
    <div className="result-lead">
      <Specimen language={language} code={codeFor(recommended)} headline={headlineFor(recommended)} reached={recommended.reached_target} hpReached={hpReached} mpReached={mpReached} stale={stale} targetHp={recommended.target_hp} finalHp={recommended.final_display_hp} targetMp={recommended.target_mp} finalMp={recommended.final_base_mp}
        figures={[[recommendedApr.toLocaleString(), "總 APR"], [recommended.final_display_hp.toLocaleString(), "最終 HP"], [recommended.final_base_mp.toLocaleString(), "最終 base MP"], [String(recommended.int_reached_level || "—"), "INT 達標等級"]]}
        extras={extras} onEditGear={onEditGear} />
      <div className="specimen-actions"><button type="button" className="quiet" onClick={() => toSimulate(recommended)}>在模擬中開啟</button><span className="field-hint">帶入策略、base INT 與 MP wash 結束等級，再微調。</span><a className="back-to-form" href="#calc-form">回到設定</a></div>
      <PlanKey title={shownLetter === recommendedLetter ? `${recommendedIsFewest ? "優勝計畫" : "建議計畫"} · ${policyTitle(shown.policy)}` : `${policyTitle(shown.policy)} 計畫`} summary={`總 APR ${totalApr(shown.apr).toLocaleString()} · base INT ${shown.target_base_int} · MP wash 到 Lv ${shown.mp_wash_end} · 最終 HP ${shown.final_display_hp.toLocaleString()}`} rows={planFor(shownLetter, shown)} file={`plan-policy-${shownLetter.toLowerCase()}.csv`} language={language} />
      <PlanTuner key={`${shownLetter}-${shown.target_base_int}-${shown.mp_wash_end}`} base={shown} letter={shownLetter} stale={stale} language={language} onTune={onTune} />
      <section className="comparison"><div className="result-heading"><h4 className="section-plate">策略比較</h4><span className="plate-note">{winner.target_mp === undefined ? "未設 MP 目標 · " : ""}點選卡片在上方查看該策略的計畫</span></div>
      <div className="comparison-grid">{policies.map(([itemLetter, candidate]) => {
        const apr = totalApr(candidate.apr);
        const delta = apr - fewestApr;
        const isShown = itemLetter === shownLetter;
        const tag = itemLetter === recommendedLetter ? (recommendedIsFewest ? "優勝" : "建議") : itemLetter === fewestLetter ? "理論最少" : undefined;
        return <article className={`${candidate.reached_target ? "reachable" : "unreachable"}${itemLetter === recommendedLetter ? " is-winner" : ""}${isShown ? " is-shown" : ""}`} key={itemLetter}>
          {tag && <span className={itemLetter === recommendedLetter ? "winner-tag" : "winner-tag is-fewest"}>{tag}</span>}
          <button type="button" className="card-select" aria-pressed={isShown} onClick={() => showPolicy(itemLetter)}>
            <span className="policy-name">{policyTitle(candidate.policy)}</span>
            <b>{apr.toLocaleString()} APR {itemLetter !== fewestLetter && <span className="apr-delta">{delta >= 0 ? `+${delta.toLocaleString()}` : delta.toLocaleString()} APR</span>}</b>
            <span className={candidate.reached_target ? "status-success" : "status-failure"}><Mark reached={candidate.reached_target} /> {candidate.reached_target ? "已達標" : "未達標"}</span>
            <small>INT {candidate.target_base_int}{" · MP wash 到 Lv "}{candidate.mp_wash_end}{" · HP "}{candidate.final_display_hp.toLocaleString()}{candidate.target_mp === undefined ? "" : ` · MP ${candidate.final_base_mp.toLocaleString()} / ${candidate.target_mp.toLocaleString()}`}</small>
            {itemLetter === fewestLetter && !recommendedIsFewest && <span className="card-cue">比建議少 {(recommendedApr - fewestApr).toLocaleString()} APR，但要逐 AP 操作</span>}
            {isShown && <span className="card-cue">正在上方顯示</span>}
          </button>        </article>;
      })}</div></section>
    </div></section>, language);
}

/** Plan action codes in the player's words; the code itself stays in the tooltip. */
function actionName(action: PlanRow["action"]): string {
  const wash = /^(HP|MP)([1-5])$/.exec(action);
  if (wash) return `${wash[1] === "HP" ? "Method 1 洗血" : "MP wash"} ×${wash[2]}`;
  const stat = /^(INT|LUK|STR|DEX)5$/.exec(action);
  if (stat) return `點 ${stat[1]}`;
  const names: Record<string, string> = { NONE: "—", BUILD: "配點", HARDCORE_GREEDY: "逐 AP 洗", M2: "Method 2", RESET_INT: "洗回 INT", RESUME: "接續起點" };
  return names[action] ?? action;
}
/** Consecutive levels that do the same thing (same move, same AP split, same APR) read as one line. */
function compressRows(rows: PlanRow[]): PlanRow[][] {
  const groups: PlanRow[][] = [];
  for (const row of rows) {
    const last = groups.at(-1)?.at(-1);
    const same = last && last.level + 1 === row.level && last.action === row.action && last.apr_spent === row.apr_spent
      && last.fresh_ap_int === row.fresh_ap_int && last.fresh_ap_hp === row.fresh_ap_hp && last.fresh_ap_mp === row.fresh_ap_mp && row.action !== "RESET_INT";
    if (same) groups.at(-1)!.push(row); else groups.push([row]);
  }
  return groups;
}
const span = (from: number, to: number) => from === to ? String(from) : `${from}→${to}`;
const noteText = (notes: string) => /[：:]\s*$/.test(notes) ? `${notes}—` : notes;
function PlanTable({ rows, language = "zh", compact = false }: { rows: SimulateResult["plan"]; language?: Language; compact?: boolean }) {
  const groups = compact ? compressRows(rows) : rows.map((row) => [row]);
  return translateTree(<div className="plan"><table><thead><tr><th scope="col">Lv</th><th scope="col">動作</th><th scope="col" className="col-detail">base INT</th><th scope="col" className="col-detail">base HP</th><th scope="col" className="col-detail">base MP</th><th scope="col" className="col-detail">Extra MP</th><th scope="col" className="col-detail">AP</th><th scope="col">APR</th><th scope="col">備註</th></tr></thead><tbody>{groups.map((group) => {
    const first = group[0];
    const last = group.at(-1)!;
    const many = group.length > 1;
    const overMp = group.some((row) => row.base_mp > 30000);
    return <tr key={`${first.level}-${first.action}`} className={`${first.action === "RESET_INT" ? "is-reset" : ""}${many ? " is-merged" : ""}`}>
      <td>{many ? `${first.level}–${last.level}` : first.level}</td>
      <td title={first.action}>{actionName(first.action)}</td>
      <td className="col-detail">{span(first.base_int, last.base_int)}</td>
      <td className="col-detail">{span(first.base_hp, last.base_hp)}</td>
      <td className="col-detail">{span(first.base_mp, last.base_mp)}{overMp && <span className="mp-warning" title="超過 30,000；建議提早做 Method 2"><span aria-hidden="true">{" ⚠"}</span><span className="visually-hidden">超過 30,000；建議提早做 Method 2</span></span>}</td>
      <td className="col-detail">{span(first.extra_mp, last.extra_mp)}</td>
      <td className="col-detail">INT {first.fresh_ap_int} · HP {first.fresh_ap_hp} · MP {first.fresh_ap_mp}</td>
      <td>{many ? `${first.apr_spent} ×${group.length}` : first.apr_spent}</td>
      <td>{noteText(first.notes)}{many && <span className="merged-note">（每級相同，共 {group.length} 級）</span>}</td>
    </tr>;
  })}</tbody></table></div>, language);
}
