import { EQUIPMENT_TYPES, type EquipmentItem, type EquipmentType, type IntGearSegment } from "./models";
import { validateIntGear } from "./gear";

const ringType: EquipmentType = "Ring";
const singleSlotTypes = EQUIPMENT_TYPES.filter((type) => type !== ringType);

export function parseEquipment(value: unknown): EquipmentItem[] {
  if (!Array.isArray(value)) throw new Error("equipment JSON must be a list");
  return value.map((item): EquipmentItem => {
    if (typeof item !== "object" || item === null) throw new Error("equipment item must be an object");
    const row = item as Record<string, unknown>;
    const type = String(row.type) as EquipmentType;
    const int = Number(row.int);
    const equip_level = Number(row.equip_level);
    if (!EQUIPMENT_TYPES.includes(type)) throw new Error(`unknown equipment type: ${type}`);
    if (!Number.isInteger(int) || int < 0) throw new Error(`int must be >= 0 for ${String(row.name ?? type)}`);
    if (!Number.isInteger(equip_level) || equip_level < 1) throw new Error(`equip_level must be >= 1 for ${String(row.name ?? type)}`);
    return { name: String(row.name ?? ""), type, int, equip_level };
  });
}

export function gearIntAtLevel(items: readonly EquipmentItem[], level: number): number {
  const available = items.filter((item) => item.equip_level <= level);
  return singleSlotTypes.reduce((total, type) => {
    const best = available.filter((item) => item.type === type).sort((a, b) => b.int - a.int || b.equip_level - a.equip_level)[0];
    return total + (best?.int ?? 0);
  }, 0) + available.filter((item) => item.type === ringType).sort((a, b) => b.int - a.int || b.equip_level - a.equip_level).slice(0, 4).reduce((total, item) => total + item.int, 0);
}

export function computeIntGearSegments(items: readonly EquipmentItem[], maxLevel = 200): IntGearSegment[] {
  if (maxLevel < 1) throw new Error("max_level must be >= 1");
  if (items.length === 0) return [{ from_level: 1, to_level: maxLevel, int_gear: 0 }];
  const points = [...new Set([1, maxLevel, ...items.map((item) => item.equip_level)])].sort((a, b) => a - b);
  const result: IntGearSegment[] = [];
  points.forEach((start, index) => {
    if (start > maxLevel) return;
    const end = Math.min(index + 1 < points.length ? points[index + 1] - 1 : maxLevel, maxLevel);
    const intGear = gearIntAtLevel(items, start);
    const previous = result.at(-1);
    if (previous?.int_gear === intGear) previous.to_level = end;
    else result.push({ from_level: start, to_level: end, int_gear: intGear });
  });
  validateIntGear(result);
  return result;
}
