import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { computeIntGearSegments, parseEquipment } from "./core/equipment";
import { EQUIPMENT_TYPES, totalApr, type EquipmentItem, type HpMode, type OptimizeResult, type PolicyName, type ResumeFrom, type SimulateResult } from "./core/models";
import { getJobProfile } from "./core/jobs";
import { JobReference } from "./JobReference";
import { optimize } from "./core/optimizer";
import { simulate } from "./core/simulator";
import { downloadText, readJsonFile } from "./file/browser";
import { planCsv } from "./file/plan-csv";
import { describeUserError, type ErrorField } from "./user-errors";
import { translateText, translateTree, type Language } from "./i18n";

type Tab = "guide" | "job-reference" | "equipment" | "optimize" | "simulate" | "actions" | "disclaimer";
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
// Ordered by task: the two calculators come straight after the guide.
const tabs: Array<{ id: Tab; label: string }> = [
  { id: "guide", label: "使用指南 Guide" }, { id: "optimize", label: "最佳化 Optimize" }, { id: "simulate", label: "模擬 Simulate" },
  { id: "equipment", label: "裝備 Equipment" }, { id: "job-reference", label: "職業數值 Job reference" },
  { id: "actions", label: "策略說明 Actions" }, { id: "disclaimer", label: "聯絡作者 Contact Author" },
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
  return { job: "thief", policy: "mp_wash_shortfall", targetHp: 27000, targetMp: "", targetLevel: "200", targetInt: 350, resetLevel: 155, mpWashEnd: 100, questHp: 0, hpMode: "avg", mwPercent: 0.1, mwFromLevel: 10, gearAfterReset: 50, autoMethod2: true, compareThiefPolicyC: true, resumeEnabled: false, resume: { ...emptyResume } };
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
function readLanguage(): Language {
  try { return localStorage.getItem("mapleroyals-hp-wash-language") === "en" ? "en" : "zh"; }
  catch { return "zh"; }
}
const optionalNumber = (value: string): number | undefined => value.trim() === "" ? undefined : Number(value);
const fieldId = (field: ErrorField) => `field-${field.replace(".", "-")}`;

type FieldProps = {
  name: ErrorField | string; label: string; value: string | number; onChange: (value: string) => void;
  invalid?: ErrorField; min?: number; max?: number; step?: number | string; hint?: string;
};
function Field({ name, label, value, onChange, invalid, min, max, step, hint }: FieldProps) {
  const id = fieldId(name as ErrorField);
  const isInvalid = invalid === name;
  const describedBy = [hint ? `${id}-hint` : "", isInvalid ? "form-error" : ""].filter(Boolean).join(" ") || undefined;
  return <label>{label}<input id={id} type="number" inputMode="decimal" min={min} max={max} step={step} value={value} aria-invalid={isInvalid || undefined} aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)} />{hint && <small id={`${id}-hint`} className="field-hint">{hint}</small>}</label>;
}

