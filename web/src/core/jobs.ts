import type { HpMode, PolicyName } from "./models";
import { pickRange } from "./formulas";

export type JobId = "fighter" | "page" | "spearman" | "bowman" | "thief" | "brawler" | "gunslinger" | "beginner";
export type PrimaryStat = "str" | "dex" | "luk";
export type FirstJobStat = "str" | "dex" | "none";

export interface GainRange { low: number; high: number; }
export interface JobAdvanceSpec { hpMid: number; mpMid: number; apBonus: number; spread?: number; }
export interface MaxHpSkillSpec { unlockAdv: number; prereqSp: number; maxLevel: number; levelupBonusPerLevel: number; apBonusPerLevel: number; spPerLevel: number; }
export interface JobProfile {
  job: JobId; displayNameZh: string; minMpFn: (level: number) => number; mpRemovedPerApr: number;
  method1Base: GainRange; method2Base: GainRange; levelupHpBeginner: GainRange; levelupHpJobbed: GainRange;
  levelupMpBeginner: GainRange; levelupMpJobbed: GainRange; freshApMpBase: GainRange;
  jobAdvances: Map<number, { number: number; spec: JobAdvanceSpec }>; firstJobStat: FirstJobStat;
  firstJobRequirement: number; primaryStat: PrimaryStat; preferMethod2: boolean; policies: readonly PolicyName[];
  maxhpSkill?: MaxHpSkillSpec; beginnerUntilLevel: number;
  minMp(level: number): number; extraMp(baseMp: number, level: number): number; defaultExtraMpThreshold(): number;
  freshApMp(baseInt: number, mode: HpMode): number; method1Hp(mode: HpMode, skill: SkillTracker): number;
  method2Hp(mode: HpMode, skill: SkillTracker): number; levelupHp(level: number, mode: HpMode, skill: SkillTracker): number;
  levelupMpBase(level: number, mode: HpMode): number;
}

const ranges = {
  beginnerHp: { low: 12, high: 16 }, beginnerMp: { low: 10, high: 12 }, explorerMp: { low: 14, high: 16 },
  thiefM1: { low: 20, high: 24 }, thiefM2: { low: 16, high: 20 }, warriorM2: { low: 20, high: 25 },
  brawlerM1: { low: 16, high: 20 }, brawlerM2: { low: 20, high: 20 }, bowmanM: { low: 16, high: 20 },
  beginnerWash: { low: 8, high: 12 }, warriorHp: { low: 24, high: 28 }, brawlerHp: { low: 22, high: 28 },
  pirateHp: { low: 22, high: 28 }, thiefHp: { low: 20, high: 24 }, pirateMp: { low: 18, high: 23 },
  freshStd: { low: 10, high: 12 }, freshBeginner: { low: 6, high: 8 }, freshWarrior: { low: 2, high: 4 },
} as const;

const thiefPolicies: readonly PolicyName[] = ["mp_wash_shortfall", "int_dump_shortfall", "mp_wash_hardcore", "int_only_plain"];
const dOnly: readonly PolicyName[] = ["int_only_plain"];
const warriorSkill: MaxHpSkillSpec = { unlockAdv: 1, prereqSp: 5, maxLevel: 10, levelupBonusPerLevel: 4, apBonusPerLevel: 3, spPerLevel: 3 };
const brawlerSkill: MaxHpSkillSpec = { unlockAdv: 2, prereqSp: 0, maxLevel: 10, levelupBonusPerLevel: 3, apBonusPerLevel: 2, spPerLevel: 3 };

function advance(hpMid: number, mpMid: number, apBonus = 0): JobAdvanceSpec { return { hpMid, mpMid, apBonus }; }
function explorerAdvances(): Map<number, { number: number; spec: JobAdvanceSpec }> {
  return new Map([[10, { number: 1, spec: advance(162.5, 0) }], [30, { number: 2, spec: advance(325, 175) }], [70, { number: 3, spec: advance(625, 175, 5) }], [120, { number: 4, spec: advance(925, 175, 5) }]]);
}
function fighterAdvances(): Map<number, { number: number; spec: JobAdvanceSpec }> {
  return new Map([[10, { number: 1, spec: advance(225, 0) }], [30, { number: 2, spec: advance(325, 0) }], [70, { number: 3, spec: advance(1025, 0, 5) }], [120, { number: 4, spec: advance(1825, 0, 5) }]]);
}
function pageAdvances(): Map<number, { number: number; spec: JobAdvanceSpec }> {
  return new Map([[10, { number: 1, spec: advance(225, 0) }], [30, { number: 2, spec: advance(0, 125) }], [70, { number: 3, spec: advance(1025, 0, 5) }], [120, { number: 4, spec: advance(1825, 0, 5) }]]);
}

