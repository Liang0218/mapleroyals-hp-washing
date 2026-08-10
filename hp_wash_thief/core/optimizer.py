"""Coarse-to-fine multi-policy APR optimizer."""

from __future__ import annotations

from typing import Iterable, Optional

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

    policy_a = by_policy.get(PolicyName.MP_WASH_SHORTFALL)
    policy_b = by_policy.get(PolicyName.INT_DUMP_SHORTFALL)
    policy_c = by_policy.get(PolicyName.MP_WASH_HARDCORE)
    policy_d = by_policy.get(PolicyName.INT_ONLY_PLAIN)
    a_best = policy_a.best if policy_a else None
    b_best = policy_b.best if policy_b else None
    c_best = policy_c.best if policy_c else None
    d_best = policy_d.best if policy_d else None
    comparison = _compare_abcd(a_best, b_best, c_best, d_best)

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
    )


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


def _search(config: OptimizeConfig, policy: PolicyName, *, coarse: bool) -> Iterable[CandidateResult]:
    int_step = 40 if coarse else config.target_base_int_step
    mp_step = 10 if coarse else 5

    int_values = list(
        range(config.target_base_int_min, config.target_base_int_max + 1, int_step)
    )
    if config.target_base_int_max not in int_values:
        int_values.append(config.target_base_int_max)

    mp_min = max(config.mp_wash_end_min, 31)
    mp_max = config.int_reset_level
    if mp_min > mp_max:
        return

    mp_values = list(range(mp_min, mp_max + 1, mp_step))
    if mp_max not in mp_values:
        mp_values.append(mp_max)

    threshold = config.extra_mp_threshold
    for target_base_int in int_values:
        for mp_wash_end in mp_values:
            yield _run(
                config,
                policy,
                target_base_int=target_base_int,
                mp_wash_end=mp_wash_end,
                extra_mp_threshold=threshold,
            )


def _refine_around(
    config: OptimizeConfig, policy: PolicyName, seed: CandidateResult
) -> Iterable[CandidateResult]:
    int_candidates = _neighbors(
        seed.target_base_int,
        low=config.target_base_int_min,
        high=config.target_base_int_max,
        step=config.target_base_int_step,
        radius=2,
    )
    mp_min = max(config.mp_wash_end_min, 31)
    mp_max = config.int_reset_level
    mp_center = min(max(seed.mp_wash_end, mp_min), mp_max)
    mp_candidates = _neighbors(mp_center, low=mp_min, high=mp_max, step=5, radius=2)
    threshold = config.extra_mp_threshold
    for target_base_int in int_candidates:
        for mp_wash_end in mp_candidates:
            yield _run(
                config,
                policy,
                target_base_int=target_base_int,
                mp_wash_end=mp_wash_end,
                extra_mp_threshold=threshold,
            )


def _run(
    config: OptimizeConfig,
    policy: PolicyName,
    *,
    target_base_int: int,
    mp_wash_end: int,
    extra_mp_threshold: int,
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
        c.int_reached_level,
        c.policy.value,
    )


def _compare_abcd(
    a: Optional[CandidateResult],
    b: Optional[CandidateResult],
    c: Optional[CandidateResult],
    d: Optional[CandidateResult],
) -> ComparisonResult:
    """Rank A/B/C/D bests; delta is winner vs runner-up."""
    available = [x for x in (a, b, c, d) if x is not None]
    if not available:
        return ComparisonResult(a, b, c, d, None, None, None)

    ranked = sorted(available, key=_candidate_sort_key)
    winner = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    return ComparisonResult(
        policy_a=a,
        policy_b=b,
        policy_c=c,
        policy_d=d,
        winner=winner,
        apr_delta=(winner.total_apr - runner_up.total_apr) if runner_up else None,
        hp_delta=(winner.final_display_hp - runner_up.final_display_hp) if runner_up else None,
    )