export function App() {
  const [cache, setCache] = useState<AppCache>(readCache);
  const [language, setLanguage] = useState<Language>(readLanguage);
  const [result, setResult] = useState<SimulateResult>();
  const [optimized, setOptimized] = useState<OptimizeResult>();
  const [failure, setFailure] = useState<Failure>();
  const [busy, setBusy] = useState(false);
  const [undo, setUndo] = useState<Undo>();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [resumeOpen, setResumeOpen] = useState(false);
  const equipmentInput = useRef<HTMLInputElement>(null);
  const { tab, equipment, optimize: optimizeConfig, simulate: simulateConfig } = cache;
  const config = tab === "simulate" ? simulateConfig : optimizeConfig;
  const profile = getJobProfile(config.job);
  const effectivePolicy = profile.policies.includes(config.policy) ? config.policy : profile.policies[0];
  const userError = failure && failure.tab === tab ? describeUserError(failure.error, language) : undefined;
  const invalid = userError?.field;
  const gearPreview = useMemo(() => {
    try { return computeIntGearSegments(equipment, Math.max(1, optimizeConfig.resetLevel - 1)); }
    catch { return []; }
  }, [equipment, optimizeConfig.resetLevel]);

  useEffect(() => {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); }
    catch { /* Browser storage may be unavailable or full. */ }
  }, [cache]);

  useEffect(() => {
    try { localStorage.setItem("mapleroyals-hp-wash-language", language); }
    catch { /* Browser storage may be unavailable. */ }
    document.documentElement.lang = language === "en" ? "en" : "zh-Hant";
  }, [language]);

  // Move focus to the field an error points at, opening its group first.
  useEffect(() => {
    if (!failure) return;
    const field = describeUserError(failure.error).field;
    if (!field || field === "equipment") { document.getElementById("form-error")?.focus(); return; }
    if (field.startsWith("resume.")) setResumeOpen(true);
    if (advancedFields.includes(field)) setAdvancedOpen(true);
    requestAnimationFrame(() => (document.getElementById(fieldId(field)) ?? document.getElementById("form-error"))?.focus());
  }, [failure]);

  function updateConfig(patch: Partial<CalculatorConfig>) {
    setCache((previous) => tab === "simulate"
      ? { ...previous, simulate: { ...previous.simulate, ...patch } }
      : { ...previous, optimize: { ...previous.optimize, ...patch } });
  }
  function updateResume(patch: Partial<ResumeFields>) { updateConfig({ resume: { ...config.resume, ...patch } }); }
  function changeTab(next: Tab) { setCache((previous) => ({ ...previous, tab: next })); setFailure(undefined); }
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
  function runSimulate() {
    try {
      const activeProfile = getJobProfile(simulateConfig.job);
      const policy = activeProfile.policies.includes(simulateConfig.policy) ? simulateConfig.policy : activeProfile.policies[0];
      setFailure(undefined); setOptimized(undefined);
      setResult(simulate({ ...sharedConfig(simulateConfig), policy, target_base_int: simulateConfig.targetInt, mp_wash_end: simulateConfig.mpWashEnd, auto_method2: simulateConfig.autoMethod2 }));
    } catch (caught) { setResult(undefined); setFailure({ error: caught, tab: "simulate" }); }
  }
  function runOptimize() {
    try {
      const activeProfile = getJobProfile(optimizeConfig.job);
      setFailure(undefined); setResult(undefined);
      setOptimized(optimize({
        ...sharedConfig(optimizeConfig), policies: activeProfile.policies.filter((policy) => optimizeConfig.job !== "thief" || optimizeConfig.compareThiefPolicyC || policy !== "mp_wash_hardcore"),
        target_base_int_min: 4, target_base_int_max: 999, target_base_int_step: 10,
        mp_wash_end_min: 31, top_n: 5,
      }));
    } catch (caught) { setOptimized(undefined); setFailure({ error: caught, tab: "optimize" }); }
  }
  // The search is synchronous; yield one frame so the busy state paints first.
  function run() {
    if (busy) return;
    setBusy(true);
    const job = tab === "optimize" ? runOptimize : runSimulate;
    window.setTimeout(() => { try { job(); } finally { setBusy(false); } }, 30);
  }
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
      <div className="notice-row"><div className="notice notice-tip"><b>計算提示</b><p>最佳化與模擬會依目前裝備清單及各自設定的洗回 INT 等級，即時更新 INT 裝備區間。</p></div><div className="notice notice-caution"><b>結果僅供參考</b><p>洗血涉及多項職業公式、能力值與遊戲機制，計算過程較為複雜。程式提供的最佳化結果可能有誤，請將結果作為參考，並在遊戲中操作前自行確認。</p></div></div>
    </section>,

    equipment: () => <section className="page-card equipment-page">
      <div className="section-heading"><div><h2>裝備設定</h2><p className="subheading">每種裝備槽取最高 INT；Ring 最多計入四件。下表會即時預覽各等級可用的總 INT。</p></div><div className="button-row"><input ref={equipmentInput} className="visually-hidden" type="file" accept="application/json,.json" tabIndex={-1} aria-hidden="true" onChange={(event) => { void importEquipment(event.target.files?.[0]); event.target.value = ""; }} /><button className="quiet" type="button" onClick={restoreDefaults}>還原預設</button><button className="quiet" type="button" onClick={() => equipmentInput.current?.click()}>載入智力裝備設定</button><button className="quiet" type="button" onClick={() => downloadText("int-equipment-settings.json", `${JSON.stringify(equipment, null, 2)}\n`, "application/json;charset=utf-8")}>儲存智力裝備設定</button></div></div>
      {errorBox}
      <div className="equipment-toolbar"><button type="button" onClick={addEquipment}>新增裝備</button><span className="equipment-auto-note">編輯裝備清單後，最佳化與模擬會依各自設定的洗回 INT 等級自動套用。</span></div>
      {undo && <div className="undo-bar" role="status"><span>{undo.message}</span><button type="button" className="quiet" onClick={revertEquipment}>復原</button></div>}
      <div className="equipment-layout"><div className="equipment-table-wrap"><table className="equipment-table"><thead><tr><th scope="col">裝備名稱</th><th scope="col">類型</th><th scope="col">INT</th><th scope="col">穿戴等級</th><th scope="col"><span className="visually-hidden">移除</span></th></tr></thead><tbody>{equipment.map((item, index) => <tr key={index}><td><input aria-label={`Equipment ${index + 1} name`} value={item.name} onChange={(event) => updateEquipment(index, { name: event.target.value })} /></td><td><select aria-label={`Equipment ${index + 1} type`} value={item.type} onChange={(event) => updateEquipment(index, { type: event.target.value as EquipmentItem["type"] })}>{EQUIPMENT_TYPES.map((type) => <option key={type}>{type}</option>)}</select></td><td><input aria-label={`Equipment ${index + 1} INT`} type="number" min="0" value={item.int} onChange={(event) => updateEquipment(index, { int: Number(event.target.value) })} /></td><td><input aria-label={`Equipment ${index + 1} level`} type="number" min="1" max="200" value={item.equip_level} onChange={(event) => updateEquipment(index, { equip_level: Number(event.target.value) })} /></td><td><button className="remove" type="button" aria-label={`Remove equipment ${index + 1}${item.name ? ` (${item.name})` : ""}`} onClick={() => removeEquipment(index)}>移除</button></td></tr>)}</tbody></table></div>
        <aside className="gear-preview"><h3>INT 裝備預覽</h3><p>洗回後升等裝備 INT：{optimizeConfig.gearAfterReset}</p>{gearPreview.length ? <table><thead><tr><th scope="col">等級</th><th scope="col">裝備 INT</th></tr></thead><tbody>{gearPreview.map((segment) => <tr key={segment.from_level}><td>{segment.from_level}–{segment.to_level}</td><td>{segment.int_gear}</td></tr>)}</tbody></table> : <p className="error">請檢查裝備名稱、INT 與裝備等級。</p>}</aside></div>
    </section>,

    "job-reference": () => <JobReference language={language} />,
    optimize: () => calculator(),
    simulate: () => calculator(),

    actions: () => <section className="page-card"><h2>策略、洗法與計畫動作說明</h2><div className="action-grid"><article><h3>Policy A — MP wash shortfall</h3><p>31 等級起進入 INT 目標階段。Extra MP 達 threshold 時用 Method 1 洗 HP；不足時先 MP wash。</p></article><article><h3>Policy B — INT dump shortfall</h3><p>Extra MP 足夠時用 Method 1；不足時把本等 AP 點入 INT，該列不增加洗血 APR。</p></article><article><h3>Policy C — Hardcore greedy</h3><p>10 等起逐 AP 檢查：Extra MP 足夠就 HP1；30 等起可嘗試 MP1；剩餘 AP 投入 INT／主屬性。</p></article><article><h3>Policy D — Plain INT</h3><p>先集中 INT，達標後進行 MP wash、Method 1／Method 2 與 INT reset。非 Thief 職業使用此策略。</p></article><article><h3>Method 1</h3><p>使用當等級新鮮 AP 加 HP，再以 APR 扣除職業對應 MP；新鮮 AP 回到 INT 或主屬性。</p></article><article><h3>Method 2</h3><p>使用 APR 扣 Extra MP 換取 HP，沒有新鮮 AP 限制；計算會遵守設定的目標 base MP 下限。</p></article><article><h3>計畫動作</h3><p><code>BUILD</code> 建立初始能力值；<code>HP1–HP5</code>／<code>MP1–MP5</code> 表示本等洗血／洗 MP；<code>M2</code> 為 Method 2；<code>RESET_INT</code> 為 INT 洗回；<code>RESUME</code> 標示接續起點。</p></article></div></section>,

    disclaimer: () => <section className="page-card"><h2>聯絡作者 Contact Author</h2><p>若發現問題或有任何疑問，歡迎聯絡作者：</p><ul><li>Discord：<b>fuhuo</b></li><li>GitHub：<a href="https://github.com/Liang0218/mapleroyals-hp-washing" target="_blank" rel="noreferrer">MapleRoyals HP Washing APR Optimizer</a></li></ul></section>,
  };

  function calculator() {
    const isOptimize = tab === "optimize";
    return <form className="calculator-page" noValidate onSubmit={(event) => { event.preventDefault(); run(); }}>
      <div className="page-title"><div><h2>{isOptimize ? "最佳化計畫" : "單一計畫模擬"}</h2><p className="subheading">{isOptimize ? "搜尋最佳 base INT 與 MP wash 結束等級，並比較適用策略。" : "固定 base INT 與 MP wash 結束等級，模擬每一級的 AP／APR 行動。"}</p></div></div>

      <fieldset className="form-section"><legend>目標與職業</legend><div className="fields">
        <label>職業<select id={fieldId("job")} value={config.job} aria-invalid={invalid === "job" || undefined} onChange={(event) => updateConfig({ job: event.target.value })}>{jobs.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <Field name="targetHp" invalid={invalid} min={1} step={1} label="目標 HP" value={config.targetHp} onChange={(value) => updateConfig({ targetHp: Number(value) })} />
        <label>目標 MP（留空則洗到最低）<input id={fieldId("targetMp")} type="number" inputMode="numeric" min={0} step={1} value={config.targetMp} aria-invalid={invalid === "targetMp" || undefined} onChange={(event) => updateConfig({ targetMp: event.target.value })} /></label>
        <label>目標等級（留空則表示 200 等）<input id={fieldId("targetLevel")} type="number" inputMode="numeric" min={31} max={200} step={1} value={config.targetLevel} aria-invalid={invalid === "targetLevel" || undefined} onChange={(event) => updateConfig({ targetLevel: event.target.value })} /></label>
        <Field name="resetLevel" invalid={invalid} min={2} max={200} step={1} label="洗回 INT 等級" value={config.resetLevel} onChange={(value) => updateConfig({ resetLevel: Number(value) })} />
      </div><p className="field-note">裝備 INT 會從「裝備 Equipment」分頁的裝備清單計算。</p></fieldset>

      {isOptimize
        ? optimizeConfig.job === "thief" && <fieldset className="form-section"><legend>最佳化比較策略</legend><label className="checkbox-field"><input type="checkbox" checked={optimizeConfig.compareThiefPolicyC} onChange={(event) => updateConfig({ compareThiefPolicyC: event.target.checked })} />比較 Policy C（Hardcore greedy）</label><p className="field-note">Policy C 會逐 AP 嘗試洗血與洗 MP，策略較繁瑣，搜尋也較耗時。關閉後只比較 A／B／D，可縮短最佳化時間。</p></fieldset>
        : <fieldset className="form-section"><legend>模擬參數</legend><div className="fields">
          <label>Policy<select id={fieldId("policy")} value={effectivePolicy} aria-describedby="policy-hint" aria-invalid={invalid === "policy" || undefined} onChange={(event) => updateConfig({ policy: event.target.value as PolicyName })}>{profile.policies.map((value) => <option key={value} value={value}>{policyLabels[value]}</option>)}</select><small id="policy-hint" className="field-hint">{policyHints[effectivePolicy]}</small></label>
          <Field name="targetInt" invalid={invalid} min={4} step={1} label="目標 base INT" value={config.targetInt} onChange={(value) => updateConfig({ targetInt: Number(value) })} />
          <Field name="mpWashEnd" invalid={invalid} min={31} max={200} step={1} label="MP wash 結束等級" value={config.mpWashEnd} onChange={(value) => updateConfig({ mpWashEnd: Number(value) })} />
          <label className="checkbox-field"><input type="checkbox" checked={config.autoMethod2} onChange={(event) => updateConfig({ autoMethod2: event.target.checked })} />自動以 Method 2 補足目標 HP</label>
        </div></fieldset>}

      <details className="disclosure" open={advancedOpen} onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}><summary>進階設定<span>裝備 INT、HP 計算方式與 Maple Warrior</span></summary><div className="fields disclosure-body">
        <Field name="gearAfterReset" invalid={invalid} min={0} step={1} label="洗回後升等裝備 INT" value={config.gearAfterReset} onChange={(value) => updateConfig({ gearAfterReset: Number(value) })} />
        <Field name="questHp" min={0} step={1} label="任務／裝備 HP" value={config.questHp} onChange={(value) => updateConfig({ questHp: Number(value) })} />
        <label>HP 模式<select value={config.hpMode} onChange={(event) => updateConfig({ hpMode: event.target.value as HpMode })}><option value="avg">平均 avg</option><option value="min">最低 min</option><option value="max">最高 max</option></select></label>
        <Field name="mwPercent" min={0} max={1} step="0.01" label="Maple Warrior 比例" hint="填 0.1 代表 10%" value={config.mwPercent} onChange={(value) => updateConfig({ mwPercent: Number(value) })} />
        <Field name="mwFromLevel" min={1} max={200} step={1} label="Maple Warrior 起始等級" value={config.mwFromLevel} onChange={(value) => updateConfig({ mwFromLevel: Number(value) })} />
      </div></details>

      <details className="disclosure" open={resumeOpen} onToggle={(event) => setResumeOpen(event.currentTarget.open)}><summary>中途接續 Resume<span>從已經在練的角色接著算</span></summary><div className="disclosure-body"><label className="checkbox-field resume-toggle"><input type="checkbox" checked={config.resumeEnabled} onChange={(event) => updateConfig({ resumeEnabled: event.target.checked })} />從目前角色狀態接續計算，APR 只統計接下來使用的 APR</label>{config.resumeEnabled && <div className="fields resume-fields">
        <Field name="resume.level" invalid={invalid} min={1} max={200} step={1} label="目前等級" value={config.resume.level} onChange={(level) => updateResume({ level })} /><Field name="resume.baseHp" invalid={invalid} min={1} step={1} label="base HP" value={config.resume.baseHp} onChange={(baseHp) => updateResume({ baseHp })} />
        <Field name="resume.baseMp" invalid={invalid} min={0} step={1} label="base MP" value={config.resume.baseMp} onChange={(baseMp) => updateResume({ baseMp })} />
        <Field name="resume.baseInt" invalid={invalid} min={4} step={1} label="base INT" value={config.resume.baseInt} onChange={(baseInt) => updateResume({ baseInt })} /><Field name="baseStr" min={4} step={1} label="base STR" value={config.resume.baseStr} onChange={(baseStr) => updateResume({ baseStr })} />
        <Field name="baseDex" min={4} step={1} label="base DEX" value={config.resume.baseDex} onChange={(baseDex) => updateResume({ baseDex })} /><Field name="baseLuk" min={4} step={1} label="base LUK" value={config.resume.baseLuk} onChange={(baseLuk) => updateResume({ baseLuk })} />
        <Field name="freshAp" min={0} step={1} label="本等尚未點的 AP" value={config.resume.freshAp} onChange={(freshAp) => updateResume({ freshAp })} />
        <Field name="unwashedAp" min={0} step={1} label="尚未洗回的 HP／MP AP" value={config.resume.unwashedAp} onChange={(unwashedAp) => updateResume({ unwashedAp })} />
        <label className="checkbox-field"><input type="checkbox" checked={config.resume.intResetDone} onChange={(event) => updateResume({ intResetDone: event.target.checked })} />INT 已洗回 4，之後不再點 INT</label>
      </div>}</div></details>

      <div className="runbar">
        <p className="runbar-note">{busy ? (isOptimize ? "正在搜尋 base INT 與 MP wash 組合，請稍候。" : "正在逐級模擬，請稍候。") : "完成後可在結果區下載逐級計畫 CSV。"}</p>
        <button type="submit" className="run-button" disabled={busy} aria-busy={busy}>{busy ? "計算中…" : isOptimize ? "執行最佳化" : "執行模擬"}</button>
      </div>
      {errorBox}
      <div aria-live="polite">{tab === "simulate" && result && !busy && <SimulationResult result={result} language={language} />}{isOptimize && optimized && !busy && <OptimizationResult result={optimized} language={language} />}</div>
    </form>;
  }

  return <main className="app-shell">
    <header className="app-header"><h1><span className="brand">MapleRoyals</span> HP Washing APR Optimizer</h1><div className="language-switch" role="group" aria-label="Language"><button type="button" aria-pressed={language === "zh"} className={language === "zh" ? "language-active" : ""} onClick={() => setLanguage("zh")}>中文</button><button type="button" aria-pressed={language === "en"} className={language === "en" ? "language-active" : ""} onClick={() => setLanguage("en")}>EN</button></div></header>
    {translateTree(<>
    <div className="tabbar" role="tablist" aria-label="Calculator sections" onKeyDown={onTabKey}>{tabs.map((item) => <button key={item.id} id={`tab-${item.id}`} type="button" role="tab" aria-selected={tab === item.id} aria-controls="tab-panel" tabIndex={tab === item.id ? 0 : -1} className={tab === item.id ? "tab active" : "tab"} onClick={() => changeTab(item.id)}>{item.label}</button>)}</div>
    <div id="tab-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
      {tab !== "optimize" && tab !== "simulate" && tab !== "equipment" && errorBox}
      {panels[tab]()}
    </div>
    <footer className="app-footer"><span>v{__APP_VERSION__}</span><span>僅供參考，操作前請在遊戲中確認。</span></footer>
    </>, language)}
  </main>;
}

