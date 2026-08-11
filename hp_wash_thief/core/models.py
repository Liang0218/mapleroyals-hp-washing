"""Shared dataclasses for configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PolicyName(str, Enum):
    MP_WASH_SHORTFALL = "mp_wash_shortfall"
    INT_DUMP_SHORTFALL = "int_dump_shortfall"
    MP_WASH_HARDCORE = "mp_wash_hardcore"
    INT_ONLY_PLAIN = "int_only_plain"


class HpMode(str, Enum):
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class Action(str, Enum):
    NONE = "NONE"
    BUILD = "BUILD"
    HP1 = "HP1"
    HP2 = "HP2"
    HP3 = "HP3"
    HP4 = "HP4"
    HP5 = "HP5"
    MP1 = "MP1"
    MP2 = "MP2"
    MP3 = "MP3"
    MP4 = "MP4"
    MP5 = "MP5"
    HARDCORE_GREEDY = "HARDCORE_GREEDY"
    INT5 = "INT5"
    LUK5 = "LUK5"
    M2 = "M2"
    RESET_INT = "RESET_INT"
    RESUME = "RESUME"


HP_ACTIONS = frozenset(
    {Action.HP1, Action.HP2, Action.HP3, Action.HP4, Action.HP5}
)

MP_ACTIONS = frozenset(
    {Action.MP1, Action.MP2, Action.MP3, Action.MP4, Action.MP5}
)


def hp_action_for_wash_count(count: int) -> Action:
    """Map 1–5 Method 1 washes to HP1…HP5 (6+ also labeled HP5)."""
    if count < 1:
        raise ValueError("wash count must be >= 1")
    if count >= 5:
        return Action.HP5
    return Action(f"HP{count}")


def mp_action_for_wash_count(count: int) -> Action:
    """Map 1–5 MP washes to MP1…MP5 (6+ also labeled MP5)."""
    if count < 1:
        raise ValueError("wash count must be >= 1")
    if count >= 5:
        return Action.MP5
    return Action(f"MP{count}")


def planned_hp_washes(action: Action, *, extra_mp: float, fresh_ap: int) -> int:
    """Resolve HP1…HP5 / HP5 into the wash count for this level."""
    from hp_wash_thief.core import formulas as F

    affordable = F.method1_washes_affordable(extra_mp, fresh_ap)
    if affordable <= 0:
        return 0
    if action is Action.HP5:
        return affordable
    if action in HP_ACTIONS:
        return min(int(action.value[2]), affordable)
    return 0


def planned_mp_washes(
    action: Action,
    *,
    base_int: int,
    base_mp: float,
    level: int,
    fresh_ap: int,
    hp_mode: HpMode,
) -> int:
    """Resolve MP1…MP5 / MP5 into the wash count for this level."""
    from hp_wash_thief.core import formulas as F

    affordable = F.mp_washes_affordable(
        base_int, base_mp, level, fresh_ap, mode=hp_mode
    )
    if affordable <= 0:
        return 0
    if action is Action.MP5:
        return affordable
    if action in MP_ACTIONS:
        return min(int(action.value[2]), affordable)
    return 0


@dataclass(frozen=True)
class IntGearSegment:
    from_level: int
    to_level: int
    int_gear: int

    def covers(self, level: int) -> bool:
        return self.from_level <= level <= self.to_level


@dataclass(frozen=True)
class ResumeFrom:
    """Mid-character snapshot for continuing a wash plan.

    Semantics: character is **already at** ``level`` (natural + job HP/MP for
    this level are already in ``base_hp`` / ``base_mp``). Fresh AP for this
    level has **not** been spent yet. APR counters start at 0 so results report
    **remaining** wash APR from this point forward.
    """

    level: int
    base_hp: float
    base_mp: float
    base_int: int
    base_luk: int = 4
    base_dex: int = 25
    base_str: int = 4
    fresh_ap: Optional[int] = None  # default 5; use 10 at 70/120 if job AP unspent
    int_reset_done: bool = False
    base_int_peak: Optional[int] = None

    @classmethod
    def from_stats(
        cls,
        *,
        level: int,
        base_hp: float,
        base_int: int,
        base_mp: Optional[float] = None,
        extra_mp: Optional[float] = None,
        base_luk: int = 4,
        base_dex: int = 25,
        base_str: int = 4,
        fresh_ap: Optional[int] = None,
        int_reset_done: bool = False,
        base_int_peak: Optional[int] = None,
    ) -> "ResumeFrom":
        """Build from base MP and/or Extra MP (Extra MP = base_mp − min_mp(level))."""
        from hp_wash_thief.core.formulas import min_mp

        if base_mp is None and extra_mp is None:
            raise ValueError("resume requires base_mp or extra_mp")
        if base_mp is None:
            base_mp = float(min_mp(level)) + float(extra_mp)
        return cls(
            level=level,
            base_hp=float(base_hp),
            base_mp=float(base_mp),
            base_int=int(base_int),
            base_luk=int(base_luk),
            base_dex=int(base_dex),
            base_str=int(base_str),
            fresh_ap=fresh_ap,
            int_reset_done=bool(int_reset_done),
            base_int_peak=base_int_peak,
        )


@dataclass
class OptimizeConfig:
    target_hp: int
    int_reset_level: int
    int_gear: list[IntGearSegment]
    policies: list[PolicyName] = field(
        default_factory=lambda: [
            PolicyName.MP_WASH_SHORTFALL,
            PolicyName.INT_DUMP_SHORTFALL,
            PolicyName.MP_WASH_HARDCORE,
            PolicyName.INT_ONLY_PLAIN,
        ]
    )
    quest_equip_hp: int = 0
    hp_mode: HpMode = HpMode.AVG
    max_level: int = 200
    # Maple Warrior: % of base INT added to total INT for level-up MP (not MP wash).
    mw_percent: float = 0.10
    mw_from_level: int = 10
    # Fixed equipment INT from int_reset_level onward (post INT→LUK reset).
    int_gear_after_reset: int = 50
    # Extra MP threshold for early HP wash×5. Fixed at 60 (= 12 MP × 5 APR).
    extra_mp_threshold: int = 60
    # Search bounds (overridable for tests)
    target_base_int_min: int = 100
    target_base_int_max: int = 500
    target_base_int_step: int = 10
    mp_wash_end_min: int = 50
    top_n: int = 5
    # Optional: continue from an in-progress character instead of level 1.
    resume_from: Optional[ResumeFrom] = None


@dataclass
class SimulateConfig:
    policy: PolicyName
    target_base_int: int
    target_hp: int
    int_reset_level: int
    int_gear: list[IntGearSegment]
    mp_wash_end: int = 135
    # 60 = 12 MP removed per APR × 5 fresh AP (one full HP5/MP5 level).
    extra_mp_threshold: int = 60
    quest_equip_hp: int = 0
    hp_mode: HpMode = HpMode.AVG
    max_level: int = 200
    auto_method2: bool = True
    mw_percent: float = 0.10
    mw_from_level: int = 10
    int_gear_after_reset: int = 50
    resume_from: Optional[ResumeFrom] = None


@dataclass
class AprBreakdown:
    mp_wash_count: int = 0
    method1_hp_wash_count: int = 0
    method2_hp_wash_count: int = 0
    int_reset_apr: int = 0

    @property
    def total_apr(self) -> int:
        return (
            self.mp_wash_count
            + self.method1_hp_wash_count
            + self.method2_hp_wash_count
            + self.int_reset_apr
        )


@dataclass
class LevelPlanRow:
    level: int
    action: Action
    base_int: int
    base_luk: int
    base_hp: int
    base_mp: int
    extra_mp: int
    fresh_ap_int: int = 0
    fresh_ap_luk: int = 0
    fresh_ap_dex: int = 0
    fresh_ap_hp: int = 0
    fresh_ap_mp: int = 0
    apr_spent: int = 0
    notes: str = ""


@dataclass
class SimulateResult:
    policy: PolicyName
    target_base_int: int
    int_reached_level: int
    mp_wash_end: int
    extra_mp_threshold: int
    int_gear_after_reset: int
    final_base_hp: int
    final_display_hp: int
    base_int_peak: int
    reached_target: bool
    apr: AprBreakdown
    plan: list[LevelPlanRow] = field(default_factory=list)
    resume_from: Optional[ResumeFrom] = None


@dataclass
class CandidateResult:
    policy: PolicyName
    target_base_int: int
    int_reached_level: int
    mp_wash_end: int
    extra_mp_threshold: int
    int_gear_after_reset: int
    final_base_hp: int
    final_display_hp: int
    base_int_peak: int
    reached_target: bool
    apr: AprBreakdown
    plan: list[LevelPlanRow] = field(default_factory=list)
    resume_from: Optional[ResumeFrom] = None

    @property
    def total_apr(self) -> int:
        return self.apr.total_apr

    @classmethod
    def from_simulate(cls, result: SimulateResult) -> "CandidateResult":
        return cls(
            policy=result.policy,
            target_base_int=result.target_base_int,
            int_reached_level=result.int_reached_level,
            mp_wash_end=result.mp_wash_end,
            extra_mp_threshold=result.extra_mp_threshold,
            int_gear_after_reset=result.int_gear_after_reset,
            final_base_hp=result.final_base_hp,
            final_display_hp=result.final_display_hp,
            base_int_peak=result.base_int_peak,
            reached_target=result.reached_target,
            apr=result.apr,
            plan=result.plan,
            resume_from=result.resume_from,
        )


@dataclass
class PolicyBest:
    policy: PolicyName
    best: Optional[CandidateResult]
    top: list[CandidateResult] = field(default_factory=list)


@dataclass
class ComparisonResult:
    policy_a: Optional[CandidateResult]
    policy_b: Optional[CandidateResult]
    policy_c: Optional[CandidateResult]
    policy_d: Optional[CandidateResult]
    winner: Optional[CandidateResult]
    apr_delta: Optional[int]  # winner_apr - runner_up_apr (negative means winner cheaper)
    hp_delta: Optional[int]


@dataclass
class OptimizeResult:
    by_policy: dict[PolicyName, PolicyBest]
    comparison: ComparisonResult
    winner: Optional[CandidateResult]
    top_candidates: list[CandidateResult] = field(default_factory=list)
    resume_from: Optional[ResumeFrom] = None
