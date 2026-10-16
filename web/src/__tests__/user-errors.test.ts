import { describe, expect, it } from "vitest";
import { formatUserError } from "../user-errors";

describe("user-facing error messages", () => {
  it("translates validation errors into Traditional Chinese with field names", () => {
    expect(formatUserError(new Error("target_hp must be positive"))).toContain("目標 HP");
    expect(formatUserError(new Error("mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level"))).toContain("MP wash 結束等級");
    expect(formatUserError(new Error("resume base_mp must be >= 0"))).toContain("base MP");
  });

  it("turns dynamic job and equipment errors into actionable messages", () => {
    expect(formatUserError(new Error("unknown job: magician"))).toContain("職業");
    expect(formatUserError(new Error("int must be >= 0 for Red Hat"))).toContain("Red Hat");
  });

  it("does not expose raw internal exception text", () => {
    expect(formatUserError(new Error("unexpected_internal_state"))).toBe("操作失敗，請檢查輸入欄位後重試。");
  });
});
