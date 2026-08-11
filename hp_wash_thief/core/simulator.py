"""Level-by-level Thief HP/MP wash simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from hp_wash_thief.core import formulas as F
from hp_wash_thief.core.gear import total_int
from hp_wash_thief.core.models import (
    Action,
    AprBreakdown,
    HP_ACTIONS,
    HpMode,
    LevelPlanRow,
    MP_ACTIONS,
    PolicyName,
    ResumeFrom,
    SimulateConfig,
    SimulateResult,
    hp_action_for_wash_count,
    mp_action_for_wash_count,
    planned_hp_washes,
    planned_mp_washes,
)
from hp_wash_thief.core.policy import choose_early_action, mp_wash_hardcore


@dataclass
class CharacterState:
    level: int = 1
    base_str: int = F.STARTING_STR
    base_dex: int = F.STARTING_DEX
    base_int: int = F.STARTING_INT
    base_luk: int = F.STARTING_LUK
    base_hp: float = F.STARTING_HP
    base_mp: float = F.STARTING_MP
    base_int_peak: int = F.STARTING_INT
    int_reached_level: int = 0
    mp_wash_count: int = 0
    method1_hp_wash_count: int = 0
    method2_hp_wash_count: int = 0
    int_reset_apr: int = 0
    int_reset_done: bool = False
    level_fresh_ap: int = F.FRESH_AP_PER_LEVEL
    plan: list[LevelPlanRow] = field(default_factory=list)

    def note_int(self) -> None:
        if self.base_int > self.base_int_peak:
            self.base_int_peak = self.base_int

    def extra_mp(self) -> float:
        return F.extra_mp(self.base_mp, self.level)

    def can_remove_mp(self, times: int = 1) -> bool:
        return self.extra_mp() >= (F.MP_REMOVED_PER_APR * times)


def simulate(config: SimulateConfig) -> SimulateResult:
    _validate_config(config)
    if config.resume_from is None:
        state = CharacterState()
        _apply_starting_ap(state, config)
        _maybe_mark_int_reached(state, config)
        start_loop = 2
    else:
        state = _seed_from_resume(config.resume_from, config)
        _append_resume_marker(state, config)
        _maybe_mark_int_reached(state, config)
        # Already at resume.level with HP/MP applied; spend this level's AP next.
        action = _decide_action(state, config)
        _execute_action(state, action, config)
        _maybe_mark_int_reached(state, config)
        _maybe_reset_int(state, config)
        start_loop = state.level + 1

    for new_level in range(start_loop, config.max_level + 1):
        _level_up(state, new_level, config)
        action = _decide_action(state, config)
        _execute_action(state, action, config)
        _maybe_mark_int_reached(state, config)
        _maybe_reset_int(state, config)

    if config.auto_method2:
        _method2_top_up(state, config)

    # If INT reset deferred somehow, settle at end.
    if not state.int_reset_done and state.base_int > F.BASE_STAT_FLOOR:
        _reset_int_to_floor(state)

    display_hp = state.base_hp + config.quest_equip_hp
    apr = AprBreakdown(
        mp_wash_count=state.mp_wash_count,
        method1_hp_wash_count=state.method1_hp_wash_count,
        method2_hp_wash_count=state.method2_hp_wash_count,
        int_reset_apr=state.int_reset_apr,
    )
    return SimulateResult(
        policy=config.policy,
        target_base_int=config.target_base_int,
        int_reached_level=state.int_reached_level,
        mp_wash_end=config.mp_wash_end,
        extra_mp_threshold=config.extra_mp_threshold,
        int_gear_after_reset=config.int_gear_after_reset,
        final_base_hp=int(round(state.base_hp)),
        final_display_hp=int(round(display_hp)),
        base_int_peak=state.base_int_peak,
        reached_target=display_hp + 1e-9 >= config.target_hp,
        apr=apr,
        plan=state.plan,
        resume_from=config.resume_from,
    )


def _validate_config(config: SimulateConfig) -> None:
    if config.target_hp <= 0:
        raise ValueError("target_hp must be positive")
    if not (1 < config.int_reset_level <= config.max_level):
        raise ValueError("int_reset_level out of range")
    if not (30 < config.mp_wash_end <= config.int_reset_level):
        raise ValueError("mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level")
    if config.target_base_int < F.BASE_STAT_FLOOR:
        raise ValueError("target_base_int too low")
    if config.extra_mp_threshold < 0:
        raise ValueError("extra_mp_threshold must be >= 0")
    if config.int_gear_after_reset < 0:
        raise ValueError("int_gear_after_reset must be >= 0")
    if config.resume_from is not None:
        _validate_resume(config.resume_from, config)


def _validate_resume(resume: ResumeFrom, config: SimulateConfig) -> None:
    if not (1 <= resume.level <= config.max_level):
        raise ValueError("resume level out of range")
    if resume.base_hp <= 0:
        raise ValueError("resume base_hp must be positive")
    if resume.base_mp < 0:
        raise ValueError("resume base_mp must be >= 0")
    if resume.base_int < F.BASE_STAT_FLOOR:
        raise ValueError("resume base_int too low")
    if resume.base_luk < F.BASE_STAT_FLOOR:
        raise ValueError("resume base_luk too low")
    if resume.base_dex < F.BASE_STAT_FLOOR:
        raise ValueError("resume base_dex too low")
    if resume.fresh_ap is not None and resume.fresh_ap < 0:
        raise ValueError("resume fresh_ap must be >= 0")
    if resume.int_reset_done and resume.base_int > F.BASE_STAT_FLOOR:
        raise ValueError("int_reset_done but base_int > 4")
    if resume.base_int_peak is not None and resume.base_int_peak < resume.base_int:
        raise ValueError("resume base_int_peak must be >= base_int")


def _seed_from_resume(resume: ResumeFrom, config: SimulateConfig) -> CharacterState:
    fresh = (
        resume.fresh_ap
        if resume.fresh_ap is not None
        else F.FRESH_AP_PER_LEVEL
    )
    peak = resume.base_int_peak if resume.base_int_peak is not None else resume.base_int
    return CharacterState(
        level=resume.level,
        base_str=resume.base_str,
        base_dex=resume.base_dex,
        base_int=resume.base_int,
        base_luk=resume.base_luk,
        base_hp=float(resume.base_hp),
        base_mp=float(resume.base_mp),
        base_int_peak=max(peak, resume.base_int),
        int_reached_level=resume.level if resume.base_int >= config.target_base_int else 0,
        int_reset_done=resume.int_reset_done,
        level_fresh_ap=fresh,
    )


def _append_resume_marker(state: CharacterState, config: SimulateConfig) -> None:
    fresh = state.level_fresh_ap
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=Action.RESUME,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            notes=(
                f"中途接續：Lv{state.level}｜INT {state.base_int}｜"
                f"Extra MP {int(round(state.extra_mp()))}｜本等剩餘 AP {fresh}"
                + ("｜INT 已洗回" if state.int_reset_done else "")
            ),
        )
    )


def _maybe_mark_int_reached(state: CharacterState, config: SimulateConfig) -> None:
    if state.int_reached_level == 0 and state.base_int >= config.target_base_int:
        state.int_reached_level = state.level


def _apply_starting_ap(state: CharacterState, config: SimulateConfig) -> None:
    """Level 1: put all creation AP into INT (PerfectSin)."""
    ap = F.STARTING_FRESH_AP
    state.base_int += ap
    state.note_int()
    state.plan.append(
        LevelPlanRow(
            level=1,
            action=Action.BUILD,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            fresh_ap_int=ap,
            notes="創角 AP → INT",
        )
    )


def _level_up(state: CharacterState, new_level: int, config: SimulateConfig) -> None:
    """Apply natural HP/MP on leveling into new_level, then job-advance bonuses."""
    # Gains are computed for the level you enter, using INT/gear at that new level.
    is_beginner = new_level <= 10
    # Gear at the level being entered (MW/gear worn at level-up).
    t_int = total_int(
        state.base_int,
        config.int_gear,
        new_level,
        mw_percent=config.mw_percent,
        mw_from_level=config.mw_from_level,
        int_reset_level=config.int_reset_level,
        int_gear_after_reset=config.int_gear_after_reset,
    )
    hp_gain = F.levelup_hp_gain(is_beginner=is_beginner, mode=config.hp_mode)
    mp_gain = F.levelup_mp_base_gain(is_beginner=is_beginner, mode=config.hp_mode)
    mp_gain += F.levelup_mp_int_bonus(t_int)
    state.base_hp += hp_gain
    state.base_mp += mp_gain
    state.level = new_level
    state.level_fresh_ap = F.FRESH_AP_PER_LEVEL

    if new_level in F.JOB_ADVANCE_LEVELS:
        adv = F.JOB_ADVANCE_LEVELS[new_level]
        hp_b, mp_b = F.job_advance_bonus(adv, config.hp_mode)
        state.base_hp += hp_b
        state.base_mp += mp_b
        state.level_fresh_ap += F.job_advance_ap(adv)


def _maybe_reset_int(state: CharacterState, config: SimulateConfig) -> None:
    """After this level's wash, convert INT→LUK once int_reset_level is reached."""
    if (
        not state.int_reset_done
        and state.level >= config.int_reset_level
        and state.base_int > F.BASE_STAT_FLOOR
    ):
        _reset_int_to_floor(state)


