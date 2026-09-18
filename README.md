# eeg-ecg-music-review-agent

Turns a published scoping review into two things an AI assistant can use
directly: a reading package, and a small tool server over its charted
evidence.

> Leimroth, S. R., Barry, R. J., De Blasio, F. M., & Byron, T. P. (2026).
> Exploring EEG and ECG in music listening: A scoping review.
> *Psychophysiology*, 63(9), e70385. https://doi.org/10.1111/psyp.70385
> (open access, CC BY 4.0)

The paper's authors are Scott R. Leimroth, Robert J. Barry, Frances M. De
Blasio and Timothy P. Byron. This tool - everything in this repository -
was built by Scott R. Leimroth alone; it is not a product of the paper's
other authors and its design or any error in it should not be attributed
to them.

**Licensing at a glance:** the code (`mcp/`, `tooling/`) is MIT licensed;
the paper's content (`skill/`, and the data files under `mcp/psyp70385-mcp/data/`)
is CC BY 4.0 with Wiley attribution. See [LICENSE](LICENSE) and
[LICENCE.md](LICENCE.md) respectively.

## Method

Built with the Paper2Agent method of Miao, Davis, Zhang, Pritchard and Zou
(2026), *Reimagining research papers as interactive and reliable AI
agents*, *Nature*. https://doi.org/10.1038/s41586-026-11044-y

## What's here

```
skill/psyp70385-eeg-ecg-music-scoping-review-paper/   the reading package
mcp/psyp70385-mcp/                                     the MCP tool server
tooling/                                               how they were built (reference; see tooling/README.md)
```

## The reading package

`skill/psyp70385-eeg-ecg-music-scoping-review-paper/` works with **any**
assistant that can read files - Claude, ChatGPT, Gemini, a local model, or
just you in a text editor. It's the paper's text as Markdown, its tables as
CSV, its PRISMA flow diagram as a JPEG, with a navigation index
(`references/index.md`). Point an assistant at the folder, or copy it under
a skills directory if your host supports that convention (e.g. Claude
Code's `~/.claude/skills/`), and ask it questions about the review.

## The MCP server

`mcp/psyp70385-mcp/` works with **any** [MCP](https://modelcontextprotocol.io/)
client - it's a standard stdio server built on the MCP Python SDK. Eleven
read-only tools over the 18 included studies' charted data (participants,
EEG measures, ECG measures, stimulus, study design, findings), the
review's eligibility criteria, search strategy, and reporting-gap
statistics - plus a prompt for charting a new study against the review's
own method. See [mcp/psyp70385-mcp/USAGE.md](mcp/psyp70385-mcp/USAGE.md)
for the full tool list.

Requires [`uv`](https://docs.astral.sh/uv/); no manual dependency
installation needed, since `server.py` declares its own.

**Claude Code:**

```bash
claude mcp add psyp70385 -- uv run /absolute/path/to/mcp/psyp70385-mcp/server.py
```

**Any other MCP client:** launch `uv run server.py` (from inside
`mcp/psyp70385-mcp/`) as the server command over stdio.

## Licence

See [LICENSE](LICENSE) (MIT, for the code) and [LICENCE.md](LICENCE.md)
(CC BY 4.0 with Wiley attribution, for the paper's content).

## Provenance

`tooling/` documents how both were built from the published PDF and its
Supporting Information - see [tooling/README.md](tooling/README.md) for
why those scripts aren't runnable as committed here.

This repository is a derived publication of a working copy Scott
Leimroth maintains privately. It is a one-way export, not a mirror: it
does not sync automatically, and it is not the place to send fixes or pull
requests against the underlying build process (only against this
snapshot's own content, e.g. a documentation typo). If you find a
correctness problem with the reading package or the tool server's data,
open an issue here describing it - it will be fixed upstream and
re-exported, not patched in place here.
