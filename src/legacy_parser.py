from __future__ import annotations

import io
import re
import zipfile
from typing import Iterable

from bs4 import BeautifulSoup

from .normalize import ACCOUNT_ALIASES, clean_label, parse_amount


def _numbers(text: str) -> list[float]:
    vals = []
    for m in re.findall(r"[-(]?[0-9][0-9,]*(?:\.[0-9]+)?\)?", text):
        v = parse_amount(m)
        if v is not None:
            vals.append(v)
    return vals


def parse_original_report(zip_bytes: bytes, metric_aliases: dict[str, list[str]] = ACCOUNT_ALIASES) -> dict[str, float | None]:
    """Heuristic parser for pre-XBRL DART report archives.

    It intentionally returns only values that can be matched to a metric label and
    a numeric cell in the same table row. Unmatched values remain null rather than
    being guessed.
    """
    candidates: dict[str, list[float]] = {k: [] for k in metric_aliases}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith((".xml", ".htm", ".html")):
                continue
            raw = zf.read(name)
            soup = BeautifulSoup(raw, "lxml")
            for tr in soup.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if len(cells) < 2:
                    continue
                label = clean_label(cells[0])
                nums = []
                for cell in cells[1:]:
                    nums.extend(_numbers(cell))
                if not nums:
                    continue
                for key, aliases in metric_aliases.items():
                    if any(clean_label(a) == label or clean_label(a) in label for a in aliases):
                        candidates[key].extend(nums[:2])

    # Prefer the first value in the first strong match. Legacy tables often place
    # current period first; exact account labels are filtered before fuzzy matches.
    return {k: (v[0] if v else None) for k, v in candidates.items()}
