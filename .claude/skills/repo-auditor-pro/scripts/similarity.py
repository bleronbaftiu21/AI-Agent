"""Token-normalized code similarity (winnowing, MOSS-style) between a target repo and a corpus.

Read-only: only reads files. Usage:
    python -I similarity.py --target REPO --corpus DIR [DIR ...] [--base TEMPLATE_DIR] [--out FILE]
"""
import argparse
import json
import os
import re
import sys
import zlib
from collections import defaultdict

EXCLUDED_DIRS = {
    ".git", "node_modules", "vendor", "venv", ".venv", "env", "dist", "build", "target", "bin", "obj",
    "__pycache__", ".next", ".nuxt", "coverage", ".idea", ".vscode", ".gradle", "Pods", "migrations",
}
SOURCE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".kt", ".kts", ".scala", ".c", ".h",
    ".cpp", ".cc", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".m", ".dart", ".lua", ".r",
    ".sql", ".sh", ".ps1", ".vue", ".svelte", ".html", ".css", ".scss", ".less",
}
HASH_COMMENT_EXTS = {".py", ".rb", ".sh", ".r", ".ps1"}
KEYWORDS = set("""
if else elif for foreach while do return def class function func fn var let const import from export
public private protected static final void int long float double char bool boolean string new try catch
except finally throw throws raise with as in not and or is none null nil true false self this super async
await yield lambda switch case default break continue struct interface extends implements package
namespace using include print echo enum match type select where insert update delete into values join
""".split())
TOKEN_RE = re.compile(
    r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`'
    r"|[A-Za-z_$][A-Za-z0-9_$]*|\d[\w.]*|==|!=|<=|>=|=>|->|&&|\|\||\+\+|--|\S"
)

K = 12  # tokens per k-gram
W = 8   # winnowing window


def strip_comments(text, ext):
    """Blank out comments while preserving newlines so line numbers stay valid."""
    keep_nl = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    if ext in {".html", ".vue", ".svelte"}:
        text = re.sub(r"<!--[\s\S]*?-->", keep_nl, text)
    if ext == ".sql":
        text = re.sub(r"--[^\n]*", keep_nl, text)
    if ext in HASH_COMMENT_EXTS:
        text = re.sub(r"(?m)(^|\s)#[^\n]*", keep_nl, text)
    else:
        text = re.sub(r"/\*[\s\S]*?\*/", keep_nl, text)
        text = re.sub(r"(?m)(^|[^:\"'])//[^\n]*", keep_nl, text)
    return text


def tokenize(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    if len(text) > 2_000_000 or ".min." in os.path.basename(path):
        return []
    text = strip_comments(text, ext)
    tokens = []
    line = 1
    pos = 0
    for m in TOKEN_RE.finditer(text):
        line += text.count("\n", pos, m.start())
        pos = m.start()
        tok = m.group(0)
        if tok[0] in "\"'`":
            norm = "LIT"
        elif tok[0].isdigit():
            norm = "LIT"
        elif re.match(r"[A-Za-z_$]", tok):
            norm = tok if tok.lower() in KEYWORDS else "ID"
        else:
            norm = tok
        tokens.append((norm, line))
    return tokens


def fingerprints(tokens):
    """Winnowing: returns dict hash -> list of (start_line, end_line)."""
    if len(tokens) < K:
        return {}
    hashes = []
    for i in range(len(tokens) - K + 1):
        gram = " ".join(t for t, _ in tokens[i:i + K])
        hashes.append((zlib.crc32(gram.encode()), tokens[i][1], tokens[i + K - 1][1]))
    selected = {}
    last = None
    for i in range(max(1, len(hashes) - W + 1)):
        window = hashes[i:i + W]
        j = min(range(len(window)), key=lambda x: (window[x][0], -x))
        if last != i + j:
            h, s, e = window[j]
            selected.setdefault(h, []).append((s, e))
            last = i + j
    return selected


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in SOURCE_EXTS:
                yield os.path.join(dirpath, name)


def index_tree(root):
    files = {}
    for path in walk(root):
        fps = fingerprints(tokenize(path))
        if fps:
            files[os.path.relpath(path, root).replace("\\", "/")] = fps
    return files


def merge_ranges(ranges):
    out = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", required=True)
    ap.add_argument("--corpus", nargs="+", required=True, help="directories of other submissions/sources")
    ap.add_argument("--base", nargs="*", default=[], help="template/starter code to ignore")
    ap.add_argument("--min-fingerprints", type=int, default=30)
    ap.add_argument("--min-containment", type=float, default=0.25)
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--out")
    args = ap.parse_args()

    base_hashes = set()
    for b in args.base:
        for fps in index_tree(b).values():
            base_hashes.update(fps)

    target = {f: {h: r for h, r in fps.items() if h not in base_hashes} for f, fps in index_tree(args.target).items()}
    target = {f: fps for f, fps in target.items() if fps}

    inverted = defaultdict(set)  # hash -> {(corpus_root, file)}
    corpus_sizes = {}
    for root in args.corpus:
        label = os.path.basename(os.path.normpath(root))
        for f, fps in index_tree(root).items():
            corpus_sizes[(label, f)] = len(fps)
            for h in fps:
                if h not in base_hashes:
                    inverted[h].add((label, f))

    matches = []
    total_fp = 0
    matched_fp = 0
    per_corpus = defaultdict(int)
    for tfile, fps in target.items():
        total_fp += len(fps)
        shared_ranges = defaultdict(list)
        shared_count = defaultdict(int)
        for h, ranges in fps.items():
            others = inverted.get(h)
            if not others:
                continue
            matched_fp += 1
            for label in {o[0] for o in others}:
                per_corpus[label] += 1
            for other in others:
                shared_ranges[other].extend(ranges)
                shared_count[other] += 1
        for (label, ofile), ranges in shared_ranges.items():
            n_shared = shared_count[(label, ofile)]
            c_target = n_shared / len(fps)
            c_other = n_shared / corpus_sizes[(label, ofile)]
            if c_target < args.min_containment:
                continue
            matches.append({
                "target_file": tfile,
                "corpus": label,
                "other_file": ofile,
                "containment_target": round(c_target, 3),
                "containment_other": round(min(c_other, 1.0), 3),
                "target_fingerprints": len(fps),
                "shared_fingerprints": n_shared,
                "small_file": len(fps) < args.min_fingerprints,
                "target_lines": merge_ranges(ranges),
            })
    matches.sort(key=lambda m: (m["small_file"], -m["containment_target"], -m["shared_fingerprints"]))

    result = {
        "params": {"k": K, "window": W, "min_containment": args.min_containment, "base": args.base},
        "target_files": len(target),
        "target_fingerprints": total_fp,
        "share_of_target_found_in_corpus": round(matched_fp / total_fp, 3) if total_fp else 0.0,
        "share_by_corpus": {k: round(v / total_fp, 3) for k, v in sorted(per_corpus.items(), key=lambda x: -x[1])} if total_fp else {},
        "matches": matches[: args.top],
        "note": "Similarity is a signal, not proof. Inspect matched ranges manually and check commit dates for direction.",
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text if not args.out else json.dumps({k: result[k] for k in result if k != "matches"} | {"matches": len(matches)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
