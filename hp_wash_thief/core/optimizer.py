"""Coarse-to-fine multi-policy APR optimizer."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from hp_wash_thief.core import formulas as F
from hp_wash_thief.core.jobs import get_job_profile
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
    profile = get_job_profile(config.job)
    policies = config.policies or list(profile.policies)
    by_policy: dict[PolicyName, PolicyBest] = {}
    all_feasible: list[CandidateResult] = []

    for policy in policies:
        bests = _optimize_policy(config, policy)
        by_policy[policy] = bests
        all_feasible.extend(c for c in bests.top if c.reached_target)

    all_feasible.sort(key=_candidate_sort_key)
    top_candidates = all_feasible[: config.top_n]

    a_best = _best_of(by_policy, PolicyName.MP_WASH_SHORTFALL)
    b_best = _best_of(by_policy, PolicyName.INT_DUMP_SHORTFALL)
    c_best = _best_of(by_policy, PolicyName.MP_WASH_HARDCORE)
    d_best = _best_of(by_policy, PolicyName.INT_ONLY_PLAIN)
    comparison = _compare_policies(a_best, b_best, c_best, d_best)

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

    if config.resume_from is not None and (config.resume_from.fresh_ap or 0) > F.FRESH_AP_PER_LEVEL:
        clean_ap = config.resume_from.fresh_ap or 0
        # Keep several distinct INT/end-level finalists from the normal search,
        # then optimize the accumulated clean AP against each full continuation.
        resume_seeds: list[CandidateResult] = []
        seen_seed_params: set[tuple[int, int]] = set()
        for seed in sorted(fine_results, key=_candidate_sort_key):
            identity = (seed.target_base_int, seed.mp_wash_end)
            if identity in seen_seed_params:
                continue
            seen_seed_params.add(identity)
            resume_seeds.append(seed)
            if len(resume_seeds) >= max(4, config.top_n):
                break
        if resume_seeds:
            anchor = resume_seeds[0]
            int_lo, int_hi = _int_search_bounds(config)
            ap_reachable_hi = min(int_hi, config.resume_from.base_int + clean_ap)
            target_values = list(range(int_lo, ap_reachable_hi + 1, config.target_base_int_step))
            if ap_reachable_hi not in target_values:
                target_values.append(ap_reachable_hi)
            end_values = list(dict.fromkeys(seed.mp_wash_end for seed in resume_seeds))[:2]
            for target_value in target_values:
                for end_value in end_values:
                    resume_seeds.append(
                        replace(anchor, target_base_int=target_value, mp_wash_end=end_value)
                    )

        allocated: list[CandidateResult] = []
        for seed in resume_seeds:
            int_need = max(0, seed.target_base_int - config.resume_from.base_int)
            for mp_washes in _allocation_grid(clean_ap, 50):
                for hp_washes in _allocation_grid(clean_ap - mp_washes, 50):
                    int_points = min(int_need, clean_ap - mp_washes - hp_washes)
                    for order in ("mp_hp", "hp_mp"):
                        allocated.append(
                            _run(
                                config,
                                policy,
                                target_base_int=seed.target_base_int,
                                mp_wash_end=seed.mp_wash_end,
                                extra_mp_threshold=seed.extra_mp_threshold,
                                protect_target_mp=config.target_mp is not None,
                                resume_clean_int_ap=int_points,
                                resume_clean_mp_washes=mp_washes,
                                resume_clean_hp_washes=hp_washes,
                                resume_clean_wash_order=order,
                            )
                        )
        allocated.sort(key=_candidate_sort_key)
        refined: list[CandidateResult] = []
        for seed in allocated[:3]:
            for mp_washes in _neighbors(seed.resume_clean_mp_washes or 0, low=0, high=clean_ap, step=5, radius=5):
                for hp_washes in _neighbors(
                    seed.resume_clean_hp_washes or 0,
                    low=0,
                    high=max(0, clean_ap - mp_washes),
                    step=5,
                    radius=5,
                ):
                    if mp_washes + hp_washes > clean_ap:
                        continue
                    int_points = min(
                        max(0, seed.target_base_int - config.resume_from.base_int),
                        clean_ap - mp_washes - hp_washes,
                    )
                    for order in ("mp_hp", "hp_mp"):
                        refined.append(
                            _run(
                                config,
                                policy,
                                target_base_int=seed.target_base_int,
                                mp_wash_end=seed.mp_wash_end,
                                extra_mp_threshold=seed.extra_mp_threshold,
                                protect_target_mp=config.target_mp is not None,
                                resume_clean_int_ap=int_points,
                                resume_clean_mp_washes=mp_washes,
                                resume_clean_hp_washes=hp_washes,
                                resume_clean_wash_order=order,
                            )
                        )
        refined.sort(key=_candidate_sort_key)
        for seed in refined[:3]:
            for mp_washes in _neighbors(seed.resume_clean_mp_washes or 0, low=0, high=clean_ap, step=1, radius=4):
                for hp_washes in _neighbors(seed.resume_clean_hp_washes or 0, low=0, high=max(0, clean_ap - mp_washes), step=1, radius=4):
                    if mp_washes + hp_washes > clean_ap:
                        continue
                    int_points = min(max(0, seed.target_base_int - config.resume_from.base_int), clean_ap - mp_washes - hp_washes)
                    for order in ("mp_hp", "hp_mp"):
                        refined.append(
                            _run(
                                config, policy,
                                target_base_int=seed.target_base_int,
                                mp_wash_end=seed.mp_wash_end,
                                extra_mp_threshold=seed.extra_mp_threshold,
                                protect_target_mp=config.target_mp is not None,
                                resume_clean_int_ap=int_points,
                                resume_clean_mp_washes=mp_washes,
                                resume_clean_hp_washes=hp_washes,
                                resume_clean_wash_order=order,
                            )
                        )
        fine_results.extend(allocated)
        fine_results.extend(refined)

    # When the normal strategy cannot meet both goals, test early MP5 washing
    # from each possible start level. Returned AP goes to INT until target INT
    # is reached; the normal strategy then resumes. Thieves A/B already start
    # with Method 1 when MP allows, so this search also evaluates how many of
    # those early Method 1 levels should be followed by MP wash into INT.
    early_mp_fallback = (
        config.target_mp is not None or not any(c.reached_target for c in fine_results)
    ) and (
        (policy is PolicyName.INT_ONLY_PLAIN and config.job != "thief")
        or (config.job == "thief" and policy in {
            PolicyName.MP_WASH_SHORTFALL,
            PolicyName.INT_DUMP_SHORTFALL,
        })
    )
    if early_mp_fallback:
        start_level = max(31, config.resume_from.level if config.resume_from else 31)
        early_candidates: list[CandidateResult] = []
        finalist_limit = max(8, config.top_n)
        int_lo, int_hi = _int_search_bounds(config)
        int_targets = list(range(int_lo, int_hi + 1, config.target_base_int_step))
        if int_hi not in int_targets:
            int_targets.append(int_hi)
        threshold = config.extra_mp_threshold
        if threshold is None:
            threshold = get_job_profile(config.job).default_extra_mp_threshold()

        # Search the full target-INT × start-level space. The best start can be
        # much later than 31 because each MP5 then removes more MP. Use the
        # reset level as the initial wash end; finalists are refined across
        # nearby wash ends below.
        for target_base_int in int_targets:
            for wash_level in range(start_level, config.int_reset_level):
                early_candidates.append(
                    _run(
                        config,
                        policy,
                        target_base_int=target_base_int,
                        mp_wash_end=config.int_reset_level,
                        extra_mp_threshold=threshold,
                        early_mp_wash_level=wash_level,
                    )
                )
                if len(early_candidates) > finalist_limit * 2:
                    early_candidates.sort(key=_candidate_sort_key)
                    del early_candidates[finalist_limit:]
        early_candidates.sort(key=_candidate_sort_key)
        del early_candidates[finalist_limit:]
        # A protected pass can discover a plan whose later M1/M2 washes would
        # otherwise push MP just below its target. Keep the relaxed plans too:
        # when the MP target is impossible, the optimizer still needs a useful
        # best-effort HP result.
        if config.target_mp is not None:
            early_candidates.extend(
                _run(
                    config,
                    policy,
                    target_base_int=seed.target_base_int,
                    mp_wash_end=seed.mp_wash_end,
                    extra_mp_threshold=seed.extra_mp_threshold,
                    early_mp_wash_level=seed.early_mp_wash_level,
                    protect_target_mp=True,
                )
                for seed in list(early_candidates)
            )
        finalists = list(early_candidates)
        for seed in finalists:
            early_candidates.extend(
                _refine_around(
                    config,
                    policy,
                    seed,
                    early_mp_wash_level=seed.early_mp_wash_level,
                    search_all_mp_wash_ends=True,
                )
            )
        if config.job == "thief" and policy in {
            PolicyName.MP_WASH_SHORTFALL,
            PolicyName.INT_DUMP_SHORTFALL,
        }:
            # Also try hybrid early levels: a selected share of AP goes to MP
            # wash and the remainder to Method 1. Search near the best pure
            # fallback schedules, then rank every hybrid by its full APR cost.
            hybrid_seeds = _unique_params(
                sorted(early_candidates, key=_candidate_sort_key)[:finalist_limit]
            )
            for seed in hybrid_seeds:
                seed_level = seed.early_mp_wash_level or start_level
                for mp_points in range(1, 5):
                    for wash_level in _neighbors(
                        seed_level,
                        low=start_level,
                        high=config.int_reset_level - 1,
                        step=1,
                        radius=20,
                    ):
                        for protect_target_mp in (
                            (False, True) if config.target_mp is not None else (False,)
                        ):
                            early_candidates.append(
                                _run(
                                    config,
                                    policy,
                                    target_base_int=seed.target_base_int,
                                    mp_wash_end=seed.mp_wash_end,
                                    extra_mp_threshold=seed.extra_mp_threshold,
                                    early_mp_wash_level=wash_level,
                                    early_mp_wash_points=mp_points,
                                    protect_target_mp=protect_target_mp,
                                )
                            )
        seen_early = {_param_key(c) for c in fine_results}
        for cand in early_candidates:
            key = _param_key(cand)
            if key not in seen_early:
                seen_early.add(key)
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


def _mp_wash_end_candidates(
    config: OptimizeConfig, *, step: int, center: Optional[int] = None, radius: int = 0
) -> list[int]:
    """mp_wash_end grid; on resume, collapse all ends below current level to one sentinel.

    Default min 31 is the earliest legal end: if INT is reached later, that
    candidate does no post-INT MP wash (unlike the old min 50, which still
    forced MP5 through 50 when INT landed earlier).
    """
    mp_min = max(config.mp_wash_end_min, 31)
    mp_max = config.int_reset_level
    if mp_min > mp_max:
        return []
    if center is None:
        values = list(range(mp_min, mp_max + 1, step))
        if mp_max not in values:
            values.append(mp_max)
    else:
        values = _neighbors(
            min(max(center, mp_min), mp_max),
            low=mp_min,
            high=mp_max,
            step=step,
            radius=radius,
        )
    resume = config.resume_from
    if resume is not None and resume.level > mp_min:
        stop_now = max(mp_min, resume.level - 1)
        continued = [v for v in values if v >= resume.level]
        values = sorted(set([stop_now] + continued))
    return values


def _search(
    config: OptimizeConfig,
    policy: PolicyName,
    *,
    coarse: bool,
) -> Iterable[CandidateResult]:
    int_step = 40 if coarse else config.target_base_int_step
    mp_step = 10 if coarse else 5

    int_lo, int_hi = _int_search_bounds(config)
    int_values = list(range(int_lo, int_hi + 1, int_step))
    if int_hi not in int_values:
        int_values.append(int_hi)

    mp_values = _mp_wash_end_candidates(config, step=mp_step)
    if not mp_values:
        return

    threshold = config.extra_mp_threshold
    if threshold is None:
        threshold = get_job_profile(config.job).default_extra_mp_threshold()

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
    config: OptimizeConfig,
    policy: PolicyName,
    seed: CandidateResult,
    *,
    early_mp_wash_level: Optional[int] = None,
    early_mp_wash_points: Optional[int] = None,
    search_all_mp_wash_ends: bool = False,
) -> Iterable[CandidateResult]:
    int_lo, int_hi = _int_search_bounds(config)
    int_candidates = _neighbors(
        seed.target_base_int,
        low=int_lo,
        high=int_hi,
        step=config.target_base_int_step,
        radius=2,
    )
    mp_candidates = (
        _mp_wash_end_candidates(config, step=5)
        if search_all_mp_wash_ends
        else _mp_wash_end_candidates(config, step=5, center=seed.mp_wash_end, radius=2)
    )
    threshold = config.extra_mp_threshold
    if threshold is None:
        threshold = get_job_profile(config.job).default_extra_mp_threshold()

    for target_base_int in int_candidates:
        for mp_wash_end in mp_candidates:
            yield _run(
                config,
                policy,
                target_base_int=target_base_int,
                mp_wash_end=mp_wash_end,
                extra_mp_threshold=threshold,
                early_mp_wash_level=early_mp_wash_level,
                early_mp_wash_points=early_mp_wash_points,
            )


def _run(
    config: OptimizeConfig,
    policy: PolicyName,
    *,
    target_base_int: int,
    mp_wash_end: int,
    extra_mp_threshold: int,
    early_mp_wash_level: Optional[int] = None,
    early_mp_wash_points: Optional[int] = None,
    protect_target_mp: bool = False,
    resume_clean_int_ap: Optional[int] = None,
    resume_clean_mp_washes: Optional[int] = None,
    resume_clean_hp_washes: Optional[int] = None,
    resume_clean_wash_order: str = "mp_hp",
) -> CandidateResult:
    sim = simulate(
        SimulateConfig(
            policy=policy,
            target_base_int=target_base_int,
            target_hp=config.target_hp,
            int_reset_level=config.int_reset_level,
            int_gear=config.int_gear,
            job=config.job,
            mp_wash_end=mp_wash_end,
            extra_mp_threshold=extra_mp_threshold,
            quest_equip_hp=config.quest_equip_hp,
            hp_mode=config.hp_mode,
            max_level=config.max_level,
            auto_method2=True,
            mw_percent=config.mw_percent,
            mw_from_level=config.mw_from_level,
            int_gear_after_reset=config.int_gear_after_reset,
            resume_from=config.resume_from,
            improved_maxhp_level=config.improved_maxhp_level,
            target_mp=config.target_mp if protect_target_mp else None,
            early_mp_wash_level=early_mp_wash_level,
            early_mp_wash_points=early_mp_wash_points,
            resume_clean_int_ap=resume_clean_int_ap,
            resume_clean_mp_washes=resume_clean_mp_washes,
            resume_clean_hp_washes=resume_clean_hp_washes,
            resume_clean_wash_order=resume_clean_wash_order,
        )
    )
    candidate = CandidateResult.from_simulate(sim)
    candidate.target_mp = config.target_mp
    if config.target_mp is not None:
        _annotate_mp_over_cap(candidate.plan)
    candidate.reached_target = (
        candidate.final_display_hp >= config.target_hp
        and (config.target_mp is None or candidate.final_base_mp >= config.target_mp)
    )
    candidate.early_mp_wash_level = early_mp_wash_level
    candidate.early_mp_wash_points = early_mp_wash_points
    candidate.resume_clean_int_ap = resume_clean_int_ap
    candidate.resume_clean_mp_washes = resume_clean_mp_washes
    candidate.resume_clean_hp_washes = resume_clean_hp_washes
    candidate.resume_clean_wash_order = resume_clean_wash_order if resume_clean_mp_washes is not None else None
    return candidate


def _allocation_grid(limit: int, step: int) -> list[int]:
    """Coarse AP allocation grid, always including both endpoints."""
    values = list(range(0, max(0, limit) + 1, step))
    if not values or values[-1] != limit:
        values.append(limit)
    return values


def _annotate_mp_over_cap(plan) -> None:
    warning = "\u26a0 base MP \u8d85\u904e 30,000\uff1b\u5efa\u8b70\u63d0\u65e9\u505a Method 2\u3002"
    for row in plan:
        if row.base_mp > 30_000 and warning not in row.notes:
            row.notes = f"{row.notes} {warning}".strip()


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
        c.early_mp_wash_level,
        c.early_mp_wash_points,
        c.resume_clean_int_ap,
        c.resume_clean_mp_washes,
        c.resume_clean_hp_washes,
        c.resume_clean_wash_order,
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
    """Feasible plans minimize APR; otherwise prioritize HP, then MP, then APR."""
    if c.reached_target:
        return (
            0,
            c.total_apr,
            -c.final_display_hp,
            c.target_base_int,
            c.base_int_peak,
            c.mp_wash_end,
            c.int_reached_level,
            c.policy.value,
        )
    hp_shortfall = max(0, c.target_hp - c.final_display_hp) if c.target_hp is not None else 0
    mp_shortfall = max(0, c.target_mp - c.final_base_mp) if c.target_mp is not None else 0
    return (
        1,
        hp_shortfall,
        mp_shortfall,
        c.total_apr,
        c.target_base_int,
        c.base_int_peak,
        c.mp_wash_end,
        c.int_reached_level,
        c.policy.value,
    )


def _compare_policies(
    a: Optional[CandidateResult],
    b: Optional[CandidateResult],
    c: Optional[CandidateResult],
    d: Optional[CandidateResult],
) -> ComparisonResult:
    """Rank A–D bests; delta is winner vs runner-up."""
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
