from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

ACCOUNT_IDS = {\n    "revenue": {"ifrs-full_Revenue"},\n    "gross_profit": {"ifrs-full_GrossProfit"},\n    "operating_income": {"dart_OperatingIncomeLoss", "ifrs-full_OperatingIncomeLoss"},\n    "pretax_income": {"ifrs-full_ProfitLossBeforeTax"},\n    "net_income": {"ifrs-full_ProfitLoss"},\n}\n\nACCOUNT_ALIASES = {
    "revenue": ["매출액", "수익(매출액)", "수익(매출)", "매출"],
    "gross_profit": ["매출총이익", "매출총손익"],
    "sga": ["판매비와관리비", "판매비및관리비", "판매비와 일반관리비"],
    "operating_income": ["영업이익", "영업이익(손실)", "영업손익"],
    "pretax_income": ["법인세비용차감전순이익", "법인세비용차감전계속영업이익", "세전이익", "법인세비용차감전순손익"],
    "net_income": ["당기순이익", "당기순이익(손실)", "당기순손익"],
    "controlling_net_income": ["지배기업의 소유주에게 귀속되는 당기순이익", "지배주주순이익", "지배기업 소유주지분 순이익"],
    "assets": ["자산총계", "총자산"],
    "cash": ["현금및현금성자산", "현금 및 현금성자산"],
    "receivables": ["매출채권", "매출채권및기타채권", "매출채권 및 기타채권"],
    "inventory": ["재고자산", "재고자산(순액)"],
    "ppe": ["유형자산", "유형자산(순액)"],
    "liabilities": ["부채총계", "총부채"],
    "equity": ["자본총계", "총자본"],
    "current_assets": ["유동자산"],
    "current_liabilities": ["유동부채"],
    "short_borrowings": ["단기차입금", "단기차입부채"],
    "long_borrowings": ["장기차입금", "장기차입부채", "장기차입금(비유동)"],
    "interest_expense": ["이자비용", "금융원가", "이자비용(금융원가)", "금융비용"],
    "cfo": ["영업활동으로 인한 현금흐름", "영업활동현금흐름", "영업활동 현금흐름"],
    "cfi": ["투자활동으로 인한 현금흐름", "투자활동현금흐름", "투자활동 현금흐름"],
    "cff": ["재무활동으로 인한 현금흐름", "재무활동현금흐름", "재무활동 현금흐름"],
    "capex_ppe": ["유형자산의 취득", "유형자산 취득", "유형자산의 취득으로 인한 현금유출"],
    "capex_intangible": ["무형자산의 취득", "무형자산 취득", "무형자산의 취득으로 인한 현금유출"],
}


def clean_label(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", "", text)
    text = text.replace("(손실)", "(손실)")
    return text


def parse_amount(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if s in {"", "-", "--", "nan", "None"}:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "")
    try:
        n = float(s)
        return -n if negative else n
    except ValueError:
        return None


def choose_account(accounts: list[dict[str, Any]], aliases: list[str]) -> dict[str, Any] | None:
    norm_aliases = [clean_label(a) for a in aliases]
    exact = []
    for row in accounts:
        label = clean_label(row.get("account_nm"))
        if label in norm_aliases:
            exact.append(row)
    if exact:
        # Prefer consolidated statement rows and common account classifications.
        return exact[0]
    for alias in norm_aliases:
        for row in accounts:
            label = clean_label(row.get("account_nm"))
            if alias and alias in label:
                return row
    return None


def extract_metrics(api_data: dict[str, Any]) -> dict[str, float | None]:
    rows = api_data.get("list", [])
    metrics: dict[str, float | None] = {}
    for key, aliases in ACCOUNT_ALIASES.items():
        row = choose_account(rows, aliases, ACCOUNT_IDS.get(key))
        metrics[key] = parse_amount(row.get("thstrm_amount")) if row else None
    return metrics


def merge_period(base: dict[str, Any], current: dict[str, float | None]) -> dict[str, Any]:
    out = dict(base)
    out.update(current)
    return out
