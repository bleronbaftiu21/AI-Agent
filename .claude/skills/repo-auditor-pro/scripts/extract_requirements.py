"""Extract text from a requirements brief (PDF, DOCX, MD, TXT) and split it into numbered items R1, R2, ...

PDF needs the `pypdf` package; everything else uses the standard library. Usage:
    python -I extract_requirements.py --file BRIEF.pdf [--out FILE]
    python -I extract_requirements.py --text-file pasted.txt [--out FILE]
"""
import argparse
import json
import os
import re
import sys
import zipfile

HEADING = re.compile(r"^\s*(?:R\s*)?(\d{1,3})\s*[.)\-:]\s+(\S.*)$")
BULLET = re.compile(r"^\s*(?:[-*•●▪]|[a-z]\))\s+(\S.*)$")
MIN_RE = re.compile(r"\b(?:minimum|min\.?|te pakten|të paktën|at least|>=)\s*(\d+)", re.I)
POINTS_RE = re.compile(r"\(?\b(\d+(?:[.,]\d+)?)\s*(?:pik[eë]|points?|pts|p)\b\)?", re.I)
OPTIONAL_RE = re.compile(r"\b(opsional\w*|optional|bonus|shtes[eë]|mund[eë]si)\b", re.I)
MD_HEADING = re.compile(r"^(#{1,6})\s+(\S.*)$")
# schedule/logistics lines are not requirements of the software ("Faza 1: 13 prill dorëzimi ...")
SCHEDULE_RE = re.compile(r"\b(dor[eë]zim\w*|prezantim\w*|deadline|due date|submission)\b", re.I)
# a plain paragraph that states an obligation is a requirement even when it is not a list item
OBLIGATION_RE = re.compile(r"\b(duhet|obligativ\w*|must|shall|required|kërkohet|kerkohet)\b", re.I)


def read_pdf(path):
    try:
        import pypdf
    except ImportError:
        raise SystemExit("Reading PDF needs the 'pypdf' package (pip install pypdf).")
    reader = pypdf.PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def read_docx(path):
    """Word -> Markdown-like text: headings become '#'/'##', list paragraphs (bullets/numbering) become '- '.
    Only <w:t> text is kept, so drawing positions and other XML values do not leak into the text."""
    import html
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    lines = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        p = re.sub(r"<w:tab/>", "<w:t>\t</w:t>", p)
        text = html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", p))).strip()
        if not text:
            continue
        style = (re.search(r'<w:pStyle w:val="([^"]+)"', p) or [None, ""])[1]
        level = re.search(r"(?i)(?:heading|titull\w*|kryetitull\w*)\s*(\d)", style)
        if level or style.lower() in ("title", "titulli"):
            lines.append("#" * (int(level.group(1)) if level else 1) + " " + text)
        elif "<w:numPr>" in p or re.match(r"(?i)list", style):
            lines.append("- " + text)
        else:
            lines.append(text)
    return "\n".join(lines)


def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return read_pdf(path)
    if ext == ".docx":
        return read_docx(path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def normalize(text):
    text = text.replace("\r", "")
    text = re.sub(r"[ \t ]+", " ", text)
    return "\n".join(line.strip() for line in text.split("\n"))


def numbered_items(lines):
    """Briefs written as '1. Title' followed by explanation lines."""
    items, current, section = [], None, ""
    for line in lines:
        h = MD_HEADING.match(line)
        m = HEADING.match(line)
        if m:
            current = {"title": m.group(2).strip(), "body": [], "section": section}
            items.append(current)
        elif h and current is None:
            section = h.group(2).strip()
        elif current is not None:
            current["body"].append(MD_HEADING.sub(r"\2", line))
    return items


def structured_items(lines):
    """Briefs written as headings with bullet lists (typical Word documents): every bullet is one requirement,
    labelled with the headings above it. Paragraphs that state an obligation ('duhet', 'must') also count."""
    items, stack = [], {}
    for line in lines:
        h = MD_HEADING.match(line)
        if h and re.fullmatch(r"[-_=*.\s]+", h.group(2)):
            continue  # a separator line styled as a heading
        if h:
            level = len(h.group(1))
            stack = {k: v for k, v in stack.items() if k < level}
            stack[level] = h.group(2).strip()
            continue
        b = BULLET.match(line)
        text = b.group(1).strip() if b else line.strip()
        if not b and not (stack and OBLIGATION_RE.search(text) and len(text) < 400):
            continue
        if SCHEDULE_RE.search(text) or re.fullmatch(r"[-_=*\s]+", text) or len(text) < 4:
            continue
        section = " › ".join(stack[k] for k in sorted(stack))
        items.append({"title": text if len(text) <= 140 else text[:137].rstrip() + "…", "body": [text] if len(text) > 140 else [],
                      "section": section})
    return items


def section_items(lines):
    """Last resort: one requirement per heading, with the heading's text as the body."""
    items, current = [], None
    for line in lines:
        h = MD_HEADING.match(line)
        if h:
            current = {"title": h.group(2).strip(), "body": [], "section": ""}
            items.append(current)
        elif current is not None:
            current["body"].append(BULLET.sub(r"\1", line))
    return [i for i in items if i["body"]]


def split_items(text):
    lines = [l for l in text.split("\n") if l.strip()]
    items = numbered_items(lines)
    if len(items) < 2:
        items = structured_items(lines)
    if len(items) < 2:
        items = section_items(lines)
    out = []
    for i, it in enumerate(items, 1):
        body = " ".join(it["body"]).strip()
        full = f"{it['section']} {it['title']} {body}".strip()
        m_min = MIN_RE.search(full)
        m_pts = POINTS_RE.search(f"{it['title']} {body}")
        out.append({
            "id": f"R{i}",
            "number": i,
            "section": it["section"],
            "title": it["title"],
            "text": body or it["title"],
            "mandatory": not OPTIONAL_RE.search(f"{it['title']} {body}"),
            "min_count": int(m_min.group(1)) if m_min else None,
            "points": float(m_pts.group(1).replace(",", ".")) if m_pts else None,
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file")
    src.add_argument("--text-file")
    ap.add_argument("--out")
    args = ap.parse_args()
    path = args.file or args.text_file
    text = normalize(read_any(path))
    items = split_items(text)
    result = {"source": os.path.basename(path), "characters": len(text), "items": items, "text": text,
              "note": "Automatic split - check the list against the brief before grading."}
    data = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(data)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"source": result["source"], "items": len(items),
                      "titles": [f"{i['id']}: {i['title']}" for i in items]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
