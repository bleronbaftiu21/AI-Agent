"""Run the automated part of a Repo Auditor Pro audit for one or many groups (batch).

Steps: requirements -> clone -> inventory -> git history -> AI signals -> GitHub process -> requirement hints
-> cross-group similarity -> summary (JSON + CSV) -> a ready prompt for the judgment step (Claude + skill).
Progress is written to <output_dir>/job.json so a UI can follow it. Read-only towards the repositories.

Usage:
    python -I pipeline.py --config job-config.json
Config keys: title, groups [{name, repos: [url, ...]}], requirements_file | requirements_text, comparison [url],
             base [url], ai_policy, deadline, start, output_dir, workspace, language.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def slug(text):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return s[:60] or "group"


def replace_with_retry(src, dst, attempts=40):
    """os.replace fails on Windows while another process (the web UI) has dst open for reading; retry briefly."""
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05)


class Job:
    def __init__(self, config):
        self.cfg = config
        self.out = config["output_dir"]
        os.makedirs(self.out, exist_ok=True)
        self.state_path = os.path.join(self.out, "job.json")
        self.log_path = os.path.join(self.out, "log.txt")
        self.state = {**config, "status": "running", "started": now(), "finished": None, "steps": [],
                      "groups_state": {}}
        self.save()

    def save(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.state, fh, indent=2, ensure_ascii=False)
        replace_with_retry(tmp, self.state_path)

    def log(self, msg):
        line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        print(line, flush=True)

    def step(self, name, group=None):
        entry = {"name": name, "group": group, "status": "running", "started": now(), "finished": None, "message": ""}
        self.state["steps"].append(entry)
        self.save()
        return entry

    def end(self, entry, status="done", message=""):
        entry.update(status=status, finished=now(), message=message[-800:])
        self.save()

    def run(self, script, *args, step=None):
        cmd = [PY, "-I", os.path.join(HERE, script), *map(str, args)]
        self.log(f"$ {script} {' '.join(str(a) for a in args)[:300]}")
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if res.returncode != 0:
            msg = (res.stderr or res.stdout).strip()[-1500:]
            self.log(f"  ! {script} failed: {msg}")
            if step:
                self.end(step, "error", msg)
            return False
        if step:
            self.end(step)
        return True


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def requirements(job):
    cfg, out = job.cfg, job.out
    target = os.path.join(out, "requirements.json")
    st = job.step("Leximi i kërkesave")
    if cfg.get("requirements_file"):
        ok = job.run("extract_requirements.py", "--file", cfg["requirements_file"], "--out", target, step=st)
    elif cfg.get("requirements_text", "").strip():
        txt = os.path.join(out, "requirements.txt")
        with open(txt, "w", encoding="utf-8") as fh:
            fh.write(cfg["requirements_text"])
        ok = job.run("extract_requirements.py", "--text-file", txt, "--out", target, step=st)
    else:
        job.end(st, "skipped", "Nuk u dha dokument kërkesash; kërkesat do të nxirren nga README.")
        return None
    data = load(target)
    if ok and data:
        st["message"] = f"{len(data['items'])} kërkesa"
        job.save()
    return target if ok else None


def acquire(job, urls, dest, label):
    out = os.path.join(dest, "acquire.json")
    st = job.step("Klonimi i repove", label)
    job.run("acquire.py", "--dest", os.path.join(job.cfg["workspace"], slug(label)), *urls, "--out", out)
    data = load(out, [])
    bad = [r for r in data if not r.get("ok")]
    job.end(st, "error" if bad and len(bad) == len(data) else "done",
            "; ".join(f"{r['url']}: {r.get('error')}" for r in bad) or
            ", ".join(f"{r['repo']}@{r['short']}" for r in data))
    return [r for r in data if r.get("ok")]


def analyze_group(job, group, req_path):
    name = group["name"]
    gdir = os.path.join(job.out, slug(name))
    ev = os.path.join(gdir, "evidence")
    os.makedirs(ev, exist_ok=True)
    gstate = job.state["groups_state"].setdefault(name, {"slug": slug(name), "dir": gdir, "status": "running"})
    job.save()
    repos = acquire(job, group["repos"], ev, name)
    if not repos:
        gstate["status"] = "error"
        job.save()
        return None
    gstate["repos"] = [{k: r.get(k) for k in ("url", "repo", "branch", "commit", "short", "dir", "commits")} for r in repos]
    labelled = [f"{r['repo']}={r['dir']}" for r in repos]

    st = job.step("Inventari (endpoint-e, modele, teste)", name)
    inv_args = []
    for spec in labelled:
        inv_args += ["--repo", spec]
    job.run("inventory.py", *inv_args, "--out", os.path.join(ev, "inventory.json"), step=st)

    st = job.step("Historia e git-it", name)
    hist_args = list(inv_args)
    for opt in ("deadline", "start"):
        if job.cfg.get(opt):
            hist_args += [f"--{opt}", job.cfg[opt]]
    job.run("git_history.py", *hist_args, "--out", os.path.join(ev, "history.json"), step=st)

    st = job.step("Sinjalet e AI-së", name)
    ok = True
    for r in repos:
        ok &= job.run("ai_signals.py", "--repo", r["dir"], "--out", os.path.join(ev, f"ai-{slug(r['repo'])}.json"))
    job.end(st, "done" if ok else "error")

    st = job.step("Procesi në GitHub (PR, review)", name)
    gh_files = []
    for r in repos:
        f = os.path.join(ev, f"github-{slug(r['repo'])}.json")
        if job.run("github_process.py", "--repo", f"{r['owner']}/{r['repo']}", "--out", f):
            gh_files.append(f)
    job.end(st, "done" if gh_files else "error")

    candidates = github_candidates(job, name, ev)
    gstate["github_candidates"] = [{"full_name": c["full_name"], "reason": c["reason"]} for c in candidates]
    job.save()

    if req_path:
        st = job.step("Lidhja e kërkesave me dëshmitë", name)
        args = ["--requirements", req_path, "--inventory", os.path.join(ev, "inventory.json"),
                "--history", os.path.join(ev, "history.json")]
        for f in gh_files:
            args += ["--github", f]
        for spec in labelled:
            args += ["--repo", spec]
        job.run("requirement_hints.py", *args, "--out", os.path.join(ev, "hints.json"), step=st)

    write_prompt(job, name, gdir, ev, req_path)
    gstate["status"] = "evidence_ready"
    job.save()
    return {"name": name, "dirs": [r["dir"] for r in repos], "candidates": candidates}


def github_candidates(job, name, ev):
    """Search all of GitHub for projects this one may be copied from, then clone them (shallow) for comparison."""
    st = job.step("Kërkimi në GitHub për projekte të ngjashme", name)
    out = os.path.join(ev, "github_similar.json")
    if not job.run("find_similar_github.py", "--acquire", os.path.join(ev, "acquire.json"), "--out", out):
        job.end(st, "error", "Kërkimi në GitHub dështoi.")
        return []
    found = (load(out, {}) or {}).get("candidates", [])
    if not found:
        job.end(st, "done", "Asnjë kandidat. " + " ".join(load(out, {}).get("limitations", [])))
        return []
    acq_out = os.path.join(ev, "github_candidates_acquire.json")
    job.run("acquire.py", "--depth", "1", "--dest", os.path.join(job.cfg["workspace"], slug(name), "_github"),
            *[c["url"] for c in found], "--out", acq_out)
    cloned = {f"{r['owner']}/{r['repo']}".lower(): r["dir"] for r in load(acq_out, []) if r.get("ok")}
    for c in found:
        c["dir"] = cloned.get(c["full_name"].lower())
    found = [c for c in found if c["dir"]]
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({**load(out, {}), "candidates": found}, fh, indent=2, ensure_ascii=False)
    limits = " ".join(load(out, {}).get("limitations", []))
    job.end(st, "done", f"{len(found)} kandidatë: " + ", ".join(c["full_name"] for c in found) + (f". {limits}" if limits else ""))
    return found


def write_prompt(job, name, gdir, ev, req_path):
    lang = job.cfg.get("language") or "shqip"
    prompt = f"""Përdor skill-in repo-auditor-pro për të përfunduar auditimin e grupit "{name}".

