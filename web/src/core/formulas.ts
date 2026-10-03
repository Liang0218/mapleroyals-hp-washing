import type { HpMode } from "./models";
import { getJobProfile } from "./jobs";

export const MP_REMOVED_PER_APR = 12;
export const EXTRA_MP_THRESHOLD_DEFAULT = MP_REMOVED_PER_APR * 5;
export const FRESH_AP_PER_LEVEL = 5;
export const STARTING_HP = 50;
export const STARTING_MP = 5;
export const STARTING_STR = 4;
export const STARTING_DEX = 4;
export const STARTING_INT = 4;
export const STARTING_LUK = 4;
export const STARTING_FRESH_AP = 9;

export function pickRange(low: number, high: number, mode: HpMode): number {
  if (mode === "min") return low;
  if (mode === "max") return high;
  return (low + high) / 2;
}

export function minMp(level: number, job = "thief"): number {
  return getJobProfile(job).minMp(level);
}

export function extraMp(baseMp: number, level: number, job = "thief"): number {
  return getJobProfile(job).extraMp(baseMp, level);
}

export function levelupMpIntBonus(totalInt: number): number {
  return Math.floor(Math.max(0, Math.trunc(totalInt)) / 10);
}

export function method1WashesAffordable(extraMpValue: number, freshAp: number, mpRemovedPerApr = MP_REMOVED_PER_APR): number {
  if (extraMpValue < mpRemovedPerApr || freshAp <= 0) return 0;
  return Math.min(Math.trunc(freshAp), Math.floor(extraMpValue / mpRemovedPerApr));
}

export function mpWashesAffordable(baseInt: number, baseMp: number, level: number, freshAp: number, mode: HpMode, job = "thief"): number {
  if (freshAp <= 0) return 0;
  const profile = getJobProfile(job);
  let mp = baseMp;
  let done = 0;
  for (let index = 0; index < freshAp; index += 1) {
    const gain = profile.freshApMp(baseInt, mode);
    mp += gain;
    if (profile.extraMp(mp, level) < profile.mpRemovedPerApr) break;
    mp -= profile.mpRemovedPerApr;
    done += 1;
  }
  return done;
}
