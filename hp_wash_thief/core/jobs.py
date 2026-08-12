"""Multi-job wash profiles and Improve MaxHP skill tracking.

Sources:
- https://royals.ms/forum/threads/hp-washing-for-new-players.41129/
- https://royals.ms/forum/threads/mapleroyals-skill-library.209540/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from hp_wash_thief.core.models import HpMode, PolicyName
from hp_wash_thief.core.formulas import pick_range


class JobId(str, Enum):
    THIEF = "thief"
    BOWMAN = "bowman"
    GUNSLINGER = "gunslinger"
    BRAWLER = "brawler"
    FIGHTER = "fighter"
    PAGE = "page"
    SPEARMAN = "spearman"
    BEGINNER = "beginner"


class PrimaryStat(str, Enum):
    STR = "str"
    DEX = "dex"
    LUK = "luk"


class FirstJobStat(str, Enum):
    STR = "str"
    DEX = "dex"
    NONE = "none"


@dataclass(frozen=True)
class GainRange:
    low: float
    high: float

    def pick(self, mode: HpMode) -> float:
        return pick_range(self.low, self.high, mode)


@dataclass(frozen=True)
class JobAdvanceSpec:
    """HP/MP granted when reaching this advancement (midpoint ±50 historically)."""

    hp_mid: float
    mp_mid: float
    ap_bonus: int = 0

    def bonus(self, mode: HpMode) -> tuple[float, float]:
        # Guides list midpoints; apply ±50 when min/max requested.
        spread = 50.0
        if mode is HpMode.MIN:
            return self.hp_mid - spread, max(0.0, self.mp_mid - spread)
        if mode is HpMode.MAX:
            return self.hp_mid + spread, self.mp_mid + spread
        return self.hp_mid, self.mp_mid


@dataclass(frozen=True)
class MaxHpSkillSpec:
    """Improve MaxHP Increase / Improve MaxHP (no SP-reset exploit)."""

    unlock_adv: int  # job advance number that unlocks the skill tree
    prereq_sp: int  # SP sunk into prerequisite before MaxHP skill
    max_level: int = 10
    levelup_bonus_per_level: int = 0  # +HP on natural level-up per skill level
    ap_bonus_per_level: int = 0  # +HP when AP applied to HP (M1 and M2)
    sp_per_level: int = 3


@dataclass
class SkillTracker:
    """Tracks Improve MaxHP skill level from SP schedule (or a fixed override)."""

    spec: Optional[MaxHpSkillSpec] = None
    prereq_spent: int = 0
    skill_level: int = 0
    unlocked: bool = False
    override_level: Optional[int] = None

    def on_job_advance(self, adv_number: int) -> None:
        if self.spec is None:
            return
        if adv_number >= self.spec.unlock_adv:
            self.unlocked = True

    def on_level(self, level: int, *, adv_number: Optional[int]) -> None:
        """Grant SP for this level once first job (or unlock) is active."""
        if self.spec is None or self.override_level is not None:
            return
        if not self.unlocked:
            return
        # SP starts after (and including) the unlock advancement level.
        self._spend(self.spec.sp_per_level)

    def seed_for_resume(self, level: int, job_advances: dict[int, int]) -> None:
        """Replay SP from unlock to ``level`` inclusive (for mid-game resume)."""
        if self.spec is None or self.override_level is not None:
            if self.override_level is not None:
                self.skill_level = max(0, min(self.override_level, self.spec.max_level if self.spec else 10))
            return
        unlock_level = None
        for lv, adv in sorted(job_advances.items()):
            if adv >= self.spec.unlock_adv:
                unlock_level = lv
                break
        if unlock_level is None or level < unlock_level:
            return
        self.unlocked = True
        for _ in range(unlock_level, level + 1):
            self._spend(self.spec.sp_per_level)

    def _spend(self, sp: int) -> None:
        assert self.spec is not None
        remaining = sp
        while remaining > 0:
            if self.prereq_spent < self.spec.prereq_sp:
                take = min(remaining, self.spec.prereq_sp - self.prereq_spent)
                self.prereq_spent += take
                remaining -= take
                continue
            if self.skill_level >= self.spec.max_level:
                break
            take = min(remaining, self.spec.max_level - self.skill_level)
            self.skill_level += take
            remaining -= take
            # leftover SP goes to other skills (ignored)

    @property
    def effective_level(self) -> int:
        if self.override_level is not None:
            max_lv = self.spec.max_level if self.spec else 10
            return max(0, min(int(self.override_level), max_lv))
        return self.skill_level

    def levelup_hp_bonus(self) -> int:
        if self.spec is None:
            return 0
        return self.effective_level * self.spec.levelup_bonus_per_level

    def ap_hp_bonus(self) -> int:
        if self.spec is None:
            return 0
        return self.effective_level * self.spec.ap_bonus_per_level


@dataclass(frozen=True)
class JobProfile:
    job: JobId
    display_name_zh: str
    min_mp_fn: Callable[[int], int]
    mp_removed_per_apr: int
    method1_base: GainRange  # without Improve MaxHP
    method2_base: GainRange
    levelup_hp_beginner: GainRange
    levelup_hp_jobbed: GainRange  # without Improve MaxHP
    levelup_mp_beginner: GainRange
    levelup_mp_jobbed: GainRange
    fresh_ap_mp_base: GainRange  # before base_int//10
    job_advances: dict[int, tuple[int, JobAdvanceSpec]]  # level -> (adv_number, spec)
    first_job_stat: FirstJobStat
    first_job_requirement: int
    primary_stat: PrimaryStat
    prefer_method2: bool
    policies: tuple[PolicyName, ...]
    maxhp_skill: Optional[MaxHpSkillSpec] = None
    # Natural level-up uses beginner ranges for levels < this value.
    # Explorers: 11 so lv≤10 match legacy ``is_beginner = level <= 10``.
    beginner_until_level: int = 11
    # Pirate MP wash has larger deficit (~5); others ~1 via (10-12)-12.
    # Net is emergent from fresh_ap_mp_base - mp_removed.

    def min_mp(self, level: int) -> int:
        if level < 1:
            raise ValueError("level must be >= 1")
        return self.min_mp_fn(level)

    def extra_mp(self, base_mp: float, level: int) -> float:
        return float(base_mp) - float(self.min_mp(level))

    def default_extra_mp_threshold(self) -> int:
        return self.mp_removed_per_apr * 5

    def method1_hp(self, mode: HpMode, *, skill: SkillTracker) -> float:
        return self.method1_base.pick(mode) + skill.ap_hp_bonus()

    def method2_hp(self, mode: HpMode, *, skill: SkillTracker) -> float:
        return self.method2_base.pick(mode) + skill.ap_hp_bonus()

    def levelup_hp(self, *, level: int, mode: HpMode, skill: SkillTracker) -> float:
        # Levels strictly below beginner_until_level use beginner ranges.
        if level < self.beginner_until_level:
            base = self.levelup_hp_beginner.pick(mode)
        else:
            base = self.levelup_hp_jobbed.pick(mode)
        return base + skill.levelup_hp_bonus()

    def levelup_mp_base(self, *, level: int, mode: HpMode) -> float:
        if level < self.beginner_until_level:
            return self.levelup_mp_beginner.pick(mode)
        return self.levelup_mp_jobbed.pick(mode)

    def fresh_ap_mp(self, base_int: int, mode: HpMode) -> float:
        return self.fresh_ap_mp_base.pick(mode) + (max(0, int(base_int)) // 10)

    def adv_at_level(self, level: int) -> Optional[tuple[int, JobAdvanceSpec]]:
        return self.job_advances.get(level)


def _thief_advances() -> dict[int, tuple[int, JobAdvanceSpec]]:
    return {
        10: (1, JobAdvanceSpec(162.5, 0.0, 0)),
        30: (2, JobAdvanceSpec(325.0, 175.0, 0)),
        70: (3, JobAdvanceSpec(325.0, 175.0, 5)),
        120: (4, JobAdvanceSpec(325.0, 175.0, 5)),
    }


def _bowman_advances() -> dict[int, tuple[int, JobAdvanceSpec]]:
    return _thief_advances()


def _pirate_advances() -> dict[int, tuple[int, JobAdvanceSpec]]:
    return _thief_advances()


def _fighter_advances() -> dict[int, tuple[int, JobAdvanceSpec]]:
    return {
        10: (1, JobAdvanceSpec(225.0, 0.0, 0)),
        30: (2, JobAdvanceSpec(325.0, 0.0, 0)),
        70: (3, JobAdvanceSpec(325.0, 0.0, 5)),
        120: (4, JobAdvanceSpec(325.0, 0.0, 5)),
    }


def _page_advances() -> dict[int, tuple[int, JobAdvanceSpec]]:
    return {
        10: (1, JobAdvanceSpec(225.0, 0.0, 0)),
        30: (2, JobAdvanceSpec(0.0, 125.0, 0)),
        70: (3, JobAdvanceSpec(0.0, 125.0, 5)),
        120: (4, JobAdvanceSpec(0.0, 125.0, 5)),
    }


def _spearman_advances() -> dict[int, tuple[int, JobAdvanceSpec]]:
    # 2nd–4th: 0 HP / 125 MP (guide); 1st same as warrior 225/0
    return {
        10: (1, JobAdvanceSpec(225.0, 0.0, 0)),
        30: (2, JobAdvanceSpec(0.0, 125.0, 0)),
        70: (3, JobAdvanceSpec(0.0, 125.0, 5)),
        120: (4, JobAdvanceSpec(0.0, 125.0, 5)),
    }


_WARRIOR_MAXHP = MaxHpSkillSpec(
    unlock_adv=1,
    prereq_sp=5,  # Improved HP Recovery 5
    max_level=10,
    levelup_bonus_per_level=4,
    ap_bonus_per_level=3,
)

_BRAWLER_MAXHP = MaxHpSkillSpec(
    unlock_adv=2,
    prereq_sp=0,
    max_level=10,
    levelup_bonus_per_level=3,
    ap_bonus_per_level=2,
)

_THIEF_POLICIES = (
    PolicyName.MP_WASH_SHORTFALL,
    PolicyName.INT_DUMP_SHORTFALL,
    PolicyName.MP_WASH_HARDCORE,
    PolicyName.INT_ONLY_PLAIN,
)
_D_ONLY = (PolicyName.INT_ONLY_PLAIN,)


def _build_profiles() -> dict[JobId, JobProfile]:
    beginner_hp = GainRange(12, 16)
    beginner_mp = GainRange(10, 12)
    explorer_mp_job = GainRange(14, 16)
    thief_m1 = GainRange(20, 24)
    thief_m2 = GainRange(16, 20)
    # Warrior published 50–54 / 50–55 at max skill (+30 AP) → base 20–24 / 20–25
    warrior_m1 = GainRange(20, 24)
    warrior_m2 = GainRange(20, 25)
    # Brawler published 36–40 / 40 at max (+20 AP) → base 16–20 / 20–20
    brawler_m1 = GainRange(16, 20)
    brawler_m2 = GainRange(20, 20)
    bowman_m = GainRange(16, 20)
    gun_m1 = GainRange(16, 20)
    gun_m2 = GainRange(20, 20)
    beginner_wash = GainRange(8, 12)
    # Level-up jobbed bases (skill bonus added separately)
    warrior_lv_hp = GainRange(24, 28)  # +40 at skill 10 → 64–68
    brawler_lv_hp = GainRange(22, 28)  # +30 at skill 10 → 52–58
    pirate_lv_hp = GainRange(22, 28)
    thief_lv_hp = GainRange(20, 24)
    pirate_lv_mp = GainRange(18, 23)
    fresh_mp_std = GainRange(10, 12)
    # Pirate fresh AP→MP same add range; larger -MP creates ~5 deficit
    fresh_mp_pirate = GainRange(10, 12)
    fresh_mp_beginner = GainRange(6, 8)
    fresh_mp_warrior = GainRange(2, 4)

    profiles = {
        JobId.THIEF: JobProfile(
            job=JobId.THIEF,
            display_name_zh="盜賊",
            min_mp_fn=lambda lv: 14 * lv + 148,
            mp_removed_per_apr=12,
            method1_base=thief_m1,
            method2_base=thief_m2,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=thief_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=explorer_mp_job,
            fresh_ap_mp_base=fresh_mp_std,
            job_advances=_thief_advances(),
            first_job_stat=FirstJobStat.DEX,
            first_job_requirement=25,
            primary_stat=PrimaryStat.LUK,
            prefer_method2=False,
            policies=_THIEF_POLICIES,
        ),
        JobId.BOWMAN: JobProfile(
            job=JobId.BOWMAN,
            display_name_zh="弓箭手",
            min_mp_fn=lambda lv: 14 * lv + 148,
            mp_removed_per_apr=12,
            method1_base=bowman_m,
            method2_base=bowman_m,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=thief_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=explorer_mp_job,
            fresh_ap_mp_base=fresh_mp_std,
            job_advances=_bowman_advances(),
            first_job_stat=FirstJobStat.DEX,
            first_job_requirement=25,
            primary_stat=PrimaryStat.DEX,
            prefer_method2=True,
            policies=_D_ONLY,
        ),
        JobId.GUNSLINGER: JobProfile(
            job=JobId.GUNSLINGER,
            display_name_zh="槍手",
            min_mp_fn=lambda lv: 18 * lv + 111,
            mp_removed_per_apr=16,
            method1_base=gun_m1,
            method2_base=gun_m2,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=pirate_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=pirate_lv_mp,
            fresh_ap_mp_base=fresh_mp_pirate,
            job_advances=_pirate_advances(),
            first_job_stat=FirstJobStat.DEX,
            first_job_requirement=20,
            primary_stat=PrimaryStat.DEX,
            prefer_method2=True,
            policies=_D_ONLY,
        ),
        JobId.BRAWLER: JobProfile(
            job=JobId.BRAWLER,
            display_name_zh="打手／Bucc",
            min_mp_fn=lambda lv: 18 * lv + 111,
            mp_removed_per_apr=16,
            method1_base=brawler_m1,
            method2_base=brawler_m2,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=brawler_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=pirate_lv_mp,
            fresh_ap_mp_base=fresh_mp_pirate,
            job_advances=_pirate_advances(),
            first_job_stat=FirstJobStat.DEX,
            first_job_requirement=20,
            primary_stat=PrimaryStat.STR,
            prefer_method2=True,
            policies=_D_ONLY,
            maxhp_skill=_BRAWLER_MAXHP,
        ),
        JobId.FIGHTER: JobProfile(
            job=JobId.FIGHTER,
            display_name_zh="戰士（Fighter）",
            min_mp_fn=lambda lv: 4 * lv + 56,
            mp_removed_per_apr=4,
            method1_base=warrior_m1,
            method2_base=warrior_m2,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=warrior_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=GainRange(4, 6),
            fresh_ap_mp_base=fresh_mp_warrior,
            job_advances=_fighter_advances(),
            first_job_stat=FirstJobStat.STR,
            first_job_requirement=35,
            primary_stat=PrimaryStat.STR,
            prefer_method2=True,
            policies=_D_ONLY,
            maxhp_skill=_WARRIOR_MAXHP,
        ),
        JobId.PAGE: JobProfile(
            job=JobId.PAGE,
            display_name_zh="戰士（Page）",
            min_mp_fn=lambda lv: 4 * lv + 56,
            mp_removed_per_apr=4,
            method1_base=warrior_m1,
            method2_base=warrior_m2,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=warrior_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=GainRange(4, 6),
            fresh_ap_mp_base=fresh_mp_warrior,
            job_advances=_page_advances(),
            first_job_stat=FirstJobStat.STR,
            first_job_requirement=35,
            primary_stat=PrimaryStat.STR,
            prefer_method2=True,
            policies=_D_ONLY,
            maxhp_skill=_WARRIOR_MAXHP,
        ),
        JobId.SPEARMAN: JobProfile(
            job=JobId.SPEARMAN,
            display_name_zh="槍兵（Spearman）",
            min_mp_fn=lambda lv: 4 * lv + 156,
            mp_removed_per_apr=4,
            method1_base=warrior_m1,
            method2_base=warrior_m2,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=warrior_lv_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=GainRange(4, 6),
            fresh_ap_mp_base=fresh_mp_warrior,
            job_advances=_spearman_advances(),
            first_job_stat=FirstJobStat.STR,
            first_job_requirement=35,
            primary_stat=PrimaryStat.STR,
            prefer_method2=True,
            policies=_D_ONLY,
            maxhp_skill=_WARRIOR_MAXHP,
        ),
        JobId.BEGINNER: JobProfile(
            job=JobId.BEGINNER,
            display_name_zh="初心者",
            min_mp_fn=lambda lv: 10 * lv + 2,
            mp_removed_per_apr=8,
            method1_base=beginner_wash,
            method2_base=beginner_wash,
            levelup_hp_beginner=beginner_hp,
            levelup_hp_jobbed=beginner_hp,
            levelup_mp_beginner=beginner_mp,
            levelup_mp_jobbed=beginner_mp,
            fresh_ap_mp_base=fresh_mp_beginner,
            job_advances={},
            first_job_stat=FirstJobStat.NONE,
            first_job_requirement=0,
            primary_stat=PrimaryStat.LUK,
            prefer_method2=True,
            policies=_D_ONLY,
            beginner_until_level=201,
        ),
    }
    return profiles


JOB_PROFILES: dict[JobId, JobProfile] = _build_profiles()


def get_job_profile(job: JobId | str) -> JobProfile:
    if isinstance(job, str):
        job = JobId(job)
    try:
        return JOB_PROFILES[job]
    except KeyError as exc:
        raise ValueError(f"unknown job: {job}") from exc


def make_skill_tracker(
    profile: JobProfile, *, override_level: Optional[int] = None
) -> SkillTracker:
    return SkillTracker(spec=profile.maxhp_skill, override_level=override_level)