def _decide_action(state: CharacterState, config: SimulateConfig) -> Action:
    level = state.level
    if _in_hardcore_early_phase(state, config):
        return mp_wash_hardcore.choose_level_action(state.level)
    if level <= 30:
        return Action.BUILD
    # Early shortfall logic continues until target_base_int is reached (not a fixed level).
    if _in_early_phase(state, config):
        if config.policy is PolicyName.INT_ONLY_PLAIN:
            return Action.BUILD if level <= 30 else Action.INT5
        return choose_early_action(
            config.policy,
            state.extra_mp(),
            config.extra_mp_threshold,
            level=level,
            fresh_ap=state.level_fresh_ap,
            base_int=state.base_int,
            base_mp=state.base_mp,
            hp_mode=config.hp_mode,
        )
    if level <= config.mp_wash_end:
        return Action.MP5
    return Action.HP5


def _in_hardcore_early_phase(state: CharacterState, config: SimulateConfig) -> bool:
    """Policy C: lv10+ until target INT; HP wash at Extra MP >= 12; MP5 only lv30+."""
    if config.policy is not PolicyName.MP_WASH_HARDCORE:
        return False
    if state.int_reset_done or state.level >= config.int_reset_level:
        return False
    if state.base_int >= config.target_base_int:
        return False
    return state.level >= mp_wash_hardcore.EARLY_START_LEVEL


