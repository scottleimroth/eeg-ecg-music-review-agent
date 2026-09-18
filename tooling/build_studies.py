#!/usr/bin/env python3
"""Join Tables 1-7 (data/tables.json) into one record per included study,
written to data/studies.json.

Join key: the Author/Year cell of each row, with any trailing footnote
markers (e.g. "^a") stripped. All seven tables must produce exactly the
same 18 keys - this script exits loudly if they do not, rather than
silently dropping or duplicating a study (see the estate rule: a filter
that keys on the wrong thing fails silently unless you make it fail loudly).

Cell values elsewhere in a row are kept verbatim, footnote markers and all
- a marker inside a data cell (e.g. "12^a" for sample size) refers to that
table's own footnote text and changes the value's meaning, so it must not
be stripped. Only the Author/Year field is normalised, because it is used
as a join key, not as data.

The record id is a full slug of the Author/Year string, not just
"surname+year": two 2018 studies share a first author and year
(Mollakazemi, Biswal, Evans, and Patwardhan 2018; Mollakazemi, Biswal, and
Patwardhan 2018), so "mollakazemi2018" would collide. A slug of the whole
string is unique by construction, since the join keys themselves are unique.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "tables.json"
OUT = ROOT / "data" / "studies.json"

FOOTNOTE_SUFFIX = re.compile(r"(\^[a-z0-9]+)+$")
YEAR_RE = re.compile(r"\((\d{4})\)")


def slugify(text_):
    # Normalise accented characters to their ASCII base (Jäncke -> Jancke)
    # before stripping non-alphanumerics, or a diacritic collapses to a bare
    # hyphen instead of the letter it decorates.
    ascii_text = unicodedata.normalize("NFKD", text_).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def strip_markers(cell):
    m = FOOTNOTE_SUFFIX.search(cell)
    if not m:
        return cell, []
    markers = re.findall(r"\^([a-z0-9]+)", m.group(0))
    return cell[: m.start()], markers


# category -> (table index in tables.json, snake_case field names for header[1:])
CATEGORY_TABLES = {
    "participants": (1, ["audiology", "musicianship", "handedness", "eligibility_criteria",
                          "sample_size", "final_number_processed", "sex_male_female", "age_years"]),
    "eeg": (2, ["variables", "electrode_configuration", "electrode_type", "impedance",
                "reference", "filtering", "hardware", "sampling_frequency_hz"]),
    "ecg": (3, ["variables", "electrode_configuration", "recording_equipment", "filtering",
                "sampling_rate_hz", "bp_resp"]),
    "stimulus": (4, ["duration", "musical_features", "style", "source", "delivery",
                      "intensity", "selection", "familiarity", "attention"]),
    "design": (5, ["hypothesis", "room_details", "time_of_day", "orientation", "visual_state",
                    "control_baseline", "power_analysis", "ethics_informed_consent"]),
    "findings": (6, ["eeg", "ecg", "eeg_ecg_interaction"]),
}


def main():
    tables = json.loads(TABLES.read_text(encoding="utf-8"))
    if len(tables) != 7:
        sys.exit(f"expected 7 tables in {TABLES}, found {len(tables)}")

    # Table 1 (Publication information) supplies the canonical key order and the
    # core fields (region, aim, findings_summary, brain_heart_interaction_tested).
    t1 = tables[0]
    if t1["label"] != "TABLE 1":
        sys.exit(f"expected tables[0] to be TABLE 1, got {t1['label']}")

    records = {}
    order = []
    for row in t1["rows"]:
        raw_author_year = row[0]
        key, markers = strip_markers(raw_author_year)
        if key in records:
            sys.exit(f"duplicate join key in TABLE 1: {key!r}")
        year_m = YEAR_RE.search(key)
        if not year_m:
            sys.exit(f"could not find a (YYYY) year in Author/Year cell: {raw_author_year!r}")
        records[key] = {
            "id": slugify(raw_author_year.replace("^", "-")),
            "author_year": key,
            "year": int(year_m.group(1)),
            "footnotes": list(markers),
            "region": row[1],
            "aim": row[2],
            "findings_summary": row[3],
            "brain_heart_interaction_tested": row[4],
        }
        order.append(key)

    if len(records) != 18:
        sys.exit(f"expected 18 studies from TABLE 1, found {len(records)}")

    ids = [r["id"] for r in records.values()]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        sys.exit(f"id collision after slugifying Author/Year: {dupes}")

    # Tables 2-7: join on the same stripped key; every table must reproduce
    # exactly the 18 keys found in Table 1, in some order - not more, not
    # fewer, not a near-miss from a footnote-stripping bug.
    for category, (idx, fields) in CATEGORY_TABLES.items():
        t = tables[idx]
        seen = set()
        for row in t["rows"]:
            key, markers = strip_markers(row[0])
            if key not in records:
                sys.exit(f"{t['label']} ({category}): join key not found in TABLE 1: {key!r} (raw: {row[0]!r})")
            if key in seen:
                sys.exit(f"{t['label']} ({category}): duplicate join key: {key!r}")
            seen.add(key)
            if len(row) != len(fields) + 1:
                sys.exit(f"{t['label']} ({category}): row for {key!r} has {len(row)} cells, expected {len(fields) + 1}")
            records[key]["footnotes"] = sorted(set(records[key]["footnotes"]) | set(markers))
            records[key][category] = {f: v for f, v in zip(fields, row[1:])}
        missing = set(records) - seen
        if missing:
            sys.exit(f"{t['label']} ({category}): missing rows for: {sorted(missing)}")

    for key, rec in records.items():
        for category in CATEGORY_TABLES:
            if category not in rec:
                sys.exit(f"study {key!r} has no {category!r} data after the join")

    studies = [records[k] for k in order]
    OUT.write_text(json.dumps(studies, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(studies)} studies to {OUT}")
    for s in studies:
        print(f"  {s['id']:55s} {s['author_year']}")


if __name__ == "__main__":
    sys.exit(main())
