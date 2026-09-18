#!/usr/bin/env python3
"""Build the small, hand-curated metadata JSON files the MCP server reads
alongside data/studies.json:

  data/review_metadata.json   citation, ids, links, licence, PRISMA counts
  data/eligibility.json       Appendix S1 (PCC framework) + the 6 numbered
                               inclusion/exclusion rules from section 2.2
  data/search_strings.json    Appendix S2 (per-database search strings)
  data/charting_items.json    Appendix S3 (the data-charting template)
  data/table_footnotes.json   per-table footnote letter -> meaning, so a
                               "^a" marker on a cell can be resolved

Source text is extracted from the reading package (references/paper.md,
references/supplement.md) and data/tables.json, not retyped, so a change to
either regenerates this file with the same wording.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "dist" / "eeg-ecg-music-review-agent" / "skill" / "psyp70385-eeg-ecg-music-scoping-review-paper"
PAPER_MD = PKG / "references" / "paper.md"
SUPP_MD = PKG / "references" / "supplement.md"
TABLES = ROOT / "data" / "tables.json"


def section(md, start_heading, end_heading=None):
    i = md.index(start_heading)
    j = md.index(end_heading, i + len(start_heading)) if end_heading else len(md)
    return md[i:j].strip()


def numbered_rules(text_):
    """Split '2.2 | Eligibility Criteria' body into its 6 numbered paragraphs."""
    body = text_.split("\n\n", 2)[-1]  # drop the heading and the lead-in sentence
    parts = re.split(r"\n\n(?=\d+\. )", body)
    rules = []
    for p in parts:
        m = re.match(r"^(\d+)\. (.+)$", p, flags=re.S)
        if not m:
            continue
        rules.append({"rule": int(m.group(1)), "text": re.sub(r"\s+", " ", m.group(2)).strip()})
    if len(rules) != 6:
        raise SystemExit(f"expected 6 eligibility rules, parsed {len(rules)}")
    return rules


def main():
    paper_md = PAPER_MD.read_text(encoding="utf-8")
    supp_md = SUPP_MD.read_text(encoding="utf-8")
    tables = json.loads(TABLES.read_text(encoding="utf-8"))

    # --- eligibility.json ---------------------------------------------
    elig_section = section(paper_md, "### 2.2 | Eligibility Criteria", "### 2.3")
    rules = numbered_rules(elig_section)
    appendix_s1 = section(supp_md, "## Appendix S1")
    eligibility = {
        "source": "Section 2.2 (Eligibility Criteria) and Appendix S1 (Framework) of Leimroth et al. 2026, doi:10.1111/psyp.70385",
        "inclusion_exclusion_rules": rules,
        "pcc_framework_markdown": appendix_s1,
    }
    (ROOT / "data" / "eligibility.json").write_text(json.dumps(eligibility, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- search_strings.json --------------------------------------------
    appendix_s2 = section(supp_md, "## Appendix S2")
    search = {
        "source": "Appendix S2 (Search Details) of Leimroth et al. 2026, doi:10.1111/psyp.70385",
        "databases": ["PsycInfo (including PsycArticles)", "PubMed", "Scopus", "Web of Science (core collection)", "Academic Search Complete (EBSCOhost)"],
        "initial_search_date": "2024-01-31",
        "update_search_date": "2025-08-10",
        "citation_searching_records": 10,
        "search_strings_markdown": appendix_s2,
    }
    (ROOT / "data" / "search_strings.json").write_text(json.dumps(search, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- charting_items.json ---------------------------------------------
    appendix_s3 = section(supp_md, "## Appendix S3")
    charting = {
        "source": "Appendix S3 (Data Items) of Leimroth et al. 2026, doi:10.1111/psyp.70385",
        "categories": {
            "publication_information": ["Author/Year", "Region", "Aim of Study", "Findings"],
            "participants": ["Audiology", "Musicianship", "Handedness", "Eligibility Criteria", "Sample Size", "Final Number Processed", "Sex", "Age"],
            "measures": {
                "eeg": ["Variables", "Electrode Configuration", "Electrode Type", "Impedance", "Referencing", "Filtering", "Hardware", "Sampling Frequency"],
                "ecg": ["Variables", "Electrode Configuration", "Recording Equipment", "Filtering", "Sampling Rate", "Blood Pressure/Respiration"],
            },
            "experimental_conditions": {
                "stimulus": ["Duration", "Musical Component Examined", "Style", "Source", "Delivery Method", "Intensity", "Selection", "Familiarity", "Attention to Stimulus"],
                "study_design": ["Hypothesis", "Room Details", "Time of Day", "Orientation", "Visual State", "Control/Baseline", "Power Analysis", "Ethics/Informed Consent"],
            },
        },
        "template_markdown": appendix_s3,
    }
    (ROOT / "data" / "charting_items.json").write_text(json.dumps(charting, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- table_footnotes.json --------------------------------------------
    footnotes = {}
    for t in tables:
        n = int(t["label"].split()[1])
        entries = {}
        for note in t["notes"]:
            m = re.match(r"^([a-z])\s+(.+)$", note, flags=re.S)
            if m:
                entries[m.group(1)] = m.group(2).strip()
        if entries:
            footnotes[str(n)] = entries
    (ROOT / "data" / "table_footnotes.json").write_text(json.dumps(footnotes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- review_metadata.json ---------------------------------------------
    metadata = {
        "citation": "Leimroth, S. R., Barry, R. J., De Blasio, F. M., & Byron, T. P. (2026). Exploring EEG and ECG in music listening: A scoping review. Psychophysiology, 63(9), e70385.",
        "doi": "10.1111/psyp.70385",
        "pubmed_id": "42693627",
        "pmc_id": "PMC13542476",
        "published_online": "2026-09-03",
        "received": "2026-05-18",
        "revised": "2026-08-18",
        "accepted": "2026-08-19",
        "licence": "CC BY 4.0",
        "open_access_pdf": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1111/psyp.70385",
        "preregistration": {"protocol": "https://osf.io/yx3rh", "project": "https://osf.io/xtznm"},
        "orcid": "0000-0003-3617-7994",
        "affiliation": "Brain & Behaviour Research Institute and School of Psychology, University of Wollongong",
        "methodology": ["Joanna Briggs Institute scoping review methodology", "PRISMA-ScR"],
        "prisma_flow": {
            "identified": 1214,
            "duplicates_removed": 596,
            "screened": 618,
            "excluded_at_screening": 581,
            "sought_for_retrieval": 37,
            "not_retrieved": 0,
            "assessed_for_eligibility": 37,
            "excluded_at_eligibility": 19,
            "included": 18,
        },
        "included_studies": 18,
        "first_authors": 13,
        "data_availability": "This scoping review did not generate or analyze primary experimental data; no original data or analysis code is associated with the manuscript.",
    }
    (ROOT / "data" / "review_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("wrote data/eligibility.json, data/search_strings.json, data/charting_items.json, data/table_footnotes.json, data/review_metadata.json")


if __name__ == "__main__":
    main()