def _in_early_phase(state: CharacterState, config: SimulateConfig) -> bool:
    """Early phase: post-30 while still building toward target_base_int."""
    if state.int_reset_done or state.level >= config.int_reset_level:
        return False
    return state.base_int < config.target_base_int


def _execute_action(state: CharacterState, action: Action, config: SimulateConfig) -> None:
    fresh_ap = state.level_fresh_ap
    if action is Action.BUILD:
        _build_ap(state, config, ap=fresh_ap)
        return
    if action is Action.HARDCORE_GREEDY:
        _execute_hardcore_greedy_level(state, config, fresh_ap=fresh_ap)
        return
    if action in HP_ACTIONS or action is Action.HP5:
        hp_washes = planned_hp_washes(
            action, extra_mp=state.extra_mp(), fresh_ap=fresh_ap
        )
        _hp_wash_method1(state, config, fresh_ap=fresh_ap, hp_washes=hp_washes)
        return
    if action in MP_ACTIONS or action is Action.MP5:
        mp_washes = planned_mp_washes(
            action,
            base_int=state.base_int,
            base_mp=state.base_mp,
            level=state.level,
            fresh_ap=fresh_ap,
            hp_mode=config.hp_mode,
        )
        _mp_wash(state, config, fresh_ap=fresh_ap, mp_washes=mp_washes)
        return
    if action is Action.INT5:
        _dump_fresh_ap_to_int_or_luk(state, config, points=fresh_ap)
        return
    raise ValueError(f"unsupported action: {action}")


def _try_one_hp_wash(state: CharacterState, config: SimulateConfig) -> float:
    """One Method 1 wash. Returns HP gained, or 0.0 if Extra MP insufficient."""
    if not state.can_remove_mp(1):
        return 0.0
    gain = F.method1_hp_gain(config.hp_mode)
    state.base_hp += gain
    state.base_mp -= F.MP_REMOVED_PER_APR
    _assign_wash_points(state, config, 1)
    state.method1_hp_wash_count += 1
    return gain


def _try_one_mp_wash(state: CharacterState, config: SimulateConfig) -> float:
    """One MP wash. Returns net MP change, or 0.0 if wash fails."""
    gain = F.fresh_ap_mp_gain(state.base_int, config.hp_mode)
    state.base_mp += gain
    if state.extra_mp() < F.MP_REMOVED_PER_APR:
        state.base_mp -= gain
        return 0.0
    state.base_mp -= F.MP_REMOVED_PER_APR
    net = gain - F.MP_REMOVED_PER_APR
    _assign_wash_points(state, config, 1)
    state.mp_wash_count += 1
    return net


