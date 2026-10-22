"""Match each requirement to automatic evidence (inventory, git history, GitHub process) and give a HINT:
likely_met / partial / not_found / manual. Hints guide the reviewer; they are not the verdict.

Usage:
    python -I requirement_hints.py --requirements req.json --inventory inv.json [--history hist.json]
                                   [--github gh1.json --github gh2.json] [--out FILE]
"""
import argparse
import json
import sys
import unicodedata


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " " + s.lower() + " "


def tech(inv, key):
    return inv.get("technology", {}).get(key, {"count": 0, "examples": []})


def ev_tech(inv, *keys):
    out = []
    for k in keys:
        t = tech(inv, k)
        if t["count"]:
            out.append(f"{k}: {', '.join(t['examples'][:3])}")
    return out


def has(inv, key, minimum=1):
    return tech(inv, key)["count"] >= minimum


def r_endpoints(req, inv, ctx):
    n, need = inv["endpoints"]["count"], req.get("min_count") or 1
    ev = [f"{n} endpoint-e ({', '.join(f'{k}: {v}' for k, v in inv['endpoints']['by_kind'].items())})"]
    return ("likely_met" if n >= need else "partial" if n else "not_found"), ev, f"Kërkohen ≥{need}."


def r_models(req, inv, ctx):
    m, mig, need = inv["models"]["count"], inv["migrations"]["count"], req.get("min_count") or 1
    ev = [f"{m} modele: {', '.join(inv['models']['names'][:12])}{'…' if m > 12 else ''}", f"{mig} migrime"]
    wants_mig = "migr" in ctx
    status = "likely_met" if m >= need and (mig or not wants_mig) else "partial" if m else "not_found"
    return status, ev, f"Kërkohen ≥{need} modele" + (" me migrime." if wants_mig else ".")


def r_swagger(req, inv, ctx):
    ok = has(inv, "swagger_openapi") or "fastapi" in inv["frameworks"]
    return ("likely_met" if ok else "not_found"), ev_tech(inv, "swagger_openapi"), "Verifiko që të gjitha endpoint-et shfaqen."


def r_orm(req, inv, ctx):
    return ("likely_met" if has(inv, "orm") else "not_found"), ev_tech(inv, "orm"), ""


def r_auth(req, inv, ctx):
    pieces = {"jwt/token": has(inv, "jwt"), "hash fjalëkalimi": has(inv, "password_hashing"),
              "role/autorizim": has(inv, "roles_authorization", 3)}
    found = [k for k, v in pieces.items() if v]
    status = "likely_met" if len(found) == 3 else "partial" if found else "not_found"
    return status, ev_tech(inv, "jwt", "password_hashing", "roles_authorization"), f"Gjetur: {', '.join(found) or '-'}."


def r_middleware(req, inv, ctx):
    ok = has(inv, "middleware")
    return ("likely_met" if ok else "not_found"), ev_tech(inv, "middleware", "logging"), "Verifiko logging + auth në middleware."


def r_react(req, inv, ctx):
    react = "react" in inv["frameworks"] or has(inv, "react")
    wants_ctx = "context" in ctx
    ctx_ok = has(inv, "react_context")
    status = "likely_met" if react and (ctx_ok or not wants_ctx) else "partial" if react else "not_found"
    return status, ev_tech(inv, "react", "react_context", "redux"), ("Context API: " + ("po" if ctx_ok else "jo")) if wants_ctx else ""


def r_frontend(req, inv, ctx):
    fws = [f for f in inv["frameworks"] if f in ("react", "vue", "@angular/core", "svelte", "next", "Flutter", "react-native")]
    return ("likely_met" if fws else "not_found"), [", ".join(fws)] if fws else [], ""


def r_tests(req, inv, ctx):
    t, ci = inv["tests"]["count"], inv["ci_files"]
    wants_ci = " ci" in ctx or "ci/cd" in ctx or "pipeline" in ctx
    wants_cd = "cd " in ctx or "/cd" in ctx or "deploy" in ctx
    ev = [f"{t} teste në {len(inv['tests']['files'])} skedarë", f"CI: {', '.join(ci) or 'asnjë'}",
          f"CD/deploy në CI: {'po' if inv.get('ci_has_deploy') else 'jo'}"]
    missing = []
    if not t:
        missing.append("teste")
    if wants_ci and not ci:
        missing.append("CI")
    if wants_cd and not inv.get("ci_has_deploy"):
        missing.append("CD")
    status = "not_found" if not t else ("partial" if missing else "likely_met")
    return status, ev, f"Mungon: {', '.join(missing)}." if missing else ""


