"""Repo Auditor Pro - local web app.

Runs the skill's evidence pipeline from a form, follows progress, shows evidence/hints/similarity/reports,
and (when the Claude Code CLI is installed) starts the repo-auditor-pro skill for the judgment step.

Start:  run_auditor.bat   (or: .venv\\Scripts\\python -m uvicorn auditor_app.server:app --port 8765)
"""
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(PROJECT, ".claude", "skills", "repo-auditor-pro")
SCRIPTS = os.path.join(SKILL, "scripts")
REPORTS = os.path.join(PROJECT, "audit-reports")
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
# short root keeps clone paths under the Windows 260-character limit
WORKSPACE = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "RepoAuditor", "ws")
PY = sys.executable

os.makedirs(REPORTS, exist_ok=True)
_spec = importlib.util.spec_from_file_location("acquire", os.path.join(SCRIPTS, "acquire.py"))
acquire = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acquire)

app = FastAPI(title="Repo Auditor Pro")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
@app.middleware("http")
async def no_cache_ui(request, call_next):
    # always revalidate the page and its JS/CSS so an updated app is picked up without a hard refresh
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


LOCK = threading.Lock()
RUNNING = {}  # job_id -> thread


def slug(text):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return s[:60] or "group"


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def job_dir(job_id):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", job_id):
        raise HTTPException(400, "Invalid id")
    path = os.path.join(REPORTS, job_id)
    if not os.path.isdir(path):
        raise HTTPException(404, "Not found")
    return path


def find_claude():
    found = shutil.which("claude")
    if found:
        return found
    home = os.path.expanduser("~")
    for cand in (os.path.join(home, ".local", "bin", "claude.exe"),
                 os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd"),
                 os.path.join(home, ".claude", "local", "claude.exe")):
        if os.path.isfile(cand):
            return cand
    return None


SETTINGS = os.path.join(os.path.dirname(WORKSPACE), "settings.json")  # per-PC, outside the project/repo


def load_settings():
    return load(SETTINGS, {}) or {}


