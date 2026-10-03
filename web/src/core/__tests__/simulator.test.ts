import { describe, expect, it } from "vitest";
import { optimize } from "../optimizer";
import { simulate } from "../simulator";

// Mirrors examples/int_gear.json. Values are locked against Python test_regression.py.
const exampleGear = [
  [1, 9, 0], [10, 14, 24], [15, 19, 37], [20, 24, 93], [25, 29, 103],
  [30, 44, 114], [45, 49, 123], [50, 69, 134], [70, 89, 138], [90, 119, 142], [120, 154, 159],
].map(([from_level, to_level, int_gear]) => ({ from_level, to_level, int_gear }));

describe("Python calculation-core parity: simulator and optimizer", () => {
  it("matches the established Thief A simulation result", () => {
    const result = simulate({ policy: "mp_wash_shortfall", target_base_int: 320, target_hp: 27000, int_reset_level: 155, int_gear: exampleGear, mp_wash_end: 120, hp_mode: "avg", extra_mp_threshold: 60, int_gear_after_reset: 50 });
    expect(result).toMatchObject({ final_base_hp: 27016, final_display_hp: 27016, final_base_mp: 6394, int_reached_level: 67 });
    expect(result.apr).toEqual({ mp_wash_count: 290, method1_hp_wash_count: 570, method2_hp_wash_count: 449, int_reset_apr: 316 });
    expect(result.plan).toHaveLength(202);
  });

  it("matches the established A/B optimizer winner", () => {
    const result = optimize({ target_hp: 27000, int_reset_level: 155, int_gear: exampleGear, policies: ["mp_wash_shortfall", "int_dump_shortfall"], target_base_int_min: 280, target_base_int_max: 360, target_base_int_step: 40, mp_wash_end_min: 100, int_gear_after_reset: 50, top_n: 3 });
    expect(result.winner).toMatchObject({ policy: "int_dump_shortfall", target_base_int: 320, mp_wash_end: 100, final_display_hp: 27012 });
    const winner = result.winner;
    expect(winner).toBeDefined();
    expect(winner!.apr.mp_wash_count + winner!.apr.method1_hp_wash_count + winner!.apr.method2_hp_wash_count + winner!.apr.int_reset_apr).toBe(1487);
  });

  it("matches a non-Thief Improve MaxHP calculation", () => {
    const result = simulate({ policy: "int_only_plain", target_base_int: 220, target_hp: 25000, int_reset_level: 155, int_gear: [{ from_level: 1, to_level: 200, int_gear: 30 }], job: "fighter", mp_wash_end: 120 });
    expect(result).toMatchObject({ final_base_hp: 25022, final_base_mp: 11782, improved_maxhp_level: 10 });
    expect(result.apr.mp_wash_count + result.apr.method1_hp_wash_count + result.apr.method2_hp_wash_count + result.apr.int_reset_apr).toBe(752);
  });

  it("continues a resume snapshot from its current level", () => {
    const result = simulate({ policy: "mp_wash_shortfall", target_base_int: 320, target_hp: 22000, int_reset_level: 155, int_gear: exampleGear, mp_wash_end: 120, int_gear_after_reset: 50, resume_from: { level: 90, base_hp: 14000, base_mp: 2208, base_int: 320, base_luk: 60, fresh_ap: 5 } });
    expect(result).toMatchObject({ final_base_hp: 26145, final_base_mp: 7664, int_reached_level: 90 });
    expect(result.plan[0].action).toBe("RESUME");
    expect(result.plan).toHaveLength(113);
    expect(result.apr.mp_wash_count + result.apr.method1_hp_wash_count + result.apr.method2_hp_wash_count + result.apr.int_reset_apr).toBe(876);
  });

  it("matches Desktop Optimize defaults for the supplied settings file", () => {
    const result = optimize({ target_hp: 27000, int_reset_level: 155, int_gear: exampleGear, job: "thief", int_gear_after_reset: 50, policies: ["mp_wash_shortfall", "int_dump_shortfall", "mp_wash_hardcore", "int_only_plain"], quest_equip_hp: 0, hp_mode: "avg", mw_percent: 0.1, mw_from_level: 10, top_n: 5 });
    expect(result.winner).toMatchObject({ policy: "mp_wash_hardcore", target_base_int: 330, mp_wash_end: 96, final_display_hp: 27002 });
    expect(result.winner?.apr.mp_wash_count).toBeDefined();
    expect(result.winner && result.winner.apr.mp_wash_count + result.winner.apr.method1_hp_wash_count + result.winner.apr.method2_hp_wash_count + result.winner.apr.int_reset_apr).toBe(1473);
    expect(result.by_policy.mp_wash_shortfall?.best).toMatchObject({ target_base_int: 380, mp_wash_end: 101, final_display_hp: 27008 });
    expect(result.by_policy.int_dump_shortfall?.best).toMatchObject({ target_base_int: 350, mp_wash_end: 101, final_display_hp: 27002 });
    expect(result.by_policy.mp_wash_hardcore?.best).toMatchObject({ target_base_int: 330, mp_wash_end: 96, final_display_hp: 27002 });
    expect(result.by_policy.int_only_plain?.best).toMatchObject({ target_base_int: 250, mp_wash_end: 106, final_display_hp: 27014 });
  });

  it("matches the supplied app's A / INT 380 / MP end 101 scenario", () => {
    const result = simulate({ policy: "mp_wash_shortfall", target_base_int: 380, target_hp: 27000, int_reset_level: 155, int_gear: exampleGear, job: "thief", mp_wash_end: 101, quest_equip_hp: 0, hp_mode: "avg", mw_percent: 0.1, mw_from_level: 10, int_gear_after_reset: 50, extra_mp_threshold: 60, auto_method2: true });
    expect(result).toMatchObject({ final_base_hp: 27008, final_display_hp: 27008, final_base_mp: 3081, int_reached_level: 78, base_int_peak: 380 });
    expect(result.apr).toEqual({ mp_wash_count: 130, method1_hp_wash_count: 730, method2_hp_wash_count: 253, int_reset_apr: 376 });
  });
});
