# psyp70385 MCP server

Tools over the charted evidence of:

> Leimroth, S. R., Barry, R. J., De Blasio, F. M., & Byron, T. P. (2026).
> Exploring EEG and ECG in music listening: A scoping review.
> *Psychophysiology*, 63(9), e70385. https://doi.org/10.1111/psyp.70385

Licensed CC BY 4.0. This server and the data it reads are derived from the
published article and its Supporting Information under that licence.

## What this is

A read-only server: no network calls, no writes, nothing executed from the
paper. Every tool returns data straight from the review's own charted tables
(Tables 1-7) and Supporting Information (Appendices S1-S3). It does not
summarise or interpret findings - for that, use the companion reading
package at `../../skill/psyp70385-eeg-ecg-music-scoping-review-paper/`.

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (the server declares its own
  dependencies inline; `uv run` installs them automatically)

No manual `pip install` is needed - `server.py` carries a PEP 723 inline
script header pinning `mcp<2` (and `pywin32` on Windows, needed for MCP's
stdio transport there).

## Running it directly

```bash
uv run server.py
```

This starts the server on stdio and waits for an MCP client to connect.

## Connecting from Claude Code

```bash
claude mcp add psyp70385 -- uv run /absolute/path/to/server.py
```

Verify with `claude mcp list` or `/mcp` inside Claude Code, then ask
something like:

> Which of the 18 studies in the psyp70385 review tested brain-heart
> interaction, and what did O'Kelly et al. (2013) report for EEG measures?

## Connecting from another MCP client

Any client that speaks MCP over stdio can launch `uv run server.py` as its
server command. See the `mcp` package's own client documentation for
non-Claude hosts.

## Tools

| Tool | What it does |
| --- | --- |
| `list_studies` | List the 18 included studies, filterable by region, brain-heart-interaction result, and year range. |
| `get_study` | Full charted record for one study by id. |
| `search_studies` | Case-insensitive substring search across all charted fields, or one named field. |
| `reporting_gaps` | Reporting completeness per charted item, with the paper's own stated percentage alongside where available. |
| `study_scorecard` | What one study left unreported, grouped by category. |
| `charting_template` | The review's data-charting items (Appendix S3), for charting a new study. |
| `eligibility_criteria` | The PCC framework (Appendix S1) and the 6 numbered inclusion/exclusion rules (section 2.2). |
| `screen_study` | Deterministically apply the 6 rules to a candidate study from yes/no answers. |
| `search_strategy` | Exact per-database search strings, search dates, and PRISMA flow counts. |
| `get_table_footnote` | Resolve a `^a`-style footnote marker for a given table number. |
| `review_metadata` | Citation, DOI, identifiers, licence, preregistration links. |

Plus one prompt, `chart_a_new_study`, that chains `charting_template` ->
fill from a new paper's text -> `screen_study`.

## Data

`data/*.json` are frozen copies of the tables and Supporting Information,
built from the published article (see the repository root's `tooling/` and
its own README for how - not runnable as committed, see that README for
why). They do not update automatically if the paper is corrected; rebuild
from `tooling/build_studies.py` and `tooling/build_metadata.py` if that
ever happens.

## Tests

```bash
uv run --with pytest --with "mcp[cli]<2" python -m pytest tests/test_tools.py -v
```

`python -m pytest` does not read `server.py`'s own inline script metadata
(that header only applies when a tool runs the file directly, e.g.
`uv run server.py`), so pytest's own `uv run` invocation must declare the
same dependencies explicitly. It must be the same version pin the server
carries (`mcp<2`): plain `--with mcp` resolves the current mcp 2.x release,
where `FastMCP` was renamed to `MCPServer` with a different API, and the
import in `server.py` breaks.

Every expected number in the tests comes from the paper's own stated
figures (section 4.2, Figure 1's PRISMA flow) or from the tables directly -
see the test file's own comments.
