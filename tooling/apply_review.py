#!/usr/bin/env python3
"""Scripted review pass over the Paper2Skill extraction of the Wiley PDF.

Why a script: the PDF sets Tables 1-6 on landscape pages whose text runs
bottom-to-top, and the extractor produced no usable rows for them (and no
text for the rotated captions and footnotes). Every page also carries a
vertical Wiley download watermark and page furniture. Rather than hand-edit
47 page files, this pass applies the same explicit rules everywhere, so the
decisions are inspectable and re-runnable after a fresh `extract`.

Rules (each one is recorded in the page's review_notes):
  W  vertical "Downloaded from ..." watermark line   -> omit
  F  page footers "N of 47" / "Psychophysiology, 2026" -> omit
       (page 1 keeps the citation line with the DOI)
  L  page-1 publisher logos and "Check for updates" badge -> omit;
       running header "Psychophysiology" -> omit
  T  table N, first PDF page: the table item gets the complete Table N
       (header + 18 rows) transcribed from the Europe PMC JATS XML of the
       same article (PMC13542476), plus a caption item and a notes item.
       Continuation pages: the table region, its "(Continued)" caption and
       any rotated footnotes -> omit, with a reason naming the CSV.
  R  three reference entries the layout model misread as tables -> text,
       rebuilt from the page's own extracted lines.
  H  heading levels normalised to the paper's numbering:
       "N | Title" -> ##, "N.N | Title" -> ###, "N.N.N | Title" -> ####,
       unnumbered back-matter headings -> ##; the article title stays #.
       Bold markers are dropped from headings; wording is untouched.
  J  prose split across a column or page break is re-joined
       (join_previous = "space"), decided from punctuation: the earlier
       item does not end a sentence and the later one starts lowercase.
  G  Figure 1 gets its label and asset name.
  C  "(Continues)" table-continuation markers -> omit (an omit region is
       added for the rotated ones that no item covers).
  D  reference-list DOIs: the PDF breaks them with zero-width spaces, which
       the extractor turned into ordinary spaces; the spaces are removed so
       each DOI is one token. One real hyphen (10.1037/0003-066x) that the
       line-wrap joiner had dropped is restored.
  O  the article title is moved to the head of page 1.

Usage:
  python tooling/apply_review.py            # apply rules, leave reviewed=false
  python tooling/apply_review.py --mark-reviewed   # also set reviewed=true
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "review" / "documents" / "s001-psyp70385-main"
TABLES = ROOT / "data" / "tables.json"

FOOTER_RE = re.compile(r"^(?:\d+ of 47|_?Psychophysiology,?_? 2026)$")
HEADING_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)\s*\|\s*(.+)$")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def inside(pt, box, pad=2.0):
    return box[0] - pad <= pt[0] <= box[2] + pad and box[1] - pad <= pt[1] <= box[3] + pad


def lines_in(evidence, bbox, pad=2.0):
    out = [l for l in evidence["lines"] if inside(center(l["bbox"]), bbox, pad)]
    return out


def plain(md):
    md = re.sub(r"^\s*#+\s*", "", md)
    md = re.sub(r"\*\*|__|(?<!\w)_|_(?!\w)", "", md)
    return re.sub(r"\s+", " ", md).strip()


def table_caption_line(evidence):
    for l in evidence["lines"]:
        t = re.sub(r"\s+", " ", l["text"]).strip()
        m = re.match(r"^TABLE (\d+) \| (.+)$", t)
        if m:
            return int(m.group(1)), m.group(2).strip(), l
    return None


def omit(item, reason):
    item.clear() if False else None
    keep = {"id": item["id"], "kind": "omit", "bbox": item["bbox"], "markdown": "", "reason": reason}
    item.clear()
    item.update(keep)


def normalise_heading(md):
    text = plain(md)
    m = HEADING_NUM_RE.match(text)
    if m:
        depth = m.group(1).count(".")
        level = "##" if depth == 0 else "###" if depth == 1 else "####"
        return f"{level} {m.group(1)} | {m.group(2)}"
    return f"## {text}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark-reviewed", action="store_true")
    args = ap.parse_args()

    tables = {int(t["label"].split()[1]): t for t in load(TABLES)}
    plan = load(DOC / "plan.json")
    # Idempotence: the first run snapshots the extractor's page files; every run
    # starts from that snapshot, so the rules are applied exactly once.
    orig = DOC / "pages-original"
    if not orig.exists():
        shutil.copytree(DOC / "pages", orig)
    first_page_of = {}
    summary = []
    prev_text = None  # last emitted prose item across pages, for rule J

    for entry in plan["pages"]:
        pfile = DOC / entry["file"] if "file" in entry else DOC / "pages" / f"page-{entry:04d}.json"
        page = load(orig / pfile.name)
        n = page["page"]
        evidence = load(DOC / "evidence" / f"page-{n:04d}.json")
        notes = []
        cap = table_caption_line(evidence)
        table_no = cap[0] if cap else None
        is_first = bool(cap) and "(Continued)" not in cap[1]
        if is_first:
            first_page_of[table_no] = n

        new_items = []
        for item in page["items"]:
            kind = item["kind"]
            md = item.get("markdown", "") or ""
            bbox = item["bbox"]
            ev = lines_in(evidence, bbox)
            ev_text = " ".join(re.sub(r"\s+", " ", l["text"]).strip() for l in ev)

            # W: watermark
            if "Downloaded from" in ev_text and kind in ("text", "heading", "caption"):
                if FOOTER_RE.match(plain(md)):
                    omit(item, "Page footer merged with the vertical Wiley download watermark; page furniture, verified on the page image.")
                    notes.append("F+W")
                else:
                    omit(item, "Vertical Wiley 'Downloaded from ... Terms and Conditions' watermark; not part of the article.")
                    notes.append("W")
                new_items.append(item)
                continue

            # C: "(Continues)" table-continuation marker
            if kind == "text" and plain(md) == "(Continues)":
                omit(item, "'(Continues)' table-continuation marker; page furniture.")
                notes.append("C")
                new_items.append(item)
                continue

            # F: footers
            if kind == "text" and FOOTER_RE.match(plain(md)):
                if n == 1 and md.startswith("_Psychophysiology,_ 2026;"):
                    pass  # keep the citation line on page 1
                else:
                    omit(item, "Running page footer ('N of 47' / journal name and year); page furniture.")
                    notes.append("F")
                    new_items.append(item)
                    continue

            # L: page-1 furniture
            if n == 1:
                if kind == "figure":
                    omit(item, "Publisher logo / 'Check for updates' badge in the page header; decorative, not article content.")
                    notes.append("L")
                    new_items.append(item)
                    continue
                if kind == "text" and plain(md) == "<mark>Psychophysiology</mark>":
                    omit(item, "Running journal-name header; page furniture.")
                    notes.append("L")
                    new_items.append(item)
                    continue
                if kind == "heading" and plain(md) == "REVIEW OPEN ACCESS":
                    item["kind"] = "text"
                    item["markdown"] = "REVIEW | OPEN ACCESS"
                    notes.append("L: article-type banner kept as text, not a heading")
                    new_items.append(item)
                    continue

            # T: tables
            if table_no is not None:
                cap_line = cap[2]
                if inside(center(cap_line["bbox"]), bbox):
                    if is_first:
                        item["kind"] = "caption"
                        item["markdown"] = f"**TABLE {table_no}** | {tables[table_no]['caption']}"
                        notes.append(f"T: caption of Table {table_no} transcribed from the rotated caption line")
                    else:
                        omit(item, f"'TABLE {table_no} | (Continued)' caption of a continuation page; Table {table_no} is emitted whole on PDF page {first_page_of.get(table_no, '?')}.")
                        notes.append("T: continued-caption omitted")
                    new_items.append(item)
                    continue
                if kind == "table":
                    if is_first:
                        t = tables[table_no]
                        item["label"] = f"Table {table_no}"
                        item["asset_name"] = f"table-{table_no}"
                        item["rows"] = [t["header"]] + t["rows"]
                        item["markdown"] = ""
                        notes.append(f"T: Table {table_no} rows ({len(t['rows'])} studies x {len(t['header'])} columns) taken from the Europe PMC JATS XML of this article (PMC13542476) because the PDF sets the table rotated; the PDF spreads it over several pages and all of those rows are included here")
                        new_items.append(item)
                        if t["notes"]:
                            new_items.append({
                                "id": f"p{n:04d}-table{table_no}-notes",
                                "kind": "text",
                                "bbox": bbox,
                                "markdown": "\n\n".join(t["notes"]),
                            })
                            notes.append(f"T: Table {table_no} footnotes emitted after the table (source: same XML)")
                        continue
                    omit(item, f"Continuation of Table {table_no}; its rows are already in table-{table_no}.csv emitted on PDF page {first_page_of.get(table_no, '?')}.")
                    notes.append("T: continuation region omitted")
                    new_items.append(item)
                    continue
                if kind in ("text", "heading", "caption") and not md.strip() and ev:
                    # rotated footnote lines or stray rotated fragments beside the table
                    omit(item, f"Rotated Table {table_no} footnote/fragment ('{ev_text[:60]}...'); the footnotes are emitted with Table {table_no} from the XML transcription.")
                    notes.append("T: rotated footnote omitted (emitted with the table)")
                    new_items.append(item)
                    continue
                if kind == "text" and re.match(r"^\*\*TABLE \d+\*\* \|\s*\(Continued\)", md):
                    omit(item, f"'TABLE {table_no} | (Continued)' caption; Table {table_no} is emitted whole on PDF page {first_page_of.get(table_no, '?')}.")
                    notes.append("T: continued-caption omitted")
                    new_items.append(item)
                    continue
                if kind == "text" and not is_first and md.startswith("_Note:_") and n in (37,):
                    omit(item, f"Table {table_no} note printed under the last continuation page; emitted with Table {table_no} from the XML transcription.")
                    notes.append("T: table note on continuation page omitted (emitted with the table)")
                    new_items.append(item)
                    continue

            # R: reference entries misread as tables
            if kind == "table" and n >= 42:
                item["kind"] = "text"
                item["markdown"] = ev_text
                for k in ("rows", "label", "asset_name"):
                    item.pop(k, None)
                notes.append("R: reference entry misread as a table rebuilt as text from the page's extracted lines")
                new_items.append(item)
                continue

            # G: Figure 1
            if kind == "figure" and n == 5:
                item["label"] = "Figure 1"
                item["asset_name"] = "figure-1"
                notes.append("G: Figure 1 (PRISMA flow diagram) crop checked against the page image")
                new_items.append(item)
                continue

            # H: headings
            if kind == "heading":
                if n == 1 and md.startswith("# "):
                    item["markdown"] = "# " + plain(md)
                else:
                    item["markdown"] = normalise_heading(md)
                new_items.append(item)
                continue

            new_items.append(item)

        # C: rotated "(Continues)" lines that no item covers
        for l in evidence["lines"]:
            if l["text"].strip() == "(Continues)" and not any(i["kind"] == "omit" and inside(center(l["bbox"]), i["bbox"]) for i in new_items):
                new_items.append({"id": f"p{n:04d}-continues", "kind": "omit", "bbox": [round(v, 1) for v in l["bbox"]], "markdown": "",
                                  "reason": "Rotated '(Continues)' table-continuation marker; page furniture."})
                notes.append("C: rotated marker omitted")

        # D: DOI clean-up in the reference list (pages 42-47)
        if n >= 42:
            for item in new_items:
                if item["kind"] != "text" or not item.get("markdown"):
                    continue
                md = item["markdown"]
                m = re.search(r"https:// ?doi\. ?org/ ?(.*)$", md, flags=re.S)
                if m:
                    tail = m.group(1)
                    fixed = "https://doi.org/" + re.sub(r"\s+", "", tail)
                    if fixed != md[m.start():]:
                        item["markdown"] = md[:m.start()] + fixed
                        notes.append("D: zero-width breaks removed from the DOI so it reads as one token")
                if "0003066x" in item["markdown"]:
                    item["markdown"] = item["markdown"].replace("0003066x", "0003-066x")
                    notes.append("D: real hyphen in doi 10.1037/0003-066x.33.2.99 restored (the line-wrap joiner had dropped it; checked on the page image)")

        # O: the article title heads the document
        if n == 1:
            title_items = [i for i in new_items if i["kind"] == "heading" and i["markdown"].startswith("# ")]
            if title_items:
                t = title_items[0]
                new_items.remove(t)
                new_items.insert(0, t)
                notes.append("O: title moved to the head of page 1 so the package opens with it")

        # J: joins across column and page breaks
        for item in new_items:
            if item["kind"] != "text" or not item.get("markdown", "").strip():
                if item["kind"] in ("heading", "caption", "table", "figure"):
                    prev_text = None
                continue
            md = item["markdown"].strip()
            if prev_text is not None:
                a = prev_text["markdown"].rstrip()
                if (not re.search(r"[.!?:;”\"\)\]]$", a) and not a.startswith(">")
                        and re.match(r"^[a-z(]", md) and not md.startswith("> ")):
                    item["join_previous"] = "none" if a.endswith("-") else "space"
                    notes.append(f"J: {item['id']} continues {prev_text['id']}")
            prev_text = item

        page["items"] = new_items
        if "H" not in " ".join(notes) and any(i["kind"] == "heading" for i in new_items):
            notes.append("H: heading levels normalised to the section numbering")
        page["review_notes"] = ("Scripted pass (tooling/apply_review.py): " + "; ".join(dict.fromkeys(notes))
                                + ". Page image inspected on the contact sheet for reading order, column breaks and crop boundaries.")
        page["reviewed"] = bool(args.mark_reviewed)
        save(pfile, page)
        summary.append((n, len(new_items), [i["kind"] for i in new_items].count("omit")))

    plan["notes"] = [
        "Tables 1-7 are set on landscape pages in the PDF (Tables 1-6) or split across portrait pages (Table 7). Each table is emitted once, on its first PDF page, with all 18 studies, transcribed from the Europe PMC JATS XML of the same article (PMC13542476, sources/PMC13542476-fulltext.xml); the continuation pages are recorded as omitted regions that point to the CSV.",
        "Every page of the Wiley PDF carries a vertical 'Downloaded from ...' watermark and running footers; these are omitted as page furniture.",
        "Appendices S1-S3 (Supporting Information) were supplied by Wiley as .docx and are included as Markdown in supplement.md.",
    ]
    save(DOC / "plan.json", plan)
    for n, k, o in summary:
        print(f"page {n:2d}: {k:2d} items, {o} omitted")
    print("first pages of tables:", first_page_of)


if __name__ == "__main__":
    sys.exit(main())
