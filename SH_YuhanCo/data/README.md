# Data directory

The agent writes the following files here:

- `financials.csv`: normalized DART financial statement values.
- `ratios.csv`: calculated financial ratios.
- `reports.csv`: report metadata and DART receipt links.
- `peers.csv`: domestic peer-firm universe.
- `latest.json`: latest-period metadata used by the dashboard.

`data/raw/` is intentionally excluded from Git because original DART ZIP files can be large. The metadata and source receipt links are retained in `reports.csv` so every extracted observation remains traceable to a DART filing.