export class SkillTracker {
  prereqSpent = 0; skillLevel = 0; unlocked = false;
  constructor(readonly spec?: MaxHpSkillSpec, readonly overrideLevel?: number) {}
  onJobAdvance(number: number): void { if (this.spec && number >= this.spec.unlockAdv) this.unlocked = true; }
  onLevel(): void { if (this.spec && this.overrideLevel === undefined && this.unlocked) this.spend(this.spec.spPerLevel); }
  seedForResume(level: number, advances: ReadonlyMap<number, { number: number }>): void {
    if (!this.spec || this.overrideLevel !== undefined) return;
    const unlockLevel = [...advances.entries()].sort(([a], [b]) => a - b).find(([, advance]) => advance.number >= this.spec!.unlockAdv)?.[0];
    if (unlockLevel === undefined || level < unlockLevel) return;
    this.unlocked = true;
    for (let current = unlockLevel; current <= level; current += 1) this.spend(this.spec.spPerLevel);
  }
  private spend(points: number): void {
    if (!this.spec) return;
    let remaining = points;
    while (remaining > 0) {
      if (this.prereqSpent < this.spec.prereqSp) { const take = Math.min(remaining, this.spec.prereqSp - this.prereqSpent); this.prereqSpent += take; remaining -= take; }
      else if (this.skillLevel < this.spec.maxLevel) { const take = Math.min(remaining, this.spec.maxLevel - this.skillLevel); this.skillLevel += take; remaining -= take; }
      else break;
    }
  }
  get effectiveLevel(): number { return this.overrideLevel === undefined ? this.skillLevel : Math.max(0, Math.min(Math.trunc(this.overrideLevel), this.spec?.maxLevel ?? 10)); }
  levelupHpBonus(): number { return (this.spec?.levelupBonusPerLevel ?? 0) * this.effectiveLevel; }
  apHpBonus(): number { return (this.spec?.apBonusPerLevel ?? 0) * this.effectiveLevel; }
}

type ProfileInput = Omit<JobProfile, "minMp" | "extraMp" | "defaultExtraMpThreshold" | "freshApMp" | "method1Hp" | "method2Hp" | "levelupHp" | "levelupMpBase">;
function profile(input: ProfileInput): JobProfile {
  return {
    ...input,
    minMp(level) { if (level < 1) throw new Error("level must be >= 1"); return input.minMpFn(level); },
    extraMp(baseMp, level) { return baseMp - input.minMpFn(level); },
    defaultExtraMpThreshold() { return input.mpRemovedPerApr * 5; },
    freshApMp(baseInt, mode) { return pickRange(input.freshApMpBase.low, input.freshApMpBase.high, mode) + Math.floor(Math.max(0, Math.trunc(baseInt)) / 10); },
    method1Hp(mode, skill) { return pickRange(input.method1Base.low, input.method1Base.high, mode) + skill.apHpBonus(); },
    method2Hp(mode, skill) { return pickRange(input.method2Base.low, input.method2Base.high, mode) + skill.apHpBonus(); },
    levelupHp(level, mode, skill) { const base = level < input.beginnerUntilLevel ? input.levelupHpBeginner : input.levelupHpJobbed; return pickRange(base.low, base.high, mode) + skill.levelupHpBonus(); },
    levelupMpBase(level, mode) { const base = level < input.beginnerUntilLevel ? input.levelupMpBeginner : input.levelupMpJobbed; return pickRange(base.low, base.high, mode); },
  };
}

