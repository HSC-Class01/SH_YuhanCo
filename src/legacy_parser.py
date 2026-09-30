from __future__ import annotations

import io
import re
import zipfile
from typing import Any

from bs4 import BeautifulSoup

from .normalize import ACCOUNT_ALIASES, clean_label, parse_amount


def _numbers(text: str) -> list[float]:
    vals = []
    for m in re.findall(r"[-(]?[0-9][0-9,]*(?:\.[0-9]+)?\)?", text):
        v = parse_amount(m)
        if v is not None:
            vals.append(v)
    return vals


def _pick_value(values: list[float], period_kind: str, flow: bool) -> float | None:
    if not values:
        return None
    # Legacy DART income/cash-flow tables commonly show:
    # current 3-month, current cumulative, prior 3-month, prior cumulative.
    # For H1/Q3, the second current value is therefore preferred for flow items.
    if flow and period_kind in {"half_year", "q3"} and len(values) >= 2:
        return values[1]
    return values[0]


def parse_original_report(
    zip_bytes: bytes,
    period_kind: str = "annual",
    metric_aliases: dict[str, list[str]] = ACCOUNT_ALIASES,
) -> dict[str, float | None]:
    """Extract legacy DART values from pre-XBRL/original report tables.

    The old reports have inconsistent table layouts. We match the metric label
    anywhere in the row, then choose the current-period numeric cell rather than
    assuming the label is always the first table cell.
    """
    candidates: dict[str, list[float]] = {k: [] for k in metric_aliases}
    flow_keys = {
        "revenue", "gross_profit", "sga", "operating_income", "pretax_income",
        "net_income", "controlling_net_income", "interest_expense",
        "cfo", "cfi", "cff", "capex_ppe", "capex_intangible",
    }
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith((".xml", ".htm", ".html")):
                continue
            raw = zf.read(name)
            soup = BeautifulSoup(raw, "lxml-xml" if name.lower().endswith(".xml") else "lxml")
            for tr in soup.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                row_text = clean_label(" ".join(cells))
                nums: list[float] = []
                for cell in cells:
                    nums.extend(_numbers(cell))
                if not nums:
                    continue
                for key, aliases in metric_aliases.items():
                    normalized_aliases = [clean_label(a) for a in aliases]
                    if any(alias and alias in row_text for alias in normalized_aliases):
                        value = _pick_value(nums, period_kind, key in flow_keys)
                        if value is not None:
                            candidates[key].append(value)

    # Some historical DART files are not table-structured after XML parsing.
    # As a fallback, search the flattened document around each account label.
    for name in zf.namelist():
        if not name.lower().endswith((".xml", ".htm", ".html")):
            continue
        raw = zf.read(name)
        soup = BeautifulSoup(raw, "lxml-xml" if name.lower().endswith(".xml") else "lxml")
        flat = clean_label(soup.get_text(" ", strip=True))
        for key, aliases in metric_aliases.items():
            if candidates[key]:
                continue
            for alias in [clean_label(a) for a in aliases]:
                pos = flat.find(alias)
                if pos < 0:
                    continue
                window = flat[pos + len(alias):pos + len(alias) + 800]
                nums = _numbers(window)
                value = _pick_value(nums, period_kind, key in flow_keys)
                if value is not None:
                    candidates[key].append(value)
                    break

    return {k: (v[0] if v else None) for k, v in candidates.items()}
