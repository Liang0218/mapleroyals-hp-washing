"""Coarse-to-fine multi-policy APR optimizer."""

from __future__ import annotations

from typing import Iterable, Optional

from hp_wash_thief.core import formulas as F
from hp_wash_thief.core.models import (
    CandidateResult,
    ComparisonResult,
    OptimizeConfig,
    OptimizeResult,
    PolicyBest,
    PolicyName,
    SimulateConfig,
)
from hp_wash_thief.core.simulator import simulate


def optimize(config: OptimizeConfig) -> OptimizeResult:
    by_policy: dict[PolicyName, PolicyBest] = {}
    all_feasible: list[CandidateResult] = []

    for policy in config.policies:
        bests = _optimize_policy(config, policy)
        by_policy[policy] = bests
        all_feasible.extend(c for c in bests.top if c.reached_target)

    all_feasible.sort(key=_candidate_sort_key)
    top_candidates = all_feasible[: config.top_n]

    a_best = _best_of(by_policy, PolicyName.MP_WASH_SHORTFALL)
    b_best = _best_of(by_policy, PolicyName.INT_DUMP_SHORTFALL)
    c_best = _best_of(by_policy, PolicyName.MP_WASH_HARDCORE)
    d_best = _best_of(by_policy, PolicyName.INT_ONLY_PLAIN)
    e_best = _best_of(by_policy, PolicyName.DEFERRED_MP_SHORTFALL)
    comparison = _compare_policies(a_best, b_best, c_best, d_best, e_best)

    winner = comparison.winner
    if winner is None and top_candidates:
        winner = top_candidates[0]
    elif winner is None:
        leftovers = [p.best for p in by_policy.values() if p.best is not None]
        leftovers.sort(key=_candidate_sort_key)
        winner = leftovers[0] if leftovers else None

    return OptimizeResult(
        by_policy=by_policy,
        comparison=comparison,
        winner=winner,
        top_candidates=top_candidates,
        resume_from=config.resume_from,
    )


def _best_of(
    by_policy: dict[PolicyName, PolicyBest], policy: PolicyName
) -> Optional[CandidateResult]:
    slot = by_policy.get(policy)
    return slot.best if slot else None


def _optimize_policy(config: OptimizeConfig, policy: PolicyName) -> PolicyBest:
    coarse = list(_search(config, policy, coarse=True))
    seeds = _unique_params(sorted(coarse, key=_candidate_sort_key)[: max(8, config.top_n)])
    fine_results: list[CandidateResult] = []
    seen: set[tuple] = set()

    for seed in seeds:
        for cand in _refine_around(config, policy, seed):
            key = _param_key(cand)
            if key in seen:
                continue
            seen.add(key)
            fine_results.append(cand)

    for cand in coarse:
        key = _param_key(cand)
        if key not in seen:
            seen.add(key)
            fine_results.append(cand)

    fine_results.sort(key=_candidate_sort_key)
    feasible = [c for c in fine_results if c.reached_target]
    pool = feasible if feasible else fine_results
    top = pool[: config.top_n]
    best = top[0] if top else None
    return PolicyBest(policy=policy, best=best, top=top)


def _int_search_bounds(config: OptimizeConfig) -> tuple[int, int]:
    """Clamp INT search to values still meaningful from a mid-game snapshot."""
    lo = config.target_base_int_min
    hi = config.target_base_int_max
    resume = config.resume_from
    if resume is None:
        return lo, hi
    if resume.int_reset_done:
        # Early INT target no longer affects actions; keep a single valid value.
        fixed = max(lo, resume.base_int_peak or resume.base_int, F.BASE_STAT_FLOOR)
        return fixed, fixed
    lo = max(lo, resume.base_int)
    if lo > hi:
        hi = lo
    return lo, hi


def _mp5_start_bounds(config: OptimizeConfig) -> tuple[int, int]:
    lo = config.mp5_start_level_min
    hi = config.mp5_start_level_max
    resume = config.resume_from
    if resume is not None and not resume.int_reset_done:
        # Values below current level are equivalent from here on; collapse them.
        lo = max(lo, resume.level)
    if lo > hi:
        hi = lo
    return lo, hi


def _mp5_start_values(config: OptimizeConfig, *, coarse: bool) -> list[int]:
    step = 10 if coarse else 5
    low, high = _mp5_start_bounds(config)
    values = list(range(low, high + 1, step))
    if high not in values:
        values.append(high)
    return values


def _search(config: OptimizeConfig, policy: PolicyName, *, coarse: bool) -> Iterable[CandidateResult]:
    int_step = 40 if coarse else config.target_base_int_step
    mp_step = 10 if coarse else 5

    int_lo, int_hi = _int_search_bounds(config)
    int_values = list(range(int_lo, int_hi + 1, int_step))
    if int_hi not in int_values:
        int_values.append(int_hi)

    mp_min = max(config.mp_wash_end_min, 31)
    mp_max = config.int_reset_level
    if mp_min > mp_max:
        return

    mp_values = list(range(mp_min, mp_max + 1, mp_step))
    if mp_max not in mp_values:
        mp_values.append(mp_max)

    threshold = config.extra_mp_threshold
    mp5_starts: list[Optional[int]]
    if policy is PolicyName.DEFERRED_MP_SHORTFALL:
        mp5_starts = list(_mp5_start_values(config, coarse=coarse))
    else:
        mp5_starts = [None]

    for target_base_int in int_values:
        for mp_wash_end in mp_values:
            for mp5_start in mp5_starts:
                yield _run(
                    config,
                    policy,
                    target_base_int=target_base_int,
                    mp_wash_end=mp_wash_end,
                    extra_mp_threshold=threshold,
                    mp5_start_level=mp5_start,
                )