const common = (job: JobId, displayNameZh: string, minMpFn: (level: number) => number, mpRemovedPerApr: number, method1Base: GainRange, method2Base: GainRange, levelupHpJobbed: GainRange, levelupMpJobbed: GainRange, freshApMpBase: GainRange, jobAdvances: JobProfile["jobAdvances"], firstJobStat: FirstJobStat, firstJobRequirement: number, primaryStat: PrimaryStat, preferMethod2: boolean, policies: readonly PolicyName[], maxhpSkill?: MaxHpSkillSpec, beginnerUntilLevel = 11): JobProfile => profile({ job, displayNameZh, minMpFn, mpRemovedPerApr, method1Base, method2Base, levelupHpBeginner: ranges.beginnerHp, levelupHpJobbed, levelupMpBeginner: ranges.beginnerMp, levelupMpJobbed, freshApMpBase, jobAdvances, firstJobStat, firstJobRequirement, primaryStat, preferMethod2, policies, maxhpSkill, beginnerUntilLevel });

export const JOB_PROFILES: Record<JobId, JobProfile> = {
  thief: common("thief", "夜使者／暗影神偷 Night Lord／Shadower", (lv) => 14 * lv + 148, 12, ranges.thiefM1, ranges.thiefM2, ranges.thiefHp, ranges.explorerMp, ranges.freshStd, explorerAdvances(), "dex", 25, "luk", false, thiefPolicies),
  bowman: common("bowman", "箭神／神射手 Bowmaster／Marksman", (lv) => 14 * lv + 148, 12, ranges.bowmanM, ranges.bowmanM, ranges.thiefHp, ranges.explorerMp, ranges.freshStd, explorerAdvances(), "dex", 25, "dex", true, dOnly),
  gunslinger: common("gunslinger", "槍神 Corsair", (lv) => 18 * lv + 111, 16, ranges.bowmanM, ranges.brawlerM2, ranges.pirateHp, ranges.pirateMp, ranges.freshStd, explorerAdvances(), "dex", 20, "dex", true, dOnly),
  brawler: common("brawler", "拳霸 Buccaneer", (lv) => 18 * lv + 111, 16, ranges.brawlerM1, ranges.brawlerM2, ranges.brawlerHp, ranges.pirateMp, ranges.freshStd, explorerAdvances(), "dex", 20, "str", true, dOnly, brawlerSkill),
  fighter: common("fighter", "英雄 Hero", (lv) => 4 * lv + 56, 4, ranges.thiefM1, ranges.warriorM2, ranges.warriorHp, { low: 4, high: 6 }, ranges.freshWarrior, fighterAdvances(), "str", 35, "str", true, dOnly, warriorSkill),
  page: common("page", "聖騎士 Paladin", (lv) => 4 * lv + 56, 4, ranges.thiefM1, ranges.warriorM2, ranges.warriorHp, { low: 4, high: 6 }, ranges.freshWarrior, pageAdvances(), "str", 35, "str", true, dOnly, warriorSkill),
  spearman: common("spearman", "黑騎士 Dark Knight", (lv) => 4 * lv + 156, 4, ranges.thiefM1, ranges.warriorM2, ranges.warriorHp, { low: 4, high: 6 }, ranges.freshWarrior, pageAdvances(), "str", 35, "str", true, dOnly, warriorSkill),
  beginner: common("beginner", "初心者 Beginner", (lv) => 10 * lv + 2, 8, ranges.beginnerWash, ranges.beginnerWash, ranges.beginnerHp, ranges.beginnerMp, ranges.freshBeginner, new Map(), "none", 0, "luk", true, dOnly, undefined, 201),
};

const aliases: Record<string, JobId> = { fighter: "fighter", hero: "fighter", page: "page", paladin: "page", pally: "page", spearman: "spearman", darkknight: "spearman", dark_knight: "spearman", dk: "spearman", bowman: "bowman", bowmaster: "bowman", bm: "bowman", marksman: "bowman", mm: "bowman", thief: "thief", nightlord: "thief", night_lord: "thief", nl: "thief", shadower: "thief", shad: "thief", brawler: "brawler", buccaneer: "brawler", bucc: "brawler", gunslinger: "gunslinger", corsair: "gunslinger", sair: "gunslinger", beginner: "beginner" };
export function resolveJob(job: string): JobId { const raw = job.trim().toLowerCase().replaceAll("-", "_").replaceAll(" ", "_"); const result = aliases[raw] ?? aliases[raw.replaceAll("_", "")]; if (!result) throw new Error(`unknown job: ${job}`); return result; }
export function getJobProfile(job: string): JobProfile { return JOB_PROFILES[resolveJob(job)]; }
export function makeSkillTracker(profile: JobProfile, overrideLevel?: number): SkillTracker { return new SkillTracker(profile.maxhpSkill, overrideLevel); }
