# Audit method

Follow this method for every audit. Scripts referenced below live in `scripts/` next to this file; call them with the skill's absolute path, e.g. `python -I <skill>/scripts/similarity.py ...`.

## 1. Acquisition

Prefer `scripts/acquire.py` (called by `pipeline.py`), which validates the URL and clones with hooks disabled, LFS smudge off, symlinks off and `core.longpaths=true` persisted in the clone (Windows paths over 260 characters otherwise break `git log` and file scans). Manual equivalent:

```bash
mkdir <workspace>/target && cd <workspace>/target
git -c core.longpaths=true clone --no-checkout https://github.com/<owner>/<repo>.git repo
git -C repo config core.longpaths true
git -C repo -c core.hooksPath=<empty-dir> checkout <branch-or-sha>
git -C repo rev-parse HEAD
```

Projects split over several repositories (backend, frontend, mobile) are one project: clone all of them, inventory them together, and grade the requirements against the union.

- Use `gh repo view` / `gh api` for metadata (default branch, fork parent, created date, visibility, languages) when `gh` is authenticated. A repository that is a **fork** or was **created from a template** must be recorded — it changes how similarity is interpreted.
- Never run `npm install`, `pip install`, `make`, `docker`, setup scripts, or Git LFS smudge filters without authorization.
- Comparison repositories: one directory each under `<workspace>/corpus/<owner>-<repo>`.

## 2. Inventory

Produce counts per language (files, lines), top-level layout, and the list of excluded paths with the reason. Default exclusions: `.git`, `node_modules`, `vendor`, `venv`/`.venv`, `dist`, `build`, `target`, `bin`, `obj`, `__pycache__`, `.next`, `coverage`, minified files (`*.min.*`), lockfiles, images/fonts/archives, and IDE folders. Large repositories (> ~2,000 source files): review all entry points, security-sensitive code, and a documented sample of the rest.

## 3. Requirements compliance (primary when a brief exists)

1. Extract every requirement from the brief into atomic items. Split compound sentences ("users can register and log in" → two items). Capture non-functional ones too (language/framework mandated, database type, tests required, deployment, documentation, team size, deadline, naming, folder structure).
2. Mark each item **mandatory** or **optional/bonus** using the brief's own wording; when the brief gives points per item, keep them.
3. For each item, look for evidence in code, configuration, schema/migrations, routes, UI templates, tests, and docs. Static evidence is enough for `Met` when the implementation is complete and reachable from an entry point. Code that exists but is unreachable, stubbed (`TODO`, `pass`, `throw new NotImplemented`, hard-coded fake data), or commented out is `Partially met` or `Not met`.
4. Status values:
   - `Met` — implemented and reachable; evidence cited.
   - `Partially met` — some sub-behavior missing, stubbed, broken, or only in UI without backend (or vice versa).
   - `Not met` — no implementation found after searching (state what you searched for).
   - `Cannot verify` — needs execution, credentials, or an external service you did not have.
5. Compliance percentage = `(Met + 0.5 × Partially met) / (items assessed, excluding Cannot verify)`, computed separately for mandatory and optional items; use point weights when the brief provides them.
6. Note scope creep only if it hurts the required features; extra features are not a defect.

If no brief is supplied, infer the claimed scope from README/docs and grade "does the project do what it claims", labelled as **inferred requirements**.

## 4. Originality / plagiarism

Collect evidence from four independent sources; conclusions need at least two agreeing sources or one decisive one (an exact located source).

### 4a. Corpus similarity (when a comparison corpus exists)

```bash
python -I <skill>/scripts/similarity.py --target <repo> --corpus <dir1> <dir2> ... \
       [--base <template-dir>] --out <out>/similarity.json
```

