import type { LevelPlanRow } from "../core/models";

const fields: Array<[string, keyof LevelPlanRow]> = [
  ["等級", "level"], ["動作", "action"], ["base INT", "base_int"], ["base LUK", "base_luk"],
  ["base HP", "base_hp"], ["base MP", "base_mp"], ["Extra MP", "extra_mp"], ["本等 AP_INT", "fresh_ap_int"],
  ["本等 AP_LUK", "fresh_ap_luk"], ["本等 AP_DEX", "fresh_ap_dex"], ["本等 AP_STR", "fresh_ap_str"],
  ["本等 AP_HP", "fresh_ap_hp"], ["本等 AP_MP", "fresh_ap_mp"], ["本等 APR", "apr_spent"], ["備註", "notes"],
];
const quote = (value: unknown): string => `"${String(value ?? "").replaceAll('"', '""')}"`;

export function planCsv(plan: readonly LevelPlanRow[]): string {
  const rows = [fields.map(([title]) => quote(title)).join(",")];
  for (const entry of plan) rows.push(fields.map(([, key]) => quote(entry[key])).join(","));
  rows.push(["說明", "Method1：新鮮 AP 點 HP，再以 APR 扣 MP。Method2：以 APR 將 Extra MP 轉成 HP。MP wash：新鮮 AP 點 MP，再以 APR 扣 MP。"].map(quote).join(","));
  return `\ufeff${rows.join("\r\n")}\r\n`;
}
