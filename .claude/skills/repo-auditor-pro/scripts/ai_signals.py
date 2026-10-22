"""Collect per-file indicators of AI-assisted code. Indicators only — never proof.

Read-only: only reads files. Usage:
    python -I ai_signals.py --repo REPO [--out FILE]
"""
import argparse
import json
import os
import re
import sys

EXCLUDED_DIRS = {
    ".git", "node_modules", "vendor", "venv", ".venv", "env", "dist", "build", "target", "bin", "obj",
    "__pycache__", ".next", ".nuxt", "coverage", ".idea", ".vscode", ".gradle", "Pods",
}
SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".scala", ".c", ".h", ".cpp",
    ".cc", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".dart", ".lua", ".r", ".sql", ".sh",
    ".ps1", ".vue", ".svelte", ".html", ".css", ".scss",
}
DOC_EXTS = {".md", ".rst", ".txt"}

STRONG = [
    ("assistant_phrase", re.compile(r"\b(as an ai( language model)?|i'm sorry, but|certainly!|sure! here|here'?s (the|an?) "
                                    r"(updated|complete|full|revised|improved) (code|version|implementation))", re.I)),
    ("elision_marker", re.compile(r"(rest of (the|your) code (remains|stays)|existing code (remains|here)|"
                                  r"\.\.\. ?(previous|existing|other) (code|methods|imports)|unchanged code)", re.I)),
    ("markdown_fence_in_source", re.compile(r"^\s*```[a-zA-Z]*\s*$", re.M)),
    ("chat_reference", re.compile(r"\b(chatgpt|openai|copilot|claude|gemini|as requested in the prompt)\b", re.I)),
]
MEDIUM = [
    ("step_comment", re.compile(r"(#|//|--)\s*(step \d+|first,|next,|finally,|now we|let's|we (will|need to|can) )", re.I)),
    ("placeholder", re.compile(r"(your[_-]?(api[_-]?key|secret|password|token|database|db)[_-]?(here)?|"
                               r"replace (this|with your)|example\.com|<your[-_ ]\w+>)", re.I)),
    ("obvious_comment", re.compile(r"(#|//)\s*(import (the )?(necessary|required) (libraries|modules|packages)|"
                                   r"define (the|a) (function|class|variable)|initiali[sz]e (the )?variables?|"
                                   r"return the result|main function|create (an? )?instance)", re.I)),
]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿✅❌✨]")
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|--|<!--|\"\"\"|''')")
DOCSTRING = re.compile(r'(""".*?"""|\'\'\'.*?\'\'\'|/\*\*.*?\*/)', re.S)
FUNC_DEF = re.compile(r"^\s*(def |async def |function |public |private |protected |static |func |fn )", re.M)


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in SOURCE_EXTS or ext in DOC_EXTS:
                yield os.path.join(dirpath, name), ext


def line_hits(pattern, text, limit=5):
    hits = []
    for m in pattern.finditer(text):
        hits.append(text.count("\n", 0, m.start()) + 1)
        if len(hits) >= limit:
            break
    return hits


def analyze(path, ext):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return None
    if len(text) > 1_000_000 or ".min." in path:
        return None
    lines = text.splitlines()
    nonblank = [l for l in lines if l.strip()]
    info = {"lines": len(nonblank), "signals": []}
    is_doc = ext in DOC_EXTS
    for name, pat in STRONG:
        if is_doc and name == "markdown_fence_in_source":
            continue
        hits = line_hits(pat, text)
        if hits:
            info["signals"].append({"name": name, "strength": "strong", "lines": hits})
    for name, pat in MEDIUM:
        hits = line_hits(pat, text)
        if hits:
            info["signals"].append({"name": name, "strength": "medium", "count": len(pat.findall(text)), "lines": hits})
    emojis = len(EMOJI.findall(text))
    if emojis >= (5 if is_doc else 3):
        info["signals"].append({"name": "emoji_heavy", "strength": "medium" if is_doc else "weak", "count": emojis})
    if not is_doc and nonblank:
        comments = sum(1 for l in nonblank if COMMENT_LINE.match(l))
        ratio = comments / len(nonblank)
        info["comment_ratio"] = round(ratio, 3)
        if ratio >= 0.35 and len(nonblank) >= 40:
            info["signals"].append({"name": "very_high_comment_ratio", "strength": "medium", "value": round(ratio, 3)})
        funcs = len(FUNC_DEF.findall(text))
        docs = len(DOCSTRING.findall(text))
        if funcs >= 5 and docs >= funcs * 0.9:
            info["signals"].append({"name": "docstring_on_every_function", "strength": "weak", "functions": funcs, "docstrings": docs})
        if ext in {".py", ".ts", ".tsx"} and funcs >= 5:
            typed = len(re.findall(r"\)\s*->\s*\w|\):\s*\w+\s*[{=]", text))
            if typed >= funcs * 0.9:
                info["signals"].append({"name": "fully_type_annotated", "strength": "weak"})
    if is_doc and re.search(r"^#{1,3}\s*(✨|🚀|📦|🛠|📁|🤝|📝)", text, re.M):
        info["signals"].append({"name": "emoji_section_headings", "strength": "medium"})
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    files = {}
    for path, ext in walk(args.repo):
        info = analyze(path, ext)
        if info:
            files[os.path.relpath(path, args.repo).replace("\\", "/")] = info

    def level(info):
        strong = sum(1 for s in info["signals"] if s["strength"] == "strong")
        medium = sum(1 for s in info["signals"] if s["strength"] == "medium")
        if strong:
            return "strong_signals"
        if medium >= 2:
            return "several_medium_signals"
        if medium or info["signals"]:
            return "weak_or_single_signal"
        return "no_signals"

    summary = {"strong_signals": 0, "several_medium_signals": 0, "weak_or_single_signal": 0, "no_signals": 0}
    lines_by_level = dict.fromkeys(summary, 0)
    for info in files.values():
        info["level"] = level(info)
        summary[info["level"]] += 1
        lines_by_level[info["level"]] += info["lines"]

    flagged = {f: i for f, i in sorted(files.items(), key=lambda x: (x[1]["level"] != "strong_signals", -x[1]["lines"]))
               if i["signals"]}
    result = {
        "files_scanned": len(files),
        "total_nonblank_lines": sum(i["lines"] for i in files.values()),
        "files_by_level": summary,
        "lines_by_level": lines_by_level,
        "flagged_files": flagged,
        "note": ("Automated indicators only. Combine with git history and manual reading; classify each component "
                 "as Likely human / Mixed / Likely AI-assisted and report a range with confidence, never a fact."),
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(json.dumps({k: v for k, v in result.items() if k != "flagged_files"} | {"flagged_files": len(flagged)}, indent=2))
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
