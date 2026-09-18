#!/usr/bin/env python3
"""Copy data/*.json into the MCP server's own data/ directory, so the
delivered mcp/psyp70385-mcp/ folder is self-contained (no path back into
the rest of the repo). Run after build_studies.py or build_metadata.py."""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data"
DST = ROOT / "dist" / "eeg-ecg-music-review-agent" / "mcp" / "psyp70385-mcp" / "data"

FILES = ["studies.json", "review_metadata.json", "eligibility.json",
         "search_strings.json", "charting_items.json", "table_footnotes.json"]

DST.mkdir(parents=True, exist_ok=True)
for name in FILES:
    shutil.copy2(SRC / name, DST / name)
    print(f"copied {name}")
