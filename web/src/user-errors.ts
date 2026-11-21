import type { Language } from "./i18n";

/** Form field an error belongs to, so the UI can mark and focus it. */
export type ErrorField =
  | "job" | "targetHp" | "targetMp" | "targetLevel" | "resetLevel" | "gearAfterReset" | "targetInt" | "mpWashEnd" | "policy"
  | "resume.level" | "resume.baseHp" | "resume.baseMp" | "resume.baseInt" | "equipment";

export type UserError = { message: string; field?: ErrorField };
type Entry = { zh: string; en: string; field?: ErrorField };

const GENERIC: Entry = { zh: "操作失敗，請檢查輸入欄位後重試。", en: "Something went wrong. Check the inputs and try again." };

const exactMessages: Record<string, Entry> = {
  "target_level out of range": { zh: "「目標等級」必須是 31 到 200 的整數。", en: "Target level must be a whole number from 31 to 200.", field: "targetLevel" },
  "target_hp must be positive": { zh: "「目標 HP」必須大於 0。", en: "Target HP must be greater than 0.", field: "targetHp" },
  "int_reset_level out of range": { zh: "「洗回 INT 等級」必須大於 1，且不可超過等級上限。", en: "INT reset level must be above 1 and no higher than the target level.", field: "resetLevel" },
  "mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level": { zh: "「MP wash 結束等級」必須大於 30，且不可高於「洗回 INT 等級」。", en: "MP wash end level must be above 30 and no higher than the INT reset level.", field: "mpWashEnd" },
  "target_base_int too low": { zh: "「目標 base INT」至少必須是 4。", en: "Target base INT must be at least 4.", field: "targetInt" },
  "INT and threshold values must not be negative": { zh: "「洗回後升等裝備 INT」與 MP wash 門檻不可為負數。", en: "Gear INT after reset and MP wash thresholds cannot be negative.", field: "gearAfterReset" },
  "improved_maxhp_level must be in [0, 10]": { zh: "Improve MaxHP 等級必須介於 0 到 10。", en: "Improve MaxHP level must be between 0 and 10." },
  "invalid resume snapshot": { zh: "請檢查中途接續的「目前等級」、「base HP」、「base MP」與「base INT」欄位。", en: "Check the resume fields: current level, base HP, base MP, and base INT.", field: "resume.level" },
  "resume missing required stats": { zh: "中途接續請填寫「目前等級」、「base HP」與「base INT」。", en: "To resume, fill in current level, base HP, and base INT.", field: "resume.level" },
  "resume missing base_mp": { zh: "中途接續請填寫「base MP」。", en: "To resume, fill in base MP.", field: "resume.baseMp" },
  "resume level out of range": { zh: "中途接續的「目前等級」必須介於 1 到 200。", en: "Resume current level must be between 1 and 200.", field: "resume.level" },
  "resume base_hp must be positive": { zh: "中途接續的「base HP」必須大於 0。", en: "Resume base HP must be greater than 0.", field: "resume.baseHp" },
  "resume base_mp must be >= 0": { zh: "中途接續的「base MP」不可為負數。", en: "Resume base MP cannot be negative.", field: "resume.baseMp" },
  "resume base_int too low": { zh: "中途接續的「base INT」至少必須是 4。", en: "Resume base INT must be at least 4.", field: "resume.baseInt" },
  "int_reset_done but base_int > 4": { zh: "勾選「INT 已洗回 4，之後不再點 INT」時，「base INT」必須填 4。", en: "When “INT has been reset to 4” is checked, base INT must be 4.", field: "resume.baseInt" },
  "INT gear must contain at least one segment": { zh: "請至少設定一段 INT 裝備等級區間。", en: "Add at least one piece of INT gear on the Equipment tab.", field: "equipment" },
  "INT gear JSON must be a list of segments or equipment items": { zh: "裝備設定檔格式錯誤：內容必須是 INT 裝備區間或裝備清單。", en: "The gear file must contain INT gear ranges or an equipment list.", field: "equipment" },
  "equipment JSON must be a list": { zh: "裝備設定檔格式錯誤：最外層必須是清單。", en: "The gear file must be a list at the top level.", field: "equipment" },
  "equipment item must be an object": { zh: "裝備設定格式錯誤：每筆裝備都必須是物件。", en: "Each item in the gear file must be an object.", field: "equipment" },
  "unknown policy": { zh: "所選策略無效，請重新選擇策略。", en: "The selected policy is not valid. Choose a policy again.", field: "policy" },
  "int_gear must be >= 0": { zh: "INT 裝備區間的 INT 不可為負數，請檢查裝備設定。", en: "INT gear values cannot be negative. Check the Equipment tab.", field: "equipment" },
  "invalid INT gear segment: from_level > to_level": { zh: "INT 裝備區間的起始等級不可高於結束等級。", en: "An INT gear range starts after it ends.", field: "equipment" },
  "overlapping INT gear segments": { zh: "INT 裝備等級區間互相重疊，請檢查裝備設定。", en: "INT gear ranges overlap. Check the Equipment tab.", field: "equipment" },
  "max_level must be >= 1": { zh: "等級上限必須至少為 1。", en: "The level cap must be at least 1.", field: "targetLevel" },
  "level must be >= 1": { zh: "等級必須至少為 1，請檢查「目前等級」欄位。", en: "Level must be at least 1. Check the current level field.", field: "resume.level" },
};

