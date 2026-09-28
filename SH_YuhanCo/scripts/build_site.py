from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "dashboard"
TARGET = SITE / "data"
TARGET.mkdir(parents=True, exist_ok=True)
for name in ["financials.csv", "ratios.csv", "reports.csv", "peers.csv", "latest.json"]:
    src = ROOT / "data" / name
    if src.exists():
        shutil.copy2(src, TARGET / name)
print("Dashboard data copied.")
