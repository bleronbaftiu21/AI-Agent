"""Token-normalized code similarity (winnowing, MOSS-style) between a target repo and a corpus.

Read-only: only reads files. Usage:
    python -I similarity.py --target REPO --corpus DIR [DIR ...] [--base TEMPLATE_DIR] [--out FILE]
    python -I similarity.py --groups groups.json [--base TEMPLATE_DIR] [--out FILE]   (every group vs every other)
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


def longpath(p):
    """Absolute path with the Windows extended-length prefix so paths over 260 chars are not skipped."""
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        p = "\\\\?\\" + p
    return p


def walk(root):
    root = longpath(root)
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
            files[os.path.relpath(path, longpath(root)).replace("\\", "/")] = fps
    return files


def merge_ranges(ranges):
    out = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def strip_base(files, base_hashes):
    out = {f: {h: r for h, r in fps.items() if h not in base_hashes} for f, fps in files.items()}
    return {f: fps for f, fps in out.items() if fps}


def file_matches(target, inverted, sizes, min_containment, min_fp):
    """target: {file: fps}; inverted: hash -> {(label, file)}; sizes: (label, file) -> fingerprint count."""
    matches, matched_fp, per_label, total_fp = [], 0, defaultdict(int), 0
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
                per_label[label] += 1
            for other in others:
                shared_ranges[other].extend(ranges)
                shared_count[other] += 1
        for (label, ofile), ranges in shared_ranges.items():
            n_shared = shared_count[(label, ofile)]
            c_target = n_shared / len(fps)
            if c_target < min_containment:
                continue
            matches.append({
                "target_file": tfile, "corpus": label, "other_file": ofile,
                "containment_target": round(c_target, 3),
                "containment_other": round(min(n_shared / sizes[(label, ofile)], 1.0), 3),
                "target_fingerprints": len(fps), "shared_fingerprints": n_shared,
                "small_file": len(fps) < min_fp, "target_lines": merge_ranges(ranges),
            })
    matches.sort(key=lambda m: (m["small_file"], -m["containment_target"], -m["shared_fingerprints"]))
    return matches, matched_fp, per_label, total_fp


def build_inverted(labelled_trees, base_hashes):
    inverted, sizes = defaultdict(set), {}
    for label, files in labelled_trees:
        for f, fps in files.items():
            sizes[(label, f)] = len(fps)
            for h in fps:
                if h not in base_hashes:
                    inverted[h].add((label, f))
    return inverted, sizes


def index_group(dirs):
    files = {}
    for d in dirs:
        prefix = os.path.basename(os.path.normpath(d))
        for f, fps in index_tree(d).items():
            files[f"{prefix}/{f}"] = fps
    return files


def compare_groups(groups, base_hashes, args):
    """Every group against every other group: repo-level overlap matrix plus top file matches per pair."""
    indexed = {name: strip_base(index_group(dirs), base_hashes) for name, dirs in groups.items()}
    hashes = {name: set(h for fps in files.values() for h in fps) for name, files in indexed.items()}
    names = sorted(indexed)
    matrix = {a: {b: (round(len(hashes[a] & hashes[b]) / len(hashes[a]), 3) if hashes[a] else 0.0)
                  for b in names if b != a} for a in names}
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            score = max(matrix[a][b], matrix[b][a])
            entry = {"a": a, "b": b, "a_in_b": matrix[a][b], "b_in_a": matrix[b][a], "max": score, "matches": []}
            if score >= args.pair_threshold:
                inverted, sizes = build_inverted([(b, indexed[b])], base_hashes)
                ms, _, _, _ = file_matches(indexed[a], inverted, sizes, args.min_containment, args.min_fingerprints)
                entry["matches"] = ms[:15]
            pairs.append(entry)
    pairs.sort(key=lambda p: -p["max"])
    return {
        "mode": "groups",
        "params": {"k": K, "window": W, "min_containment": args.min_containment, "pair_threshold": args.pair_threshold},
        "groups": {n: {"files": len(indexed[n]), "fingerprints": len(hashes[n])} for n in names},
        "matrix": matrix,
        "max_by_group": {n: max(matrix[n].values(), default=0.0) for n in names},
        "pairs": pairs,
        "note": ("Overlap = share of a group's code fingerprints that also appear in the other group. Shared framework "
                 "boilerplate gives a few percent; inspect pairs above ~20% manually and use --base for starter code."),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", help="repo to check (single-target mode)")
    ap.add_argument("--corpus", nargs="+", help="directories of other submissions/sources")
    ap.add_argument("--groups", help="JSON file {group_name: [dir, ...]}: compare every group with every other")
    ap.add_argument("--base", nargs="*", default=[], help="template/starter code to ignore")
    ap.add_argument("--min-fingerprints", type=int, default=30)
    ap.add_argument("--min-containment", type=float, default=0.25)
    ap.add_argument("--pair-threshold", type=float, default=0.05, help="groups mode: list file matches above this overlap")
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--out")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    base_hashes = set()
    for b in args.base:
        for fps in index_tree(b).values():
            base_hashes.update(fps)

    if args.groups:
        with open(args.groups, encoding="utf-8") as fh:
            groups = json.load(fh)
        result = compare_groups(groups, base_hashes, args)
        summary = {"groups": result["groups"], "max_by_group": result["max_by_group"],
                   "top_pairs": [{k: p[k] for k in ("a", "b", "a_in_b", "b_in_a")} for p in result["pairs"][:10]]}
    else:
        if not args.target or not args.corpus:
            ap.error("--target and --corpus are required unless --groups is given")
        target = strip_base(index_tree(args.target), base_hashes)
        trees = [(os.path.basename(os.path.normpath(r)), index_tree(r)) for r in args.corpus]
        inverted, sizes = build_inverted(trees, base_hashes)
        matches, matched_fp, per_corpus, total_fp = file_matches(target, inverted, sizes, args.min_containment,
                                                                 args.min_fingerprints)
        result = {
            "mode": "target",
            "params": {"k": K, "window": W, "min_containment": args.min_containment, "base": args.base},
            "target_files": len(target),
            "target_fingerprints": total_fp,
            "share_of_target_found_in_corpus": round(matched_fp / total_fp, 3) if total_fp else 0.0,
            "share_by_corpus": {k: round(v / total_fp, 3) for k, v in sorted(per_corpus.items(), key=lambda x: -x[1])} if total_fp else {},
            "matches": matches[: args.top],
            "note": "Similarity is a signal, not proof. Inspect matched ranges manually and check commit dates for direction.",
        }
        summary = {k: result[k] for k in result if k != "matches"} | {"matches": len(matches)}
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(json.dumps(summary, indent=2, ensure_ascii=False) if args.out else text)


if __name__ == "__main__":
    sys.exit(main())
