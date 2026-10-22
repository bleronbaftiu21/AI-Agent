# Report contract

Write both files to the output directory (outside the inspected repository). Write the human-readable report in the configured language (default: the language of the user's request); keep JSON keys and enum values in English.

## audit-report.md

Use these sections, in this order. Omit nothing; write "Not assessed — <reason>" where a section has no evidence.

1. **Header** — repository URL, branch, commit SHA, audit date, auditor ("Repo Auditor Pro"), requirements source, comparison corpus, AI policy.
2. **Executive summary** — 4–8 sentences: what the project is, overall verdict, final score (and uncapped score if a cap applied), top 3 strengths, top 3 problems, integrity flags.
3. **Scorecard** — first the requirements-only score; then a table: category, weight, score (1–10), one-line justification; then weighted score, cap applied, final score, confidence.
4. **Project overview** — purpose, stack, entry points, architecture (a short diagram in text/mermaid is fine), trust boundaries, data stores, integrations, build/deploy, tests, CI/CD.
5. **Requirements compliance** — table: `ID | Requirement | Mandatory | Status | Evidence | Notes`; then mandatory % and optional %.
6. **Integrity**
   - 6.1 Originality — method, corpus, top similarity matches table (`target file | other file | containment | lines | verdict`), git-history signals, unattributed external code, overall originality %.
   - 6.2 AI-assistance estimate — range %, confidence, per-component table (`component | lines | classification | signals`), policy assessment, and this disclaimer: *"This is a probabilistic estimate from indirect signals, not proof of authorship. It must be confirmed by a human reviewer, e.g. by asking the author to explain the code."*
   - 6.3 Contribution breakdown (team projects only).
7. **Findings** — grouped by severity, each with: ID (`F-01`…), title, category, severity, status (`Confirmed` / `Potential` / `Needs manual verification`), location(s) `path:line`, evidence (short, secrets redacted), impact, recommendation.
8. **Category notes** — short paragraph per technical category with key evidence; label performance claims measured/inferred.
9. **Suggested viva / defense questions** — 5–10 specific questions about this code that a genuine author could answer easily (useful for verifying originality and AI concerns).
10. **Limitations** — tools missing, execution skipped, sampling, inaccessible services, corpus gaps, unreadable brief.
11. **Appendix** — inventory summary, excluded paths, commands run.

## audit-report.json

```json
{
  "schema_version": "1.0",
  "repository": {"url": "", "branch": "", "commit": "", "is_fork": false, "fork_parent": null},
  "audit": {"date": "YYYY-MM-DD", "language": "", "requirements_source": "", "ai_policy": "unspecified", "executed_tests": false, "corpus": []},
  "scores": {
    "categories": [{"name": "requirements_compliance", "weight": 0.30, "score": 0.0, "status": "assessed", "justification": ""}],
    "weighted": 0.0,
    "cap": {"applied": false, "value": null, "reason": null},
    "final": 0.0,
    "requirements_only": 0.0,
    "confidence": "Medium"
  },
  "requirements": {
    "items": [{"id": "R1", "text": "", "mandatory": true, "points": null, "status": "Met", "evidence": ["path:line"], "notes": ""}],
    "mandatory_compliance_pct": 0.0,
    "optional_compliance_pct": 0.0
  },
  "integrity": {
    "originality": {
      "originality_pct": 0.0,
      "matches": [{"target_file": "", "other_file": "", "containment": 0.0, "target_lines": [[1, 10]], "verdict": "Suspected copy"}],
      "history_signals": [""],
      "external_code": [{"location": "", "source": "", "attributed": false}]
    },
    "ai_assistance": {
      "estimate_low_pct": 0,
      "estimate_high_pct": 0,
      "confidence": "Low",
      "components": [{"path": "", "lines": 0, "classification": "Mixed/uncertain", "signals": [""]}],
      "policy_assessment": "",
      "needs_human_review": false
    },
    "contributions": [{"author": "", "commits": 0, "lines_added": 0, "lines_removed": 0}]
  },
  "findings": [{"id": "F-01", "title": "", "category": "security", "severity": "High", "status": "Confirmed", "locations": ["path:line"], "evidence": "", "impact": "", "recommendation": ""}],
  "viva_questions": [""],
  "limitations": [""]
}
```

Enums — status: `Met | Partially met | Not met | Cannot verify`; match verdict: `Confirmed copy | Suspected copy | Attributed reuse | Expected/boilerplate similarity | No concern`; classification: `Likely human | Mixed/uncertain | Likely AI-assisted`; severity: `Critical | High | Medium | Low | Info`; finding status: `Confirmed | Potential | Needs manual verification`; confidence: `High | Medium | Low`; category status: `assessed | not_applicable | not_assessed`.

## Terminal summary

After writing the files, print (in the report language):

```
Repo Auditor Pro — <owner>/<repo> @ <shortsha>
Final score: X.X / 10  (uncapped Y.Y, confidence: …)
Requirements-only score: R.R / 10
Requirements: mandatory NN% · optional NN%  (Met a · Partial b · Not met c · Unverified d)
Originality: NN%  · flags: …
AI-assistance estimate: LL–HH% (confidence …)
Top issues: 1) … 2) … 3) …
Reports: <path>/audit-report.md, <path>/audit-report.json
```

Then 3–6 sentences explaining why the evidence produced the score, including which cap (if any) applied and the main limitations.
