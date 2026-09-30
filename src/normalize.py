from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

ACCOUNT_IDS = {
    "revenue": {"ifrs-full_Revenue"},
    "gross_profit": {"ifrs-full_GrossProfit"},
    "operating_income": {"dart_OperatingIncomeLoss", "ifrs-full_OperatingIncomeLoss"},
    "pretax_income": {"ifrs-full_ProfitLossBeforeTax"},
    "net_income": {"ifrs-full_ProfitLoss"},
}

ACCOUNT_ALIASES = {
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


def choose_account(
    accounts: list[dict[str, Any]],
    aliases: list[str],
    account_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    # XBRL account_id is more stable than Korean account names, so use it first.
    if account_ids:
        for row in accounts:
            if str(row.get("account_id") or "").strip() in account_ids:
                return row

    norm_aliases = [clean_label(a) for a in aliases]
    exact = []
    for row in accounts:
        label = clean_label(row.get("account_nm"))
        if label in norm_aliases:
            exact.append(row)
    if exact:
        return exact[0]

    for alias in norm_aliases:
        for row in accounts:
            label = clean_label(row.get("account_nm"))
            if alias and alias in label:
                return row
    return None


FLOW_METRICS = {  # financial flow fields; interim cumulative handling is enabled below
    "revenue", "gross_profit", "sga", "operating_income", "pretax_income",
    "net_income", "controlling_net_income", "interest_expense",
    "cfo", "cfi", "cff", "capex_ppe", "capex_intangible",
}


def extract_metrics(
    api_data: dict[str, Any],
    cumulative: bool = False,
) -> dict[str, float | None]:
    rows = api_data.get("list", [])
    metrics: dict[str, float | None] = {}
    for key, aliases in ACCOUNT_ALIASES.items():
        row = choose_account(rows, aliases, ACCOUNT_IDS.get(key))
        if not row:
            metrics[key] = None
            continue

        # OpenDART reports 3-month amounts in thstrm_amount for
        # quarterly/semi-annual comprehensive income statements.
        # Use thstrm_add_amount for H1/Q3 cumulative flow measures.
        field = "thstrm_add_amount" if cumulative and key in FLOW_METRICS else "thstrm_amount"
        value = row.get(field)
        if value in (None, "", "-") and field != "thstrm_amount":
            value = row.get("thstrm_amount")
        metrics[key] = parse_amount(value)
    return metrics


def merge_period(base: dict[str, Any], current: dict[str, float | None]) -> dict[str, Any]:
    out = dict(base)
    out.update(current)
    return out

# CI trigger: legacy parser maintenance verified.
