import { FRESH_AP_PER_LEVEL, STARTING_DEX, STARTING_FRESH_AP, STARTING_HP, STARTING_INT, STARTING_LUK, STARTING_MP, STARTING_STR, levelupMpIntBonus, method1WashesAffordable, mpWashesAffordable } from "./formulas";
import { totalInt } from "./gear";
import { getJobProfile, makeSkillTracker, type JobProfile, type SkillTracker } from "./jobs";
import type { Action, AprBreakdown, LevelPlanRow, SimulateConfig, SimulateResult } from "./models";
import { chooseEarlyAction, HARDCORE_EARLY_START_LEVEL, HARDCORE_MP_WASH_MIN_LEVEL } from "./policy";

const BASE_STAT_FLOOR = 4;
const pyRound = (value: number): number => {
  const floor = Math.floor(value);
  const fraction = value - floor;
  if (fraction < 0.5) return floor;
  if (fraction > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
};

type NormalizedConfig = Required<Omit<SimulateConfig, "resume_from" | "improved_maxhp_level" | "target_mp">> & Pick<SimulateConfig, "resume_from" | "improved_maxhp_level" | "target_mp">;

class State {
  level = 1; base_str = STARTING_STR; base_dex = STARTING_DEX; base_int = STARTING_INT; base_luk = STARTING_LUK;
  base_hp = STARTING_HP; base_mp = STARTING_MP; base_int_peak = STARTING_INT; int_reached_level = 0;
  mp_wash_count = 0; method1_hp_wash_count = 0; method2_hp_wash_count = 0; int_reset_apr = 0;
  int_reset_done = false; level_fresh_ap = FRESH_AP_PER_LEVEL; plan: LevelPlanRow[] = [];
  constructor(readonly profile: JobProfile, readonly skill: SkillTracker) {}
  noteInt(): void { this.base_int_peak = Math.max(this.base_int_peak, this.base_int); }
  extraMp(): number { return this.profile.extraMp(this.base_mp, this.level); }
  canRemoveMp(times: number, floor?: number): boolean {
    const removed = this.profile.mpRemovedPerApr * times;
    return this.extraMp() >= removed && (floor === undefined || this.base_mp - removed + 1e-9 >= floor);
  }
}

function row(state: State, action: Action, fields: Partial<LevelPlanRow> = {}): LevelPlanRow {
  return { level: state.level, action, base_int: state.base_int, base_luk: state.base_luk, base_hp: pyRound(state.base_hp), base_mp: pyRound(state.base_mp), extra_mp: pyRound(state.extraMp()), fresh_ap_int: 0, fresh_ap_luk: 0, fresh_ap_dex: 0, fresh_ap_str: 0, fresh_ap_hp: 0, fresh_ap_mp: 0, apr_spent: 0, notes: "", ...fields };
}

function normalize(config: SimulateConfig): NormalizedConfig {
  const profile = getJobProfile(config.job ?? "thief");
  return { ...config, job: config.job ?? "thief", mp_wash_end: config.mp_wash_end ?? 135, extra_mp_threshold: config.extra_mp_threshold ?? profile.defaultExtraMpThreshold(), quest_equip_hp: config.quest_equip_hp ?? 0, hp_mode: config.hp_mode ?? "avg", max_level: config.max_level ?? 200, auto_method2: config.auto_method2 ?? true, mw_percent: config.mw_percent ?? 0.1, mw_from_level: config.mw_from_level ?? 10, int_gear_after_reset: config.int_gear_after_reset ?? 50 };
}

function validate(config: NormalizedConfig): void {
  const profile = getJobProfile(config.job);
  if (config.target_hp <= 0) throw new Error("target_hp must be positive");
  if (!(1 < config.int_reset_level && config.int_reset_level <= config.max_level)) throw new Error("int_reset_level out of range");
  if (!(30 < config.mp_wash_end && config.mp_wash_end <= config.int_reset_level)) throw new Error("mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level");
  if (config.target_base_int < BASE_STAT_FLOOR) throw new Error("target_base_int too low");
  if (config.extra_mp_threshold < 0 || config.int_gear_after_reset < 0) throw new Error("INT and threshold values must not be negative");
  if (config.improved_maxhp_level !== undefined && (config.improved_maxhp_level < 0 || config.improved_maxhp_level > 10)) throw new Error("improved_maxhp_level must be in [0, 10]");
  if (config.target_mp !== undefined && config.target_mp < profile.minMp(config.max_level)) throw new Error(`target_mp below job min_mp at max_level (min=${profile.minMp(config.max_level)})`);
}

export function simulate(input: SimulateConfig): SimulateResult {
  const config = normalize(input); validate(config);
  const profile = getJobProfile(config.job); const skill = makeSkillTracker(profile, config.improved_maxhp_level);
  const state = new State(profile, skill);
  let startLoop = 2;
  if (config.resume_from) {
    seedResume(state, config); state.plan.push(row(state, "RESUME", { notes: "Resume snapshot" }));
    markIntReached(state, config); execute(state, decide(state, config), config); markIntReached(state, config); maybeReset(state, config); startLoop = state.level + 1;
  } else { applyStartingAp(state, config); markIntReached(state, config); }
  for (let level = startLoop; level <= config.max_level; level += 1) { levelUp(state, level, config); execute(state, decide(state, config), config); markIntReached(state, config); maybeReset(state, config); }
  if (config.auto_method2) method2TopUp(state, config);
  if (!state.int_reset_done && state.base_int > BASE_STAT_FLOOR) resetInt(state);
  const apr: AprBreakdown = { mp_wash_count: state.mp_wash_count, method1_hp_wash_count: state.method1_hp_wash_count, method2_hp_wash_count: state.method2_hp_wash_count, int_reset_apr: state.int_reset_apr };
  const display = state.base_hp + config.quest_equip_hp;
  return { policy: config.policy, target_base_int: config.target_base_int, target_hp: config.target_hp, int_reached_level: state.int_reached_level, mp_wash_end: config.mp_wash_end, extra_mp_threshold: config.extra_mp_threshold, int_gear_after_reset: config.int_gear_after_reset, final_base_hp: pyRound(state.base_hp), final_display_hp: pyRound(display), final_base_mp: pyRound(state.base_mp), base_int_peak: state.base_int_peak, reached_target: display + 1e-9 >= config.target_hp && (config.target_mp === undefined || state.base_mp + 1e-9 >= config.target_mp), apr, plan: state.plan, resume_from: config.resume_from, job: config.job, improved_maxhp_level: profile.maxhpSkill ? state.skill.effectiveLevel : undefined, target_mp: config.target_mp };
}

function seedResume(state: State, config: NormalizedConfig): void {
  const resume = config.resume_from!;
  if (!(resume.level >= 1 && resume.level <= config.max_level) || resume.base_hp <= 0 || resume.base_mp < 0 || resume.base_int < 4) throw new Error("invalid resume snapshot");
  if (resume.base_mp + 1e-9 < state.profile.minMp(resume.level)) throw new Error(`resume base_mp below job min_mp at level (min=${state.profile.minMp(resume.level)})`);
  if (resume.int_reset_done && resume.base_int > BASE_STAT_FLOOR) throw new Error("int_reset_done but base_int > 4");
  state.level = resume.level; state.base_hp = resume.base_hp; state.base_mp = resume.base_mp; state.base_int = resume.base_int;
  state.base_luk = resume.base_luk ?? 4; state.base_dex = resume.base_dex ?? 25; state.base_str = resume.base_str ?? 4;
  state.base_int_peak = Math.max(resume.base_int_peak ?? resume.base_int, resume.base_int); state.int_reset_done = resume.int_reset_done ?? false;
  state.level_fresh_ap = resume.fresh_ap ?? FRESH_AP_PER_LEVEL; state.int_reached_level = state.base_int >= config.target_base_int || state.int_reset_done ? state.level : 0;
  if (state.profile.maxhpSkill) state.skill.seedForResume(state.level, state.profile.jobAdvances);
}
function markIntReached(state: State, config: NormalizedConfig): void { if (state.int_reached_level === 0 && state.base_int >= config.target_base_int) state.int_reached_level = state.level; }
function applyStartingAp(state: State, config: NormalizedConfig): void { state.base_int += STARTING_FRESH_AP; state.noteInt(); state.plan.push(row(state, "BUILD", { fresh_ap_int: STARTING_FRESH_AP, notes: "Creation AP → INT" })); void config; }
function levelUp(state: State, level: number, config: NormalizedConfig): void {
  const advance = state.profile.jobAdvances.get(level); if (advance) state.skill.onJobAdvance(advance.number); state.skill.onLevel();
  const currentInt = totalInt(state.base_int, config.int_gear, level, { mwPercent: config.mw_percent, mwFromLevel: config.mw_from_level, intResetLevel: config.int_reset_level, intGearAfterReset: config.int_gear_after_reset });
  state.base_hp += state.profile.levelupHp(level, config.hp_mode, state.skill); state.base_mp += state.profile.levelupMpBase(level, config.hp_mode) + levelupMpIntBonus(currentInt); state.level = level; state.level_fresh_ap = FRESH_AP_PER_LEVEL;
  if (advance) { state.base_hp += pickAdvance(advance.spec.hpMid, advance.spec.spread, config.hp_mode); state.base_mp += pickAdvance(advance.spec.mpMid, advance.spec.spread, config.hp_mode); state.level_fresh_ap += advance.spec.apBonus; }
}
function pickAdvance(mid: number, spread = 25, mode: "avg" | "min" | "max"): number { if (mid === 0) return 0; return mode === "min" ? Math.max(0, mid - spread) : mode === "max" ? mid + spread : mid; }
function maybeReset(state: State, config: NormalizedConfig): void { if (!state.int_reset_done && state.level >= config.int_reset_level && state.base_int > BASE_STAT_FLOOR) resetInt(state); }
function primaryAction(state: State): Action { return state.profile.primaryStat === "str" ? "STR5" : state.profile.primaryStat === "dex" ? "DEX5" : "LUK5"; }
function decide(state: State, config: NormalizedConfig): Action {
  const hardcore = config.policy === "mp_wash_hardcore" && !state.int_reset_done && state.level < config.int_reset_level && state.base_int < config.target_base_int && state.level >= HARDCORE_EARLY_START_LEVEL;
  if (hardcore) return "HARDCORE_GREEDY";
  if (state.level <= 30) return "BUILD";
  if (!state.int_reset_done && state.level < config.int_reset_level && state.base_int < config.target_base_int) return chooseEarlyAction(config.policy, state.extraMp(), config.extra_mp_threshold);
  if (state.level <= config.mp_wash_end) return "MP5";
  return state.profile.preferMethod2 ? primaryAction(state) : "HP5";
}
function intRoom(state: State, config: NormalizedConfig): number { return !state.int_reset_done && state.level < config.int_reset_level ? Math.max(0, config.target_base_int - state.base_int) : 0; }
function addPrimary(state: State, points: number): void { if (state.profile.primaryStat === "str") state.base_str += points; else if (state.profile.primaryStat === "dex") state.base_dex += points; else state.base_luk += points; }
function primaryFields(state: State, points: number): Partial<LevelPlanRow> { return points <= 0 ? {} : state.profile.primaryStat === "str" ? { fresh_ap_str: points } : state.profile.primaryStat === "dex" ? { fresh_ap_dex: points } : { fresh_ap_luk: points }; }
function assignWash(state: State, config: NormalizedConfig, points: number): [number, number] { const toInt = Math.min(points, intRoom(state, config)); state.base_int += toInt; addPrimary(state, points - toInt); state.noteInt(); return [toInt, points - toInt]; }
function dump(state: State, config: NormalizedConfig, points: number): [number, number] { return assignWash(state, config, points); }
function build(state: State, config: NormalizedConfig): void {
  let ap = state.level_fresh_ap; let dex = 0; let str = 0; let toInt = 0;
  if (state.level < 11 && state.profile.firstJobStat !== "none") { const need = state.profile.firstJobStat === "dex" ? Math.max(0, state.profile.firstJobRequirement - state.base_dex) : Math.max(0, state.profile.firstJobRequirement - state.base_str); if (state.profile.firstJobStat === "dex" && need && state.base_int < 20) { const take = Math.min(ap, 20 - state.base_int); state.base_int += take; toInt += take; ap -= take; } const take = Math.min(ap, need); if (state.profile.firstJobStat === "dex") { state.base_dex += take; dex += take; } else { state.base_str += take; str += take; } ap -= take; }
  const stack = Math.min(ap, intRoom(state, config)); state.base_int += stack; toInt += stack; ap -= stack; if (ap) addPrimary(state, ap); state.noteInt();
  if (state.profile.primaryStat === "dex") dex += ap; if (state.profile.primaryStat === "str") str += ap;
  state.plan.push(row(state, "BUILD", { fresh_ap_int: toInt, fresh_ap_dex: dex, fresh_ap_str: str, fresh_ap_luk: state.profile.primaryStat === "luk" ? ap : 0, notes: "Build stats" }));
}
function method1(state: State, config: NormalizedConfig, requested: number): void { let done = 0; let toInt = 0; let toPrimary = 0; for (let index = 0; index < requested; index += 1) { if (!state.canRemoveMp(1, config.target_mp)) break; state.base_hp += state.profile.method1Hp(config.hp_mode, state.skill); state.base_mp -= state.profile.mpRemovedPerApr; const [i, p] = assignWash(state, config, 1); toInt += i; toPrimary += p; done += 1; } const [leftInt, leftPrimary] = done < state.level_fresh_ap ? dump(state, config, state.level_fresh_ap - done) : [0, 0]; state.method1_hp_wash_count += done; state.plan.push(row(state, done ? (`HP${Math.min(5, done)}` as Action) : leftInt ? "INT5" : primaryAction(state), { fresh_ap_hp: done, fresh_ap_int: leftInt, apr_spent: done, ...primaryFields(state, leftPrimary), notes: `Method1 × ${done}; return INT ${toInt}, primary ${toPrimary}` })); }
function mpWash(state: State, config: NormalizedConfig, requested: number): void { let done = 0; let toInt = 0; let toPrimary = 0; for (let index = 0; index < requested; index += 1) { const gain = state.profile.freshApMp(state.base_int, config.hp_mode); state.base_mp += gain; if (state.extraMp() < state.profile.mpRemovedPerApr) { state.base_mp -= gain; break; } state.base_mp -= state.profile.mpRemovedPerApr; const [i, p] = assignWash(state, config, 1); toInt += i; toPrimary += p; done += 1; } const [leftInt, leftPrimary] = done < state.level_fresh_ap ? dump(state, config, state.level_fresh_ap - done) : [0, 0]; state.mp_wash_count += done; state.plan.push(row(state, done ? (`MP${Math.min(5, done)}` as Action) : leftInt ? "INT5" : primaryAction(state), { fresh_ap_mp: done, fresh_ap_int: leftInt, apr_spent: done, ...primaryFields(state, leftPrimary), notes: `MP wash × ${done}; return INT ${toInt}, primary ${toPrimary}` })); }
function greedy(state: State, config: NormalizedConfig): void { let remaining = state.level_fresh_ap; let hp = 0; let mp = 0; while (remaining > 0) { if (state.canRemoveMp(1, config.target_mp)) { state.base_hp += state.profile.method1Hp(config.hp_mode, state.skill); state.base_mp -= state.profile.mpRemovedPerApr; assignWash(state, config, 1); state.method1_hp_wash_count += 1; hp += 1; remaining -= 1; continue; } if (state.level >= HARDCORE_MP_WASH_MIN_LEVEL) { const gain = state.profile.freshApMp(state.base_int, config.hp_mode); state.base_mp += gain; if (state.extraMp() >= state.profile.mpRemovedPerApr) { state.base_mp -= state.profile.mpRemovedPerApr; assignWash(state, config, 1); state.mp_wash_count += 1; mp += 1; remaining -= 1; continue; } state.base_mp -= gain; } break; } const [toInt, toPrimary] = remaining ? dump(state, config, remaining) : [0, 0]; state.plan.push(row(state, "HARDCORE_GREEDY", { fresh_ap_hp: hp, fresh_ap_mp: mp, fresh_ap_int: toInt, apr_spent: hp + mp, ...primaryFields(state, toPrimary), notes: "Greedy HP1/MP1" })); }
function execute(state: State, action: Action, config: NormalizedConfig): void { if (action === "BUILD") return build(state, config); if (action === "HARDCORE_GREEDY") return greedy(state, config); if (action.startsWith("HP")) return method1(state, config, method1WashesAffordable(state.extraMp(), state.level_fresh_ap, state.profile.mpRemovedPerApr)); if (action.startsWith("MP")) return mpWash(state, config, mpWashesAffordable(state.base_int, state.base_mp, state.level, state.level_fresh_ap, config.hp_mode, config.job)); if (action === "INT5") { const [toInt, toPrimary] = dump(state, config, state.level_fresh_ap); state.plan.push(row(state, toInt ? "INT5" : primaryAction(state), { fresh_ap_int: toInt, ...primaryFields(state, toPrimary), notes: "Dump fresh AP" })); return; } if (action === "LUK5" || action === "STR5" || action === "DEX5") { addPrimary(state, state.level_fresh_ap); state.plan.push(row(state, action, { ...primaryFields(state, state.level_fresh_ap), notes: "Primary stat" })); } }
function resetInt(state: State): void { if (state.base_int <= BASE_STAT_FLOOR) { state.int_reset_done = true; return; } const moved = state.base_int - BASE_STAT_FLOOR; state.base_int = BASE_STAT_FLOOR; addPrimary(state, moved); state.int_reset_apr += moved; state.int_reset_done = true; state.plan.push(row(state, "RESET_INT", { apr_spent: moved, notes: "Reset INT" })); }
function method2TopUp(state: State, config: NormalizedConfig): void {
  const target = config.target_hp - config.quest_equip_hp;
  let washes = 0;
  const wash = () => { state.base_hp += state.profile.method2Hp(config.hp_mode, state.skill); state.base_mp -= state.profile.mpRemovedPerApr; washes += 1; };
  while (state.base_hp + 1e-9 < target && state.canRemoveMp(1, config.target_mp)) wash();
  if (washes) {
    state.method2_hp_wash_count += washes;
    state.plan.push(row(state, "M2", { apr_spent: washes, notes: `Method2 × ${washes}` }));
  }
}
