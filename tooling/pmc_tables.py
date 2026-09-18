#!/usr/bin/env python3
"""Extract Tables 1-7 of doi:10.1111/psyp.70385 from the Europe PMC JATS XML
(PMC13542476) into data/tables.json: header, rows (all cells as strings),
caption and footnotes. A superscript footnote marker is rendered as a caret
plus the letter (e.g. '12^a'), never run together with the value, so the
marker is unambiguous in the CSVs and can be reliably stripped when a table
is joined into a study record by author/year."""
import json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources" / "PMC13542476-fulltext.xml"
OUT = ROOT / "data" / "tables.json"

def text(e):
    if e is None:
        return ""
    parts = []
    def walk(n):
        if n.tag == "break":
            parts.append(" ")
        if n.tag == "xref" and n.get("ref-type") == "table-fn":
            marker = "".join(n.itertext()).strip()
            if marker:
                parts.append("^" + marker)  # unambiguous marker, never fused with the preceding digit/word
            return
        if n.text:
            parts.append(n.text)
        for c in n:
            walk(c)
            if c.tail:
                parts.append(c.tail)
    walk(e)
    s = "".join(parts)
    s = s.replace("\u00a0", " ").replace("\u202f", " ")
    return re.sub(r"\s+", " ", s).strip()

root = ET.parse(SRC).getroot()
tables = []
for tw in root.iter("table-wrap"):
    label = text(tw.find("label"))
    caption = text(tw.find("caption"))
    tab = tw.find(".//table")
    header = [text(th) for th in tab.find("thead").iter("th")]
    rows = []
    for tr in tab.find("tbody").findall("tr"):
        cells = [text(td) for td in tr.findall("td")]
        if len(cells) != len(header):
            sys.exit(f"{label}: row has {len(cells)} cells, header {len(header)}: {cells[:2]}")
        rows.append(cells)
    foot = tw.find("table-wrap-foot")
    notes = []
    if foot is not None:
        for fn in foot.iter("fn"):
            lab = text(fn.find("label"))
            body = text(fn.find("p")) if fn.find("p") is not None else text(fn)
            notes.append((lab + " " + body).strip() if lab else body)
        for p in foot.findall("p"):
            notes.append(text(p))
        if not notes:
            notes.append(text(foot))
    tables.append({"label": label, "caption": caption, "header": header, "rows": rows, "notes": notes})
OUT.write_text(json.dumps(tables, ensure_ascii=False, indent=1), encoding="utf-8")
for t in tables:
    print(t["label"], t["caption"], len(t["rows"]), "rows x", len(t["header"]), "cols;", len(t["notes"]), "notes")
