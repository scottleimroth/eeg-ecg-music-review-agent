"""Tests for the psyp70385 MCP server tools.

Every expected number here comes from the published paper itself
(Leimroth et al. 2026, doi:10.1111/psyp.70385), section 4.2 and the PRISMA
flow diagram (Figure 1), or from Tables 1-7 directly. Run with:

    uv run pytest tests/test_tools.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server as srv  # noqa: E402


# ---------------------------------------------------------------------------
# The join / data build itself
# ---------------------------------------------------------------------------

def test_eighteen_studies():
    assert len(srv.STUDIES) == 18


def test_studies_have_unique_ids():
    ids = [s["id"] for s in srv.STUDIES]
    assert len(set(ids)) == 18


def test_every_study_has_all_categories():
    for s in srv.STUDIES:
        for cat in ("participants", "eeg", "ecg", "stimulus", "design", "findings"):
            assert cat in s, f"{s['id']} missing {cat}"


# ---------------------------------------------------------------------------
# list_studies
# ---------------------------------------------------------------------------

def test_regions_match_paper():
    counts = {}
    for s in srv.STUDIES:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    assert counts == {
        "Western Europe": 6,
        "North America": 5,
        "East Asia": 4,
        "Southeast Asia": 2,
        "South Asia": 1,
    }


def test_list_studies_filters_by_region():
    out = srv.list_studies(region="South Asia")
    assert len(out) == 1
    assert out[0]["author_year"] == "Sharma et al. (2021)"


def test_list_studies_filters_by_brain_heart():
    out = srv.list_studies(brain_heart_interaction_tested="Yes")
    assert len(out) == 7
    out = srv.list_studies(brain_heart_interaction_tested="Partial")
    assert len(out) == 3
    out = srv.list_studies(brain_heart_interaction_tested="No")
    assert len(out) == 8


def test_list_studies_filters_by_year_range():
    since_2015 = srv.list_studies(year_from=2015)
    assert len(since_2015) == 11  # "11 of 18 (61%) published since 2015"
    before_2015 = srv.list_studies(year_to=2014)
    assert len(before_2015) == 7


# ---------------------------------------------------------------------------
# get_study
# ---------------------------------------------------------------------------

def test_get_study_returns_full_record():
    s = srv.get_study(id="nanba-et-al-1992")
    assert s["author_year"] == "Nanba et al. (1992)"
    assert s["region"] == "East Asia"


def test_get_study_unknown_id_raises():
    with pytest.raises(ValueError):
        srv.get_study(id="not-a-real-study")


def test_mollakazemi_2018_duplicate_authors_stay_distinct():
    a = srv.get_study(id="mollakazemi-biswal-evans-and-patwardhan-2018")
    b = srv.get_study(id="mollakazemi-biswal-and-patwardhan-2018")
    assert a["author_year"] != b["author_year"]
    assert a["year"] == b["year"] == 2018


# ---------------------------------------------------------------------------
# search_studies
# ---------------------------------------------------------------------------

def test_search_studies_impedance_field_matches_three():
    out = srv.search_studies(query="kΩ", field="eeg.impedance")
    assert len(out) == 3
    names = {r["author_year"] for r in out}
    assert names == {"Baumgartner et al. (2006)", "Jäncke et al. (2015)", "Teixeira Borges et al. (2019)"}


def test_search_studies_unknown_field_raises():
    with pytest.raises(ValueError):
        srv.search_studies(query="x", field="not.a.field")

    with pytest.raises(ValueError):
        srv.search_studies(query="x", field="eeg.not_a_real_column")


def test_search_studies_across_all_fields_finds_headphones():
    out = srv.search_studies(query="headphones")
    assert len(out) >= 1
    for r in out:
        assert any("headphone" in v.lower() for v in r["matched_fields"].values())


# ---------------------------------------------------------------------------
# reporting_gaps - every number the paper states in section 4.2
# ---------------------------------------------------------------------------

EXPECTED_GAPS = {
    ("eeg", "impedance"): 15,
    ("eeg", "electrode_type"): 10,
    ("eeg", "reference"): 8,
    ("eeg", "filtering"): 4,
    ("ecg", "filtering"): 14,
    ("ecg", "sampling_rate_hz"): 6,
    ("participants", "audiology"): 10,
    ("participants", "musicianship"): 12,
    ("participants", "handedness"): 9,
    ("participants", "eligibility_criteria"): 10,
    ("stimulus", "delivery"): 11,
    ("stimulus", "attention"): 11,
    ("design", "room_details"): 12,
    ("design", "power_analysis"): 17,
}


def test_reporting_gaps_matches_every_paper_stated_figure():
    gaps = {(g["category"], g["field"]): g["not_reported"] for g in srv.reporting_gaps()}
    for key, expected in EXPECTED_GAPS.items():
        assert gaps[key] == expected, f"{key}: got {gaps[key]}, paper states {expected}"


def test_reporting_gaps_percent_is_out_of_18():
    gaps = srv.reporting_gaps(category="eeg")
    imp = next(g for g in gaps if g["field"] == "impedance")
    assert imp["percent_not_reported"] == round(100 * 15 / 18, 1)


def test_reporting_gaps_rejects_bad_category():
    with pytest.raises(ValueError):
        srv.reporting_gaps(category="not-a-category")


# ---------------------------------------------------------------------------
# study_scorecard
# ---------------------------------------------------------------------------

def test_study_scorecard_lists_blank_fields():
    card = srv.study_scorecard(id="nanba-et-al-1992")
    assert card["not_reported_count"] > 0
    assert "eeg" in card["not_reported_by_category"] or "ecg" in card["not_reported_by_category"]


# ---------------------------------------------------------------------------
# screen_study - deterministic against the review's own 6 rules
# ---------------------------------------------------------------------------

ALL_PASS = dict(
    published_peer_reviewed_journal=True,
    english_language=True,
    is_review_or_protocol_or_abstract_only=False,
    eeg_and_ecg_recorded_concurrently=True,
    participants_adult_18_plus=True,
    participants_healthy_nonclinical=True,
    participants_nonmusicians=True,
    stimulus_is_music=True,
    passive_listening_no_concurrent_task=True,
)


def test_screen_study_all_criteria_met_includes():
    r = srv.screen_study(**ALL_PASS)
    assert r == {"result": "include", "failing_rules": []}


def test_screen_study_trained_musicians_excluded_naming_rule_3():
    args = dict(ALL_PASS, participants_nonmusicians=False)
    r = srv.screen_study(**args)
    assert r["result"] == "exclude"
    assert 3 in r["failing_rules"]


def test_screen_study_no_concurrent_eeg_ecg_excluded_naming_rule_2():
    args = dict(ALL_PASS, eeg_and_ecg_recorded_concurrently=False)
    r = srv.screen_study(**args)
    assert r["result"] == "exclude"
    assert r["failing_rules"] == [2]


def test_screen_study_review_paper_excluded_naming_rule_1():
    args = dict(ALL_PASS, is_review_or_protocol_or_abstract_only=True)
    r = srv.screen_study(**args)
    assert 1 in r["failing_rules"]


def test_screen_study_multiple_failures_all_named():
    args = dict(ALL_PASS, stimulus_is_music=False, passive_listening_no_concurrent_task=False)
    r = srv.screen_study(**args)
    assert set(r["failing_rules"]) == {4, 5}


# ---------------------------------------------------------------------------
# search_strategy / eligibility_criteria / charting_template / review_metadata
# ---------------------------------------------------------------------------

def test_search_strategy_prisma_counts():
    out = srv.search_strategy()
    flow = out["prisma_flow"]
    assert flow["identified"] == 1214
    assert flow["duplicates_removed"] == 596
    assert flow["screened"] == 618
    assert flow["excluded_at_screening"] == 581
    assert flow["assessed_for_eligibility"] == 37
    assert flow["excluded_at_eligibility"] == 19
    assert flow["included"] == 18
    assert len(out["databases"]) == 5
    assert out["initial_search_date"] == "2024-01-31"
    assert out["update_search_date"] == "2025-08-10"


def test_search_strategy_single_database():
    out = srv.search_strategy(database="PubMed")
    assert out["requested_database"] == "PubMed"


def test_search_strategy_unknown_database_raises():
    with pytest.raises(ValueError):
        srv.search_strategy(database="Not A Real Database")


def test_eligibility_criteria_has_six_rules():
    out = srv.eligibility_criteria()
    assert len(out["inclusion_exclusion_rules"]) == 6
    assert [r["rule"] for r in out["inclusion_exclusion_rules"]] == [1, 2, 3, 4, 5, 6]


def test_charting_template_has_expected_categories():
    out = srv.charting_template()
    assert "publication_information" in out["categories"]
    assert "eeg" in out["categories"]["measures"]
    assert "ecg" in out["categories"]["measures"]


def test_review_metadata_doi_and_licence():
    out = srv.review_metadata()
    assert out["doi"] == "10.1111/psyp.70385"
    assert out["licence"] == "CC BY 4.0"
    assert out["included_studies"] == 18
    assert out["first_authors"] == 13  # "13 individual first authors across the 18 studies"


# ---------------------------------------------------------------------------
# get_table_footnote
# ---------------------------------------------------------------------------

def test_get_table_footnote_resolves_known_marker():
    text = srv.get_table_footnote(table=1, marker="a")
    assert "Kumarasinghe" in text and "Namazi" in text


def test_get_table_footnote_accepts_caret_prefix():
    a = srv.get_table_footnote(table=1, marker="^a")
    b = srv.get_table_footnote(table=1, marker="a")
    assert a == b


def test_get_table_footnote_unknown_table_raises():
    with pytest.raises(ValueError):
        srv.get_table_footnote(table=3, marker="a")  # Table 3 has no lettered footnotes


def test_get_table_footnote_unknown_marker_raises():
    with pytest.raises(ValueError):
        srv.get_table_footnote(table=1, marker="z")


# ---------------------------------------------------------------------------
# Server smoke test - the MCP object itself is well formed
# ---------------------------------------------------------------------------

def test_server_registers_all_ten_tools():
    import asyncio
    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "list_studies", "get_study", "search_studies", "reporting_gaps",
        "study_scorecard", "charting_template", "eligibility_criteria",
        "screen_study", "search_strategy", "get_table_footnote", "review_metadata",
    }


def test_server_registers_the_prompt():
    import asyncio
    prompts = asyncio.run(srv.mcp.list_prompts())
    assert {p.name for p in prompts} == {"chart_a_new_study"}
