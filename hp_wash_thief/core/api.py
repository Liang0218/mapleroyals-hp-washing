"""Public core API shared by CLI and future GUI."""

from __future__ import annotations

from hp_wash_thief.core.optimizer import optimize as _optimize
from hp_wash_thief.core.models import OptimizeConfig, OptimizeResult, SimulateConfig, SimulateResult
from hp_wash_thief.core.simulator import simulate as _simulate


def optimize(config: OptimizeConfig) -> OptimizeResult:
    """Search policies for the lowest-APR plan that reaches target HP."""
    return _optimize(config)


def simulate(config: SimulateConfig) -> SimulateResult:
    """Run a single parameterized wash plan."""
    return _simulate(config)


__all__ = [
    "optimize",
    "simulate",
    "OptimizeConfig",
    "OptimizeResult",
    "SimulateConfig",
    "SimulateResult",
]
