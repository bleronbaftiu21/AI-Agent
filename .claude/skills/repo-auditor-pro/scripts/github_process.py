"""Collaboration evidence from the GitHub REST API: pull requests, code reviews, branches, issues, contributors.

Read-only GET requests. Uses GITHUB_TOKEN / GH_TOKEN from the environment when present (5,000 req/h);
without a token GitHub allows 60 req/h, so reviews are checked on a sample. Usage:
    python -I github_process.py --repo owner/name [--max-review-checks 40] [--out FILE]
"""
import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


class RateLimited(Exception):
    pass


def get(path, token):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "repo-auditor-pro",
        **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.headers
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429) and exc.headers.get("X-RateLimit-Remaining") == "0":
            raise RateLimited(exc.headers.get("X-RateLimit-Reset"))
        if exc.code == 404:
            return None, exc.headers
        raise


def paged(path, token, limit=1000):
    items, page = [], 1
    while len(items) < limit:
        sep = "&" if "?" in path else "?"
        data, _ = get(f"{path}{sep}per_page=100&page={page}", token)
        if not data:
            break
        items.extend(data)
        if len(data) < 100:
            break
        page += 1
    return items[:limit]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--max-review-checks", type=int, default=None,
                    help="how many PRs to check for reviews (default: all with a token, 25 without)")
    ap.add_argument("--out")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    result = {"repo": args.repo, "authenticated": bool(token), "limitations": []}
    try:
        info, _ = get(f"/repos/{args.repo}", token)
        if info is None:
            result["error"] = "Repository not found or not accessible."
            return finish(result, args.out)
        result["info"] = {k: info.get(k) for k in ("full_name", "private", "fork", "created_at", "pushed_at",
                                                    "default_branch", "has_issues", "has_projects", "language")}
        result["info"]["parent"] = (info.get("parent") or {}).get("full_name")
        result["info"]["template"] = (info.get("template_repository") or {}).get("full_name")

        prs = paged(f"/repos/{args.repo}/pulls?state=all", token)
        merged = [p for p in prs if p.get("merged_at")]
        authors = {}
        for p in prs:
            a = (p.get("user") or {}).get("login", "?")
            authors[a] = authors.get(a, 0) + 1
        result["pull_requests"] = {"total": len(prs), "merged": len(merged),
                                   "open": sum(1 for p in prs if p.get("state") == "open"),
                                   "by_author": dict(sorted(authors.items(), key=lambda x: -x[1])),
                                   "self_merged_hint": None}

        cap = args.max_review_checks if args.max_review_checks is not None else (len(prs) if token else 25)
        sample = prs if cap >= len(prs) else random.Random(42).sample(prs, cap)
        reviewed, reviewers, checked, with_comments = 0, {}, 0, 0
        for p in sample:
            try:
                reviews, _ = get(f"/repos/{args.repo}/pulls/{p['number']}/reviews", token)
            except RateLimited:
                result["limitations"].append("GitHub rate limit reached while checking reviews; partial sample.")
                break
            checked += 1
            reviews = [r for r in (reviews or []) if (r.get("user") or {}).get("login") != (p.get("user") or {}).get("login")]
            if reviews:
                reviewed += 1
                for r in reviews:
                    login = (r.get("user") or {}).get("login", "?")
                    reviewers[login] = reviewers.get(login, 0) + 1
                if any(r.get("body") for r in reviews):
                    with_comments += 1
        result["reviews"] = {"prs_checked": checked, "sampled": checked < len(prs),
                             "prs_with_review_by_other": reviewed,
                             "share_reviewed": round(reviewed / checked, 3) if checked else None,
                             "prs_with_review_comment": with_comments,
                             "reviewers": dict(sorted(reviewers.items(), key=lambda x: -x[1]))}
        try:
            result["branches"] = len(paged(f"/repos/{args.repo}/branches", token, limit=500))
            issues = [i for i in paged(f"/repos/{args.repo}/issues?state=all", token, limit=500) if "pull_request" not in i]
            result["issues"] = {"total": len(issues), "closed": sum(1 for i in issues if i.get("state") == "closed")}
            contributors = paged(f"/repos/{args.repo}/contributors", token, limit=100)
            result["contributors"] = [{"login": c.get("login"), "contributions": c.get("contributions")} for c in contributors]
        except RateLimited:
            result["limitations"].append("GitHub rate limit reached; branches/issues/contributors incomplete.")
    except RateLimited:
        result["limitations"].append("GitHub rate limit reached before any data was read. Set GITHUB_TOKEN and retry.")
    except urllib.error.URLError as exc:
        result["error"] = f"Network error: {exc}"
    result["limitations"].append("GitHub Projects (v2) and Jira boards are not visible through this API; check them manually.")
    if not token:
        result["limitations"].append("No GITHUB_TOKEN: unauthenticated API (60 requests/hour), reviews sampled.")
    return finish(result, args.out)


def finish(result, out):
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
