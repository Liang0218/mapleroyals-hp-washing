const exactMessages: Record<string, string> = {
  "target_hp must be positive": "「目標 HP」必須大於 0。",
  "int_reset_level out of range": "「洗回 INT 等級」必須大於 1，且不可超過等級上限。",
  "mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level": "「MP wash 結束等級」必須大於 30，且不可高於「洗回 INT 等級」。",
  "target_base_int too low": "「目標 base INT」至少必須是 4。",
  "INT and threshold values must not be negative": "「洗回後升等裝備 INT」與 MP wash 門檻不可為負數。",
  "improved_maxhp_level must be in [0, 10]": "Improve MaxHP 等級必須介於 0 到 10。",
  "invalid resume snapshot": "請檢查中途接續的「目前等級」、「base HP」、「base MP」與「base INT」欄位。",
  "resume level out of range": "中途接續的「目前等級」必須介於 1 到 200。",
  "resume base_hp must be positive": "中途接續的「base HP」必須大於 0。",
  "resume base_mp must be >= 0": "中途接續的「base MP」不可為負數。",
  "resume base_int too low": "中途接續的「base INT」至少必須是 4。",
  "int_reset_done but base_int > 4": "勾選「INT 已洗回 4，之後不再點 INT」時，「base INT」必須填 4。",
  "INT gear must contain at least one segment": "請至少設定一段 INT 裝備等級區間。",
  "INT gear JSON must be a list of segments or equipment items": "裝備設定檔格式錯誤：內容必須是 INT 裝備區間或裝備清單。",
  "equipment JSON must be a list": "裝備設定檔格式錯誤：最外層必須是清單。",
  "equipment item must be an object": "裝備設定格式錯誤：每筆裝備都必須是物件。",
  "unknown policy": "所選策略無效，請重新選擇策略。",
};

export function formatUserError(error: unknown): string {
  if (error instanceof SyntaxError) return "裝備設定檔不是有效的 JSON，請檢查檔案內容。";
  const raw = error instanceof Error ? error.message.trim() : "";
  if (!raw) return "操作失敗，請檢查輸入欄位後重試。";
  if (exactMessages[raw]) return exactMessages[raw];

  let match = /^target_mp below job min_mp at max_level \(min=(\d+)\)$/.exec(raw);
  if (match) return `「目標 MP」不可低於此職業滿等的最低 MP（${match[1]}），請確認「職業」與「目標 MP」。`;
  match = /^unknown job: (.+)$/.exec(raw);
  if (match) return `「職業」欄位的值「${match[1]}」不支援，請從職業清單選擇。`;
  match = /^unknown equipment type: (.+)$/.exec(raw);
  if (match) return `裝備類型「${match[1]}」不支援，請檢查裝備清單中的「Type」欄位。`;
  match = /^int must be >= 0 for (.+)$/.exec(raw);
  if (match) return `裝備「${match[1]}」的 INT 不可為負數，請檢查裝備清單的「INT」欄位。`;
  match = /^equip_level must be >= 1 for (.+)$/.exec(raw);
  if (match) return `裝備「${match[1]}」的穿戴等級必須至少為 1，請檢查「Level to Equip」欄位。`;

  if (raw === "int_gear must be >= 0") return "INT 裝備區間的 INT 不可為負數，請檢查裝備設定。";
  if (raw === "invalid INT gear segment: from_level > to_level") return "INT 裝備區間的起始等級不可高於結束等級。";
  if (raw === "overlapping INT gear segments") return "INT 裝備等級區間互相重疊，請檢查裝備設定。";
  if (raw === "max_level must be >= 1") return "等級上限必須至少為 1。";
  if (raw === "level must be >= 1") return "等級必須至少為 1，請檢查「目前等級」欄位。";

  // Do not show internal exception text or implementation names to users.
  return "操作失敗，請檢查輸入欄位後重試。";
}
