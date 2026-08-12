"""Level-by-level multi-job HP/MP wash simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from hp_wash_thief.core import formulas as F
from hp_wash_thief.core.gear import total_int
from hp_wash_thief.core.jobs import (
    FirstJobStat,
    JobProfile,
    PrimaryStat,
    SkillTracker,
    get_job_profile,
    make_skill_tracker,
)
from hp_wash_thief.core.models import (
    Action,
    AprBreakdown,
    HP_ACTIONS,
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
    skill: SkillTracker = field(default_factory=SkillTracker)
    profile: Optional[JobProfile] = None

    def note_int(self) -> None:
        if self.base_int > self.base_int_peak:
            self.base_int_peak = self.base_int

    def extra_mp(self) -> float:
        assert self.profile is not None
        return self.profile.extra_mp(self.base_mp, self.level)

    def can_remove_mp(
        self, times: int = 1, *, mp_floor: Optional[int] = None
    ) -> bool:
        """True if Extra MP allows removing MP for HP wash.

        ``mp_floor`` (optional ``target_mp``) stops removes that would drop
        ``base_mp`` below the floor. Not used for MP-wash net stacking.
        """
        assert self.profile is not None
        removed = self.profile.mp_removed_per_apr * times
        if self.extra_mp() < removed:
            return False
        if mp_floor is not None and self.base_mp - removed + 1e-9 < mp_floor:
            return False
        return True


def simulate(config: SimulateConfig) -> SimulateResult:
    _validate_config(config)
    profile = get_job_profile(config.job)
    skill = make_skill_tracker(profile, override_level=config.improved_maxhp_level)

    if config.resume_from is None:
        state = CharacterState(profile=profile, skill=skill)
        _apply_starting_ap(state, config)
        _maybe_mark_int_reached(state, config)
        start_loop = 2
    else:
        state = _seed_from_resume(config.resume_from, config, profile, skill)
        _append_resume_marker(state, config)
        _maybe_mark_int_reached(state, config)
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

    if not state.int_reset_done and state.base_int > F.BASE_STAT_FLOOR:
        _reset_int_to_floor(state, config)

    display_hp = state.base_hp + config.quest_equip_hp
    apr = AprBreakdown(
        mp_wash_count=state.mp_wash_count,
        method1_hp_wash_count=state.method1_hp_wash_count,
        method2_hp_wash_count=state.method2_hp_wash_count,
        int_reset_apr=state.int_reset_apr,
    )
    assert config.extra_mp_threshold is not None
    hp_ok = display_hp + 1e-9 >= config.target_hp
    mp_ok = config.target_mp is None or state.base_mp + 1e-9 >= config.target_mp
    return SimulateResult(
        policy=config.policy,
        target_base_int=config.target_base_int,
        int_reached_level=state.int_reached_level,
        mp_wash_end=config.mp_wash_end,
        extra_mp_threshold=config.extra_mp_threshold,
        int_gear_after_reset=config.int_gear_after_reset,
        final_base_hp=int(round(state.base_hp)),
        final_display_hp=int(round(display_hp)),
        final_base_mp=int(round(state.base_mp)),
        base_int_peak=state.base_int_peak,
        reached_target=hp_ok and mp_ok,
        apr=apr,
        plan=state.plan,
        resume_from=config.resume_from,
        job=config.job,
        improved_maxhp_level=state.skill.effective_level if profile.maxhp_skill else None,
        target_mp=config.target_mp,
    )


def _validate_config(config: SimulateConfig) -> None:
    profile = get_job_profile(config.job)
    if config.target_hp <= 0:
        raise ValueError("target_hp must be positive")
    if not (1 < config.int_reset_level <= config.max_level):
        raise ValueError("int_reset_level out of range")
    if not (30 < config.mp_wash_end <= config.int_reset_level):
        raise ValueError("mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level")
    if config.target_base_int < F.BASE_STAT_FLOOR:
        raise ValueError("target_base_int too low")
    if config.extra_mp_threshold is not None and config.extra_mp_threshold < 0:
        raise ValueError("extra_mp_threshold must be >= 0")
    if config.int_gear_after_reset < 0:
        raise ValueError("int_gear_after_reset must be >= 0")
    if config.improved_maxhp_level is not None and not (0 <= config.improved_maxhp_level <= 10):
        raise ValueError("improved_maxhp_level must be in [0, 10]")
    if config.target_mp is not None:
        floor = profile.min_mp(config.max_level)
        if config.target_mp < floor:
            raise ValueError(
                f"target_mp below job min_mp at max_level (min={floor})"
            )
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


def _seed_from_resume(
    resume: ResumeFrom,
    config: SimulateConfig,
    profile: JobProfile,
    skill: SkillTracker,
) -> CharacterState:
    fresh = resume.fresh_ap if resume.fresh_ap is not None else F.FRESH_AP_PER_LEVEL
    peak = resume.base_int_peak if resume.base_int_peak is not None else resume.base_int
    # Replay SP schedule up to current level unless overridden.
    if skill.override_level is None:
        adv_map = {lv: adv for lv, (adv, _) in profile.job_advances.items()}
        skill.seed_for_resume(resume.level, adv_map)
    else:
        skill.skill_level = skill.effective_level
        skill.unlocked = True
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
        profile=profile,
        skill=skill,
    )


def _append_resume_marker(state: CharacterState, config: SimulateConfig) -> None:
    fresh = state.level_fresh_ap
    skill_note = ""
    if state.profile and state.profile.maxhp_skill:
        skill_note = f"｜ImproveMaxHP Lv{state.skill.effective_level}"
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
                + skill_note
                + ("｜INT 已洗回" if state.int_reset_done else "")
            ),
        )
    )


def _maybe_mark_int_reached(state: CharacterState, config: SimulateConfig) -> None:
    if state.int_reached_level == 0 and state.base_int >= config.target_base_int:
        state.int_reached_level = state.level


def _apply_starting_ap(state: CharacterState, config: SimulateConfig) -> None:
    """Level 1: put all creation AP into INT."""
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
    assert state.profile is not None
    profile = state.profile
    t_int = total_int(
        state.base_int,
        config.int_gear,
        new_level,
        mw_percent=config.mw_percent,
        mw_from_level=config.mw_from_level,
        int_reset_level=config.int_reset_level,
        int_gear_after_reset=config.int_gear_after_reset,
    )
    # Apply job advance first so skill unlock + SP for this level see the new adv.
    adv_info = profile.adv_at_level(new_level)
    if adv_info is not None:
        adv_number, spec = adv_info
        state.skill.on_job_advance(adv_number)

    # Natural gains use skill bonus at current skill level (after unlock this level).
    # SP for this level is granted after advance unlock so MaxHP can start same level.
    if adv_info is not None:
        state.skill.on_level(new_level, adv_number=adv_info[0])
    else:
        # Still grant SP if already unlocked on a non-advance level.
        current_adv = _current_adv_number(profile, new_level)
        state.skill.on_level(new_level, adv_number=current_adv)

    hp_gain = profile.levelup_hp(level=new_level, mode=config.hp_mode, skill=state.skill)
    mp_gain = profile.levelup_mp_base(level=new_level, mode=config.hp_mode)
    mp_gain += F.levelup_mp_int_bonus(t_int)
    state.base_hp += hp_gain
    state.base_mp += mp_gain
    state.level = new_level
    state.level_fresh_ap = F.FRESH_AP_PER_LEVEL

    if adv_info is not None:
        adv_number, spec = adv_info
        hp_b, mp_b = spec.bonus(config.hp_mode)
        state.base_hp += hp_b
        state.base_mp += mp_b
        state.level_fresh_ap += spec.ap_bonus


def _current_adv_number(profile: JobProfile, level: int) -> Optional[int]:
    current = None
    for lv, (adv, _) in sorted(profile.job_advances.items()):
        if lv <= level:
            current = adv
    return current


def _maybe_reset_int(state: CharacterState, config: SimulateConfig) -> None:
    if (
        not state.int_reset_done
        and state.level >= config.int_reset_level
        and state.base_int > F.BASE_STAT_FLOOR
    ):
        _reset_int_to_floor(state, config)


def _decide_action(state: CharacterState, config: SimulateConfig) -> Action:
    assert state.profile is not None
    level = state.level
    if _in_hardcore_early_phase(state, config):
        return mp_wash_hardcore.choose_level_action(state.level)
    if level <= 30:
        return Action.BUILD
    if _in_early_phase(state, config):
        if config.policy is PolicyName.INT_ONLY_PLAIN:
            return Action.BUILD if level <= 30 else Action.INT5
        return choose_early_action(
            config.policy,
            state.extra_mp(),
            config.extra_mp_threshold or state.profile.default_extra_mp_threshold(),
            level=level,
            fresh_ap=state.level_fresh_ap,
            base_int=state.base_int,
            base_mp=state.base_mp,
            hp_mode=config.hp_mode,
        )
    if level <= config.mp_wash_end:
        return Action.MP5
    # Prefer Method2 classes: dump fresh AP to primary; HP comes from Method2 top-up.
    if state.profile.prefer_method2:
        return _primary_dump_action(state.profile)
    return Action.HP5


def _primary_dump_action(profile: JobProfile) -> Action:
    if profile.primary_stat is PrimaryStat.STR:
        return Action.STR5
    if profile.primary_stat is PrimaryStat.DEX:
        return Action.DEX5
    return Action.LUK5


def _in_hardcore_early_phase(state: CharacterState, config: SimulateConfig) -> bool:
    if config.policy is not PolicyName.MP_WASH_HARDCORE:
        return False
    if state.int_reset_done or state.level >= config.int_reset_level:
        return False
    if state.base_int >= config.target_base_int:
        return False
    return state.level >= mp_wash_hardcore.EARLY_START_LEVEL


def _in_early_phase(state: CharacterState, config: SimulateConfig) -> bool:
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
        assert state.profile is not None
        hp_washes = planned_hp_washes(
            action,
            extra_mp=state.extra_mp(),
            fresh_ap=fresh_ap,
            mp_removed_per_apr=state.profile.mp_removed_per_apr,
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
            job=config.job,
        )
        _mp_wash(state, config, fresh_ap=fresh_ap, mp_washes=mp_washes)
        return
    if action is Action.INT5:
        _dump_fresh_ap_to_int_or_primary(state, config, points=fresh_ap)
        return
    if action in {Action.LUK5, Action.STR5, Action.DEX5}:
        _dump_fresh_ap_to_primary_only(state, config, points=fresh_ap, action=action)
        return
    raise ValueError(f"unsupported action: {action}")


def _try_one_hp_wash(state: CharacterState, config: SimulateConfig) -> float:
    assert state.profile is not None
    if not state.can_remove_mp(1, mp_floor=config.target_mp):
        return 0.0
    gain = state.profile.method1_hp(config.hp_mode, skill=state.skill)
    state.base_hp += gain
    state.base_mp -= state.profile.mp_removed_per_apr
    _assign_wash_points(state, config, 1)
    state.method1_hp_wash_count += 1
    return gain


def _try_one_mp_wash(state: CharacterState, config: SimulateConfig) -> float:
    assert state.profile is not None
    gain = state.profile.fresh_ap_mp(state.base_int, config.hp_mode)
    state.base_mp += gain
    if state.extra_mp() < state.profile.mp_removed_per_apr:
        state.base_mp -= gain
        return 0.0
    state.base_mp -= state.profile.mp_removed_per_apr
    net = gain - state.profile.mp_removed_per_apr
    _assign_wash_points(state, config, 1)
    state.mp_wash_count += 1
    return net


def _execute_hardcore_greedy_level(
    state: CharacterState, config: SimulateConfig, *, fresh_ap: int
) -> None:
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

    leftover_int = leftover_pri = 0
    if remaining > 0:
        leftover_int, leftover_pri = _dump_points(state, config, remaining)
        step_notes.append(f"INT {remaining}")

    notes = "greedy: " + " → ".join(step_notes) if step_notes else "greedy: （無）"
    if hp_done:
        notes += f"；M1×{hp_done}（+{hp_gain_total:.1f} HP）"
    if mp_done:
        notes += f"；MP×{mp_done}（淨增 {net_mp_total:.1f} MP）"
    if leftover_int or leftover_pri:
        notes += f"；剩餘 AP → INT {leftover_int} 主屬 {leftover_pri}"

    pri_fields = _primary_fresh_fields(state.profile, leftover_pri)
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
            apr_spent=hp_done + mp_done,
            notes=notes,
            **pri_fields,
        )
    )


def _int_building_allowed(state: CharacterState, config: SimulateConfig) -> bool:
    return (not state.int_reset_done) and state.level < config.int_reset_level


def _int_room(state: CharacterState, config: SimulateConfig) -> int:
    if not _int_building_allowed(state, config):
        return 0
    return max(0, config.target_base_int - state.base_int)


def _add_primary(state: CharacterState, points: int) -> None:
    assert state.profile is not None
    if state.profile.primary_stat is PrimaryStat.STR:
        state.base_str += points
    elif state.profile.primary_stat is PrimaryStat.DEX:
        state.base_dex += points
    else:
        state.base_luk += points


def _primary_fresh_fields(profile: Optional[JobProfile], points: int) -> dict:
    if profile is None or points <= 0:
        return {}
    if profile.primary_stat is PrimaryStat.STR:
        return {"fresh_ap_str": points}
    if profile.primary_stat is PrimaryStat.DEX:
        return {"fresh_ap_dex": points}
    return {"fresh_ap_luk": points}


def _primary_name(profile: JobProfile) -> str:
    return profile.primary_stat.value.upper()


def _assign_wash_points(state: CharacterState, config: SimulateConfig, points: int) -> tuple[int, int]:
    """Assign wash return points to INT until target, then primary."""
    to_int = min(points, _int_room(state, config))
    to_pri = points - to_int
    state.base_int += to_int
    _add_primary(state, to_pri)
    state.note_int()
    return to_int, to_pri


def _build_ap(state: CharacterState, config: SimulateConfig, *, ap: int) -> None:
    """Pre-30 build: meet first-job requirement, then stack INT."""
    assert state.profile is not None
    profile = state.profile
    to_dex = to_str = to_int = to_pri = 0
    notes: list[str] = []

    if (
        profile.first_job_stat is not FirstJobStat.NONE
        and state.level < 11
    ):
        if profile.first_job_stat is FirstJobStat.DEX:
            need = max(0, profile.first_job_requirement - state.base_dex)
            if need > 0:
                if state.base_int < 20:
                    int_need = 20 - state.base_int
                    take_int = min(ap, int_need)
                    state.base_int += take_int
                    to_int += take_int
                    ap -= take_int
                take = min(ap, need)
                state.base_dex += take
                to_dex += take
                ap -= take
                notes.append("建 DEX／INT")
        elif profile.first_job_stat is FirstJobStat.STR:
            need = max(0, profile.first_job_requirement - state.base_str)
            if need > 0:
                take = min(ap, need)
                state.base_str += take
                to_str += take
                ap -= take
                notes.append("建 STR")

    if ap > 0:
        room = _int_room(state, config)
        take_int = min(ap, room)
        state.base_int += take_int
        to_int += take_int
        ap -= take_int
        if ap > 0:
            _add_primary(state, ap)
            to_pri += ap
            notes.append(f"INT 達標 → {_primary_name(profile)}")
        else:
            notes.append("堆 INT")
    state.note_int()
    fresh_ap_dex = to_dex
    fresh_ap_str = to_str
    fresh_ap_luk = 0
    if profile.primary_stat is PrimaryStat.DEX:
        fresh_ap_dex += to_pri
    elif profile.primary_stat is PrimaryStat.STR:
        fresh_ap_str += to_pri
    else:
        fresh_ap_luk = to_pri
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
            fresh_ap_dex=fresh_ap_dex,
            fresh_ap_str=fresh_ap_str,
            fresh_ap_luk=fresh_ap_luk,
            notes="; ".join(notes) if notes else "BUILD",
        )
    )


def _hp_wash_method1(
    state: CharacterState, config: SimulateConfig, *, fresh_ap: int, hp_washes: int
) -> None:
    assert state.profile is not None
    hp_washes = max(0, min(int(hp_washes), int(fresh_ap)))
    done = 0
    to_int = to_pri = 0
    hp_gain_total = 0.0
    removed = state.profile.mp_removed_per_apr
    for _ in range(hp_washes):
        if not state.can_remove_mp(1, mp_floor=config.target_mp):
            break
        gain = state.profile.method1_hp(config.hp_mode, skill=state.skill)
        state.base_hp += gain
        hp_gain_total += gain
        state.base_mp -= removed
        i, p = _assign_wash_points(state, config, 1)
        to_int += i
        to_pri += p
        done += 1
    leftover = fresh_ap - done
    leftover_int = leftover_pri = 0
    if leftover > 0:
        leftover_int, leftover_pri = _dump_points(state, config, leftover)

    state.method1_hp_wash_count += done
    if done > 0:
        action = hp_action_for_wash_count(done)
    elif leftover_int:
        action = Action.INT5
    else:
        action = _primary_dump_action(state.profile)
    pri_name = _primary_name(state.profile)
    pri_fields = _primary_fresh_fields(state.profile, leftover_pri)
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
            apr_spent=done,
            notes=(
                f"Method1×{done}（+{hp_gain_total:.1f} HP）；洗回 INT {to_int} {pri_name} {to_pri}"
                + (
                    f"；剩餘 AP → INT {leftover_int} {pri_name} {leftover_pri}"
                    if leftover
                    else ""
                )
            ),
            **pri_fields,
        )
    )


def _mp_wash(
    state: CharacterState, config: SimulateConfig, *, fresh_ap: int, mp_washes: int
) -> None:
    assert state.profile is not None
    mp_washes = max(0, min(int(mp_washes), int(fresh_ap)))
    done = 0
    to_int = to_pri = 0
    net_mp = 0.0
    removed = state.profile.mp_removed_per_apr
    for _ in range(mp_washes):
        gain = state.profile.fresh_ap_mp(state.base_int, config.hp_mode)
        state.base_mp += gain
        if state.extra_mp() < removed:
            state.base_mp -= gain
            break
        state.base_mp -= removed
        net_mp += gain - removed
        i, p = _assign_wash_points(state, config, 1)
        to_int += i
        to_pri += p
        done += 1
    leftover = fresh_ap - done
    leftover_int = leftover_pri = 0
    if leftover > 0:
        leftover_int, leftover_pri = _dump_points(state, config, leftover)

    state.mp_wash_count += done
    if done > 0:
        action = mp_action_for_wash_count(done)
    elif leftover_int:
        action = Action.INT5
    else:
        action = _primary_dump_action(state.profile)
    pri_name = _primary_name(state.profile)
    pri_fields = _primary_fresh_fields(state.profile, leftover_pri)
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
            apr_spent=done,
            notes=(
                f"MP wash×{done}（淨增 MP {net_mp:.1f}）；→ INT {to_int} {pri_name} {to_pri}"
                + (
                    f"；剩餘 AP → INT {leftover_int} {pri_name} {leftover_pri}"
                    if leftover
                    else ""
                )
            ),
            **pri_fields,
        )
    )


def _dump_points(state: CharacterState, config: SimulateConfig, points: int) -> tuple[int, int]:
    to_int = min(points, _int_room(state, config))
    to_pri = points - to_int
    state.base_int += to_int
    _add_primary(state, to_pri)
    state.note_int()
    return to_int, to_pri


def _dump_fresh_ap_to_int_or_primary(
    state: CharacterState, config: SimulateConfig, *, points: int
) -> None:
    assert state.profile is not None
    to_int, to_pri = _dump_points(state, config, points)
    if to_int and not to_pri:
        action = Action.INT5
    elif to_pri and not to_int:
        action = _primary_dump_action(state.profile)
    else:
        action = Action.INT5
    pri_name = _primary_name(state.profile)
    pri_fields = _primary_fresh_fields(state.profile, to_pri)
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
            apr_spent=0,
            notes=f"全點 INT {to_int} {pri_name} {to_pri}（本等 0 wash APR）",
            **pri_fields,
        )
    )


def _dump_fresh_ap_to_primary_only(
    state: CharacterState, config: SimulateConfig, *, points: int, action: Action
) -> None:
    assert state.profile is not None
    _add_primary(state, points)
    pri_name = _primary_name(state.profile)
    pri_fields = _primary_fresh_fields(state.profile, points)
    state.plan.append(
        LevelPlanRow(
            level=state.level,
            action=action,
            base_int=state.base_int,
            base_luk=state.base_luk,
            base_hp=int(round(state.base_hp)),
            base_mp=int(round(state.base_mp)),
            extra_mp=int(round(state.extra_mp())),
            apr_spent=0,
            notes=f"本等 AP → {pri_name} {points}（HP 靠 Method2；0 wash APR）",
            **pri_fields,
        )
    )


def _reset_int_to_floor(state: CharacterState, config: SimulateConfig) -> None:
    assert state.profile is not None
    if state.base_int <= F.BASE_STAT_FLOOR:
        state.int_reset_done = True
        return
    moved = state.base_int - F.BASE_STAT_FLOOR
    state.base_int = F.BASE_STAT_FLOOR
    _add_primary(state, moved)
    state.int_reset_apr += moved
    state.int_reset_done = True
    pri_name = _primary_name(state.profile)
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
            notes=f"INT → {pri_name}（{moved} APR）",
        )
    )


def _method2_top_up(state: CharacterState, config: SimulateConfig) -> None:
    assert state.profile is not None
    target = config.target_hp - config.quest_equip_hp
    washes = 0
    hp_gained = 0.0
    removed = state.profile.mp_removed_per_apr
    while state.base_hp + 1e-9 < target and state.can_remove_mp(
        1, mp_floor=config.target_mp
    ):
        gain = state.profile.method2_hp(config.hp_mode, skill=state.skill)
        state.base_hp += gain
        state.base_mp -= removed
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
            notes=(
                f"Method2×{washes}（+{hp_gained:.1f} HP；"
                f"ImproveMaxHP Lv{state.skill.effective_level}）"
                if state.profile.maxhp_skill
                else f"Method2×{washes}（+{hp_gained:.1f} HP）"
            ),
        )
    )
