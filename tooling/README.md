# tooling/

These scripts document how `skill/` and `mcp/psyp70385-mcp/data/` were
built from the published article and its Supporting Information: extracting
Tables 1-7 from the article's Europe PMC XML (`pmc_tables.py`), the
scripted per-page review pass applied to the [Paper2Agent](https://github.com/jmiao24/Paper2Agent)
extraction (`apply_review.py`, `bundle_setup.py`, `adjudicate.py`), joining
the tables into one record per study (`build_studies.py`), and building the
MCP server's remaining data files (`build_metadata.py`, `sync_mcp_data.py`).

**They are not runnable as committed here.** Each one resolves paths like
`sources/`, `review/` and a repo-root `data/` relative to its own location,
and those directories - the original PDF, the appendices, and the
Paper2Skill working evidence for all 47 pages - are not included in this
public repository (they add no value beyond what `skill/` and
`mcp/psyp70385-mcp/data/` already contain in finished form, and the review
evidence tree alone is tens of megabytes of per-page working files). They
are included here for transparency and reproducibility: to run them again,
start from the published PDF and Supporting Information yourself, in the
layout each script's own docstring describes.
