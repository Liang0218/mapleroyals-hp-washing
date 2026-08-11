"""Shared fixtures for integration / regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from hp_wash_thief.core.gear import load_int_gear


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture(scope="module")
def example_gear():
    return load_int_gear(EXAMPLES / "int_gear.json")


@pytest.fixture(scope="module")
def example_gear_path() -> Path:
    return EXAMPLES / "int_gear.json"
