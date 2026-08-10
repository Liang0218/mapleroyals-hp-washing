"""UI user error message tests."""

from __future__ import annotations

from hp_wash_thief.ui.user_errors import format_user_error


def test_format_user_error_chinese_validation_passthrough():
    exc = ValueError("「目標 HP」必須是整數")
    assert format_user_error(exc) == "「目標 HP」必須是整數"


def test_format_user_error_simulator_messages():
    assert (
        format_user_error(ValueError("target_hp must be positive"))
        == "目標 HP 必須大於 0。"
    )
    assert "30 < 等級" in format_user_error(
        ValueError("mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level")
    )


def test_format_user_error_gear_segments():
    msg = format_user_error(ValueError("no INT gear segments before int_reset_level"))
    assert "裝備 Equipment" in msg


def test_format_user_error_equipment_row():
    exc = ValueError("「Wooden Wand」的 INT／穿戴等級必須是整數")
    assert format_user_error(exc) == exc.args[0]
