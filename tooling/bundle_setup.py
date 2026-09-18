#!/usr/bin/env python3
"""Fill review/bundle.json after `paper_bundle.py prepare`: source roles and
titles, package notes, and the curated navigation index."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "review" / "bundle.json"

ROLES = {
    "s001-psyp70385-main": ("main", "Exploring EEG and ECG in Music Listening: A Scoping Review (Psychophysiology 63(9), e70385, 2026)"),
    "s002-appendix-s1": ("supplement", "Appendix S1: Framework (Population, Concept, Context)"),
    "s003-appendix-s2": ("supplement", "Appendix S2: Search Details"),
    "s004-appendix-s3": ("supplement", "Appendix S3: Data Items"),
}

NAV = [
    ("references/paper.md", "## ABSTRACT", "One-paragraph summary: aim, 18 papers, heterogeneous EEG and cardiac findings, call for standardisation"),
    ("references/paper.md", "## 1 | Introduction", "Background on music, EEG, ECG, rhythmic patterns and brain-heart interaction; the review's objective (1.4)"),
    ("references/paper.md", "## 2 | Methods", "Preregistration, eligibility criteria (2.2), databases (2.3), search strategy (2.4), study selection and PRISMA flow (2.5), data charting (2.6)"),
    ("references/paper.md", "### 2.2 | Eligibility Criteria", "The six inclusion/exclusion rules applied to studies"),
    ("references/paper.md", "## 3 | Results", "Charted data on the 18 studies; Tables 1-7 sit inside this section"),
    ("references/paper.md", "### 3.1 | Publication Information", "Authors, years, regions, aims and findings (Table 1)"),
    ("references/paper.md", "### 3.2 | Participants", "Audiology, musicianship, handedness, eligibility, sample size, sex, age (Table 2)"),
    ("references/paper.md", "### 3.3 | Measures", "EEG measures (Table 3), ECG measures (Table 4), synchronisation, peak detection and cardiac artefacts"),
    ("references/paper.md", "### 3.4 | Experimental Conditions", "Stimulus details (Table 5) and study design (Table 6)"),
    ("references/paper.md", "### 3.5 | Findings", "Reported EEG, ECG and EEG-ECG interaction findings (Table 7)"),
    ("references/paper.md", "## 4 | Discussion", "Publication pattern, methodological gaps by category, findings, brain-heart interaction, limitations (4.7), conclusions (4.8)"),
    ("references/paper.md", "### 4.7 | Limitations", "What the review cannot say and why"),
    ("references/paper.md", "## Data Availability Statement", "No primary data or code; OSF preregistration links"),
    ("references/paper.md", "## References", "The 173 cited works"),
    ("references/supplement.md", "## Appendix S1: Framework (Population, Concept, Context)", "Inclusion and exclusion criteria by PCC category"),
    ("references/supplement.md", "## Appendix S2: Search Details", "Exact search strings per database"),
    ("references/supplement.md", "## Appendix S3: Data Items", "The charting template: every data item extracted per study"),
]

b = json.loads(B.read_text(encoding="utf-8"))
REVIEW_NOTES = {
    "s001-psyp70385-main": "All 47 pages inspected on the review-aid contact sheets; per-page decisions are scripted in tooling/apply_review.py and recorded in each page's review_notes; Tables 1-7 taken from the article's Europe PMC XML because the PDF sets them rotated.",
    "s002-appendix-s1": "Converted from the Wiley .docx (one 5x3 table) with tooling; every cell compared with the .docx text; multi-line cells joined with '; '.",
    "s003-appendix-s2": "Converted from the Wiley .docx (one 7x2 table of search strings); every cell compared with the .docx text; multi-line cells joined with '; '.",
    "s004-appendix-s3": "Converted from the Wiley .docx (one 8x2 table of charting items); every cell compared with the .docx text; multi-line cells joined with '; '.",
}
for s in b["sources"]:
    s["role"], s["title"] = ROLES[s["id"]]
    s["reviewed"] = True
    s["review_notes"] = REVIEW_NOTES[s["id"]]
b["notes"] = [
    "Main document is the Wiley open-access PDF (CC BY 4.0) of doi:10.1111/psyp.70385, published 3 September 2026.",
    "Appendices S1 to S3 were supplied by Wiley as .docx and converted to Markdown tables for this package; the .docx originals are kept in sources/.",
    "The review generated no primary data or code (Data Availability Statement); protocol preregistered at osf.io/yx3rh.",
]
b["navigation"] = [{"file": f, "heading": h.lstrip("# "), "purpose": p} for f, h, p in NAV]  # index wants heading text without the # markers
B.write_text(json.dumps(b, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("bundle.json: roles, notes and navigation set")