function Outcome({ reached, hpReached, mpReached, targetHp, finalHp, targetMp, finalMp, apr }: { reached: boolean; hpReached: boolean; mpReached: boolean; targetHp: number; finalHp: number; targetMp?: number; finalMp: number; apr: number }) {
  const outcome = reached ? "已達成目標" : hpReached && !mpReached ? "無法同時達標 — HP 已達標，MP 未達標" : "無法達成 — 最接近結果";
  const mpDetail = targetMp === undefined ? "未設定 MP 目標" : `MP 目標 ${targetMp}，實際 ${finalMp}${mpReached ? "（達標）" : "（未達標）"}`;
  return <div className={`goal-outcome ${reached ? "success" : "failure"}`} role="status"><strong>{outcome}</strong><span>HP 目標 {targetHp}，實際 {finalHp}（{hpReached ? "達標" : "未達標"}）；{mpDetail}；APR {apr}。</span></div>;
}

function SimulationResult({ result, language }: { result: SimulateResult; language: Language }) {
  const hpReached = result.final_display_hp >= result.target_hp;
  const mpReached = result.target_mp === undefined || result.final_base_mp >= result.target_mp;
  return translateTree(<section className="result-panel"><div className="result-heading"><h3>模擬結果</h3></div><Outcome reached={result.reached_target} hpReached={hpReached} mpReached={mpReached} targetHp={result.target_hp} finalHp={result.final_display_hp} targetMp={result.target_mp} finalMp={result.final_base_mp} apr={totalApr(result.apr)} /><Metrics language={language} items={[[result.final_display_hp.toLocaleString(), "最終 HP"], [result.final_base_mp.toLocaleString(), "最終 base MP"], [totalApr(result.apr).toLocaleString(), "總 APR"], [String(result.int_reached_level || "—"), "INT 達標等級"]]} /><div className="result-heading"><h4>逐級計畫（{result.plan.length} 列）</h4><button type="button" className="quiet" onClick={() => downloadText("plan.csv", planCsv(result.plan), "text/csv;charset=utf-8")}>下載 CSV</button></div><PlanTable language={language} rows={result.plan} /></section>, language);
}
function OptimizationResult({ result, language }: { result: OptimizeResult; language: Language }) {
  const winner = result.winner;
  if (!winner) return translateTree(<section className="result-panel"><h3>沒有可用候選計畫</h3><p className="subheading">請放寬目標 HP／MP，或調整洗回 INT 等級後再試一次。</p></section>, language);
  const policies: Array<[string, OptimizeResult["comparison"]["policy_a"]]> = [["A", result.comparison.policy_a], ["B", result.comparison.policy_b], ["C", result.comparison.policy_c], ["D", result.comparison.policy_d]];
  const hpReached = winner.final_display_hp >= winner.target_hp;
  const mpReached = winner.target_mp === undefined || winner.final_base_mp >= winner.target_mp;
  const fullPlan = result.continued_to_200_plan ? [...winner.plan, ...result.continued_to_200_plan] : winner.plan;
  return translateTree(<section className="result-panel"><div className="result-heading"><h3>最佳化結果</h3></div><Outcome reached={winner.reached_target} hpReached={hpReached} mpReached={mpReached} targetHp={winner.target_hp} finalHp={winner.final_display_hp} targetMp={winner.target_mp} finalMp={winner.final_base_mp} apr={totalApr(winner.apr)} /><Metrics language={language} items={[[policyLabels[winner.policy], "優勝策略"], [totalApr(winner.apr).toLocaleString(), "總 APR"], [String(winner.target_base_int), "最佳 base INT"], [String(winner.mp_wash_end), "MP wash 結束等級"], [winner.final_display_hp.toLocaleString(), "最終 HP"], [winner.final_base_mp.toLocaleString(), "最終 base MP"], [String(winner.plan.at(-1)?.level ?? ""), "目標等級"], [(result.continued_to_200_hp ?? winner.final_display_hp).toLocaleString(), "繼續到 200 等最高 HP"]]} /><h4>策略比較</h4><div className="comparison-grid">{policies.filter((item): item is [string, NonNullable<typeof item[1]>] => item[1] !== undefined).map(([letter, candidate]) => <article className={candidate.reached_target ? "reachable" : "unreachable"} key={letter}><span>Policy {letter}{" · "}<b className={candidate.reached_target ? "status-success" : "status-failure"}>{candidate.reached_target ? "已達標" : "未達標"}</b></span><b>{totalApr(candidate.apr).toLocaleString()} APR</b><small>INT {candidate.target_base_int}{" · MP "}結束 {candidate.mp_wash_end}{" · HP "}{candidate.final_display_hp.toLocaleString()} / {candidate.target_hp?.toLocaleString() ?? "?"}{" · MP "}{candidate.final_base_mp.toLocaleString()} / {candidate.target_mp?.toLocaleString() ?? "?"}</small></article>)}</div><div className="result-heading"><h4>優勝計畫（{fullPlan.length} 列）</h4><button type="button" className="quiet" onClick={() => downloadText("optimized-plan.csv", planCsv(fullPlan), "text/csv;charset=utf-8")}>下載 CSV</button></div><PlanTable language={language} rows={fullPlan} /></section>, language);
}
function Metrics({ items, language = "zh" }: { items: Array<[string, string]>; language?: Language }) { return <div className="metrics">{items.map(([value, label]) => <span key={label}><b>{value}</b>{translateText(label, language)}</span>)}</div>; }
function PlanTable({ rows, language = "zh" }: { rows: SimulateResult["plan"]; language?: Language }) { return translateTree(<div className="plan"><table><thead><tr><th scope="col">Lv</th><th scope="col">Action</th><th scope="col">base INT</th><th scope="col">base HP</th><th scope="col">base MP</th><th scope="col">Extra MP</th><th scope="col">AP</th><th scope="col">APR</th><th scope="col">備註</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.level}-${row.action}-${index}`}><td>{row.level}</td><td>{row.action}</td><td>{row.base_int}</td><td>{row.base_hp}</td><td>{row.base_mp}{row.base_mp > 30000 && <span className="mp-warning" title="超過 30,000；建議提早做 Method 2" aria-label="超過 30,000；建議提早做 Method 2">{" ⚠"}</span>}</td><td>{row.extra_mp}</td><td>INT {row.fresh_ap_int} · HP {row.fresh_ap_hp} · MP {row.fresh_ap_mp}</td><td>{row.apr_spent}</td><td>{row.notes}</td></tr>)}</tbody></table></div>, language); }
