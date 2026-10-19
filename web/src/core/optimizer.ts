import { getJobProfile, makeSkillTracker } from "./jobs";
import { simulate } from "./simulator";
import { totalApr, type CandidateResult, type ComparisonResult, type OptimizeConfig, type OptimizeResult, type PolicyBest, type PolicyName } from "./models";

const MAX_BASE_HP = 30_000;

type Normalized = Required<Omit<OptimizeConfig, "policies" | "resume_from" | "improved_maxhp_level" | "target_mp" | "hp_cap">> & Pick<OptimizeConfig, "policies" | "resume_from" | "improved_maxhp_level" | "target_mp" | "hp_cap">;
function normalize(config: OptimizeConfig): Normalized {
  return { ...config, job: config.job ?? "thief", quest_equip_hp: config.quest_equip_hp ?? 0, hp_mode: config.hp_mode ?? "avg", max_level: config.max_level ?? 200, mw_percent: config.mw_percent ?? 0.1, mw_from_level: config.mw_from_level ?? 10, int_gear_after_reset: config.int_gear_after_reset ?? 50, extra_mp_threshold: config.extra_mp_threshold ?? getJobProfile(config.job ?? "thief").defaultExtraMpThreshold(), target_base_int_min: config.target_base_int_min ?? 4, target_base_int_max: config.target_base_int_max ?? 999, target_base_int_step: config.target_base_int_step ?? 10, mp_wash_end_min: config.mp_wash_end_min ?? 31, top_n: config.top_n ?? 5 };
}
function candidate(config: Normalized, policy: PolicyName, targetBaseInt: number, mpWashEnd: number, earlyMpWashLevel?: number, protectTargetMp = false): CandidateResult {
  const result = simulate({ policy, target_base_int: targetBaseInt, target_hp: config.target_hp, target_mp: protectTargetMp ? config.target_mp : undefined, int_reset_level: config.int_reset_level, int_gear: config.int_gear, job: config.job, mp_wash_end: mpWashEnd, extra_mp_threshold: config.extra_mp_threshold, quest_equip_hp: config.quest_equip_hp, hp_mode: config.hp_mode, max_level: config.max_level, auto_method2: true, mw_percent: config.mw_percent, mw_from_level: config.mw_from_level, int_gear_after_reset: config.int_gear_after_reset, resume_from: config.resume_from, improved_maxhp_level: config.improved_maxhp_level, early_mp_wash_level: earlyMpWashLevel });
  const mpWarning = "⚠ base MP 超過 30,000；建議提早做 Method 2。";
  if (config.target_mp !== undefined) for (const row of result.plan) if (row.base_mp > 30_000 && !row.notes.includes(mpWarning)) row.notes = `${row.notes} ${mpWarning}`.trim();
  return { ...result, target_mp: config.target_mp, early_mp_wash_level: earlyMpWashLevel, reached_target: result.final_display_hp >= config.target_hp && (config.target_mp === undefined || result.final_base_mp >= config.target_mp) };
}
function ints(from: number, to: number, step: number): number[] { const values: number[] = []; for (let value = from; value <= to; value += step) values.push(value); if (values.at(-1) !== to) values.push(to); return values; }
function intBounds(config: Normalized): [number, number] { if (!config.resume_from) return [config.target_base_int_min, config.target_base_int_max]; if (config.resume_from.int_reset_done) { const fixed = Math.max(config.target_base_int_min, config.resume_from.base_int_peak ?? config.resume_from.base_int, 4); return [fixed, fixed]; } const low = Math.max(config.target_base_int_min, config.resume_from.base_int); return [low, Math.max(low, config.target_base_int_max)]; }
function mpEnds(config: Normalized, step: number): number[] { const minimum = Math.max(31, config.mp_wash_end_min); const values = ints(minimum, config.int_reset_level, step); if (!config.resume_from || config.resume_from.level <= minimum) return values; return [...new Set([Math.max(minimum, config.resume_from.level - 1), ...values.filter((value) => value >= config.resume_from!.level)])].sort((a, b) => a - b); }
function sortKey(candidate: CandidateResult): (number | string)[] {
  if (candidate.reached_target) return [0, totalApr(candidate.apr), -candidate.final_display_hp, candidate.target_base_int, candidate.base_int_peak, candidate.mp_wash_end, candidate.int_reached_level, candidate.policy];
  const hpShortfall = candidate.target_hp === undefined ? 0 : Math.max(0, candidate.target_hp - candidate.final_display_hp);
  const mpShortfall = candidate.target_mp === undefined ? 0 : Math.max(0, candidate.target_mp - candidate.final_base_mp);
  return [1, hpShortfall, mpShortfall, totalApr(candidate.apr), candidate.target_base_int, candidate.base_int_peak, candidate.mp_wash_end, candidate.int_reached_level, candidate.policy];
}
function compare(left: CandidateResult, right: CandidateResult): number { const a = sortKey(left); const b = sortKey(right); for (let index = 0; index < a.length; index += 1) { if (a[index] < b[index]) return -1; if (a[index] > b[index]) return 1; } return 0; }
function unique(items: CandidateResult[]): CandidateResult[] { const seen = new Set<string>(); return items.filter((item) => { const key = `${item.policy}:${item.target_base_int}:${item.mp_wash_end}:${item.extra_mp_threshold}:${item.early_mp_wash_level ?? ""}`; if (seen.has(key)) return false; seen.add(key); return true; }); }
function search(config: Normalized, policy: PolicyName, intStep: number, mpStep: number): CandidateResult[] { const [low, high] = intBounds(config); return ints(low, high, intStep).flatMap((baseInt) => mpEnds(config, mpStep).map((end) => candidate(config, policy, baseInt, end))); }
function policyBest(config: Normalized, policy: PolicyName): PolicyBest {
  const [low, high] = intBounds(config);
  const refine = (coarse: CandidateResult[], earlyMpWashLevel?: number, allMpEnds = false) => {
    const seeds = unique(coarse.sort(compare).slice(0, Math.max(8, config.top_n)));
    return seeds.flatMap((seed) => ints(Math.max(low, seed.target_base_int - config.target_base_int_step * 2), Math.min(high, seed.target_base_int + config.target_base_int_step * 2), config.target_base_int_step).flatMap((baseInt) => (allMpEnds ? mpEnds(config, 5) : mpEnds(config, 5).filter((end) => Math.abs(end - seed.mp_wash_end) <= 10)).map((end) => candidate(config, policy, baseInt, end, earlyMpWashLevel))));
  };
  const coarse = search(config, policy, 40, 10);
  let candidates = unique([...coarse, ...refine([...coarse])]);
  if ((config.target_mp !== undefined || !candidates.some((item) => item.reached_target)) && policy === "int_only_plain" && config.job !== "thief") {
    const startLevel = Math.max(31, config.resume_from?.level ?? 31);
    // Early MP5 repeats from the selected start level until returned AP reaches
    // target INT. Normal post-INT washing, including Method 2, is then simulated
    // and included in the candidate's total APR cost.
    const finalistLimit = Math.max(8, config.top_n);
    const early: CandidateResult[] = [];
    for (const baseInt of ints(low, high, config.target_base_int_step)) {
      for (const level of ints(startLevel, config.int_reset_level - 1, 1)) {
        early.push(candidate(config, policy, baseInt, config.int_reset_level, level));
        if (early.length > finalistLimit * 2) {
          early.sort(compare);
          early.length = finalistLimit;
        }
      }
    }
    early.sort(compare);
    early.length = Math.min(early.length, finalistLimit);
    if (config.target_mp !== undefined) {
      early.push(...early.map((seed) => candidate(config, policy, seed.target_base_int, seed.mp_wash_end, seed.early_mp_wash_level, true)));
    }
    for (const seed of [...early]) early.push(...refine([seed], seed.early_mp_wash_level, true));
    candidates = unique([...candidates, ...early]);
  }
  candidates.sort(compare); const feasible = candidates.filter((item) => item.reached_target); const top = (feasible.length ? feasible : candidates).slice(0, config.top_n); return { policy, best: top[0], top };
}
function comparison(byPolicy: Partial<Record<PolicyName, PolicyBest>>): ComparisonResult {
  const policy_a = byPolicy.mp_wash_shortfall?.best; const policy_b = byPolicy.int_dump_shortfall?.best; const policy_c = byPolicy.mp_wash_hardcore?.best; const policy_d = byPolicy.int_only_plain?.best; const ranked = [policy_a, policy_b, policy_c, policy_d].filter((item): item is CandidateResult => item !== undefined).sort(compare); const winner = ranked[0]; const runnerUp = ranked[1]; return { policy_a, policy_b, policy_c, policy_d, winner, apr_delta: winner && runnerUp ? totalApr(winner.apr) - totalApr(runnerUp.apr) : undefined, hp_delta: winner && runnerUp ? winner.final_display_hp - runnerUp.final_display_hp : undefined };
}
export function optimize(input: OptimizeConfig): OptimizeResult {
  const config = normalize(input); const policies = config.policies?.length ? config.policies : getJobProfile(config.job).policies; const by_policy: Partial<Record<PolicyName, PolicyBest>> = {};
  for (const policy of policies) by_policy[policy] = policyBest(config, policy);
  const all = Object.values(by_policy).flatMap((entry) => entry?.top.filter((item) => item.reached_target) ?? []).sort(compare); const resultComparison = comparison(by_policy); const fallback = Object.values(by_policy).map((entry) => entry?.best).filter((item): item is CandidateResult => item !== undefined).sort(compare)[0];
  let winner = resultComparison.winner ?? all[0] ?? fallback;
  let continued_to_200_hp: number | undefined;
  let continued_to_200_plan: CandidateResult["plan"] | undefined;
  let resetLevelMethod2Hp: number | undefined;
  if (winner) {
    if (config.max_level >= 200) continued_to_200_hp = Math.min(MAX_BASE_HP + config.quest_equip_hp, winner.final_display_hp);
    else {
      const finalState = winner.plan.at(-1);
      const continuation = simulate({
        policy: winner.policy, target_base_int: winner.target_base_int, target_hp: 1_000_000_000,
        int_reset_level: config.int_reset_level, int_gear: config.int_gear,
        job: config.job, mp_wash_end: 31,
        extra_mp_threshold: config.extra_mp_threshold, quest_equip_hp: config.quest_equip_hp,
        hp_mode: config.hp_mode, max_level: 200, auto_method2: true,
        hp_cap: MAX_BASE_HP,
        mw_percent: config.mw_percent, mw_from_level: config.mw_from_level,
        int_gear_after_reset: config.int_gear_after_reset,
        resume_from: {
          level: config.max_level, base_hp: winner.final_base_hp, base_mp: winner.final_base_mp,
          base_int: finalState?.base_int ?? 4, base_int_peak: winner.base_int_peak, fresh_ap: 0,
          int_reset_done: config.max_level >= config.int_reset_level,
        },
      });
      continued_to_200_hp = continuation.final_display_hp;
      continued_to_200_plan = continuation.plan;
    }

    if ((!config.resume_from || config.resume_from.level <= config.int_reset_level) && !config.resume_from?.int_reset_done) {
      const resetSnapshot = simulate({
        policy: winner.policy, target_base_int: winner.target_base_int, target_hp: 1_000_000_000,
        int_reset_level: config.int_reset_level, int_gear: config.int_gear,
        job: config.job, mp_wash_end: winner.mp_wash_end,
        extra_mp_threshold: config.extra_mp_threshold, quest_equip_hp: config.quest_equip_hp,
        hp_mode: config.hp_mode, max_level: config.int_reset_level, auto_method2: false,
        hp_cap: MAX_BASE_HP,
        mw_percent: config.mw_percent, mw_from_level: config.mw_from_level,
        int_gear_after_reset: config.int_gear_after_reset, resume_from: config.resume_from,
      });
      const profile = getJobProfile(config.job);
      const extraMpAtReset = Math.max(0, profile.extraMp(resetSnapshot.final_base_mp, config.int_reset_level));
      const plannedMethod2 = winner.apr.method2_hp_wash_count;
      const skill = makeSkillTracker(profile, config.improved_maxhp_level);
      skill.seedForResume(config.int_reset_level, profile.jobAdvances);
      const method2Hp = profile.method2Hp(config.hp_mode, skill);
      const capBaseHp = MAX_BASE_HP;
      const affordableBeforeHpCap = Math.max(0, Math.ceil((extraMpAtReset - 1e-9) / profile.mpRemovedPerApr));
      const hpSpace = Math.max(0, capBaseHp - resetSnapshot.final_base_hp);
      const washesToHpCap = method2Hp > 0 ? Math.ceil(hpSpace / method2Hp) : 0;
      const earlyMethod2Count = Math.min(plannedMethod2, affordableBeforeHpCap, washesToHpCap);
      const afterEarlyMethod2 = simulate({
        policy: winner.policy, target_base_int: 4,
        target_hp: resetSnapshot.final_base_hp + earlyMethod2Count * method2Hp + config.quest_equip_hp,
        int_reset_level: config.int_reset_level, int_gear: config.int_gear,
        job: config.job, mp_wash_end: 31, extra_mp_threshold: config.extra_mp_threshold,
        quest_equip_hp: config.quest_equip_hp, hp_mode: config.hp_mode,
        max_level: config.int_reset_level, auto_method2: true, hp_cap: capBaseHp,
        mw_percent: config.mw_percent, mw_from_level: config.mw_from_level,
        int_gear_after_reset: config.int_gear_after_reset,
        resume_from: {
          level: config.int_reset_level, base_hp: resetSnapshot.final_base_hp,
          base_mp: resetSnapshot.final_base_mp, base_int: 4,
          base_int_peak: resetSnapshot.base_int_peak, fresh_ap: 0, int_reset_done: true,
        },
      });
      resetLevelMethod2Hp = afterEarlyMethod2.final_display_hp;
      const afterEarlyMethod2To200 = simulate({
        policy: winner.policy, target_base_int: 4, target_hp: 1_000_000_000,
        int_reset_level: config.int_reset_level, int_gear: config.int_gear,
        job: config.job, mp_wash_end: 31, extra_mp_threshold: config.extra_mp_threshold,
        quest_equip_hp: config.quest_equip_hp, hp_mode: config.hp_mode,
        max_level: 200, auto_method2: true, hp_cap: capBaseHp,
        mw_percent: config.mw_percent, mw_from_level: config.mw_from_level,
        int_gear_after_reset: config.int_gear_after_reset,
        resume_from: {
          level: config.int_reset_level, base_hp: afterEarlyMethod2.final_base_hp,
          base_mp: afterEarlyMethod2.final_base_mp, base_int: 4,
          base_int_peak: resetSnapshot.base_int_peak, fresh_ap: 0, int_reset_done: true,
        },
      });
      const earlyMethod2To200Hp = afterEarlyMethod2To200.final_display_hp;
      const note = `\u4E5F\u53EF\u9078\u64C7\u5728\u6B64\u63D0\u65E9\u505A Method 2\uFF1A\u6700\u591A ${earlyMethod2Count} \u6B21\uFF08\u539F\u8A08\u756B 200 \u7B49 ${plannedMethod2} \u6B21\uFF09\uFF0C\u7576\u4E0B HP ${resetLevelMethod2Hp.toLocaleString()}\uFF1B\u7E7C\u7E8C\u6D17\u5230 200 \u7B49\u53EF\u9054 ${earlyMethod2To200Hp.toLocaleString()} HP\u3002`;
      const annotate = (plan: CandidateResult["plan"]) => plan.map((row) => row.level === config.int_reset_level && row.action === "RESET_INT" ? { ...row, notes: `${row.notes} ${note}` } : row);
      if (config.max_level < config.int_reset_level && continued_to_200_plan) continued_to_200_plan = annotate(continued_to_200_plan);
      else winner = { ...winner, plan: annotate(winner.plan) };
    }
  }
  return { by_policy, comparison: resultComparison, winner, top_candidates: all.slice(0, config.top_n), resume_from: config.resume_from, continued_to_200_hp, continued_to_200_plan };
}
