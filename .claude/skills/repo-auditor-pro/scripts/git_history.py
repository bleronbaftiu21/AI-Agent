"""Summarize git history for authorship/originality signals.

Read-only: runs only `git log`. Usage:
    python -I git_history.py --repo REPO [--rev HEAD] [--deadline YYYY-MM-DD] [--out FILE]
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

EXCLUDED_PARTS = (
    "node_modules/", "vendor/", "venv/", ".venv/", "dist/", "build/", "target/", "bin/", "obj/",
    "__pycache__/", ".next/", "coverage/", ".idea/", ".vscode/",
)
LOCKFILES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock",
             "composer.lock", "Cargo.lock", "Gemfile.lock", "go.sum")
GENERIC_MSG = re.compile(r"^(update|updates|fix|fixes|changes|commit|wip|test|asd+|\.+|first commit|initial commit|"
                         r"add files via upload|update \S+|create \S+)$", re.I)


def excluded(path):
    p = path.replace("\\", "/")
    return any(part in p for part in EXCLUDED_PARTS) or p.endswith(LOCKFILES) or ".min." in p


def run_git(repo, rev):
    cmd = ["git", "-C", repo, "-c", "core.hooksPath=", "log", rev, "--no-textconv", "--no-ext-diff",
           "--no-renames", "--format=%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%cI%x1f%P%x1f%s", "--numstat"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise SystemExit(f"git log failed: {res.stderr.strip()}")
    return res.stdout


def parse(raw):
    commits = []
    for block in raw.split("\x1e")[1:]:
        lines = block.strip("\n").split("\n")
        sha, name, email, adate, cdate, parents, subject = lines[0].split("\x1f", 6)
        added = removed = 0
        files = 0
        for ln in lines[1:]:
            parts = ln.split("\t")
            if len(parts) != 3 or excluded(parts[2]):
                continue
            files += 1
            if parts[0] != "-":
                added += int(parts[0])
                removed += int(parts[1])
        commits.append({
            "sha": sha[:10], "author": name, "email": email,
            "author_date": adate, "commit_date": cdate,
            "merge": len(parents.split()) > 1, "subject": subject,
            "files": files, "added": added, "removed": removed,
        })
    commits.reverse()  # oldest first
    return commits


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--deadline", help="YYYY-MM-DD (end of day, UTC) — commits after it are flagged")
    ap.add_argument("--start", help="YYYY-MM-DD assignment publish date — commits before it are flagged")
    ap.add_argument("--out")
    args = ap.parse_args()

    commits = parse(run_git(args.repo, args.rev))
    if not commits:
        print(json.dumps({"commits": 0, "note": "No commits found."}))
        return
    non_merge = [c for c in commits if not c["merge"]]
    total_added = sum(c["added"] for c in non_merge) or 1

    authors = defaultdict(lambda: {"commits": 0, "lines_added": 0, "lines_removed": 0, "emails": set()})
    for c in non_merge:
        a = authors[c["author"]]
        a["commits"] += 1
        a["lines_added"] += c["added"]
        a["lines_removed"] += c["removed"]
        a["emails"].add(c["email"])

    to_dt = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    days = Counter(to_dt(c["author_date"]).date().isoformat() for c in non_merge)
    biggest = sorted(non_merge, key=lambda c: -c["added"])[:10]

    flags = []
    first = non_merge[0] if non_merge else commits[0]
    first_share = first["added"] / total_added
    if first_share >= 0.5:
        flags.append(f"First commit adds {first_share:.0%} of all lines ever added ({first['added']} lines).")
    top_share = biggest[0]["added"] / total_added if biggest else 0
    if top_share >= 0.6 and biggest[0] is not first:
        flags.append(f"Single commit {biggest[0]['sha']} adds {top_share:.0%} of all lines.")
    if len(non_merge) <= 3:
        flags.append(f"Only {len(non_merge)} non-merge commit(s) — little iterative history.")
    if len(days) == 1 and len(non_merge) > 1:
        flags.append("All commits were authored on a single day.")
    generic = [c for c in non_merge if GENERIC_MSG.match(c["subject"].strip())]
    if non_merge and len(generic) / len(non_merge) >= 0.6:
        flags.append(f"{len(generic)}/{len(non_merge)} commit messages are generic (e.g. 'update', 'Add files via upload').")
    uploads = [c for c in non_merge if c["subject"].lower().startswith(("add files via upload", "create "))]
    if uploads:
        flags.append(f"{len(uploads)} commit(s) look like GitHub web uploads ('Add files via upload'/'Create …').")
    late, early = [], []
    if args.deadline:
        dl = datetime.fromisoformat(args.deadline).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        late = [c["sha"] for c in non_merge if to_dt(c["author_date"]) > dl]
        if late:
            flags.append(f"{len(late)} commit(s) authored after the deadline {args.deadline}.")
    if args.start:
        st = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        early = [c["sha"] for c in non_merge if to_dt(c["author_date"]) < st]
        if early:
            flags.append(f"{len(early)} commit(s) authored before the assignment start {args.start}.")
    skew = [c["sha"] for c in non_merge if abs((to_dt(c["commit_date"]) - to_dt(c["author_date"])).days) > 7]
    if skew:
        flags.append(f"{len(skew)} commit(s) with author/commit date > 7 days apart (rebased, cherry-picked or imported history).")
    if len(authors) > 1:
        flags.append(f"{len(authors)} distinct author names — verify they match the submitting student/team.")

    result = {
        "rev": args.rev,
        "commits": len(commits),
        "non_merge_commits": len(non_merge),
        "first_commit": {k: first[k] for k in ("sha", "author", "author_date", "subject", "added")},
        "last_commit": {k: commits[-1][k] for k in ("sha", "author", "author_date", "subject")},
        "active_days": len(days),
        "commits_per_day": dict(sorted(days.items())),
        "authors": [
            {"author": n, "emails": sorted(a["emails"]), "commits": a["commits"],
             "lines_added": a["lines_added"], "lines_removed": a["lines_removed"],
             "share_of_added": round(a["lines_added"] / total_added, 3)}
            for n, a in sorted(authors.items(), key=lambda x: -x[1]["lines_added"])
        ],
        "largest_commits": [{k: c[k] for k in ("sha", "author", "author_date", "subject", "files", "added")} for c in biggest],
        "late_commits": late,
        "early_commits": early,
        "flags": flags,
        "note": "History signals are indicators only; squash merges, uploads and pair programming distort them.",
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