def _execute_hardcore_greedy_level(
    state: CharacterState, config: SimulateConfig, *, fresh_ap: int
) -> None:
    """Policy C: each AP slot — HP1 if Extra MP >= 12, else MP1 (lv30+), else dump INT."""
    allow_mp = state.level >= mp_wash_hardcore.MP_WASH_MIN_LEVEL
    hp_done = mp_done = 0
    hp_gain_total = 0.0
    net_mp_total = 0.0
    remaining = int(fresh_ap)
    step_notes: list[str] = []

    while remaining > 0:
        hp_gain = _try_one_hp_wash(state, config)
        if hp_gain > 0:
            hp_done += 1
            hp_gain_total += hp_gain
            remaining -= 1
            step_notes.append("HP1")
            continue
        if allow_mp:
            prev_mp_count = state.mp_wash_count
            net_mp = _try_one_mp_wash(state, config)
            if state.mp_wash_count > prev_mp_count:
                mp_done += 1
                net_mp_total += net_mp
                remaining -= 1
                step_notes.append("MP1")
                continue
        break

    leftover_int = leftover_luk = 0
    if remaining > 0:
        leftover_int, leftover_luk = _dump_points(state, config, remaining)
        step_notes.append(f"INT {remaining}")

    notes = "greedy: " + " → ".join(step_notes) if step_notes else "greedy: （無）"
    if hp_done:
        notes += f"；M1×{hp_done}（+{hp_gain_total:.1f} HP）"
    if mp_done:
        notes += f"；MP×{mp_done}（淨增 {net_mp_total:.1f} MP）"
    if leftover_int or leftover_luk:
        notes += f"；剩餘 AP → INT {leftover_int} LUK {leftover_luk}"

    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=Action.HARDCORE_GREEDY,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            fresh_ap_hp=hp_done,
            fresh_ap_mp=mp_done,
            fresh_ap_int=leftover_int,
            fresh_ap_luk=leftover_luk,
            apr_spent=hp_done + mp_done,
            notes=notes,
        )
    )


def _int_building_allowed(state: CharacterState, config: SimulateConfig) -> bool:
    """Stop building INT once reset level is reached or reset has already run."""
    return (not state.int_reset_done) and state.level < config.int_reset_level


def _int_room(state: CharacterState, config: SimulateConfig) -> int:
    if not _int_building_allowed(state, config):
        return 0
    return max(0, config.target_base_int - state.base_int)


def _assign_wash_points(state: CharacterState, config: SimulateConfig, points: int) -> tuple[int, int]:
    """Assign APR wash return points to INT until target, then LUK.

    After ``int_reset_level``, all return points go to LUK (never rebuild INT).
    """
    to_int = min(points, _int_room(state, config))
    to_luk = points - to_int
    state.base_int += to_int
    state.base_luk += to_luk
    state.note_int()
    return to_int, to_luk


def _build_ap(state: CharacterState, config: SimulateConfig, *, ap: int) -> None:
    """Pre-30 build: DEX to first-job requirement, then stack INT."""
    to_dex = 0
    to_int = 0
    to_luk = 0
    notes = []

    if state.level <= 10 and state.base_dex < F.FIRST_JOB_DEX_REQUIREMENT:
        need = F.FIRST_JOB_DEX_REQUIREMENT - state.base_dex
        # PerfectSin: reach ~20 INT first, then finish DEX, then INT.
        if state.base_int < 20:
            int_need = 20 - state.base_int
            take_int = min(ap, int_need)
            state.base_int += take_int
            to_int += take_int
            ap -= take_int
        take_dex = min(ap, need)
        state.base_dex += take_dex
        to_dex += take_dex
        ap -= take_dex
        notes.append("建 DEX／INT")
    if ap > 0:
        room = _int_room(state, config)
        take_int = min(ap, room)
        state.base_int += take_int
        to_int += take_int
        ap -= take_int
        if ap > 0:
            state.base_luk += ap
            to_luk += ap
            notes.append("INT 達標 → LUK")
        else:
            notes.append("堆 INT")
    state.note_int()
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=Action.BUILD,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            fresh_ap_int=to_int,
            fresh_ap_luk=to_luk,
            fresh_ap_dex=to_dex,
            notes="; ".join(notes),
        )
    )


