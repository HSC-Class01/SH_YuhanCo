from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "financials.csv")
required = {"year", "kind", "revenue", "operating_income", "net_income"}
missing = required - set(df.columns)
if missing:
    raise SystemExit(f"Missing columns: {sorted(missing)}")

latest = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))
json.dumps(latest, allow_nan=False)
latest_row = latest.get("latest") or {}
if latest_row.get("revenue") is None or latest_row.get("net_income") is None:
    raise SystemExit("Latest DART period is missing core financial values.")

blank_core = df[["revenue", "operating_income", "net_income"]].isna().all(axis=1)
if blank_core.any():
    rows = df.loc[blank_core, ["year", "kind"]].to_dict("records")
    print(f"Warning: historical/source-limited periods remain blank: {rows}")

print(f"Validation OK: {len(df)} periods; latest={latest_row.get('year')} {latest_row.get('period')}")
