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
OPTIONAL_RE = re.compile(r"\b(opsional|optional|bonus|shtes[eë])\b", re.I)


def read_pdf(path):
    try:
        import pypdf
    except ImportError:
        raise SystemExit("Reading PDF needs the 'pypdf' package (pip install pypdf).")
    reader = pypdf.PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return re.sub(r"&amp;", "&", re.sub(r"&lt;", "<", re.sub(r"&gt;", ">", text)))


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


def split_items(text):
    lines = [l for l in text.split("\n") if l.strip()]
    items, current = [], None
    for line in lines:
        m = HEADING.match(line)
        if m:
            current = {"number": int(m.group(1)), "title": m.group(2).strip(), "body": []}
            items.append(current)
        elif current is not None:
            current["body"].append(line)
    if len(items) < 2:  # no numbered structure: fall back to bullets
        items = [{"number": i + 1, "title": BULLET.match(l).group(1), "body": []}
                 for i, l in enumerate(x for x in lines if BULLET.match(x))]
    out = []
    for i, it in enumerate(items, 1):
        body = " ".join(it["body"]).strip()
        full = f"{it['title']} {body}".strip()
        m_min = MIN_RE.search(full)
        m_pts = POINTS_RE.search(full)
        out.append({
            "id": f"R{i}",
            "number": it["number"],
            "title": it["title"],
            "text": body or it["title"],
            "mandatory": not OPTIONAL_RE.search(full),
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
