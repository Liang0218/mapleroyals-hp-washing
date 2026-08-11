"""User-facing error messages for the desktop UI (Traditional Chinese)."""

from __future__ import annotations

import re

# Exact English messages from core → 繁中
_EXACT: dict[str, str] = {
    "target_hp must be positive": "目標 HP 必須大於 0。",
    "int_reset_level out of range": "INT 洗回等級超出有效範圍（須為 2–200，且小於等級上限）。",
    "mp_wash_end must satisfy 30 < mp_wash_end <= int_reset_level": (
        "MP wash 結束等級須滿足：30 < 等級 ≤ INT 洗回等級。"
    ),
    "target_base_int too low": "目標 base INT 過低（至少需 4）。",
    "extra_mp_threshold must be >= 0": "Extra MP 門檻不可為負數。",
    "int_gear_after_reset must be >= 0": "INT reset 後 int_gear 不可為負數。",
    "no INT gear segments before int_reset_level": (
        "INT 洗回等級前沒有有效的裝備 INT 區間，請到「裝備 Equipment」分頁檢查設定。"
    ),
    "INT gear must contain at least one segment": "INT 裝備至少需要一個等級區間。",
    "INT gear JSON must be a list of segments": "INT 裝備 JSON 必須是區間陣列格式。",
    "equipment JSON must be a list": "裝備 JSON 必須是陣列格式。",
    "int_gear must be >= 0": "int_gear 不可為負數。",
    "max_level must be >= 1": "等級上限必須 ≥ 1。",
    "沒有可匯出的優勝計畫。": "無優勝方案，無法匯出 CSV。請調整參數後再試，或先取消 CSV 路徑。",
    "resume level out of range": "中途接續等級超出有效範圍。",
    "resume base_hp must be positive": "中途接續的 base HP 必須大於 0。",
    "resume base_mp must be >= 0": "中途接續的 base MP 不可為負數。",
    "resume base_int too low": "中途接續的 base INT 過低（至少需 4）。",
    "resume base_luk too low": "中途接續的 base LUK 過低（至少需 4）。",
    "resume base_dex too low": "中途接續的 base DEX 過低（至少需 4）。",
    "resume fresh_ap must be >= 0": "尚未點的 AP 不可為負數。",
    "int_reset_done but base_int > 4": "已勾選 INT 洗回時，base INT 應為 4。",
    "resume base_int_peak must be >= base_int": "INT 峰值不可小於目前 base INT。",
    "resume requires base_mp or extra_mp": "中途接續請填 base MP（APR 顯示的數值）。",
}

# Substring patterns (regex) → 繁中
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"^「.+」必須是整數$"),
        lambda m: m.group(0),
    ),
    (
        re.compile(r"^「.+」必須是數字$"),
        lambda m: m.group(0),
    ),
    (
        re.compile(r"^「.+」的 INT／穿戴等級必須是整數$"),
        lambda m: m.group(0),
    ),
    (
        re.compile(r"^unknown equipment type: (.+)$"),
        lambda m: f"未知的裝備類型：{m.group(1)}",
    ),
    (
        re.compile(r"^int must be >= 0 for (.+)$"),
        lambda m: f"「{m.group(1)}」的 INT 不可為負數。",
    ),
    (
        re.compile(r"^equip_level must be >= 1 for (.+)$"),
        lambda m: f"「{m.group(1)}」的穿戴等級必須 ≥ 1。",
    ),
    (
        re.compile(r"^overlapping INT gear segments:"),
        lambda _m: "INT 裝備等級區間重疊，請檢查裝備或 INT 洗回等級設定。",
    ),
    (
        re.compile(r"^invalid segment \d+-\d+: from_level > to_level$"),
        lambda _m: "INT 裝備區間無效：起始等級大於結束等級。",
    ),
    (
        re.compile(r"^\[Errno 13\]|Permission denied"),
        lambda _m: "無法寫入 CSV 檔案（權限不足或檔案被其他程式占用）。",
    ),
    (
        re.compile(r"^\[Errno 2\]|No such file"),
        lambda _m: "找不到指定的檔案或路徑。",
    ),
]


def format_user_error(exc: BaseException) -> str:
    """Return a short Traditional Chinese message suitable for messagebox / result panel."""
    raw = str(exc).strip()
    if not raw:
        return "發生未知錯誤。"

    if raw in _EXACT:
        return _EXACT[raw]

    for pattern, repl in _PATTERNS:
        match = pattern.search(raw)
        if match:
            return repl(match) if callable(repl) else repl

    if isinstance(exc, PermissionError):
        return "無法寫入檔案（權限不足或檔案被其他程式占用）。"
    if isinstance(exc, FileNotFoundError):
        return "找不到指定的檔案或路徑。"

    # Already Chinese (UI validation, custom RuntimeError)
    if any("\u4e00" <= ch <= "\u9fff" for ch in raw):
        return raw

    return f"執行失敗：{raw}"