def r_docs(req, inv, ctx):
    docs = inv["docs"]
    return ("manual" if docs else "not_found"), [", ".join(docs[:6])], "Kontrollo saktësinë e README-së kundrejt kodit."


def r_pm(req, inv, ctx):
    hist = ctx_data["history"] or {}
    keys = hist.get("issue_tracker_keys", {})
    n = keys.get("commits_with_key", 0)
    gh = ctx_data["github"]
    issues = sum((g.get("issues") or {}).get("total", 0) for g in gh)
    ev = [f"{n} commit-e me çelës tiketash ({', '.join(keys.get('projects', {}))})" if n else "asnjë çelës Jira/tiketash në commit-e",
          f"{issues} GitHub issues"]
    return ("likely_met" if n >= 5 or issues >= 5 else "partial" if n or issues else "manual"), ev, "Board-i (Jira/Projects) duhet parë me dorë."


def r_git(req, inv, ctx):
    gh = [g for g in ctx_data["github"] if g.get("pull_requests")]
    if not gh:
        limits = [l for g in ctx_data["github"] for l in g.get("limitations", []) if "rate limit" in l]
        return "manual", [], ("GitHub API: kufiri i kërkesave u arrit - vendos GITHUB_TOKEN." if limits
                              else "Mungojnë të dhënat nga GitHub API.")
    prs = sum((g.get("pull_requests") or {}).get("total", 0) for g in gh)
    checked = sum((g.get("reviews") or {}).get("prs_checked", 0) for g in gh)
    reviewed = sum((g.get("reviews") or {}).get("prs_with_review_by_other", 0) for g in gh)
    ev = [f"{prs} pull request", f"review nga dikush tjetër: {reviewed}/{checked} PR të kontrolluara"]
    wants_review = "review" in ctx
    status = "not_found" if not prs else ("partial" if wants_review and checked and reviewed / checked < 0.3 else "likely_met")
    return status, ev, ""


def r_llm(req, inv, ctx):
    openai_code = tech(inv, "openai").get("code_hits", 0) > 0
    openai_pkg = has(inv, "openai")
    other = tech(inv, "other_llm").get("code_hits", 0) > 0
    wants_openai = "openai" in ctx
    if openai_code:
        return "likely_met", ev_tech(inv, "openai"), ""
    if openai_pkg and other:
        return "partial", ev_tech(inv, "openai", "other_llm"), \
            "Paketa OpenAI është e instaluar por nuk përdoret në kod; thirrjet bëhen te një LLM tjetër."
    if openai_pkg:
        return "partial", ev_tech(inv, "openai"), "Paketa OpenAI është e deklaruar por nuk u gjet përdorim në kod."
    if other:
        return ("partial" if wants_openai else "likely_met"), ev_tech(inv, "other_llm"), \
            "Përdoret LLM tjetër (jo OpenAI)." if wants_openai else ""
    return "not_found", [], ""


def r_cache(req, inv, ctx):
    redis, cache = has(inv, "redis"), has(inv, "cache")
    wants_redis_only = "redis" in ctx and "ngjashme" not in ctx and "similar" not in ctx
    status = "likely_met" if (redis or (cache and not wants_redis_only)) else "partial" if cache else "not_found"
    return status, ev_tech(inv, "redis", "cache"), ""


def r_background(req, inv, ctx):
    return ("likely_met" if has(inv, "background_jobs") else "not_found"), ev_tech(inv, "background_jobs"), ""


def r_tenant(req, inv, ctx):
    n = tech(inv, "multi_tenancy")["count"]
    return ("likely_met" if n >= 20 else "partial" if n else "not_found"), ev_tech(inv, "multi_tenancy"), \
        "Verifiko izolimin e të dhënave mes tenant-ëve."


def r_search(req, inv, ctx):
    return ("manual" if has(inv, "search_filter") else "not_found"), ev_tech(inv, "search_filter"), \
        "Verifiko filtrimin e avancuar (disa kritere, pagination) me dorë."


def r_client_server(req, inv, ctx):
    fws = inv["frameworks"]
    fe = any(f in fws for f in ("react", "vue", "@angular/core", "svelte", "next", "Flutter", "react-native"))
    be = inv["endpoints"]["count"] > 0
    ev = [f"repo: {', '.join(r['label'] for r in inv.get('repos', []))}", f"framework-e: {', '.join(fws)}"]
    return ("likely_met" if fe and be else "partial" if be else "not_found"), ev, "Verifiko që klienti flet vetëm me API."


