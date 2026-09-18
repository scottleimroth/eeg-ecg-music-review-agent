#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]<2", "pywin32; sys_platform == 'win32'"]
# ///
"""MCP server over the charted evidence of Leimroth et al. 2026,
"Exploring EEG and ECG in Music Listening: A Scoping Review"
(Psychophysiology 63(9) e70385, doi:10.1111/psyp.70385).

Read-only. No network calls, no LLM calls, no writes. Every tool reads the
JSON files in data/ next to this script and returns data straight from the
review's own charted tables - it never summarises or interprets a finding
(that is what the reading package skill is for). Run with:

    uv run server.py

and connect over stdio, e.g. `claude mcp add psyp70385 -- uv run <path>/server.py`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

DATA = Path(__file__).resolve().parent / "data"


def load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


STUDIES: list[dict] = load("studies.json")
STUDIES_BY_ID = {s["id"]: s for s in STUDIES}
REVIEW_METADATA = load("review_metadata.json")
ELIGIBILITY = load("eligibility.json")
SEARCH_STRINGS = load("search_strings.json")
CHARTING_ITEMS = load("charting_items.json")
TABLE_FOOTNOTES = load("table_footnotes.json")

CATEGORIES = ("participants", "eeg", "ecg", "stimulus", "design", "findings")

mcp = FastMCP(
    name="psyp70385-eeg-ecg-music-scoping-review",
    instructions=(
        "Tools over the charted evidence of Leimroth et al. (2026), 'Exploring EEG and ECG "
        "in Music Listening: A Scoping Review' (Psychophysiology 63(9) e70385, "
        "doi:10.1111/psyp.70385) - 18 studies that recorded EEG and ECG concurrently during "
        "passive music listening in healthy adult non-musicians. If the user is asking about "
        "a different paper or a different scoping review, these tools do not apply to it - "
        "say so rather than answering from this data. Every tool returns the review's own "
        "charted data verbatim; none of them summarise or interpret findings. A study "
        "record's cell values may carry a footnote marker like '^a' - call get_table_footnote "
        "to resolve what it means."
    ),
)


def _study_summary(s: dict) -> dict:
    return {
        "id": s["id"],
        "author_year": s["author_year"],
        "year": s["year"],
        "region": s["region"],
        "brain_heart_interaction_tested": s["brain_heart_interaction_tested"],
    }


@mcp.tool()
def list_studies(
    region: str | None = None,
    brain_heart_interaction_tested: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict]:
    """List the 18 included studies, optionally filtered.

    region: exact match, e.g. "Western Europe", "North America", "East Asia",
        "Southeast Asia", "South Asia".
    brain_heart_interaction_tested: exact match, one of "Yes", "Partial", "No".
    year_from / year_to: inclusive publication-year bounds.

    Returns a list of {id, author_year, year, region, brain_heart_interaction_tested}.
    """
    out = STUDIES
    if region is not None:
        out = [s for s in out if s["region"] == region]
    if brain_heart_interaction_tested is not None:
        out = [s for s in out if s["brain_heart_interaction_tested"] == brain_heart_interaction_tested]
    if year_from is not None:
        out = [s for s in out if s["year"] >= year_from]
    if year_to is not None:
        out = [s for s in out if s["year"] <= year_to]
    return [_study_summary(s) for s in out]


@mcp.tool()
def get_study(id: str) -> dict:
    """Return the full charted record for one study by its id (see list_studies).

    Includes publication information, participants, EEG measures, ECG
    measures, stimulus, study design and reported findings, exactly as
    charted in Tables 1-7 of the review. An empty string in any field means
    that item was not reported by the original study.
    """
    if id not in STUDIES_BY_ID:
        raise ValueError(f"no study with id {id!r}; call list_studies to see valid ids")
    return STUDIES_BY_ID[id]


@mcp.tool()
def search_studies(query: str, field: str | None = None) -> list[dict]:
    """Case-insensitive substring search over the charted text.

    field: a dotted path such as "eeg.impedance", "stimulus.delivery",
        "findings.eeg_ecg_interaction". If omitted, searches every text field
        of every study (all of participants/eeg/ecg/stimulus/design/findings,
        plus aim and findings_summary).

    Returns each matching study's summary plus the matched field(s) and value(s).
    """
    q = query.lower()
    results = []
    for s in STUDIES:
        matches: dict[str, str] = {}
        if field is not None:
            if "." not in field or field.split(".")[0] not in CATEGORIES:
                raise ValueError(f"field must be '<category>.<name>' where category is one of {CATEGORIES}")
            cat, name = field.split(".", 1)
            value = s.get(cat, {}).get(name)
            if value is None:
                raise ValueError(f"unknown field {field!r} for study records")
            if q in value.lower():
                matches[field] = value
        else:
            for cat in CATEGORIES:
                for name, value in s[cat].items():
                    if isinstance(value, str) and q in value.lower():
                        matches[f"{cat}.{name}"] = value
            for top in ("aim", "findings_summary"):
                if q in s[top].lower():
                    matches[top] = s[top]
        if matches:
            results.append({**_study_summary(s), "matched_fields": matches})
    return results


@mcp.tool()
def reporting_gaps(category: str | None = None) -> list[dict]:
    """Reporting completeness for every charted item, across all 18 studies.

    category: one of "participants", "eeg", "ecg", "stimulus", "design". If
        omitted, covers all five.

    For each item: how many of the 18 studies left it blank, the percentage,
    and (where the paper states a matching figure in section 4.2) that
    stated figure for cross-reference. A field is counted as reported unless
    its value is an empty string; a footnote marker alone (e.g. "^a" with no
    other text) counts as not reported.
    """
    cats = [category] if category else ["participants", "eeg", "ecg", "stimulus", "design"]
    for c in cats:
        if c not in ("participants", "eeg", "ecg", "stimulus", "design"):
            raise ValueError(f"unknown category {c!r}; use participants, eeg, ecg, stimulus or design")

    paper_states = {
        ("eeg", "impedance"): "15 of 18 (83%) did not mention impedance levels",
        ("eeg", "electrode_type"): "10 of 18 (56%) did not specify electrode type",
        ("eeg", "reference"): "8 of 18 (44%) did not mention the reference used",
        ("eeg", "filtering"): "4 of 18 (22%) omitted filter details",
        ("ecg", "filtering"): "14 of 18 (78%) did not report filtering details",
        ("ecg", "sampling_rate_hz"): "6 of 18 (33%) did not report sampling rate",
        ("participants", "audiology"): "10 of 18 (56%) overlooked hearing assessment",
        ("participants", "musicianship"): "12 of 18 (67%) did not assess musical ability",
        ("participants", "handedness"): "9 of 18 (50%) did not mention handedness",
        ("participants", "eligibility_criteria"): "10 of 18 (56%) overlooked exclusion criteria such as alcohol or caffeine",
        ("stimulus", "delivery"): "11 of 18 (61%) gave no information on delivery method",
        ("stimulus", "attention"): "11 of 18 (61%) omitted reporting of attentional engagement",
        ("design", "room_details"): "12 of 18 (67%) did not mention room details",
        ("design", "power_analysis"): "1 of 18 (6%) mentioned an a priori power analysis",
    }

    out = []
    for cat in cats:
        fields = list(STUDIES[0][cat].keys())
        for f in fields:
            blank = sum(1 for s in STUDIES if not s[cat][f].strip())
            reported = len(STUDIES) - blank
            entry = {
                "category": cat,
                "field": f,
                "reported": reported,
                "not_reported": blank,
                "percent_not_reported": round(100 * blank / len(STUDIES), 1),
            }
            if (cat, f) in paper_states:
                entry["paper_states"] = paper_states[(cat, f)]
            out.append(entry)
    return out


@mcp.tool()
def study_scorecard(id: str) -> dict:
    """The charted items one study left blank, grouped by category.

    id: a study id (see list_studies).
    """
    if id not in STUDIES_BY_ID:
        raise ValueError(f"no study with id {id!r}; call list_studies to see valid ids")
    s = STUDIES_BY_ID[id]
    blanks: dict[str, list[str]] = {}
    for cat in ("participants", "eeg", "ecg", "stimulus", "design"):
        missing = [f for f, v in s[cat].items() if not v.strip()]
        if missing:
            blanks[cat] = missing
    total_fields = sum(len(STUDIES[0][cat]) for cat in ("participants", "eeg", "ecg", "stimulus", "design"))
    total_blank = sum(len(v) for v in blanks.values())
    return {
        "id": id,
        "author_year": s["author_year"],
        "not_reported_by_category": blanks,
        "not_reported_count": total_blank,
        "charted_field_count": total_fields,
    }


@mcp.tool()
def charting_template() -> dict:
    """The review's data-charting template (Appendix S3), for applying the
    review's method to a new study: fill each item from the new paper's
    methods section, then call screen_study to check eligibility.
    """
    return CHARTING_ITEMS


@mcp.tool()
def eligibility_criteria() -> dict:
    """The review's eligibility framework: the Population/Concept/Context
    table (Appendix S1) and the 6 numbered inclusion/exclusion rules from
    section 2.2 of the paper.
    """
    return ELIGIBILITY


@mcp.tool()
def screen_study(
    published_peer_reviewed_journal: bool,
    english_language: bool,
    is_review_or_protocol_or_abstract_only: bool,
    eeg_and_ecg_recorded_concurrently: bool,
    participants_adult_18_plus: bool,
    participants_healthy_nonclinical: bool,
    participants_nonmusicians: bool,
    stimulus_is_music: bool,
    passive_listening_no_concurrent_task: bool,
) -> dict:
    """Deterministically apply the review's 6 eligibility rules to a candidate
    study, given yes/no answers about it. Every argument is a plain boolean;
    pass what is known and reason conservatively about the rest (an unclear
    point is not the same as a "no" - see the "unknown" result below, which
    this tool cannot produce on its own since it takes only booleans. If a
    fact is genuinely unknown, call this twice, once per plausible answer,
    and report both outcomes to the user, or answer False only for the
    ones actually confirmed absent).

    Returns {"result": "include"|"exclude", "failing_rules": [...]} - one
    entry per rule (1-6, see eligibility_criteria) the study fails, in the
    review's own numbering. An empty failing_rules list with result
    "include" means all 6 rules are satisfied.
    """
    failing = []
    if not (published_peer_reviewed_journal and english_language) or is_review_or_protocol_or_abstract_only:
        failing.append(1)
    if not eeg_and_ecg_recorded_concurrently:
        failing.append(2)
    if not (participants_adult_18_plus and participants_healthy_nonclinical and participants_nonmusicians):
        failing.append(3)
    if not stimulus_is_music:
        failing.append(4)
    if not passive_listening_no_concurrent_task:
        failing.append(5)
    return {"result": "exclude" if failing else "include", "failing_rules": failing}


@mcp.tool()
def search_strategy(database: str | None = None) -> dict:
    """The review's search strategy (Appendix S2): exact search strings per
    database, search dates, and the PRISMA identification counts.

    database: optional exact name, e.g. "PubMed", "Scopus". If omitted,
        returns all databases plus the PRISMA flow counts.
    """
    out = dict(SEARCH_STRINGS)
    out["prisma_flow"] = REVIEW_METADATA["prisma_flow"]
    if database is None:
        return out
    if database not in out["databases"]:
        raise ValueError(f"unknown database {database!r}; known: {out['databases']}")
    out["requested_database"] = database
    return out


@mcp.tool()
def get_table_footnote(table: int, marker: str) -> str:
    """Resolve a footnote marker (e.g. "a" from a cell like "12^a") to its
    meaning for a given table number (1-7, matching the review's own Table
    1-7 numbering).
    """
    key = str(table)
    if key not in TABLE_FOOTNOTES:
        raise ValueError(f"table {table} has no lettered footnotes")
    entries = TABLE_FOOTNOTES[key]
    marker = marker.lstrip("^")
    if marker not in entries:
        raise ValueError(f"table {table} has no footnote {marker!r}; known: {sorted(entries)}")
    return entries[marker]


@mcp.tool()
def review_metadata() -> dict:
    """Citation, identifiers, licence, preregistration links and the PRISMA
    flow counts for the review this server is built from."""
    return REVIEW_METADATA


@mcp.prompt()
def chart_a_new_study(paper_text: str) -> str:
    """Chart a new paper against this review's method: retrieve the
    charting template and eligibility rules, fill every item from the
    supplied paper text, then screen it for eligibility."""
    return (
        "Apply this scoping review's charting method to the paper below.\n\n"
        "1. Call charting_template to get the review's data-charting items.\n"
        "2. Fill every item you can from the paper text; leave an item blank "
        "(empty string) if the paper does not report it - do not guess.\n"
        "3. Call eligibility_criteria, then call screen_study with your best "
        "assessment of each of its boolean questions from the paper text.\n"
        "4. Report the filled template, the screening result, and which "
        "charted items the new paper leaves unreported (compare against "
        "reporting_gaps for how the 18 reviewed studies did on the same items).\n\n"
        f"Paper text:\n\n{paper_text}"
    )


if __name__ == "__main__":
    mcp.run()
