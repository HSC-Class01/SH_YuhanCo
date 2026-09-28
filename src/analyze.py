from __future__ import annotations

import math
import pandas as pd


def safe_div(a, b):
    if a is None or b in (None, 0) or (isinstance(b, float) and math.isnan(b)):
        return None
    return a / b


def calculate_ratios(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy().sort_values(["year", "period_order"])
    x["gross_margin"] = x.apply(lambda r: safe_div(r.gross_profit, r.revenue), axis=1)
    x["operating_margin"] = x.apply(lambda r: safe_div(r.operating_income, r.revenue), axis=1)
    x["net_margin"] = x.apply(lambda r: safe_div(r.net_income, r.revenue), axis=1)
    x["current_ratio"] = x.apply(lambda r: safe_div(r.current_assets, r.current_liabilities), axis=1)
    x["debt_ratio"] = x.apply(lambda r: safe_div(r.liabilities, r.equity), axis=1)
    x["equity_ratio"] = x.apply(lambda r: safe_div(r.equity, r.assets), axis=1)
    x["debt_to_assets"] = x.apply(lambda r: safe_div(r.liabilities, r.assets), axis=1)
    x["interest_bearing_debt"] = x[["short_borrowings", "long_borrowings"]].fillna(0).sum(axis=1, min_count=1)
    x["net_debt"] = x.apply(lambda r: None if pd.isna(r.interest_bearing_debt) and pd.isna(r.cash) else (r.interest_bearing_debt or 0) - (r.cash or 0), axis=1)
    x["interest_coverage"] = x.apply(lambda r: safe_div(r.operating_income, r.interest_expense), axis=1)
    x["fcf"] = x.apply(lambda r: None if pd.isna(r.cfo) else r.cfo - abs((r.capex_ppe or 0) + (r.capex_intangible or 0)), axis=1)
    x["cfo_to_net_income"] = x.apply(lambda r: safe_div(r.cfo, r.net_income), axis=1)
    x["revenue_growth"] = x.groupby("period")["revenue"].pct_change()
    # Average-balance ROA/ROE for annual data; for interim periods this is an indicative period ratio.
    x["roa"] = x.apply(lambda r: safe_div(r.net_income, r.assets), axis=1)
    x["roe"] = x.apply(lambda r: safe_div(r.net_income, r.equity), axis=1)
    x["asset_turnover"] = x.apply(lambda r: safe_div(r.revenue, r.assets), axis=1)
    return x