def _refine_around(
    config: OptimizeConfig, policy: PolicyName, seed: CandidateResult
) -> Iterable[CandidateResult]:
    int_lo, int_hi = _int_search_bounds(config)
    int_candidates = _neighbors(
        seed.target_base_int,
        low=int_lo,
        high=int_hi,
        step=config.target_base_int_step,
        radius=2,
    )
    mp_min = max(config.mp_wash_end_min, 31)
    mp_max = config.int_reset_level
    mp_center = min(max(seed.mp_wash_end, mp_min), mp_max)
    mp_candidates = _neighbors(mp_center, low=mp_min, high=mp_max, step=5, radius=2)
    threshold = config.extra_mp_threshold

    if policy is PolicyName.DEFERRED_MP_SHORTFALL:
        mp5_lo, mp5_hi = _mp5_start_bounds(config)
        start_center = seed.mp5_start_level or mp5_lo
        mp5_candidates = _neighbors(
            start_center,
            low=mp5_lo,
            high=mp5_hi,
            step=5,
            radius=2,
        )
    else:
        mp5_candidates = [None]

    for target_base_int in int_candidates:
        for mp_wash_end in mp_candidates:
            for mp5_start in mp5_candidates:
                yield _run(
                    config,
                    policy,
                    target_base_int=target_base_int,
                    mp_wash_end=mp_wash_end,
                    extra_mp_threshold=threshold,
                    mp5_start_level=mp5_start,
                )


def _run(
    config: OptimizeConfig,
    policy: PolicyName,
    *,
    target_base_int: int,
    mp_wash_end: int,
    extra_mp_threshold: int,
    mp5_start_level: Optional[int],
) -> CandidateResult:
    sim = simulate(
        SimulateConfig(
            policy=policy,
            target_base_int=target_base_int,
            target_hp=config.target_hp,
            int_reset_level=config.int_reset_level,
            int_gear=config.int_gear,
            mp_wash_end=mp_wash_end,
            extra_mp_threshold=extra_mp_threshold,
            quest_equip_hp=config.quest_equip_hp,
            hp_mode=config.hp_mode,
            max_level=config.max_level,
            auto_method2=True,
            mw_percent=config.mw_percent,
            mw_from_level=config.mw_from_level,
            int_gear_after_reset=config.int_gear_after_reset,
            mp5_start_level=mp5_start_level if mp5_start_level is not None else 50,
            resume_from=config.resume_from,
        )
    )
    return CandidateResult.from_simulate(sim)


def _neighbors(center: int, *, low: int, high: int, step: int, radius: int) -> list[int]:
    values = []
    for i in range(-radius, radius + 1):
        v = center + i * step
        if low <= v <= high:
            values.append(v)
    if center not in values and low <= center <= high:
        values.append(center)
    return sorted(set(values))


def _param_key(c: CandidateResult) -> tuple:
    return (
        c.policy.value,
        c.target_base_int,
        c.mp_wash_end,
        c.extra_mp_threshold,
        c.mp5_start_level,
    )


def _unique_params(cands: list[CandidateResult]) -> list[CandidateResult]:
    seen: set[tuple] = set()
    out: list[CandidateResult] = []
    for c in cands:
        key = _param_key(c)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def _candidate_sort_key(c: CandidateResult) -> tuple:
    return (
        0 if c.reached_target else 1,
        c.total_apr,
        -c.final_display_hp,
        c.target_base_int,
        c.base_int_peak,
        c.mp_wash_end,
        c.mp5_start_level if c.mp5_start_level is not None else 0,
        c.int_reached_level,
        c.policy.value,
    )


def _compare_policies(
    a: Optional[CandidateResult],
    b: Optional[CandidateResult],
    c: Optional[CandidateResult],
    d: Optional[CandidateResult],
    e: Optional[CandidateResult],
) -> ComparisonResult:
    """Rank A–E bests; delta is winner vs runner-up."""
    available = [x for x in (a, b, c, d, e) if x is not None]
    if not available:
        return ComparisonResult(a, b, c, d, e, None, None, None)

    ranked = sorted(available, key=_candidate_sort_key)
    winner = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    return ComparisonResult(
        policy_a=a,
        policy_b=b,
        policy_c=c,
        policy_d=d,
        policy_e=e,
        winner=winner,
        apr_delta=(winner.total_apr - runner_up.total_apr) if runner_up else None,
        hp_delta=(winner.final_display_hp - runner_up.final_display_hp) if runner_up else None,
    )
