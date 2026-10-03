import { describe, expect, it } from "vitest";
import { parseGearJson } from "../gear-json";
import { planCsv } from "../plan-csv";

describe("browser file formats", () => {
  it("accepts legacy INT gear segments and desktop equipment JSON", () => {
    expect(parseGearJson([{ from_level: 1, to_level: 200, int_gear: 30 }])).toEqual([{ from_level: 1, to_level: 200, int_gear: 30 }]);
    expect(parseGearJson([{ name: "Hat", type: "Hat", int: 15, equip_level: 10 }])).toEqual([{ from_level: 1, to_level: 9, int_gear: 0 }, { from_level: 10, to_level: 200, int_gear: 15 }]);
  });

  it("exports Excel-friendly UTF-8 CSV with plan fields", () => {
    const csv = planCsv([{ level: 10, action: "BUILD", base_int: 20, base_luk: 4, base_hp: 100, base_mp: 100, extra_mp: 0, fresh_ap_int: 5, fresh_ap_luk: 0, fresh_ap_dex: 0, fresh_ap_str: 0, fresh_ap_hp: 0, fresh_ap_mp: 0, apr_spent: 0, notes: "test" }]);
    expect(csv.startsWith("\ufeff")).toBe(true);
    expect(csv).toContain("\"等級\"");
    expect(csv).toContain("\"BUILD\"");
  });
});