def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    with open(SETTINGS, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def github_token(form_value=""):
    return (form_value or "").strip() or load_settings().get("github_token") or \
        os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def claude_env():
    """Environment for the Claude CLI. When this server was started from inside another Claude session it inherits
    that session's CLAUDE_*/ANTHROPIC_* variables, which stop the CLI from using the user's own sign-in."""
    keep = {"CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "CLAUDE_CONFIG_DIR"}
    return {k: v for k, v in os.environ.items()
            if k in keep or not (k.startswith("CLAUDE") or k.startswith("ANTHROPIC"))}


def claude_signed_in():
    claude = find_claude()
    if not claude:
        return False
    try:
        res = subprocess.run([claude, "auth", "status"], capture_output=True, text=True, timeout=30,
                             env=claude_env(), encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    try:
        return bool(json.loads(res.stdout).get("loggedIn"))
    except ValueError:
        return None


def parse_groups(text):
    """One group per line: 'Name: url1, url2' or just 'url1 url2'. Blank lines and # comments are ignored."""
    groups, errors = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, urls_part = (None, line)
        m = re.match(r"^([^:]{1,80}?)\s*:\s*(https://.*)$", line)
        if m:
            name, urls_part = m.group(1).strip(), m.group(2)
        urls = [u for u in re.split(r"[\s,;]+", urls_part) if u]
        good = []
        for u in urls:
            try:
                owner, repo, _ = acquire.parse_url(u)
                good.append(u)
            except ValueError as exc:
                errors.append(str(exc))
        if good:
            if not name:
                owner, repo, _ = acquire.parse_url(good[0])
                name = owner if len(good) > 1 else f"{owner}-{repo}"
            groups.append({"name": name, "repos": good})
    names = [g["name"] for g in groups]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        errors.append(f"Emra grupesh të përsëritur: {', '.join(sorted(dupes))}")
    return groups, errors


def parse_urls(text):
    urls, errors = [], []
    for u in re.split(r"[\s,;]+", text or ""):
        if not u:
            continue
        try:
            acquire.parse_url(u)
            urls.append(u)
        except ValueError as exc:
            errors.append(str(exc))
    return urls, errors


def update_group_state(out, name, **changes):
    with LOCK:
        state = load(os.path.join(out, "job.json"), {})
        state.setdefault("groups_state", {}).setdefault(name, {}).update(changes)
        tmp = os.path.join(out, "job.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, os.path.join(out, "job.json"))


def run_claude_for_group(out, name, gstate):
    claude = find_claude()
    gdir = gstate["dir"]
    prompt_path = os.path.join(gdir, "claude_prompt.txt")
    if not claude or not os.path.isfile(prompt_path):
        update_group_state(out, name, claude="unavailable")
        return
    with open(prompt_path, encoding="utf-8") as fh:
        prompt = fh.read()
    update_group_state(out, name, claude="running", claude_started=dt.datetime.now().isoformat(timespec="seconds"))
    # the prompt goes through stdin: a multi-line argument breaks when the CLI is a Windows .cmd shim
    cmd = [claude, "-p", "--permission-mode", "acceptEdits",
           "--allowedTools", "Read,Grep,Glob,Write,Edit,Bash(git log:*),Bash(git show:*),Bash(git -C:*),Bash(python:*)",
           "--add-dir", WORKSPACE, "--add-dir", out]
    with open(os.path.join(gdir, "claude_log.txt"), "w", encoding="utf-8") as log:
        res = subprocess.run(cmd, cwd=PROJECT, input=prompt, stdout=log, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", env=claude_env())
    ok = res.returncode == 0 and os.path.isfile(os.path.join(gdir, "audit-report.json"))
    update_group_state(out, name, claude="done" if ok else "error",
                       claude_finished=dt.datetime.now().isoformat(timespec="seconds"))


def refresh_summary(out):
    subprocess.run([PY, "-I", os.path.join(SCRIPTS, "pipeline.py"), "--config", os.path.join(out, "config.json"),
                    "--summary-only"], capture_output=True)


def run_job(job_id, out, github_token, run_claude):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if github_token:
        env["GITHUB_TOKEN"] = github_token  # passed to the child process only, never written to disk
    with open(os.path.join(out, "pipeline_stdout.txt"), "w", encoding="utf-8") as log:
        subprocess.run([PY, "-I", os.path.join(SCRIPTS, "pipeline.py"), "--config", os.path.join(out, "config.json")],
                       stdout=log, stderr=subprocess.STDOUT, env=env)
    if run_claude:
        state = load(os.path.join(out, "job.json"), {})
        for name, gs in state.get("groups_state", {}).items():
            if gs.get("status") == "evidence_ready":
                run_claude_for_group(out, name, gs)
        refresh_summary(out)
    RUNNING.pop(job_id, None)


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/api/status")
def status():
    return {"claude": find_claude(), "claude_signed_in": claude_signed_in(), "github_token": bool(github_token()),
            "reports_dir": REPORTS, "workspace": WORKSPACE, "running": list(RUNNING)}


def github_rate(token):
    import urllib.request
    req = urllib.request.Request("https://api.github.com/rate_limit", headers={
        "User-Agent": "repo-auditor-pro", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode())["resources"]
        return {"ok": True, "core": res["core"], "code_search": res.get("code_search"), "authenticated": res["core"]["limit"] > 60}
    except Exception as exc:  # network error or invalid token (401)
        return {"ok": False, "error": str(exc)}


@app.get("/api/settings")
def get_settings():
    tok = load_settings().get("github_token", "")
    return {"github_token_saved": bool(tok), "github_token_hint": f"…{tok[-4:]}" if tok else None,
            "settings_file": SETTINGS, "github": github_rate(github_token())}


@app.post("/api/settings")
def post_settings(github_token_value: str = Form("", alias="github_token"), clear: bool = Form(False)):
    data = load_settings()
    if clear:
        data.pop("github_token", None)
    elif github_token_value.strip():
        check = github_rate(github_token_value.strip())
        if not check.get("authenticated"):
            raise HTTPException(400, "Token-i nuk u pranua nga GitHub. Kontrollo që është i saktë dhe aktiv.")
        data["github_token"] = github_token_value.strip()
    save_settings(data)
    return get_settings()


@app.post("/api/jobs")
async def create_job(
    links: str = Form(""), groups: str = Form(""), title: str = Form(""), requirements_text: str = Form(""),
    requirements_file: UploadFile | None = File(None), comparison: str = Form(""), base: str = Form(""),
    ai_policy: str = Form("unspecified"), deadline: str = Form(""), start: str = Form(""),
    language: str = Form("shqip"), skip_claude: bool = Form(False),
):
    # simple mode: all links form one project; advanced mode: one group per line
    if groups.strip():
        parsed, errors = parse_groups(groups)
    else:
        urls, errors = parse_urls(links)
        parsed = []
        if urls:
            owner, repo, _ = acquire.parse_url(urls[0])
            parsed = [{"name": owner if len(urls) > 1 else repo, "repos": urls}]
    comp, e2 = parse_urls(comparison)
    base_urls, e3 = parse_urls(base)
    errors += e2 + e3
    if not parsed:
        errors.append("Vendos të paktën një link GitHub të projektit.")
    for d in (deadline, start):
        if d and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            errors.append(f"Data e pavlefshme: {d}")
    if ai_policy not in ("unspecified", "forbidden", "allowed-if-disclosed", "allowed"):
        errors.append("Politika e AI e pavlefshme.")
    if errors:
        return JSONResponse({"errors": errors}, status_code=400)

    job_id = f"{dt.datetime.now():%Y%m%d-%H%M%S}-{slug(title or parsed[0]['name'])[:40]}"
    out = os.path.join(REPORTS, job_id)
    os.makedirs(out)
    req_file = None
    if requirements_file is not None and requirements_file.filename:
        ext = os.path.splitext(requirements_file.filename)[1].lower()
        if ext not in (".pdf", ".docx", ".md", ".txt"):
            return JSONResponse({"errors": ["Kërkesat: lejohen vetëm PDF, DOCX, MD ose TXT."]}, status_code=400)
        req_file = os.path.join(out, f"brief{ext}")
        with open(req_file, "wb") as fh:
            fh.write(await requirements_file.read())
    config = {
        "job_id": job_id, "title": title or parsed[0]["name"], "created": dt.datetime.now().isoformat(timespec="seconds"),
        "groups": parsed, "requirements_file": req_file, "requirements_name": requirements_file.filename if req_file else None,
        "requirements_text": requirements_text if not req_file else "", "comparison": comp, "base": base_urls,
        "ai_policy": ai_policy, "deadline": deadline or None, "start": start or None, "language": language,
        "output_dir": out, "workspace": os.path.join(WORKSPACE, job_id[:15]), "run_claude": bool(not skip_claude and find_claude() and claude_signed_in() is not False),
    }
    with open(os.path.join(out, "config.json"), "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(out, "job.json"), "w", encoding="utf-8") as fh:
        json.dump({**config, "status": "queued", "steps": [], "groups_state": {}}, fh, indent=2, ensure_ascii=False)
    t = threading.Thread(target=run_job, args=(job_id, out, github_token(), config["run_claude"]), daemon=True)
    RUNNING[job_id] = t
    t.start()
    return {"id": job_id}


@app.get("/api/jobs")
def list_jobs():
    jobs = []
    for name in sorted(os.listdir(REPORTS), reverse=True):
        path = os.path.join(REPORTS, name)
        if not os.path.isdir(path):
            continue
        state = load(os.path.join(path, "job.json"))
        if state:
            reports = sum(1 for g in state.get("groups_state", {}).values()
                          if os.path.isfile(os.path.join(g.get("dir", ""), "audit-report.json")))
            jobs.append({"id": name, "title": state.get("title"), "created": state.get("created"),
                         "status": "running" if name in RUNNING else state.get("status"),
                         "groups": len(state.get("groups", [])), "reports": reports})
        elif os.path.isfile(os.path.join(path, "audit-report.json")):
            rep = load(os.path.join(path, "audit-report.json"), {})
            jobs.append({"id": name, "title": name, "created": (rep.get("audit") or {}).get("date"), "status": "report",
                         "groups": 1, "reports": 1, "legacy": True,
                         "final": (rep.get("scores") or {}).get("final")})
    return jobs


def group_payload(gdir):
    ev = os.path.join(gdir, "evidence")
    inv = load(os.path.join(ev, "inventory.json"), {})
    if inv:
        inv["endpoints"]["items"] = inv["endpoints"]["items"][:400]
    ai = {}
    gh = {}
    if os.path.isdir(ev):
        for f in sorted(os.listdir(ev)):
            if f.startswith("ai-"):
                ai[f[3:-5]] = load(os.path.join(ev, f), {})
            elif f.startswith("github-") and not f.startswith(("github_similar", "github_candidates")):
                gh[f[7:-5]] = load(os.path.join(ev, f), {})
    md_path = os.path.join(gdir, "audit-report.md")
    prompt_path = os.path.join(gdir, "claude_prompt.txt")
    claude_log = os.path.join(gdir, "claude_log.txt")
    return {
        "acquire": load(os.path.join(ev, "acquire.json"), []),
        "inventory": inv, "history": load(os.path.join(ev, "history.json"), {}),
        "hints": load(os.path.join(ev, "hints.json"), {}), "ai": ai, "github": gh,
        "github_similar": load(os.path.join(ev, "github_similar.json")),
        "report": load(os.path.join(gdir, "audit-report.json")),
        "report_md": open(md_path, encoding="utf-8").read() if os.path.isfile(md_path) else None,
        "prompt": open(prompt_path, encoding="utf-8").read() if os.path.isfile(prompt_path) else None,
        "claude_log": open(claude_log, encoding="utf-8", errors="replace").read()[-4000:] if os.path.isfile(claude_log) else None,
    }


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    out = job_dir(job_id)
    state = load(os.path.join(out, "job.json"))
    if not state:  # a report written directly by the skill, without the app
        payload = group_payload(out)
        return {"id": job_id, "legacy": True, "title": job_id, "status": "report",
                "groups_state": {job_id: {"slug": "."}}, "groups_data": {job_id: payload}, "summary": []}
    state["id"] = job_id
    state["status"] = "running" if job_id in RUNNING and state.get("status") != "evidence_ready" else state.get("status")
    if job_id in RUNNING and state.get("status") == "evidence_ready":
        state["status"] = "claude_running"
    state["requirements"] = load(os.path.join(out, "requirements.json"), {}).get("items")
    state["summary"] = load(os.path.join(out, "summary.json"), [])
    sim = load(os.path.join(out, "similarity.json"))
    if sim:
        for p in sim.get("pairs", []):
            p["matches"] = p.get("matches", [])[:8]
    state["similarity"] = sim
    state["groups_data"] = {name: group_payload(gs["dir"]) for name, gs in state.get("groups_state", {}).items()
                            if gs.get("dir")}
    state.pop("requirements_text", None)
    return state


@app.get("/api/jobs/{job_id}/log", response_class=PlainTextResponse)
def get_log(job_id: str):
    path = os.path.join(job_dir(job_id), "log.txt")
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()[-20000:]


@app.get("/api/jobs/{job_id}/file")
def get_file(job_id: str, path: str):
    out = os.path.realpath(job_dir(job_id))
    full = os.path.realpath(os.path.join(out, path))
    if not full.startswith(out + os.sep) or not os.path.isfile(full):
        raise HTTPException(404, "Not found")
    return FileResponse(full, filename=os.path.basename(full))


@app.post("/api/jobs/{job_id}/groups/{name}/claude")
def start_claude(job_id: str, name: str):
    out = job_dir(job_id)
    if not find_claude():
        raise HTTPException(400, "Claude Code CLI nuk u gjet.")
    if claude_signed_in() is False:
        raise HTTPException(400, "Claude Code CLI nuk është i kyçur. Hap PowerShell, shkruaj 'claude' dhe pastaj '/login'.")
    if job_id in RUNNING:
        raise HTTPException(409, "Ky auditim është ende duke punuar.")
    state = load(os.path.join(out, "job.json"), {})
    gs = state.get("groups_state", {}).get(name)
    if not gs:
        raise HTTPException(404, "Grupi nuk u gjet.")

    def work():
        run_claude_for_group(out, name, gs)
        refresh_summary(out)
        RUNNING.pop(job_id, None)

    t = threading.Thread(target=work, daemon=True)
    RUNNING[job_id] = t
    t.start()
    return {"started": True}


@app.post("/api/jobs/{job_id}/refresh-summary")
def post_refresh(job_id: str):
    out = job_dir(job_id)
    refresh_summary(out)
    return {"summary": load(os.path.join(out, "summary.json"), [])}
