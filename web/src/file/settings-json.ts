import type { HpMode, IntGearSegment, PolicyName, ResumeFrom } from "../core/models";

export interface WebSettings {
  format: "mapleroyals-hp-wash-web";
  version: 1;
  job: string;
  policy: PolicyName;
  targetHp: number;
  targetInt: number;
  resetLevel: number;
  mpWashEnd: number;
  intGear: IntGearSegment[];
  targetMp?: number;
  questEquipHp?: number;
  hpMode?: HpMode;
  mwPercent?: number;
  mwFromLevel?: number;
  intGearAfterReset?: number;
  autoMethod2?: boolean;
  topN?: number;
  resume?: ResumeFrom;
}

export function parseWebSettings(value: unknown): WebSettings {
  if (typeof value !== "object" || value === null) throw new Error("settings file must be an object");
  const raw = value as Record<string, unknown>;
  if (raw.format !== "mapleroyals-hp-wash-web" || raw.version !== 1) throw new Error("unsupported settings file");
  if (!Array.isArray(raw.intGear)) throw new Error("settings file has no INT gear");
  return { format: "mapleroyals-hp-wash-web", version: 1, job: String(raw.job), policy: String(raw.policy) as PolicyName, targetHp: Number(raw.targetHp), targetInt: Number(raw.targetInt), resetLevel: Number(raw.resetLevel), mpWashEnd: Number(raw.mpWashEnd), intGear: raw.intGear as IntGearSegment[], targetMp: raw.targetMp === undefined ? undefined : Number(raw.targetMp), questEquipHp: raw.questEquipHp === undefined ? undefined : Number(raw.questEquipHp), hpMode: raw.hpMode as HpMode | undefined, mwPercent: raw.mwPercent === undefined ? undefined : Number(raw.mwPercent), mwFromLevel: raw.mwFromLevel === undefined ? undefined : Number(raw.mwFromLevel), intGearAfterReset: raw.intGearAfterReset === undefined ? undefined : Number(raw.intGearAfterReset), autoMethod2: raw.autoMethod2 === undefined ? undefined : Boolean(raw.autoMethod2), topN: raw.topN === undefined ? undefined : Number(raw.topN), resume: raw.resume as ResumeFrom | undefined };
}