const patterns: Array<[RegExp, (match: RegExpExecArray) => Entry]> = [
  [/^target_mp below job min_mp at max_level \(min=(\d+)\)$/, (m) => ({ zh: `「目標 MP」不可低於此職業滿等的最低 MP（${m[1]}），請確認「職業」與「目標 MP」。`, en: `Target MP is below this job's minimum MP at the target level (${m[1]}). Check the job and target MP.`, field: "targetMp" })],
  [/^unknown job: (.+)$/, (m) => ({ zh: `「職業」欄位的值「${m[1]}」不支援，請從職業清單選擇。`, en: `The job “${m[1]}” is not supported. Choose one from the list.`, field: "job" })],
  [/^unknown equipment type: (.+)$/, (m) => ({ zh: `裝備類型「${m[1]}」不支援，請檢查裝備清單中的「Type」欄位。`, en: `Equipment type “${m[1]}” is not supported. Check the Type column on the Equipment tab.`, field: "equipment" })],
  [/^int must be >= 0 for (.+)$/, (m) => ({ zh: `裝備「${m[1]}」的 INT 不可為負數，請檢查裝備清單的「INT」欄位。`, en: `INT for “${m[1]}” cannot be negative. Check the INT column on the Equipment tab.`, field: "equipment" })],
  [/^equip_level must be >= 1 for (.+)$/, (m) => ({ zh: `裝備「${m[1]}」的穿戴等級必須至少為 1，請檢查「Level to Equip」欄位。`, en: `Equip level for “${m[1]}” must be at least 1. Check the equip level column.`, field: "equipment" })],
];

function resolve(error: unknown): Entry {
  if (error instanceof SyntaxError) return { zh: "裝備設定檔不是有效的 JSON，請檢查檔案內容。", en: "The gear file is not valid JSON. Check its contents.", field: "equipment" };
  const raw = error instanceof Error ? error.message.trim() : "";
  if (!raw) return GENERIC;
  if (exactMessages[raw]) return exactMessages[raw];
  for (const [pattern, build] of patterns) {
    const match = pattern.exec(raw);
    if (match) return build(match);
  }
  // Do not show internal exception text or implementation names to users.
  return GENERIC;
}

/** Message plus the field it points at, in the requested language. */
export function describeUserError(error: unknown, language: Language = "zh"): UserError {
  const entry = resolve(error);
  return { message: entry[language], field: entry.field };
}

export function formatUserError(error: unknown, language: Language = "zh"): string {
  return describeUserError(error, language).message;
}
