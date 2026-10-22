"""Summarize git history for authorship/originality signals.

Read-only: runs only `git log`. Usage:
    python -I git_history.py --repo [LABEL=]REPO [--repo ...] [--alias "Raw=Canonical"] [--rev HEAD] [--deadline YYYY-MM-DD] [--out FILE]
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


GENERATED = re.compile(r"(^|/)(migrations|alembic/versions|db/migrate)/|\.Designer\.cs$|ModelSnapshot\.cs$|\.g\.cs$", re.I)
JIRA_KEY = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")


def excluded(path):
    p = path.replace("\\", "/")
    return (any(part in p for part in EXCLUDED_PARTS) or p.endswith(LOCKFILES) or ".min." in p
            or bool(GENERATED.search(p)))


def name_tokens(name):
    """'ZubakuRiga' -> {'zubaku','riga'}; 'oltikrasniqi21' -> {'oltikrasniqi'}; 'Olti Krasniqi' -> {'olti','krasniqi'}."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return [t for t in re.split(r"[^a-z]+", spaced.lower()) if t]


def merge_identities(names_emails, aliases):
    """Map each raw author name to one canonical name for the same person (same email, same tokens in any
    order, glued tokens, or a single first name that matches exactly one fuller name). Returns {raw: canonical}."""
    names = sorted(names_emails)
    parent = {n: n for n in names}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            # keep the longer, more complete name as canonical
            keep, drop = (ra, rb) if (len(name_tokens(ra)), len(ra)) >= (len(name_tokens(rb)), len(rb)) else (rb, ra)
            parent[drop] = keep

    by_email = defaultdict(list)
    for n, emails in names_emails.items():
        for e in emails:
            if e and e.lower() not in ("noreply@github.com", "none", "unknown"):
                by_email[e.lower()].append(n)
    for group in by_email.values():
        for other in group[1:]:
            union(group[0], other)
    keys = {n: name_tokens(n) for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ta, tb = keys[a], keys[b]
            if not ta or not tb:
                continue
            if sorted(ta) == sorted(tb) or "".join(ta) in ("".join(tb), "".join(reversed(tb))) \
                    or "".join(tb) in ("".join(ta), "".join(reversed(ta))):
                union(a, b)
    for a in names:
        if len(keys[a]) == 1:
            fuller = [b for b in names if b != a and len(keys[b]) > 1 and keys[b][0] == keys[a][0]]
            if len(fuller) == 1:
                union(a, fuller[0])
    for alias, canonical in aliases.items():
        if alias in parent and canonical in parent:
            union(canonical, alias)
            parent[find(alias)] = canonical if canonical in parent else parent[find(alias)]
    return {n: find(n) for n in names}


def run_git(repo, rev):
    cmd = ["git", "-C", repo, "-c", "core.hooksPath=", "-c", "core.longpaths=true", "log", rev, "--no-textconv", "--no-ext-diff",
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


def to_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def repo_flags(label, commits, args):
    """History signals for one repository (non-merge, de-duplicated commits, oldest first)."""
    flags = []
    if not commits:
        return flags, [], []
    prefix = f"[{label}] " if label else ""
    total_added = sum(c["added"] for c in commits) or 1
    first = commits[0]
    biggest = max(commits, key=lambda c: c["added"])
    first_share = first["added"] / total_added
    if first_share >= 0.5:
        flags.append(f"{prefix}First commit adds {first_share:.0%} of all lines ever added ({first['added']} lines).")
    top_share = biggest["added"] / total_added
    if top_share >= 0.6 and biggest is not first:
        flags.append(f"{prefix}Single commit {biggest['sha']} adds {top_share:.0%} of all lines.")
    if len(commits) <= 3:
        flags.append(f"{prefix}Only {len(commits)} non-merge commit(s) - little iterative history.")
    days = {to_dt(c["author_date"]).date() for c in commits}
    if len(days) == 1 and len(commits) > 1:
        flags.append(f"{prefix}All commits were authored on a single day.")
    generic = [c for c in commits if GENERIC_MSG.match(c["subject"].strip())]
    if len(generic) / len(commits) >= 0.6:
        flags.append(f"{prefix}{len(generic)}/{len(commits)} commit messages are generic (e.g. 'update').")
    uploads = [c for c in commits if c["subject"].lower().startswith(("add files via upload", "create "))]
    if uploads:
        flags.append(f"{prefix}{len(uploads)} commit(s) look like GitHub web uploads.")
    late, early = [], []
    if args.deadline:
        dl = datetime.fromisoformat(args.deadline).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        late = [c["sha"] for c in commits if to_dt(c["author_date"]) > dl]
        if late:
            flags.append(f"{prefix}{len(late)} commit(s) authored after the deadline {args.deadline}.")
    if args.start:
        st = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
        early = [c["sha"] for c in commits if to_dt(c["author_date"]) < st]
        if early:
            flags.append(f"{prefix}{len(early)} commit(s) authored before the assignment start {args.start}.")
    skew = [c for c in commits if abs((to_dt(c["commit_date"]) - to_dt(c["author_date"])).days) > 7]
    if skew:
        flags.append(f"{prefix}{len(skew)} commit(s) with author/commit date > 7 days apart (rebased or imported history).")
    return flags, late, early


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", action="append", required=True, help="repo folder; LABEL=DIR to name it; repeatable")
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--deadline", help="YYYY-MM-DD (end of day, UTC); later commits are flagged")
    ap.add_argument("--start", help="YYYY-MM-DD assignment publish date; earlier commits are flagged")
    ap.add_argument("--alias", action="append", default=[], help="'Raw Name=Canonical Name' to merge identities")
    ap.add_argument("--out")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    per_repo = []
    for spec in args.repo:
        label, sep, path = spec.partition("=")
        if not sep:
            label, path = "", spec
        commits = parse(run_git(path, args.rev))
        for c in commits:
            c["repo"] = label
        per_repo.append((label, commits))
    all_commits = [c for _, cs in per_repo for c in cs]
    if not all_commits:
        print(json.dumps({"commits": 0, "note": "No commits found."}))
        return

    names_emails = defaultdict(set)
    for c in all_commits:
        names_emails[c["author"]].add(c["email"])
    aliases = dict(a.split("=", 1) for a in args.alias if "=" in a)
    canonical = merge_identities(names_emails, aliases)

    # identical commits re-applied by squash/rebase/cherry-pick are counted once
    seen, duplicates = set(), 0
    for c in all_commits:
        c["person"] = canonical[c["author"]]
        subject = re.sub(r"\s*\(#\d+\)$", "", c["subject"].strip().lower())
        key = (c["repo"], c["person"], subject, c["added"], c["removed"], c["files"])
        c["duplicate"] = not c["merge"] and key in seen
        duplicates += c["duplicate"]
        seen.add(key)
    counted = [c for c in all_commits if not c["merge"] and not c["duplicate"]]
    total_added = sum(c["added"] for c in counted) or 1

    people = defaultdict(lambda: {"commits": 0, "lines_added": 0, "lines_removed": 0, "names": set(),
                                  "emails": set(), "by_repo": Counter()})
    for c in counted:
        p = people[c["person"]]
        p["commits"] += 1
        p["lines_added"] += c["added"]
        p["lines_removed"] += c["removed"]
        p["names"].add(c["author"])
        p["emails"].add(c["email"])
        p["by_repo"][c["repo"] or "repo"] += 1

    flags, late, early, repos_out = [], [], [], []
    for label, commits in per_repo:
        mine = [c for c in commits if not c["merge"] and not c["duplicate"]]
        f, l, e = repo_flags(label, mine, args)
        flags += f
        late += l
        early += e
        if commits:
            repos_out.append({"label": label, "commits": len(commits), "non_merge": len(mine),
                              "first": {k: commits[0][k] for k in ("sha", "author", "author_date", "subject")},
                              "last": {k: commits[-1][k] for k in ("sha", "author", "author_date", "subject")}})
    if len(people) > 1:
        flags.append(f"{len(people)} distinct people after merging {len(names_emails)} git identities - "
                     "verify they match the submitting student/team.")
    if duplicates:
        flags.append(f"{duplicates} duplicate commit(s) from squash/rebase were counted once.")

    # work over time: per ISO week, and how much arrived in the final 7 days (deadline, or last commit)
    weekly = defaultdict(lambda: {"commits": 0, "lines_added": 0})
    for c in counted:
        y, w, _ = to_dt(c["author_date"]).isocalendar()
        weekly[f"{y}-W{w:02d}"]["commits"] += 1
        weekly[f"{y}-W{w:02d}"]["lines_added"] += c["added"]
    end = (datetime.fromisoformat(args.deadline).replace(hour=23, minute=59, tzinfo=timezone.utc) if args.deadline
           else max((to_dt(c["author_date"]) for c in counted), default=None))
    last_week_share = None
    if end and counted:
        recent = sum(c["added"] for c in counted if 0 <= (end - to_dt(c["author_date"])).total_seconds() <= 7 * 86400)
        last_week_share = round(recent / total_added, 3)
        if last_week_share >= 0.5:
            flags.append(f"{last_week_share:.0%} of all code was added in the last 7 days before "
                         f"{'the deadline' if args.deadline else 'the last commit'} (last-minute work).")

    days = Counter(to_dt(c["author_date"]).date().isoformat() for c in counted)
    jira = Counter(k.split("-")[0] for c in all_commits for k in JIRA_KEY.findall(c["subject"]))
    jira_commits = sum(1 for c in all_commits if JIRA_KEY.search(c["subject"]))
    biggest = sorted(counted, key=lambda c: -c["added"])[:10]

    result = {
        "rev": args.rev,
        "repos": repos_out,
        "commits": len(all_commits),
        "non_merge_commits": sum(1 for c in all_commits if not c["merge"]),
        "duplicate_commits": duplicates,
        "active_days": len(days),
        "first_date": min(days) if days else None,
        "last_date": max(days) if days else None,
        "commits_per_day": dict(sorted(days.items())),
        "weekly": [{"week": k, **v} for k, v in sorted(weekly.items())],
        "last_7_days_share": last_week_share,
        "identity_map": {raw: can for raw, can in canonical.items() if raw != can},
        "authors": [
            {"author": n, "names": sorted(p["names"]), "emails": sorted(p["emails"]), "commits": p["commits"],
             "lines_added": p["lines_added"], "lines_removed": p["lines_removed"],
             "share_of_added": round(p["lines_added"] / total_added, 3), "commits_by_repo": dict(p["by_repo"])}
            for n, p in sorted(people.items(), key=lambda x: -x[1]["lines_added"])
        ],
        "issue_tracker_keys": {"commits_with_key": jira_commits, "projects": dict(jira)},
        "largest_commits": [{k: c[k] for k in ("repo", "sha", "author", "author_date", "subject", "files", "added")}
                            for c in biggest],
        "late_commits": late,
        "early_commits": early,
        "flags": flags,
        "note": ("Line counts exclude merges, duplicates, lockfiles, migrations and generated files. Identity merging is "
                 "heuristic - confirm it. History signals are indicators only."),
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    sys.exit(main())