def _hp_wash_method1(
    state: CharacterState, config: SimulateConfig, *, fresh_ap: int, hp_washes: int
) -> None:
    """Spend up to ``hp_washes`` fresh AP on HP (Method 1); rest → INT/LUK (0 APR)."""
    hp_washes = max(0, min(int(hp_washes), int(fresh_ap)))
    done = 0
    to_int = 0
    to_luk = 0
    hp_gain_total = 0.0
    for _ in range(hp_washes):
        if not state.can_remove_mp(1):
            break
        gain = F.method1_hp_gain(config.hp_mode)
        state.base_hp += gain
        hp_gain_total += gain
        state.base_mp -= F.MP_REMOVED_PER_APR
        i, l = _assign_wash_points(state, config, 1)
        to_int += i
        to_luk += l
        done += 1
    leftover = fresh_ap - done
    leftover_int = leftover_luk = 0
    if leftover > 0:
        leftover_int, leftover_luk = _dump_points(state, config, leftover)

    state.method1_hp_wash_count += done
    if done > 0:
        action = hp_action_for_wash_count(done)
    elif leftover_int:
        action = Action.INT5
    else:
        action = Action.LUK5
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=action,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            fresh_ap_hp=done,
            fresh_ap_int=leftover_int,
            fresh_ap_luk=leftover_luk,
            apr_spent=done,
            notes=(
                f"Method1×{done}（+{hp_gain_total:.1f} HP）；洗回 INT {to_int} LUK {to_luk}"
                + (f"；剩餘 AP → INT {leftover_int} LUK {leftover_luk}" if leftover else "")
            ),
        )
    )


def _mp_wash(
    state: CharacterState, config: SimulateConfig, *, fresh_ap: int, mp_washes: int
) -> None:
    mp_washes = max(0, min(int(mp_washes), int(fresh_ap)))
    done = 0
    to_int = 0
    to_luk = 0
    net_mp = 0.0
    for _ in range(mp_washes):
        gain = F.fresh_ap_mp_gain(state.base_int, config.hp_mode)
        state.base_mp += gain
        if state.extra_mp() < F.MP_REMOVED_PER_APR:
            state.base_mp -= gain
            break
        state.base_mp -= F.MP_REMOVED_PER_APR
        net_mp += gain - F.MP_REMOVED_PER_APR
        i, l = _assign_wash_points(state, config, 1)
        to_int += i
        to_luk += l
        done += 1
    leftover = fresh_ap - done
    leftover_int = leftover_luk = 0
    if leftover > 0:
        leftover_int, leftover_luk = _dump_points(state, config, leftover)

    state.mp_wash_count += done
    if done > 0:
        action = mp_action_for_wash_count(done)
    elif leftover_int:
        action = Action.INT5
    else:
        action = Action.LUK5
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=action,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            fresh_ap_mp=done,
            fresh_ap_int=leftover_int,
            fresh_ap_luk=leftover_luk,
            apr_spent=done,
            notes=(
                f"MP wash×{done}（淨增 MP {net_mp:.1f}）；→ INT {to_int} LUK {to_luk}"
                + (f"；剩餘 AP → INT {leftover_int} LUK {leftover_luk}" if leftover else "")
            ),
        )
    )


def _dump_points(state: CharacterState, config: SimulateConfig, points: int) -> tuple[int, int]:
    to_int = min(points, _int_room(state, config))
    to_luk = points - to_int
    state.base_int += to_int
    state.base_luk += to_luk
    state.note_int()
    return to_int, to_luk


def _dump_fresh_ap_to_int_or_luk(
    state: CharacterState, config: SimulateConfig, *, points: int
) -> None:
    to_int, to_luk = _dump_points(state, config, points)
    action = Action.INT5 if to_int >= to_luk else Action.LUK5
    if to_int and to_luk:
        action = Action.INT5
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=action,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            fresh_ap_int=to_int,
            fresh_ap_luk=to_luk,
            apr_spent=0,
            notes=f"不足時全點 INT {to_int} LUK {to_luk}（本等 0 wash APR）",
        )
    )


def _reset_int_to_floor(state: CharacterState) -> None:
    if state.base_int <= F.BASE_STAT_FLOOR:
        state.int_reset_done = True
        return
    moved = state.base_int - F.BASE_STAT_FLOOR
    state.base_int = F.BASE_STAT_FLOOR
    state.base_luk += moved
    state.int_reset_apr += moved
    state.int_reset_done = True
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=Action.RESET_INT,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            apr_spent=moved,
            notes=f"INT → LUK（{moved} APR）",
        )
    )


def _method2_top_up(state: CharacterState, config: SimulateConfig) -> None:
    """Spend Extra MP via Method 2 until target HP or Extra MP exhausted."""
    target = config.target_hp - config.quest_equip_hp
    washes = 0
    hp_gained = 0.0
    while state.base_hp + 1e-9 < target and state.can_remove_mp(1):
        gain = F.method2_hp_gain(config.hp_mode)
        state.base_hp += gain
        state.base_mp -= F.MP_REMOVED_PER_APR
        hp_gained += gain
        washes += 1
    if washes == 0:
        return
    state.method2_hp_wash_count += washes
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=Action.M2,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            apr_spent=washes,
            notes=f"Method2×{washes}（+{hp_gained:.1f} HP）",
        )
    )
