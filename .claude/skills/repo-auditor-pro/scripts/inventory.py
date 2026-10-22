"""Inventory one project (one or more repo folders): languages, frameworks, endpoints, models, migrations,
tests, docs/CI, and technology markers used as evidence for requirements. Read-only.

Usage:
    python -I inventory.py --repo DIR [--repo DIR ...] [--out FILE]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

EXCLUDED_DIRS = {
    ".git", "node_modules", "vendor", "venv", ".venv", "env", "dist", "build", "target", "bin", "obj",
    "__pycache__", ".next", ".nuxt", "coverage", ".idea", ".vscode", ".gradle", "Pods", "packages",
    "wwwroot", "static/admin", ".dart_tool", ".expo",
}
LANG = {
    ".cs": "C#", ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript (JSX)", ".ts": "TypeScript",
    ".tsx": "TypeScript (TSX)", ".java": "Java", ".kt": "Kotlin", ".go": "Go", ".rs": "Rust", ".php": "PHP",
    ".rb": "Ruby", ".dart": "Dart", ".swift": "Swift", ".c": "C", ".cpp": "C++", ".h": "C/C++ header",
    ".vue": "Vue", ".svelte": "Svelte", ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sql": "SQL",
    ".prisma": "Prisma",
}
TEXT_EXTRA = {".json", ".yml", ".yaml", ".xml", ".csproj", ".toml", ".cfg", ".ini", ".md", ".gradle", ".env",
              ".properties", ".txt", ".mod"}
GENERATED = re.compile(r"(\.Designer\.cs$|ModelSnapshot\.cs$|\.g\.cs$|\.min\.(js|css)$|-lock\.json$|\.lock$)", re.I)
MIGRATION_PATH = re.compile(r"(^|/)(migrations|alembic/versions|db/migrate|database/migrations)(/|$)", re.I)
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|.*\.tests?|.*tests)(/|$)|(\.|_)(test|spec)s?\.[a-z]+$|^test_.*\.py$|Tests?\.cs$", re.I)

ENDPOINT_PATTERNS = [
    ("aspnet", (".cs",), re.compile(r"\[\s*Http(Get|Post|Put|Patch|Delete)\b(?:\s*\(\s*\"([^\"]*)\")?")),
    ("aspnet-minimal", (".cs",), re.compile(r"\.Map(Get|Post|Put|Patch|Delete)\s*\(\s*\"([^\"]*)\"")),
    ("fastapi/flask", (".py",), re.compile(r"@\w+\.(get|post|put|patch|delete)\s*\(\s*[\"']([^\"']*)")),
    ("flask-route", (".py",), re.compile(r"@\w+\.route\s*\(\s*[\"']([^\"']*)[\"'](.*)")),
    ("drf-action", (".py",), re.compile(r"@action\s*\((.*)")),
    ("express", (".js", ".ts", ".mjs", ".cjs"), re.compile(r"\b(?:app|router|server|r)\.(get|post|put|patch|delete)\s*\(\s*[\"'`]([^\"'`]*)")),
    ("nestjs", (".ts",), re.compile(r"@(Get|Post|Put|Patch|Delete)\s*\(\s*[\"']?([^\"')]*)")),
    ("spring", (".java", ".kt"), re.compile(r"@(Get|Post|Put|Patch|Delete|Request)Mapping\b(?:\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?\"?([^\")]*))?")),
    ("go", (".go",), re.compile(r"\.(GET|POST|PUT|PATCH|DELETE|HandleFunc)\s*\(\s*\"([^\"]*)")),
    ("laravel", (".php",), re.compile(r"Route::(get|post|put|patch|delete|apiResource|resource)\s*\(\s*['\"]([^'\"]*)")),
]
DRF_VIEWSET = re.compile(r"class\s+(\w+)\s*\(\s*[\w.]*(ModelViewSet|ViewSet|GenericViewSet|ReadOnlyModelViewSet)")
DJANGO_PATH = re.compile(r"\b(?:re_)?path\s*\(\s*r?[\"']([^\"']*)")

MODEL_PATTERNS = [
    ("ef-dbset", (".cs",), re.compile(r"DbSet\s*<\s*(\w+)\s*>")),
    ("django", (".py",), re.compile(r"class\s+(\w+)\s*\(\s*[\w.]*models\.Model\s*\)")),
    ("sqlalchemy/sqlmodel", (".py",), re.compile(r"class\s+(\w+)\s*\(\s*(?:Base|db\.Model|SQLModel\s*,\s*table\s*=\s*True)\s*\)")),
    ("jpa/typeorm", (".java", ".kt", ".ts"), re.compile(r"@Entity\b[^\n]*\n(?:\s*@[^\n]*\n)*\s*(?:export\s+)?(?:public\s+)?(?:data\s+)?class\s+(\w+)")),
    ("mongoose", (".js", ".ts"), re.compile(r"mongoose\.model\s*\(\s*[\"'](\w+)")),
    ("sequelize", (".js", ".ts"), re.compile(r"(?:sequelize\.define\s*\(\s*[\"'](\w+)|class\s+(\w+)\s+extends\s+Model\b)")),
    ("prisma", (".prisma",), re.compile(r"^model\s+(\w+)\s*\{", re.M)),
    ("laravel", (".php",), re.compile(r"class\s+(\w+)\s+extends\s+Model\b")),
]
TEST_FUNC = re.compile(r"\[(Fact|Theory|Test|TestMethod|TestCase)\b|^\s*(?:async\s+)?def\s+test_\w+|"
                       r"\b(?:it|test)\s*\(\s*[\"'`]|@Test\b|func\s+Test\w+\s*\(", re.M)

# technology markers: name -> regex (searched in source + config files)
TECH = {
    "swagger_openapi": r"AddSwaggerGen|UseSwaggerUI|swagger-ui|swagger_ui|drf_spectacular|drf_yasg|springdoc|swagger-jsdoc|@nestjs/swagger|FastAPI\(",
    "jwt": r"JwtBearer|jsonwebtoken|jwt\.(encode|decode|sign|verify)|SimpleJWT|rest_framework_simplejwt|PyJWT|jjwt|python-jose",
    "password_hashing": r"BCrypt|bcrypt|argon2|PasswordHasher|pbkdf2|make_password|passlib",
    "roles_authorization": r"\[Authorize\(|RequireRole|IsAdminUser|has_perm|@PreAuthorize|@Roles\(|hasRole|permission_classes|role",
    "middleware": r"\bclass\s+\w*Middleware\b|app\.use\(|UseMiddleware<|MIDDLEWARE\s*=|@app\.middleware|BaseHTTPMiddleware|HandlerInterceptor|OncePerRequestFilter",
    "logging": r"ILogger<|logging\.getLogger|winston|morgan|pino|Serilog|LoggerFactory|console\.log",
    "orm": r"DbContext|EntityFrameworkCore|sqlalchemy|django\.db|mongoose|sequelize|prisma|typeorm|hibernate|jakarta\.persistence|Eloquent|gorm",
    "redis": r"redis|StackExchangeRedis|ioredis|django_redis|RedisCache",
    "cache": r"IDistributedCache|IMemoryCache|@Cacheable|cache\.(get|set)|lru_cache|CacheHelper|caches\[|node-cache",
    "openai": r"openai|OpenAI|api\.openai\.com|Azure\.AI\.OpenAI|ChatCompletion|gpt-4|gpt-3\.5|gpt-4o",
    "other_llm": r"ollama|Ollama|anthropic|gemini|huggingface|llama|mistral",
    "background_jobs": r"Hangfire|IHostedService|BackgroundService|Quartz|celery|Celery|rq\.Queue|bullmq|Bull\(|agenda|node-cron|APScheduler|@Scheduled|@Async|sidekiq|BackgroundTasks",
    "multi_tenancy": r"[Tt]enant",
    "search_filter": r"[?&]search=|\bsearch\b|\bfilter\b|Filter|OrderBy|order_by|pageSize|page_size|Skip\(|Take\(|limit\(|offset",
    "react": r"from\s+[\"']react[\"']|require\([\"']react[\"']\)",
    "react_context": r"createContext\s*\(|useContext\s*\(",
    "redux": r"@reduxjs/toolkit|createStore\(|useSelector\(",
    "websocket_realtime": r"SignalR|socket\.io|WebSocket|channels\.layers|ws\.Server",
    "message_queue": r"RabbitMQ|rabbitmq|Kafka|kafka|MassTransit|amqp|pika|NATS",
    "grpc": r"\bgrpc\b|Grpc\.|\.proto\b",
    "graphql": r"graphql|GraphQL|HotChocolate|apollo",
    "docker": r"^FROM\s+\S+|docker-compose|services:",
    "email": r"SmtpClient|MailKit|nodemailer|send_mail|JavaMailSender|sendgrid|mailtrap",
    "https": r"UseHttpsRedirection|SECURE_SSL_REDIRECT|https\.createServer|requiresSecure|HSTS|UseHsts",
}
TECH_RE = {k: re.compile(v) for k, v in TECH.items()}
# starter-template code left unchanged by the student (unfinished work; also not the student's own code)
TEMPLATE_LEFTOVERS = [
    ("ASP.NET WeatherForecast", re.compile(r"\bWeatherForecast\b")),
    ("Create React App", re.compile(r"Edit <code>src/App\.(js|tsx?)</code> and save to reload|renders learn react link|>\s*Learn React\s*<")),
    ("Vite starter", re.compile(r"and save to test HMR|Click on the Vite and React logos|count is \{count\}|Vite \+ (React|Vue)")),
    ("Next.js starter", re.compile(r"Get started by editing")),
    ("Vue starter", re.compile(r"You did it!|<HelloWorld\b")),
    ("Angular starter", re.compile(r"app is running!|Congratulations! Your app is running")),
    ("Spring Initializr demo", re.compile(r"package com\.example\.demo\b|class DemoApplication\b")),
    ("Express generator", re.compile(r"Welcome to Express")),
    ("Django/Flask hello", re.compile(r"Hello,? World!?['\"]\s*\)?$", re.M)),
]
DEPLOY_RE = re.compile(r"(?i)\bdeploy|azure/webapps|heroku|vercel|netlify|docker push|ssh-action|aws-actions|gcloud|kubectl")
SECRET_RE = re.compile(r"(?i)(password|secret|api[_-]?key|token|connectionstring)[\"']?\s*[:=]\s*[\"']?([^\s\"',;]{6,})")



# third-party code copied into the repo is not the student's work: folders with their own licence file, or known libraries
VENDORED_NAME = re.compile(r"(?i)^(phpmailer|jquery|bootstrap|font-?awesome|tinymce|ckeditor|chart\.?js|swiper|slick|owl\.?carousel|"
                           r"select2|datatables|lightbox|fpdf|tcpdf|dompdf|smarty|third[_-]?party)([-_. ].*)?$")


def is_vendored(dirpath, root, filenames):
    return dirpath != root and any(f.upper().startswith(("LICENSE", "LICENCE", "COPYING")) for f in filenames)

def longpath(p):
    """Absolute path with the Windows extended-length prefix so paths over 260 chars are not skipped."""
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        p = "\\\\?\\" + p
    return p


def walk(root):
    root = longpath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS and not (d.startswith(".") and d != ".github")]
        if is_vendored(dirpath, root, filenames):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not VENDORED_NAME.match(d)]
        for name in filenames:
            rel = (name if rel_dir == "." else f"{rel_dir}/{name}")
            yield os.path.join(dirpath, name), rel


def read(path, limit=1_500_000):
    try:
        if os.path.getsize(path) > limit:
            return None
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def detect_frameworks(files):
    found = set()
    for rel, text in files:
        low = rel.lower()
        if low.endswith(".csproj"):
            if "Microsoft.NET.Sdk.Web" in text or "Microsoft.AspNetCore" in text:
                found.add("ASP.NET Core")
            if "EntityFrameworkCore" in text:
                found.add("Entity Framework Core")
        elif low.endswith(("requirements.txt", "pyproject.toml", "pipfile")):
            for fw in ("fastapi", "django", "djangorestframework", "flask", "sqlalchemy", "celery"):
                if re.search(rf"(?im)^\s*\"?{fw}\b", text):
                    found.add(fw)
        elif low.endswith("package.json"):
            try:
                pkg = json.loads(text)
            except ValueError:
                continue
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for fw in ("react", "next", "vue", "@angular/core", "svelte", "express", "@nestjs/core", "fastify",
                       "react-native", "expo", "vite", "jest", "vitest", "cypress", "@playwright/test", "prisma",
                       "mongoose", "sequelize", "typeorm"):
                if fw in deps:
                    found.add(fw)
        elif low.endswith(("pom.xml", "build.gradle", "build.gradle.kts")) and "spring-boot" in text:
            found.add("Spring Boot")
        elif low.endswith("go.mod"):
            for fw in ("gin-gonic", "labstack/echo", "gofiber", "gorm"):
                if fw in text:
                    found.add(fw)
        elif low.endswith("composer.json") and "laravel/framework" in text:
            found.add("Laravel")
        elif low.endswith("pubspec.yaml") and "flutter" in text:
            found.add("Flutter")
    return sorted(found)


def scan(repos):
    files_by_lang = Counter()
    lines_by_lang = Counter()
    endpoints, models, migrations, tests_files = [], defaultdict(set), [], []
    test_count = 0
    tech = defaultdict(list)
    tech_code = Counter()  # hits in source code, as opposed to package manifests/config
    docs, ci, docker, secrets_hits, generated = [], [], [], [], 0
    config_files = []
    ci_deploy = False
    leftovers = []
    for label, root in repos:
        for path, rel in walk(root):
            ext = os.path.splitext(rel)[1].lower()
            name = os.path.basename(rel)
            shown = f"{label}/{rel}" if len(repos) > 1 else rel
            if rel.startswith(".github/workflows/") or name in (".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"):
                ci.append(shown)
                if DEPLOY_RE.search(read(path) or ""):
                    ci_deploy = True
            if name.lower() in ("dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml"):
                docker.append(shown)
            if ext == ".md" or name.lower().startswith("readme"):
                docs.append(shown)
            if ext not in LANG and ext not in TEXT_EXTRA and name not in ("Dockerfile", "Jenkinsfile"):
                continue
            text = read(path)
            if text is None:
                continue
            if ext in TEXT_EXTRA or name in ("Dockerfile", "Jenkinsfile"):
                config_files.append((rel, text))
            is_generated = bool(GENERATED.search(name))
            is_migration = bool(MIGRATION_PATH.search(rel))
            if is_migration and not is_generated and ext in (".cs", ".py", ".js", ".ts", ".sql", ".php", ".rb"):
                if not re.search(r"(__init__|ModelSnapshot)", name):
                    migrations.append(shown)
            if is_generated or is_migration:
                generated += 1
            if ext in LANG and not is_generated and not is_migration:
                files_by_lang[LANG[ext]] += 1
                lines_by_lang[LANG[ext]] += sum(1 for l in text.split("\n") if l.strip())
            is_test = bool(TEST_PATH.search(rel))
            if is_test and ext in LANG:
                n = len(TEST_FUNC.findall(text))
                if n:
                    tests_files.append({"file": shown, "tests": n})
                    test_count += n
            if ext in LANG and not is_generated:
                for tname, tpat in TEMPLATE_LEFTOVERS:
                    m = tpat.search(text)
                    if m and len(leftovers) < 30:
                        leftovers.append({"template": tname, "location": f"{shown}:{line_of(text, m.start())}"})
            if ext in LANG and not is_test and not is_generated:
                for kind, exts, pat in ENDPOINT_PATTERNS:
                    if ext not in exts:
                        continue
                    for m in pat.finditer(text):
                        endpoints.append({"kind": kind, "method": (m.group(1) or "").upper()[:12],
                                          "route": (m.group(2) or "").strip()[:120] if m.lastindex and m.lastindex >= 2 else "",
                                          "location": f"{shown}:{line_of(text, m.start())}"})
                if ext == ".py":
                    for m in DRF_VIEWSET.finditer(text):
                        endpoints.append({"kind": "drf-viewset", "method": m.group(2), "route": m.group(1),
                                          "location": f"{shown}:{line_of(text, m.start())}"})
                    if name == "urls.py":
                        for m in DJANGO_PATH.finditer(text):
                            endpoints.append({"kind": "django-path", "method": "", "route": m.group(1),
                                              "location": f"{shown}:{line_of(text, m.start())}"})
                for kind, exts, pat in MODEL_PATTERNS:
                    if ext not in exts:
                        continue
                    for m in pat.finditer(text):
                        nm = next((g for g in m.groups() if g), None)
                        if nm and not re.fullmatch(r"T(Entity|Model|Key|Item|Type)?", nm):
                            models[nm].add(f"{shown}:{line_of(text, m.start())}")
            # documentation mentioning a technology is not evidence that it is implemented
            if (not is_generated and not is_migration and ext not in (".md", ".txt")
                    and (ext in LANG or ext in TEXT_EXTRA or name == "Dockerfile")):
                for key, pat in TECH_RE.items():
                    if key == "docker" and name not in ("Dockerfile",) and not name.startswith("docker-compose"):
                        continue
                    hits = list(pat.finditer(text))
                    if hits and ext in LANG:
                        tech_code[key] += len(hits)
                    if hits and len(tech[key]) < 400:
                        for m in hits[:3]:
                            tech[key].append(f"{shown}:{line_of(text, m.start())}")
                if ext in TEXT_EXTRA and not name.endswith(".md"):
                    for m in SECRET_RE.finditer(text):
                        val = m.group(2)
                        if val.startswith(("$", "{", "<", "${")) or val.lower() in ("password", "string", "true", "false", "null"):
                            continue
                        secrets_hits.append({"location": f"{shown}:{line_of(text, m.start())}", "key": m.group(1),
                                             "value": "[REDACTED]"})
    return {
        "frameworks": detect_frameworks(config_files),
        "files_by_language": dict(files_by_lang.most_common()),
        "lines_by_language": dict(lines_by_lang.most_common()),
        "source_lines_total": sum(lines_by_lang.values()),
        "generated_or_migration_files": generated,
        "endpoints": {"count": len(endpoints), "by_kind": dict(Counter(e["kind"] for e in endpoints)),
                      "by_method": dict(Counter(e["method"] for e in endpoints)), "items": endpoints},
        "models": {"count": len(models), "names": sorted(models), "locations": {k: sorted(v)[:3] for k, v in models.items()}},
        "migrations": {"count": len(migrations), "files": migrations},
        "tests": {"count": test_count, "files": tests_files},
        "ci_files": ci,
        "ci_has_deploy": ci_deploy,
        "docker_files": docker,
        "docs": docs,
        "technology": {k: {"count": len(v), "code_hits": tech_code[k], "examples": v[:6]} for k, v in sorted(tech.items())},
        "possible_secrets": secrets_hits[:50],
        "template_leftovers": leftovers,
        "notes": [
            "Endpoint/model counts come from static patterns; verify borderline cases manually.",
            "DRF ViewSets and Laravel resources expose several routes each; they are counted once here.",
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", action="append", required=True, help="repo folder; LABEL=DIR to name it")
    ap.add_argument("--out")
    args = ap.parse_args()
    repos = []
    for r in args.repo:
        label, _, path = r.partition("=") if "=" in r and not os.path.isdir(r) else (os.path.basename(os.path.normpath(r)), "", r)
        repos.append((label, path))
    result = scan(repos)
    result["repos"] = [{"label": l, "path": p} for l, p in repos]
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    summary = {k: result[k] for k in ("frameworks", "files_by_language", "source_lines_total")}
    summary.update(endpoints=result["endpoints"]["count"], models=result["models"]["count"],
                   migrations=result["migrations"]["count"], tests=result["tests"]["count"],
                   ci=len(result["ci_files"]), possible_secrets=len(result["possible_secrets"]),
                   technology={k: v["count"] for k, v in result["technology"].items()})
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
