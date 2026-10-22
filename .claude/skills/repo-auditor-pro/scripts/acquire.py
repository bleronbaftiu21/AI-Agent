"""Validate GitHub URLs and clone them safely (no hooks, no LFS smudge, no symlinks, long paths on).

Usage:
    python -I acquire.py --dest DIR URL [URL ...] [--out FILE]
A URL may carry a ref: https://github.com/owner/repo/tree/<branch-or-sha> or https://github.com/owner/repo@<ref>.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<repo>[A-Za-z0-9._-]{1,100}?)"
    r"(?:\.git)?(?:/tree/(?P<tree>[A-Za-z0-9._/-]+)|@(?P<at>[A-Za-z0-9._/-]+))?/?$"
)


def parse_url(url):
    url = url.strip()
    m = URL_RE.match(url)
    if not m or ".." in url:
        raise ValueError(f"Not an accepted GitHub repository URL: {url!r}")
    return m.group("owner"), m.group("repo"), m.group("tree") or m.group("at")


def git(args, cwd=None, hooks_dir=None):
    base = ["git", "-c", "core.longpaths=true", "-c", "core.symlinks=false", "-c", "protocol.file.allow=never",
            "-c", "filter.lfs.smudge=", "-c", "filter.lfs.process=", "-c", "filter.lfs.required=false"]
    if hooks_dir:
        base += ["-c", f"core.hooksPath={hooks_dir}"]
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    return subprocess.run(base + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)


def acquire(url, dest_root, hooks_dir, depth=None):
    owner, repo, ref = parse_url(url)
    target = os.path.join(dest_root, f"{owner}-{repo}")
    info = {"url": f"https://github.com/{owner}/{repo}", "owner": owner, "repo": repo, "dir": target,
            "requested_ref": ref, "ok": False}
    if os.path.isdir(os.path.join(target, ".git")):
        res = git(["-C", target, "fetch", "--quiet", "origin"], hooks_dir=hooks_dir)
    else:
        os.makedirs(dest_root, exist_ok=True)
        shallow = ["--depth", str(depth), "--no-single-branch"] if depth else []
        res = git(["clone", "--quiet", "--no-checkout", *shallow, info["url"] + ".git", target], hooks_dir=hooks_dir)
    if res.returncode != 0:
        info["error"] = res.stderr.strip()[-500:] or "git clone failed"
        return info
    # persist the safe settings so later read-only git commands (log, show) work on long Windows paths
    for key, value in (("core.longpaths", "true"), ("core.symlinks", "false"), ("core.hooksPath", hooks_dir)):
        git(["-C", target, "config", key, value])
    # ".../tree/main/some/folder" = branch "main" + sub-folder "some/folder"; branch names may contain "/"
    checkout_ref, subpath = ("origin/HEAD", "") if not ref else resolve_ref(target, ref)
    if not checkout_ref:
        info["error"] = f"branch/tag/commit {ref!r} not found in the repository"
        return info
    res = git(["-C", target, "checkout", "--quiet", "--force", "--detach", checkout_ref], hooks_dir=hooks_dir)
    if res.returncode != 0:
        info["error"] = f"checkout of {checkout_ref!r} failed: {res.stderr.strip()[-300:]}"
        return info
    if subpath:
        sub_dir = os.path.join(target, *subpath.split("/"))
        if not os.path.isdir(sub_dir):
            info["error"] = f"folder {subpath!r} does not exist in {checkout_ref}"
            return info
        info.update(dir=sub_dir, repo_root=target, subpath=subpath)
    head = git(["-C", target, "rev-parse", "HEAD"]).stdout.strip()
    branch = git(["-C", target, "rev-parse", "--abbrev-ref", "origin/HEAD"]).stdout.strip().replace("origin/", "")
    count_args = ["-C", target, "rev-list", "--count", "HEAD"] + (["--", subpath] if subpath else [])
    info.update(ok=True, commit=head, short=head[:7], branch=checkout_ref.replace("origin/", "") if ref else branch,
                commits=int(git(count_args).stdout.strip() or 0))
    return info


def resolve_ref(target, ref_path):
    """Split 'main/some/folder' into the longest existing ref and the remaining folder path."""
    parts = ref_path.strip("/").split("/")
    for i in range(len(parts), 0, -1):
        cand = "/".join(parts[:i])
        for c in (f"origin/{cand}", cand):
            if git(["-C", target, "rev-parse", "--verify", "--quiet", c + "^{commit}"]).returncode == 0:
                return c, "/".join(parts[i:])
    return None, ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--dest", required=True)
    ap.add_argument("--depth", type=int, help="shallow clone (for comparison candidates that only need the code)")
    ap.add_argument("--out")
    args = ap.parse_args()
    hooks_dir = tempfile.mkdtemp(prefix="no-hooks-")
    results = []
    for url in args.urls:
        try:
            results.append(acquire(url, args.dest, hooks_dir, args.depth))
        except ValueError as exc:
            results.append({"url": url, "ok": False, "error": str(exc)})
    text = json.dumps(results, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
