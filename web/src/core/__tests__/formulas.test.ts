import { describe, expect, it } from "vitest";
import { extraMp, levelupMpIntBonus, method1WashesAffordable, minMp, mpWashesAffordable } from "../formulas";
import { computeIntGearSegments, gearIntAtLevel, parseEquipment } from "../equipment";
import { mapleWarriorInt, totalInt, validateIntGear } from "../gear";
import { getJobProfile, resolveJob, SkillTracker } from "../jobs";

describe("Python calculation-core parity: formulas", () => {
  it("keeps the legacy Thief MP formulas", () => {
    expect(minMp(50)).toBe(848);
    expect(extraMp(1000, 50)).toBe(152);
    expect(method1WashesAffordable(60, 5)).toBe(5);
    expect(method1WashesAffordable(36, 5)).toBe(3);
    expect(mpWashesAffordable(100, 1000, 50, 5, "avg")).toBeGreaterThanOrEqual(0);
  });

  it("uses floor(total INT / 10) for level-up MP", () => {
    expect(levelupMpIntBonus(109)).toBe(10);
    expect(levelupMpIntBonus(-10)).toBe(0);
  });
});

describe("Python calculation-core parity: jobs and gear", () => {
  it("resolves aliases and carries job-specific minimum MP", () => {
    expect(resolveJob("Hero")).toBe("fighter");
    expect(resolveJob("dark-knight")).toBe("spearman");
    expect(getJobProfile("fighter").minMp(50)).toBe(256);
    expect(getJobProfile("gunslinger").mpRemovedPerApr).toBe(16);
  });

  it("applies Maple Warrior to base INT only", () => {
    expect(mapleWarriorInt(319, 10)).toBe(31);
    expect(totalInt(319, [{ from_level: 1, to_level: 200, int_gear: 50 }], 10)).toBe(400);
  });

  it("uses the four best rings and one item per other slot", () => {
    const equipment = parseEquipment([
      { name: "Hat A", type: "Hat", int: 5, equip_level: 10 },
      { name: "Hat B", type: "Hat", int: 9, equip_level: 20 },
      { name: "Ring 1", type: "Ring", int: 1, equip_level: 1 },
      { name: "Ring 2", type: "Ring", int: 2, equip_level: 1 },
      { name: "Ring 3", type: "Ring", int: 3, equip_level: 1 },
      { name: "Ring 4", type: "Ring", int: 4, equip_level: 1 },
      { name: "Ring 5", type: "Ring", int: 5, equip_level: 1 },
    ]);
    expect(gearIntAtLevel(equipment, 10)).toBe(19);
    expect(gearIntAtLevel(equipment, 20)).toBe(23);
    expect(computeIntGearSegments(equipment, 30)).toEqual([
      { from_level: 1, to_level: 9, int_gear: 14 },
      { from_level: 10, to_level: 19, int_gear: 19 },
      { from_level: 20, to_level: 30, int_gear: 23 },
    ]);
  });

  it("retains the Improve MaxHP SP schedule", () => {
    const tracker = new SkillTracker(getJobProfile("fighter").maxhpSkill);
    tracker.onJobAdvance(1);
    for (let level = 10; level <= 15; level += 1) tracker.onLevel();
    expect(tracker.prereqSpent).toBe(5);
    expect(tracker.effectiveLevel).toBe(10);
    expect(tracker.apHpBonus()).toBe(30);
  });

  it("rejects overlapping gear segments", () => {
    expect(() => validateIntGear([{ from_level: 1, to_level: 20, int_gear: 1 }, { from_level: 20, to_level: 30, int_gear: 2 }])).toThrow("overlapping");
  });
});
