import type { IntGearSegment } from "./models";

export function validateIntGear(segments: readonly IntGearSegment[]): void {
  const ordered = [...segments].sort((a, b) => a.from_level - b.from_level || a.to_level - b.to_level);
  if (ordered.length === 0) throw new Error("INT gear must contain at least one segment");
  for (const segment of ordered) {
    if (segment.from_level > segment.to_level) throw new Error("invalid INT gear segment: from_level > to_level");
    if (segment.int_gear < 0) throw new Error("int_gear must be >= 0");
  }
  for (let index = 1; index < ordered.length; index += 1) {
    if (ordered[index].from_level <= ordered[index - 1].to_level) throw new Error("overlapping INT gear segments");
  }
}

export function gearForLevel(segments: readonly IntGearSegment[], level: number): number {
  return segments.find((segment) => segment.from_level <= level && level <= segment.to_level)?.int_gear ?? 0;
}

export function effectiveGearForLevel(segments: readonly IntGearSegment[], level: number, intResetLevel: number, intGearAfterReset: number): number {
  return level >= intResetLevel ? intGearAfterReset : gearForLevel(segments, level);
}

export function mapleWarriorInt(baseInt: number, level: number, mwPercent = 0.1, mwFromLevel = 10): number {
  if (level < mwFromLevel || mwPercent <= 0) return 0;
  return Math.floor(Math.max(0, Math.trunc(baseInt)) * mwPercent);
}

export function totalInt(baseInt: number, segments: readonly IntGearSegment[], level: number, options: { mwPercent?: number; mwFromLevel?: number; intResetLevel?: number; intGearAfterReset?: number } = {}): number {
  const { mwPercent = 0.1, mwFromLevel = 10, intResetLevel, intGearAfterReset } = options;
  const gear = intResetLevel !== undefined && intGearAfterReset !== undefined
    ? effectiveGearForLevel(segments, level, intResetLevel, intGearAfterReset)
    : gearForLevel(segments, level);
  return Math.trunc(baseInt) + gear + mapleWarriorInt(baseInt, level, mwPercent, mwFromLevel);
}