The script normalizes tokens (identifiers → `ID`, literals → `LIT`, comments removed), so renamed variables and reformatting do not hide copying. It reports per file pair: `containment_target` (share of the target file's fingerprints found in the other file) and matched line ranges. Fingerprints present in `--base` are ignored.

Interpretation (per file, files with ≥ 30 fingerprints):

| containment_target | Meaning |
|---|---|
| ≥ 0.80 | Near-identical — strong copying signal |
| 0.50–0.79 | Substantial shared structure — inspect manually |
| 0.25–0.49 | Partial overlap — often shared boilerplate/tutorial; inspect if non-trivial logic |
| < 0.25 | Not significant |

Always open the matched ranges side by side before reporting. Downgrade matches that are framework scaffolding, generated code, configuration, textbook algorithms written the only obvious way, or code from the supplied template. Check which side came first using commit dates — similarity alone does not say who copied whom.

### 4a-bis. Search across public GitHub (no corpus needed)

`scripts/find_similar_github.py` (run by the pipeline) picks distinctive lines from the project (long, identifier-rich, not boilerplate, unique in the project) and searches them with GitHub code search (requires `GITHUB_TOKEN`); repositories containing several of these lines are strong candidates. It also searches repositories with a similar name or README title. The project's own organisation and forks of it are excluded. Candidates are cloned shallowly and compared with `similarity.py`. For every candidate above ~20% overlap: open the matching files side by side, and compare the candidate's `created_at` and first commits with the project's first commit to decide who was first. Name-only candidates with low overlap are not evidence of anything. Without a token, say in the limitations that code search was skipped.

### 4b. Git history

```bash
python -I <skill>/scripts/git_history.py --repo <repo> [--deadline YYYY-MM-DD] --out <out>/history.json
```

Signals (none is proof on its own):
- Whole project arriving in one or very few commits ("initial commit" with thousands of lines).
- Commit author names/emails that do not match the submitting student/team; foreign authors in early history (a cloned project with history kept).
- Commit timestamps clustered in an implausible window, commits after the deadline, or dates earlier than the assignment was published.
- Repository is a fork of, or contains history from, another project.
- Team projects: contribution share per member (lines added/removed, commits) — report it, but note squash merges and pair programming distort it.
- Work over time (`weekly`, `last_7_days_share`): a bachelor/semester project normally grows over weeks. When more than ~60% of the code arrives in the final 7 days, flag it as last-minute work and ask about it in the defense questions (it is not proof of copying on its own).
- Individual (bachelor) projects: every commit author should be the student. Other authors in the history need an explanation (co-supervisor, template, copied repository with history kept).
- `template_leftovers` in the inventory: unchanged starter code (e.g. `WeatherForecast`, "Edit src/App.jsx and save") is unfinished work and must not be counted as the student's own code.

### 4c. Unattributed external code

- Licence headers, copyright lines, author tags, or URLs naming someone else.
- Leftover identifiers from another project (different app name, package name, DB name, foreign-language comments that differ from the rest).
- Distinctive snippets: for public repos and with consent, search 2–4 distinctive lines (not boilerplate) on the web/GitHub code search. Record the URL only if it is a real match you opened.
- Using a library or a cited tutorial with attribution is **not** plagiarism; report it as attributed reuse.

### 4d. Verdict

Per suspicious file or component: `Confirmed copy (source: …)`, `Suspected copy`, `Attributed reuse`, `Expected/boilerplate similarity`, or `No concern`. Overall originality estimate = share of non-excluded source lines that are **not** in confirmed/suspected copied regions; report it as a percentage with the line counts behind it.

## 5. AI-assistance estimate

There is no reliable automated detector of AI-written code. Produce an **estimate** from converging signals and say so explicitly in the report.

```bash
python -I <skill>/scripts/ai_signals.py --repo <repo> --out <out>/ai_signals.json
```

The script reports per-file indicators; you add judgement from reading code and history. Signal families:

| Strength | Signal |
|---|---|
| Strong | Verbatim assistant artifacts in files: "As an AI…", "Here's the updated code", "Certainly!", markdown code fences (```` ``` ````) inside source files, "… rest of the code remains the same …", `// your code here` left beside finished code, hallucinated APIs/imports that don't exist in the declared library version |
| Strong | Large, polished, fully-commented files appearing in a single commit with no iterative history, in a project whose other commits look hand-written |
| Medium | Tutorial-style explanatory comments on every line or block ("# Step 1: Import the necessary libraries"), uniform docstrings on trivial functions, emoji-heavy README with generic section boilerplate |
| Medium | Abrupt style shifts between files/commits (naming convention, language of comments, error-handling idiom) inconsistent with the same author |
| Medium | Defensive code and features far beyond the brief, generic placeholder values (`your_api_key_here`, `example.com`), over-engineered abstractions for trivial tasks |
| Weak | Consistent formatting, type hints, good naming — also produced by linters, IDEs, and competent humans; never use alone |

Estimation procedure:
1. Classify each substantive source file (or component) as `Likely human`, `Mixed/uncertain`, or `Likely AI-assisted`, citing the signals.
2. Weight by non-blank source lines: `low = lines(Likely AI) / total`, `high = (lines(Likely AI) + lines(Mixed)) / total`.
3. Report the range `low–high %` and a confidence level: `Low` (only weak/medium signals, or < 300 source lines), `Medium` (several medium signals agreeing, or one strong), `High` (multiple strong signals across files and history).
4. If the AI policy is `allowed`, report without penalty. If `allowed-if-disclosed`, check README/report for disclosure. If `forbidden`, flag for human review — still no definitive accusation.

## 6. Technical categories

Assess only what evidence supports; mark others `Not applicable` or `Not assessed` with reason.

- **Structure & architecture** — separation of concerns, layering, module boundaries, coupling, configuration management, consistency with the framework's conventions.
- **Security** — input validation, injection (SQL, command, template, path), authN/authZ checks on every protected route, password hashing, session/JWT handling, secrets in repo or history (`git log -p` grep), CORS/CSRF, file upload handling, dependency CVEs (only if an audit tool/database was actually available), unsafe deserialization, debug mode in production config.
- **Code quality** — correctness bugs, error handling, dead code, duplication, complexity, naming, idiomatic use of the language.
- **Testing** — presence, meaningful assertions, coverage of core logic and edge cases, CI execution. Do not run tests unless explicitly asked.
- **Dependencies** — pinned versions, unused/abandoned packages, licence conflicts, size proportionate to need.
- **Performance** — N+1 queries, unbounded loops/queries, missing pagination, blocking I/O in async code, unnecessary re-renders. Label measured vs inferred.
- **Maintainability & documentation** — README with setup/run instructions that match the code, comments where needed, consistent style, commit hygiene.
- **Production readiness** — configuration via environment, logging, error pages, migrations, build/deploy files, CI/CD, health checks — proportionate to the project's purpose (a classroom project needs far less than a SaaS).

Finding severity: `Critical` (exploitable now or core requirement broken), `High`, `Medium`, `Low`, `Info`. One root cause = one finding, even if it appears in many files (list the locations).

## 7. Scoring

### 7a. Weighted model (each category scored 1–10)

Requirements compliance is the primary measure: when a brief exists it carries 70% of the score, and the technical review is a smaller 30% adjustment on top of it. Default weights when a requirements brief exists:

| Category | Weight |
|---|---|
| Requirements compliance | 70% |
| Code quality | 7% |
| Structure & architecture | 5% |
| Security | 5% |
| Testing | 5% |
| Maintainability & documentation | 4% |
| Production readiness | 2% |
| Performance | 1% |
| Dependencies | 1% |

Without a brief, requirements compliance (inferred) gets 40% and the technical categories share the remaining 60% in the same proportions as above.

Proportionality rules for the technical categories:
- Judge the project against what its purpose needs. For a course/educational project, do not lower scores for missing production concerns (CD, Dockerfiles, hard-coded `localhost`, external config) unless the brief asks for them; mention them as advice instead.
- A finding with status `Potential` or `Needs manual verification` costs at most half of what the same finding would cost if `Confirmed`.
- Do not penalize the same root cause in both requirements compliance and a technical category; count it where it matters most (usually requirements). User-supplied weights override these. Categories marked `Not applicable` are removed and the remaining weights renormalized; `Not assessed` categories are removed too and listed as a limitation.

Category anchors: 9–10 exemplary, no material issues · 7–8 good, minor issues · 5–6 adequate, notable gaps · 3–4 weak, serious issues · 1–2 missing or fundamentally broken. Requirements score ≈ mandatory compliance % / 10, adjusted ±1 for optional items and quality of implementation.

Always also report the **requirements-only score** (requirements score on its own, 1–10) next to the final score, so the reader sees how well the brief itself was met.

### 7b. Integrity caps (applied after weighting)

| Condition | Cap on final score |
|---|---|
| Confirmed copy covering ≥ 50% of source lines, unattributed | 2 |
| Confirmed copy covering 20–49% | 4 |
| Suspected copy ≥ 20%, or confirmed < 20% of core logic | No cap — flag `Needs human review` |
| AI policy `forbidden` and estimate `high` bound ≥ 60% with confidence High | No cap — flag `Needs human review` |
| Hard-coded live secret or critical exploitable vulnerability | 5 (production-oriented projects only) |
| Mandatory requirements compliance < 40% | 4 |

Caps never stack below the lowest applicable cap. Always show the uncapped score next to the capped one and explain which cap applied.

### 7c. Rounding and confidence

Final score: one decimal, 1.0–10.0. Overall confidence `High/Medium/Low` reflects how much was verified (execution skipped, sampled files, no corpus, unreadable brief all lower it).
