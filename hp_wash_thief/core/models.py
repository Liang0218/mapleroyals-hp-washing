"""Shared dataclasses for configuration and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PolicyName(str, Enum):
    MP_WASH_SHORTFALL = "mp_wash_shortfall"
    INT_DUMP_SHORTFALL = "int_dump_shortfall"


class HpMode(str, Enum):
    AVG = "avg"
    MIN = "min"
    MAX = "max"


class Action(str, Enum):
    NONE = "NONE"
    BUILD = "BUILD"
    HP5 = "HP5"
    MP5 = "MP5"
    INT5 = "INT5"
    LUK5 = "LUK5"
    M2 = "M2"
    RESET_INT = "RESET_INT"


@dataclass(frozen=True)
class IntGearSegment:
    from_level: int
    to_level: int
    int_gear: int
    mw_int: int = 0

    def covers(self, level: int) -> bool:
        return self.from_level <= level <= self.to_level


@dataclass
class OptimizeConfig:
    target_hp: int
    int_reset_level: int
    int_gear: list[IntGearSegment]
    policies: list[PolicyName] = field(
        default_factory=lambda: [PolicyName.MP_WASH_SHORTFALL, PolicyName.INT_DUMP_SHORTFALL]
    )
    quest_equip_hp: int = 0
    hp_mode: HpMode = HpMode.AVG
    max_level: int = 200
    # Search bounds (overridable for tests)
    target_base_int_min: int = 100
    target_base_int_max: int = 500
    target_base_int_step: int = 10
    early_phase_end_min: int = 50
    early_phase_end_max: int = 90
    extra_mp_thresholds: tuple[int, ...] = (48, 60, 72)
    top_n: int = 5


@dataclass
class SimulateConfig:
    policy: PolicyName
    target_base_int: int
    target_hp: int
    int_reset_level: int
    int_gear: list[IntGearSegment]
    early_phase_end: int = 70
    mp_wash_end: int = 135
    extra_mp_threshold: int = 60
    quest_equip_hp: int = 0
    hp_mode: HpMode = HpMode.AVG
    max_level: int = 200
    auto_method2: bool = True


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
    early_phase_end: int
    mp_wash_end: int
    extra_mp_threshold: int
    final_base_hp: int
    final_display_hp: int
    base_int_peak: int
    reached_target: bool
    apr: AprBreakdown
    plan: list[LevelPlanRow] = field(default_factory=list)


@dataclass
class CandidateResult:
    policy: PolicyName
    target_base_int: int
    early_phase_end: int
    mp_wash_end: int
    extra_mp_threshold: int
    final_base_hp: int
    final_display_hp: int
    base_int_peak: int
    reached_target: bool
    apr: AprBreakdown
    plan: list[LevelPlanRow] = field(default_factory=list)

    @property
    def total_apr(self) -> int:
        return self.apr.total_apr

    @classmethod
    def from_simulate(cls, result: SimulateResult) -> "CandidateResult":
        return cls(
            policy=result.policy,
            target_base_int=result.target_base_int,
            early_phase_end=result.early_phase_end,
            mp_wash_end=result.mp_wash_end,
            extra_mp_threshold=result.extra_mp_threshold,
            final_base_hp=result.final_base_hp,
            final_display_hp=result.final_display_hp,
            base_int_peak=result.base_int_peak,
            reached_target=result.reached_target,
            apr=result.apr,
            plan=result.plan,
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
    winner: Optional[CandidateResult]
    apr_delta: Optional[int]  # winner_apr - other_apr (negative means winner cheaper)
    hp_delta: Optional[int]


@dataclass
class OptimizeResult:
    by_policy: dict[PolicyName, PolicyBest]
    comparison: ComparisonResult
    winner: Optional[CandidateResult]
    top_candidates: list[CandidateResult] = field(default_factory=list)
