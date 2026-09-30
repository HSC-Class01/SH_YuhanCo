from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "financials.csv")
required = {"year", "kind", "revenue", "operating_income", "net_income"}
missing = required - set(df.columns)
if missing:
    raise SystemExit(f"Missing columns: {sorted(missing)}")

bad = df[["revenue", "operating_income", "net_income"]].isna().all(axis=1)
if bad.any():
    rows = df.loc[bad, ["year", "kind"]].to_dict("records")
    raise SystemExit(f"Rows have no core financial values: {rows}")

latest = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))
json.dumps(latest, allow_nan=False)
if not latest.get("latest"):
    raise SystemExit("latest.json has no latest record")

print(f"Validation OK: {len(df)} periods; latest={latest['latest'].get('year')} {latest['latest'].get('period')}")