def r_http(req, inv, ctx):
    n = inv["endpoints"]["count"]
    return ("likely_met" if n else "not_found"), [f"{n} endpoint-e HTTP"] + ev_tech(inv, "https"), "Stili REST verifikohet me dorë."


def r_framework(req, inv, ctx):
    fws = inv["frameworks"]
    backend = [f for f in fws if f in ("ASP.NET Core", "fastapi", "django", "djangorestframework", "flask", "express",
                                       "@nestjs/core", "Spring Boot", "fastify", "Laravel", "gin-gonic")]
    return ("likely_met" if backend else "manual"), [", ".join(fws)], ""


def r_oop(req, inv, ctx):
    langs = list(inv["files_by_language"])
    return "manual", [f"gjuhët: {', '.join(langs[:5])}"], "OOP gjykohet duke lexuar kodin (klasa, ndërfaqe, trashëgimi)."


def r_docker(req, inv, ctx):
    d = inv["docker_files"]
    return ("likely_met" if d else "not_found"), [", ".join(d)], ""


def r_realtime(req, inv, ctx):
    return ("likely_met" if has(inv, "websocket_realtime") else "not_found"), ev_tech(inv, "websocket_realtime"), ""


def r_queue(req, inv, ctx):
    return ("likely_met" if has(inv, "message_queue") else "not_found"), ev_tech(inv, "message_queue"), ""


# priority order matters: first rule whose keyword appears in the title wins, then the same over the full text
RULES = [
    (("swagger", "openapi"), r_swagger),
    (("endpoint",), r_endpoints),
    (("modele", "model", "entitet", "entity", "migrim", "migration"), r_models),
    (("openai", "llm", "chatbot", "gpt", " ai "), r_llm),
    (("cach", "redis"), r_cache),
    (("background", "asynchron", "asinkron", "job", "queue task", "celery"), r_background),
    (("tenan",), r_tenant),
    (("search", "kerkim", "filter"), r_search),
    (("middleware",), r_middleware),
    (("react",), r_react),
    (("frontend", "vue", "angular", "mobile"), r_frontend),
    (("test",), r_tests),
    (("ci/cd", "pipeline"), r_tests),
    (("autentik", "autoriz", "authentic", "authoriz", "login", "register", "jwt"), r_auth),
    (("orm", "databaz", "database"), r_orm),
    (("jira", "github projects", "trello", "menaxhim", "project management", "scrum"), r_pm),
    (("pull request", "code review", " git ", "bashkepun", "collaboration"), r_git),
    (("framework", "fastapi", "django", "spring", ".net", "node"), r_framework),
    (("klient", "client", "server"), r_client_server),
    (("http", "rest"), r_http),
    (("oop", "object"), r_oop),
    (("docker", "container", "kontejner"), r_docker),
    (("websocket", "real-time", "realtime", "signalr"), r_realtime),
    (("rabbitmq", "kafka", "message broker", "mesazh"), r_queue),
    (("dokument", "documentation", "readme"), r_docs),
]

ctx_data = {"history": None, "github": []}


def hint_for(req, inv):
    title, full = norm(req.get("title")), norm(f"{req.get('title')} {req.get('text')}")
    for haystack in (title, full):
        for keywords, fn in RULES:
            if any(k in haystack for k in keywords):
                status, evidence, note = fn(req, inv, full)
                return {"id": req["id"], "title": req.get("title"), "rule": fn.__name__[2:], "status": status,
                        "evidence": [e for e in evidence if e], "note": note}
    return {"id": req["id"], "title": req.get("title"), "rule": None, "status": "manual", "evidence": [],
            "note": "Asnjë rregull automatik; vlerësohet me dorë."}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--history")
    ap.add_argument("--github", action="append", default=[])
    ap.add_argument("--out")
    args = ap.parse_args()
    def load(p, default=None):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            if default is None:
                raise
            return default

    reqs, inv = load(args.requirements), load(args.inventory)
    ctx_data["history"] = load(args.history, {}) if args.history else None
    ctx_data["github"] = [g for g in (load(p, {}) for p in args.github) if g]
    hints = [hint_for(r, inv) for r in reqs["items"]]
    counts = {s: sum(1 for h in hints if h["status"] == s) for s in ("likely_met", "partial", "not_found", "manual")}
    result = {"hints": hints, "counts": counts,
              "note": "Automatic hints only. The final Met/Partially met/Not met decision is made by reading the code."}
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"counts": counts, "hints": [f"{h['id']} {h['status']:<10} {h['title']}" for h in hints]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
