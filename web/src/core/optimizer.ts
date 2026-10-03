import { getJobProfile } from "./jobs";
import { simulate } from "./simulator";
import { totalApr, type CandidateResult, type ComparisonResult, type OptimizeConfig, type OptimizeResult, type PolicyBest, type PolicyName } from "./models";

type Normalized = Required<Omit<OptimizeConfig, "policies" | "resume_from" | "improved_maxhp_level" | "target_mp">> & Pick<OptimizeConfig, "policies" | "resume_from" | "improved_maxhp_level" | "target_mp">;
function normalize(config: OptimizeConfig): Normalized {
  return { ...config, job: config.job ?? "thief", quest_equip_hp: config.quest_equip_hp ?? 0, hp_mode: config.hp_mode ?? "avg", max_level: config.max_level ?? 200, mw_percent: config.mw_percent ?? 0.1, mw_from_level: config.mw_from_level ?? 10, int_gear_after_reset: config.int_gear_after_reset ?? 50, extra_mp_threshold: config.extra_mp_threshold ?? getJobProfile(config.job ?? "thief").defaultExtraMpThreshold(), target_base_int_min: config.target_base_int_min ?? 100, target_base_int_max: config.target_base_int_max ?? 500, target_base_int_step: config.target_base_int_step ?? 10, mp_wash_end_min: config.mp_wash_end_min ?? 31, top_n: config.top_n ?? 5 };
}
function candidate(config: Normalized, policy: PolicyName, targetBaseInt: number, mpWashEnd: number): CandidateResult {
  return simulate({ policy, target_base_int: targetBaseInt, target_hp: config.target_hp, int_reset_level: config.int_reset_level, int_gear: config.int_gear, job: config.job, mp_wash_end: mpWashEnd, extra_mp_threshold: config.extra_mp_threshold, quest_equip_hp: config.quest_equip_hp, hp_mode: config.hp_mode, max_level: config.max_level, auto_method2: true, mw_percent: config.mw_percent, mw_from_level: config.mw_from_level, int_gear_after_reset: config.int_gear_after_reset, resume_from: config.resume_from, improved_maxhp_level: config.improved_maxhp_level, target_mp: config.target_mp });
}
function ints(from: number, to: number, step: number): number[] { const values: number[] = []; for (let value = from; value <= to; value += step) values.push(value); if (values.at(-1) !== to) values.push(to); return values; }
function intBounds(config: Normalized): [number, number] { if (!config.resume_from) return [config.target_base_int_min, config.target_base_int_max]; if (config.resume_from.int_reset_done) { const fixed = Math.max(config.target_base_int_min, config.resume_from.base_int_peak ?? config.resume_from.base_int, 4); return [fixed, fixed]; } const low = Math.max(config.target_base_int_min, config.resume_from.base_int); return [low, Math.max(low, config.target_base_int_max)]; }
function mpEnds(config: Normalized, step: number): number[] { const minimum = Math.max(31, config.mp_wash_end_min); const values = ints(minimum, config.int_reset_level, step); if (!config.resume_from || config.resume_from.level <= minimum) return values; return [...new Set([Math.max(minimum, config.resume_from.level - 1), ...values.filter((value) => value >= config.resume_from!.level)])].sort((a, b) => a - b); }
function sortKey(candidate: CandidateResult): (number | string)[] {
  if (candidate.reached_target) return [0, totalApr(candidate.apr), -candidate.final_display_hp, candidate.target_base_int, candidate.base_int_peak, candidate.mp_wash_end, candidate.int_reached_level, candidate.policy];
  const hpReached = candidate.target_hp !== undefined && candidate.final_display_hp >= candidate.target_hp;
  if (candidate.target_mp !== undefined && hpReached) return [1, -candidate.final_base_mp, totalApr(candidate.apr), candidate.target_base_int, candidate.base_int_peak, candidate.mp_wash_end, candidate.int_reached_level, candidate.policy];
  return [2, -candidate.final_display_hp, totalApr(candidate.apr), candidate.target_base_int, candidate.base_int_peak, candidate.mp_wash_end, candidate.int_reached_level, candidate.policy];
}
function compare(left: CandidateResult, right: CandidateResult): number { const a = sortKey(left); const b = sortKey(right); for (let index = 0; index < a.length; index += 1) { if (a[index] < b[index]) return -1; if (a[index] > b[index]) return 1; } return 0; }
function unique(items: CandidateResult[]): CandidateResult[] { const seen = new Set<string>(); return items.filter((item) => { const key = `${item.policy}:${item.target_base_int}:${item.mp_wash_end}:${item.extra_mp_threshold}`; if (seen.has(key)) return false; seen.add(key); return true; }); }
function search(config: Normalized, policy: PolicyName, intStep: number, mpStep: number): CandidateResult[] { const [low, high] = intBounds(config); return ints(low, high, intStep).flatMap((baseInt) => mpEnds(config, mpStep).map((end) => candidate(config, policy, baseInt, end))); }
function policyBest(config: Normalized, policy: PolicyName): PolicyBest {
  const coarse = search(config, policy, 40, 10).sort(compare); const seeds = unique(coarse.slice(0, Math.max(8, config.top_n))); const [low, high] = intBounds(config);
  const refined = seeds.flatMap((seed) => ints(Math.max(low, seed.target_base_int - config.target_base_int_step * 2), Math.min(high, seed.target_base_int + config.target_base_int_step * 2), config.target_base_int_step).flatMap((baseInt) => mpEnds(config, 5).filter((end) => Math.abs(end - seed.mp_wash_end) <= 10).map((end) => candidate(config, policy, baseInt, end))));
  const candidates = unique([...coarse, ...refined]).sort(compare); const feasible = candidates.filter((item) => item.reached_target); const top = (feasible.length ? feasible : candidates).slice(0, config.top_n); return { policy, best: top[0], top };
}
function comparison(byPolicy: Partial<Record<PolicyName, PolicyBest>>): ComparisonResult {
  const policy_a = byPolicy.mp_wash_shortfall?.best; const policy_b = byPolicy.int_dump_shortfall?.best; const policy_c = byPolicy.mp_wash_hardcore?.best; const policy_d = byPolicy.int_only_plain?.best; const ranked = [policy_a, policy_b, policy_c, policy_d].filter((item): item is CandidateResult => item !== undefined).sort(compare); const winner = ranked[0]; const runnerUp = ranked[1]; return { policy_a, policy_b, policy_c, policy_d, winner, apr_delta: winner && runnerUp ? totalApr(winner.apr) - totalApr(runnerUp.apr) : undefined, hp_delta: winner && runnerUp ? winner.final_display_hp - runnerUp.final_display_hp : undefined };
}
export function optimize(input: OptimizeConfig): OptimizeResult {
  const config = normalize(input); const policies = config.policies?.length ? config.policies : getJobProfile(config.job).policies; const by_policy: Partial<Record<PolicyName, PolicyBest>> = {};
  for (const policy of policies) by_policy[policy] = policyBest(config, policy);
  const all = Object.values(by_policy).flatMap((entry) => entry?.top.filter((item) => item.reached_target) ?? []).sort(compare); const resultComparison = comparison(by_policy); const fallback = Object.values(by_policy).map((entry) => entry?.best).filter((item): item is CandidateResult => item !== undefined).sort(compare)[0];
  return { by_policy, comparison: resultComparison, winner: resultComparison.winner ?? all[0] ?? fallback, top_candidates: all.slice(0, config.top_n), resume_from: config.resume_from };
}
