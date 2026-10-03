import { computeIntGearSegments, parseEquipment } from "../core/equipment";
import { validateIntGear } from "../core/gear";
import type { IntGearSegment } from "../core/models";

export function parseGearJson(value: unknown): IntGearSegment[] {
  if (!Array.isArray(value)) throw new Error("INT gear JSON must be a list of segments or equipment items");
  if (value.length === 0 || (typeof value[0] === "object" && value[0] !== null && "from_level" in value[0])) {
    const segments = value.map((item): IntGearSegment => {
      const row = item as Record<string, unknown>;
      return { from_level: Number(row.from_level), to_level: Number(row.to_level), int_gear: Number(row.int_gear ?? 0) };
    });
    validateIntGear(segments);
    return segments;
  }
  return computeIntGearSegments(parseEquipment(value));
}

export function gearJson(segments: readonly IntGearSegment[]): string {
  return `${JSON.stringify(segments, null, 2)}\n`;
}