Dëshmitë automatike janë mbledhur tashmë - mos i kloni repot përsëri:
- Repot e klonuara dhe commit-et: {os.path.join(ev, 'acquire.json')}
- Kërkesat (R1..Rn): {req_path or 'nuk u dhanë - nxirri nga README'}
- Lidhja automatike kërkesë -> dëshmi (vetëm sugjerime): {os.path.join(ev, 'hints.json')}
- Inventari: {os.path.join(ev, 'inventory.json')}
- Historia e git-it: {os.path.join(ev, 'history.json')}
- Sinjalet e AI-së: {ev}/ai-*.json
- Procesi në GitHub: {ev}/github-*.json
- Projekte të ngjashme të gjetura në GitHub (kandidatë për kopjim): {os.path.join(ev, 'github_similar.json')}
- Ngjashmëria e kodit me grupet e tjera dhe me kandidatët nga GitHub (çelësat "GitHub: ..."): {os.path.join(job.out, 'similarity.json')}

Kontrollo edhe: kodin e mbetur nga shabllonet (inventory.json -> template_leftovers), punën në kohë
(history.json -> weekly, last_7_days_share), sekretet (inventory.json -> possible_secrets) dhe nëse README
pretendon gjëra që kodi nuk i ka. Për çdo kandidat me ngjashmëri mbi ~20%, hap skedarët që përputhen dhe
krahaso datat (created_at i kandidatit kundrejt commit-it të parë të projektit) për të parë kush ishte i pari.

