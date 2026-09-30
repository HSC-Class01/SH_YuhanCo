from __future__ import annotations

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analyze import calculate_ratios
from src.dart_client import DartAPIError, DartClient
from src.legacy_parser import parse_original_report
from src.normalize import extract_metrics


def report_url(rcept_no: str) -> str:
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"


def year_windows(year: int, kind: str) -> tuple[str, str]:
    if kind == "annual":
        return f"{year+1}0101", f"{year+1}0430"
    if kind == "half_year":
        return f"{year}0701", f"{year}0930"
    if kind == "q1":
        return f"{year}0401", f"{year}0630"
    if kind == "q3":
        return f"{year}1001", f"{year}1231"
    raise ValueError(kind)


def find_regular_filing(client: DartClient, corp_code: str, year: int, kind: str) -> dict | None:
    bgn, end = year_windows(year, kind)
    try:
        data = client.report_list(corp_code, bgn, end, page_no=1, page_count=100)
    except DartAPIError as exc:
        print(f"filing search warning: {year} {kind}: {exc}")
        return None
    targets = {
        "annual": "사업보고서",
        "half_year": "반기보고서",
        "q1": "분기보고서",
        "q3": "분기보고서",
    }
    matched = [r for r in data.get("list", []) if targets[kind] in str(r.get("report_nm", ""))]
    if kind == "q1":
        matched = [r for r in matched if "1분기" in str(r.get("report_nm", "")) or "분기보고서" in str(r.get("report_nm", ""))]
    elif kind == "q3":
        matched = [r for r in matched if "3분기" in str(r.get("report_nm", "")) or "분기보고서" in str(r.get("report_nm", ""))]
    if not matched:
        return None
    matched.sort(key=lambda r: (str(r.get("rcept_dt", "")), str(r.get("rcept_no", ""))), reverse=True)
    return matched[0]


def legacy_row(client: DartClient, corp_code: str, year: int, kind: str, filing: dict | None = None) -> dict | None:
    filing = filing or find_regular_filing(client, corp_code, year, kind)
    if not filing:
        return None
    try:
        raw = client.original_document(filing["rcept_no"])
        metrics = parse_original_report(raw, period_kind=kind)
    except Exception as exc:
        print(f"legacy parse warning: {year} {kind}: {exc}")
        return None
    core = [metrics.get(k) for k in ("revenue", "operating_income", "net_income")]
    if all(v is None for v in core):
        print(f"legacy parse produced no core values: {year} {kind}")
    return {
        "year": year,
        "kind": kind,
        "report_code": {"annual":"11011","half_year":"11012","q1":"11013","q3":"11014"}[kind],
        "rcept_no": filing.get("rcept_no"),
        "report_name": filing.get("report_nm"),
        "report_url": report_url(filing.get("rcept_no", "")),
        "source_method": "DART original report heuristic",
        **metrics,
    }


def structured_rows(client: DartClient, corp_code: str, year: int, fs_div: str) -> list[dict]:
    output = []
    for kind, code in [("annual", "11011"), ("half_year", "11012"), ("q1", "11013"), ("q3", "11014")]:
        try:
            data = client.full_financials(corp_code, year, code, fs_div)
        except DartAPIError as exc:
            print(f"XBRL unavailable; falling back to original report: {year} {kind}: {exc}")
            row = legacy_row(client, corp_code, year, kind)
            if row:
                output.append(row)
            continue
        if data.get("list"):
            metrics = extract_metrics(data, cumulative=(kind in {"half_year", "q3"}))
            output.append({"year": year, "kind": kind, "report_code": code, "source_method": "OpenDART XBRL API", **metrics})
        else:
            row = legacy_row(client, corp_code, year, kind)
            if row:
                output.append(row)
    return output


def legacy_rows(client: DartClient, corp_code: str, year: int) -> list[dict]:
    kinds = ["annual", "half_year", "q1", "q3"]
    # Original-report downloads are independent and can be fetched concurrently.
    # Keep the pool small to avoid stressing the DART API.
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(legacy_row, client, corp_code, year, kind): kind for kind in kinds}
        for future in as_completed(futures):
            row = future.result()
            if row:
                rows.append(row)
    return rows


def standalone_quarters(rows: list[dict]) -> list[dict]:
    by_year = {}
    for r in rows:
        by_year.setdefault(r["year"], {})[r["kind"]] = r
    for year, d in by_year.items():
        q3, h1 = d.get("q3"), d.get("half_year")
        if not q3 or not h1:
            continue
        for key in ["revenue", "gross_profit", "sga", "operating_income", "pretax_income", "net_income", "controlling_net_income", "cfo", "cfi", "cff", "fcf"]:
            if q3.get(key) is not None and h1.get(key) is not None:
                q3[key] = q3[key] - h1[key]
        q3["period_label"] = "Q3 (standalone)"
    return rows


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def main() -> None:
    config = yaml.safe_load((ROOT / "config/company.yml").read_text(encoding="utf-8"))
    company = config["company"]
    api_key = os.environ.get("DART_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("DART_API_KEY 환경변수가 없습니다. GitHub Actions Secret 또는 로컬 환경변수로 설정하세요.")

    client = DartClient(api_key, ROOT / "data/raw")
    corp_code = client.find_corp_code(company["stock_code"])
    (ROOT / "data" / "corp_code.json").write_text(
        json.dumps({"stock_code": company["stock_code"], "corp_code": corp_code}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    rows: list[dict] = []
    for year in range(int(company["start_year"]), datetime.now().year + 1):
        if year <= 2014:
            rows.extend(legacy_rows(client, corp_code, year))
        else:
            rows.extend(structured_rows(client, corp_code, year, company["fs_div"]))

    if not rows:
        raise SystemExit("재무데이터를 가져오지 못했습니다. DART API 키/회사코드/서비스 상태를 확인하세요.")

    rows = standalone_quarters(rows)
    df = pd.DataFrame(rows)
    order = {"q1": 1, "half_year": 2, "q3": 3, "annual": 4}
    df["period_order"] = df["kind"].map(order)
    labels = {"q1":"Q1", "half_year":"H1", "q3":"Q3", "annual":"FY"}
    df["period"] = df["kind"].map(labels)
    df["period_label"] = df["period"]

    df = df.sort_values(["year", "period_order", "source_method"]).drop_duplicates(["year", "kind"], keep="last")
    ratio_df = calculate_ratios(df)

    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    df.to_csv(data_dir / "financials.csv", index=False, encoding="utf-8-sig")
    ratio_df.to_csv(data_dir / "ratios.csv", index=False, encoding="utf-8-sig")

    reports = df[[c for c in ["year","kind","rcept_no","report_name","report_url","source_method"] if c in df.columns]].copy()
    reports.to_csv(data_dir / "reports.csv", index=False, encoding="utf-8-sig")

    peers = pd.DataFrame(config["peer_firms"])
    peers.to_csv(data_dir / "peers.csv", index=False, encoding="utf-8-sig")

    latest = _json_safe(ratio_df.sort_values(["year", "period_order"]).iloc[-1].to_dict())
    payload = {"company": company["name"], "stock_code": company["stock_code"], "corp_code": corp_code, "updated_at": datetime.now(timezone.utc).isoformat(), "latest": latest}
    (data_dir / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"Updated {len(df)} periods; corp_code={corp_code}")


if __name__ == "__main__":
    main()
