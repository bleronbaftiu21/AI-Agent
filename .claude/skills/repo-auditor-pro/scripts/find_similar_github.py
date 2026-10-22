"""Find public GitHub repositories that may be the source of (or a copy of) the audited project.

Two searches, both read-only GET requests to the GitHub API:
  1. Code search (needs GITHUB_TOKEN): distinctive lines from the project are searched across all of GitHub;
     repositories that contain several of them are strong candidates.
  2. Repository search (works without a token): repositories with a similar name/description/README title.
The project's own repositories, its organisation's other repos and forks of them are excluded.
The candidates are then cloned and compared with similarity.py by pipeline.py.

Usage:
    python -I find_similar_github.py --acquire acquire.json [--max-queries 12] [--max-candidates 6] [--out FILE]
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

API = "https://api.github.com"
SOURCE_LANG = {".cs": "C#", ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
               ".tsx": "TypeScript", ".java": "Java", ".kt": "Kotlin", ".go": "Go", ".php": "PHP", ".rb": "Ruby",
               ".dart": "Dart", ".vue": "Vue", ".swift": "Swift", ".cpp": "C++", ".c": "C"}
EXCLUDED_DIRS = {".git", "node_modules", "vendor", "venv", ".venv", "dist", "build", "bin", "obj", "target",
                 "__pycache__", "migrations", "Migrations", "coverage", ".next", "public", "assets", "wwwroot"}
BORING = re.compile(r"^\s*(using |import |from |#include|package |namespace |export \{|export default|require\(|"
                    r"return;|\}|\{|//|/\*|\*|#|<|@|public (class|interface)|private readonly|\[Http|\[Route|"
                    r"console\.log|print\()")
STOP_WORDS = {"the", "and", "app", "project", "api", "web", "backend", "frontend", "client", "server", "system",
              "management", "grupi", "group", "final", "projekti", "main", "master", "test", "demo", "repo"}


class RateLimited(Exception):
    pass


def get(path, token, search=False):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "repo-auditor-pro",
        **({"Authorization": f"Bearer {token}"} if token else {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429):
                reset = int(exc.headers.get("X-RateLimit-Reset") or 0)
                wait = max(1, reset - int(time.time())) if reset else 10
                if search and wait <= 65 and attempt < 2:  # search limits reset every minute
                    time.sleep(wait + 1)
                    continue
                raise RateLimited(exc.headers.get("X-RateLimit-Reset"))
            if exc.code in (404, 422):
                return None
            raise
    return None


def longpath(p):
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        p = "\\\\?\\" + p
    return p


def distinctive_lines(dirs, limit):
    """Lines likely to be unique to this code base: long, identifier-rich, not boilerplate, not repeated."""
    seen = Counter()
    candidates = []
    for d in dirs:
        root = longpath(d)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [x for x in dirnames if x not in EXCLUDED_DIRS and not x.startswith(".")]
            if re.search(r"[\\/](tests?|__tests__|spec)[\\/]?", dirpath, re.I):
                continue
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext not in SOURCE_LANG or re.search(r"(\.min\.|\.Designer\.|Snapshot|\.test\.|\.spec\.|config\.|setupTests)",
                                                       name, re.I):
                    continue
                try:
                    with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                for line in lines:
                    s = line.strip()
                    seen[s] += 1
                    if not (45 <= len(s) <= 110) or BORING.match(s) or '"' not in s and "'" not in s and "(" not in s:
                        continue
                    idents = re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,}", s)
                    if len(idents) < 3 or len(set(idents)) < 3:
                        continue
                    # prefer lines with project-specific words (string literals, long identifiers)
                    score = len(re.findall(r"[\"'][^\"']{8,}[\"']", s)) * 3 + sum(len(i) > 10 for i in idents)
                    candidates.append((score, s, SOURCE_LANG[ext], name))
    picked, used_files = [], Counter()
    for score, s, lang, fname in sorted(candidates, key=lambda c: -c[0]):
        if seen[s] > 1 or used_files[fname] >= 2 or any(s == p["line"] for p in picked):
            continue
        picked.append({"line": s, "language": lang, "file": fname})
        used_files[fname] += 1
        if len(picked) >= limit:
            break
    return picked


def project_terms(acq, dirs):
    words = Counter()
    for r in acq:
        for w in re.split(r"[^A-Za-z0-9]+", r.get("repo", "")):
            if len(w) >= 4 and w.lower() not in STOP_WORDS and not w.isdigit():
                words[w.lower()] += 3
    for d in dirs:
        readme = next((os.path.join(d, n) for n in os.listdir(d) if n.lower().startswith("readme")), None)
        if readme:
            with open(readme, encoding="utf-8", errors="replace") as fh:
                title = next((l.strip("# ").strip() for l in fh if l.startswith("#")), "")
            for w in re.split(r"[^A-Za-z0-9]+", title):
                if len(w) >= 4 and w.lower() not in STOP_WORDS:
                    words[w.lower()] += 2
    return [w for w, _ in words.most_common(3)]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--acquire", required=True, help="acquire.json of the audited project")
    ap.add_argument("--max-queries", type=int, default=12)
    ap.add_argument("--max-candidates", type=int, default=6)
    ap.add_argument("--out")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    with open(args.acquire, encoding="utf-8") as fh:
        acq = [r for r in json.load(fh) if r.get("ok")]
    dirs = [r["dir"] for r in acq]
    own = {f"{r['owner']}/{r['repo']}".lower() for r in acq}
    own_owners = {r["owner"].lower() for r in acq}
    result = {"authenticated": bool(token), "queries": [], "candidates": [], "limitations": []}
    hits = defaultdict(lambda: {"code_hits": 0, "lines": [], "name_match": False, "info": None})

    def is_own(full, item=None):
        fl = full.lower()
        if fl in own or fl.split("/")[0] in own_owners:
            return True
        parent = ((item or {}).get("parent") or {}).get("full_name", "").lower()
        return parent in own

    # 1) code search
    if token:
        for q in distinctive_lines(dirs, args.max_queries):
            query = f'"{q["line"][:100]}" language:"{q["language"]}"'
            try:
                data = get("/search/code?" + urllib.parse.urlencode({"q": query, "per_page": 20}), token, search=True)
            except RateLimited:
                result["limitations"].append("GitHub code-search rate limit reached; fewer lines were searched.")
                break
            found = [] if not data else [i["repository"]["full_name"] for i in data.get("items", [])]
            foreign = sorted({f for f in found if not is_own(f)})
            result["queries"].append({"line": q["line"], "file": q["file"], "matches": foreign[:10],
                                      "total": (data or {}).get("total_count", 0)})
            for f in foreign:
                hits[f]["code_hits"] += 1
                if len(hits[f]["lines"]) < 5:
                    hits[f]["lines"].append(q["line"])
    else:
        result["limitations"].append("No GITHUB_TOKEN: GitHub code search (the strongest copy check) was skipped; "
                                     "only repositories with a similar name were searched.")

    # 2) repository search by name / README title
    terms = project_terms(acq, dirs)
    result["name_terms"] = terms
    for term in terms[:2]:
        try:
            data = get("/search/repositories?" + urllib.parse.urlencode(
                {"q": f"{term} in:name,description", "sort": "stars", "per_page": 15}), token, search=True)
        except RateLimited:
            result["limitations"].append("GitHub repository-search rate limit reached.")
            break
        for item in (data or {}).get("items", []):
            full = item["full_name"]
            if is_own(full, item):
                continue
            hits[full]["name_match"] = True
            hits[full]["info"] = item

    # rank: code hits first, then name matches; keep the size small enough to clone
    ranked = sorted(hits.items(), key=lambda kv: (-kv[1]["code_hits"], not kv[1]["name_match"]))
    for full, h in ranked:
        if len(result["candidates"]) >= args.max_candidates:
            break
        if h["code_hits"] == 0 and len([c for c in result["candidates"] if c["code_hits"] == 0]) >= 3:
            continue  # at most 3 name-only candidates
        info = h["info"]
        if info is None:
            try:
                info = get(f"/repos/{full}", token) or {}
            except RateLimited:
                info = {}
        if info.get("fork") and (info.get("parent") or {}).get("full_name", "").lower() in own:
            continue
        if (info.get("size") or 0) > 300_000:  # KB; skip huge repositories
            continue
        result["candidates"].append({
            "full_name": full, "url": f"https://github.com/{full}", "code_hits": h["code_hits"],
            "matched_lines": h["lines"], "name_match": h["name_match"],
            "created_at": info.get("created_at"), "pushed_at": info.get("pushed_at"),
            "stars": info.get("stargazers_count"), "description": (info.get("description") or "")[:200],
            "reason": (f"{h['code_hits']} rreshta identikë të kodit" if h["code_hits"] else "emër/përshkrim i ngjashëm"),
        })
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(json.dumps({"authenticated": result["authenticated"], "queries": len(result["queries"]),
                      "name_terms": terms, "candidates": [(c["full_name"], c["reason"]) for c in result["candidates"]],
                      "limitations": result["limitations"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