Politika e AI: {job.cfg.get('ai_policy') or 'unspecified'}. Afati: {job.cfg.get('deadline') or '-'}.
Lexo kodin për çdo kërkesë dhe vendos Met / Partially met / Not met / Cannot verify me dëshmi file:line,
pastaj integritetin, kategoritë teknike dhe notën sipas audit-method.md (kërkesat 70%).
Shkruaj audit-report.md (në {lang}) dhe audit-report.json te: {gdir}
Mos ekzekuto kodin e projektit dhe mos ndrysho asgjë në repot e klonuara.
"""
    with open(os.path.join(gdir, "claude_prompt.txt"), "w", encoding="utf-8") as fh:
        fh.write(prompt)


def similarity(job, analyzed):
    cfg = job.cfg
    groups = {g["name"]: g["dirs"] for g in analyzed if g}
    for g in analyzed:
        for c in (g or {}).get("candidates", []):
            groups.setdefault(f"GitHub: {c['full_name']}", [c["dir"]])
    if cfg.get("comparison"):
        ev = os.path.join(job.out, "_comparison")
        os.makedirs(ev, exist_ok=True)
        for r in acquire(job, cfg["comparison"], ev, "_comparison"):
            groups[f"krahasim: {r['repo']}"] = [r["dir"]]
    if len(groups) < 2:
        st = job.step("Ngjashmëria e kodit")
        job.end(st, "skipped", "S'ka me çka të krahasohet: asnjë grup tjetër dhe asnjë kandidat nga GitHub.")
        return
    base_dirs = []
    if cfg.get("base"):
        ev = os.path.join(job.out, "_base")
        os.makedirs(ev, exist_ok=True)
        base_dirs = [r["dir"] for r in acquire(job, cfg["base"], ev, "_base")]
    gfile = os.path.join(job.out, "similarity-groups.json")
    with open(gfile, "w", encoding="utf-8") as fh:
        json.dump(groups, fh, ensure_ascii=False)
    st = job.step("Ngjashmëria e kodit (grupet + GitHub)")
    args = ["--groups", gfile, "--out", os.path.join(job.out, "similarity.json")]
    if base_dirs:
        args += ["--base", *base_dirs]
    job.run("similarity.py", *args, step=st)


def ai_lines(ev):
    strong = medium = total = 0
    for f in os.listdir(ev):
        if f.startswith("ai-") and f.endswith(".json"):
            d = load(os.path.join(ev, f), {})
            total += d.get("total_nonblank_lines", 0)
            strong += d.get("lines_by_level", {}).get("strong_signals", 0)
            medium += d.get("lines_by_level", {}).get("several_medium_signals", 0)
    return strong, medium, total


def summarize(job):
    st = job.step("Përmbledhja (tabela)")
    sim = load(os.path.join(job.out, "similarity.json"), {})
    rows = []
    for name, gs in job.state["groups_state"].items():
        gdir = gs["dir"]
        ev = os.path.join(gdir, "evidence")
        inv = load(os.path.join(ev, "inventory.json"), {})
        hist = load(os.path.join(ev, "history.json"), {})
        hints = load(os.path.join(ev, "hints.json"), {})
        rep = load(os.path.join(gdir, "audit-report.json"), {})
        strong, medium, total = ai_lines(ev) if os.path.isdir(ev) else (0, 0, 0)
        row_sim = (sim.get("matrix") or {}).get(name, {})
        mine = {f"GitHub: {c['full_name']}" for c in gs.get("github_candidates", [])}
        others = {k: v for k, v in row_sim.items() if not k.startswith("GitHub: ")}
        on_github = {k: v for k, v in row_sim.items() if k in mine}
        top_other = max(others.items(), key=lambda x: x[1]) if others else (None, None)
        top_gh = max(on_github.items(), key=lambda x: x[1]) if on_github else (None, None)
        gh = [load(os.path.join(ev, f), {}) for f in os.listdir(ev) if f.startswith("github-")] if os.path.isdir(ev) else []
        checked = sum((g.get("reviews") or {}).get("prs_checked", 0) for g in gh)
        reviewed = sum((g.get("reviews") or {}).get("prs_with_review_by_other", 0) for g in gh)
        scores = rep.get("scores", {})
        reqs = rep.get("requirements", {})
        ai = (rep.get("integrity") or {}).get("ai_assistance") or {}
        rows.append({
            "grupi": name,
            "repot": " ".join(r["url"] for r in gs.get("repos", [])),
            "statusi": "raport i plotë" if rep else gs.get("status"),
            "nota_perfundimtare": scores.get("final"),
            "nota_kerkesat": scores.get("requirements_only"),
            "kerkesat_detyrueshme_pct": reqs.get("mandatory_compliance_pct"),
            "sugjerime_met": (hints.get("counts") or {}).get("likely_met"),
            "sugjerime_partial": (hints.get("counts") or {}).get("partial"),
            "sugjerime_not_found": (hints.get("counts") or {}).get("not_found"),
            "sugjerime_manual": (hints.get("counts") or {}).get("manual"),
            "endpoint": (inv.get("endpoints") or {}).get("count"),
            "modele": (inv.get("models") or {}).get("count"),
            "migrime": (inv.get("migrations") or {}).get("count"),
            "teste": (inv.get("tests") or {}).get("count"),
            "rreshta_kodi": inv.get("source_lines_total"),
            "anetare": len(hist.get("authors", [])),
            "commit": hist.get("non_merge_commits"),
            "dite_aktive": hist.get("active_days"),
            "pr_me_review": f"{reviewed}/{checked}" if checked else None,
            "ai_vleresim": f"{ai.get('estimate_low_pct')}-{ai.get('estimate_high_pct')}% ({ai.get('confidence')})" if ai else None,
            "ai_sinjale_forta_rreshta": strong,
            "ngjashmeria_max": top_other[1],
            "ngjashem_me": top_other[0],
            "github_ngjashmeria_max": top_gh[1],
            "github_ngjashem_me": top_gh[0].replace("GitHub: ", "") if top_gh[0] else None,
            "github_kandidate": len(gs.get("github_candidates", [])),
            "kodi_7_ditet_e_fundit": hist.get("last_7_days_share"),
            "mbetje_shablloni": len(inv.get("template_leftovers", [])),
            "flamuj_historie": len(hist.get("flags", [])),
            "sekrete_te_mundshme": len(inv.get("possible_secrets", [])),
        })
    with open(os.path.join(job.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)
    if rows:
        with open(os.path.join(job.out, "summary.csv"), "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter=";")
            w.writeheader()
            w.writerows(rows)
    job.end(st, "done", f"{len(rows)} grupe")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--summary-only", action="store_true", help="only rebuild summary.json/csv (after reports change)")
    args = ap.parse_args()
    cfg = load(args.config)
    if args.summary_only:
        job = Job.__new__(Job)
        job.cfg, job.out = cfg, cfg["output_dir"]
        job.state_path, job.log_path = os.path.join(job.out, "job.json"), os.path.join(job.out, "log.txt")
        job.state = load(job.state_path)
        summarize(job)
        return 0
    job = Job(cfg)
    try:
        req = requirements(job)
        analyzed = []
        for group in cfg["groups"]:
            job.log(f"=== Grupi: {group['name']}")
            try:
                analyzed.append(analyze_group(job, group, req))
            except Exception:
                job.log(traceback.format_exc())
                job.state["groups_state"].setdefault(group["name"], {})["status"] = "error"
                job.save()
        similarity(job, analyzed)
        summarize(job)
        job.state["status"] = "evidence_ready"
    except Exception:
        job.log(traceback.format_exc())
        job.state["status"] = "error"
    job.state["finished"] = now()
    job.save()
    job.log(f"Përfundoi: {job.state['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
