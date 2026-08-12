"""CLI smoke tests."""

from __future__ import annotations

from hp_wash_thief.cli import main


def test_simulate_cli(tmp_path):
    csv_path = tmp_path / "plan.csv"
    rc = main(
        [
            "simulate",
            "--policy",
            "mp_wash_shortfall",
            "--target-base-int",
            "240",
            "--target-hp",
            "18000",
            "--int-reset-level",
            "130",
            "--int-gear-file",
            "examples/int_gear.json",
            "--mp-wash-end",
            "120",
            "--csv",
            str(csv_path),
        ]
    )
    assert rc in (0, 1)
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert "action" in text.splitlines()[0]
    assert "RESET_INT" in text or "HP5" in text


def test_optimize_cli_fighter_d_only(tmp_path):
    csv_path = tmp_path / "fighter.csv"
    rc = main(
        [
            "optimize",
            "--job",
            "fighter",
            "--target-hp",
            "12000",
            "--int-reset-level",
            "120",
            "--int-gear-file",
            "examples/int_gear.json",
            "--policies",
            "auto",
            "--improved-maxhp-level",
            "10",
            "--csv",
            str(csv_path),
        ]
    )
    assert rc in (0, 1)
    assert csv_path.exists()
