"""UI resource path helpers."""

from __future__ import annotations

from hp_wash_thief.ui.resources import default_csv_path, default_int_gear_path


def test_default_int_gear_exists():
    path = default_int_gear_path()
    assert path.is_file()
    assert "int_gear" in path.name


def test_default_csv_path_is_csv():
    assert default_csv_path().suffix == ".csv"
