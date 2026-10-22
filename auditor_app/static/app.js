"use strict";

const app = document.getElementById("app");
let STATUS = { claude: null };
let pollTimer = null;

// ---------- helpers ----------
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, d = "–") => (v === null || v === undefined || v === "" ? d : v);
const pct = (v) => (v === null || v === undefined ? "–" : `${Math.round(v * 100)}%`);
const api = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) {
    let msg = `${r.status}`;
    try { const j = await r.json(); msg = j.detail || (j.errors || []).join("\n") || msg; } catch { /* not json */ }
    throw new Error(msg);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r.text();
};
const toast = (msg) => {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg; document.body.appendChild(t);
  setTimeout(() => t.remove(), 2600);
};
const md = (text) => DOMPurify.sanitize(marked.parse(text || ""));

const HINT = {
  likely_met: ["ok", "Duket e plotësuar"], partial: ["warn", "Pjesërisht"],
  not_found: ["bad", "Nuk u gjet"], manual: ["info", "Kontrollo me dorë"],
};
const VERDICT = {
  "Met": ["ok", "Met"], "Partially met": ["warn", "Partially met"],
  "Not met": ["bad", "Not met"], "Cannot verify": ["info", "Cannot verify"],
};
const JOB_STATUS = {
  queued: ["muted", "Në pritje"], running: ["run", "Duke punuar"], claude_running: ["run", "Claude po vlerëson"],
  evidence_ready: ["ok", "Dëshmitë gati"], error: ["bad", "Gabim"], report: ["ok", "Raport"],
};
const badge = (map, key, fallback) => {
  const [cls, label] = map[key] || ["muted", fallback ?? key ?? "–"];
  return `<span class="badge ${cls}">${esc(label)}</span>`;
};
const scoreColor = (s) => (s == null ? "muted" : s >= 8 ? "ok" : s >= 6 ? "warn" : "bad");

// ---------- router ----------
function route() {
  clearTimeout(pollTimer);
  const parts = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.nav === (parts[0] || "jobs")));
  if (parts[0] === "new") return renderNew();
  if (parts[0] === "settings") return renderSettings();
  if (parts[0] === "job" && parts[1]) return renderJob(parts[1], parts[3], parts[4]);
  return renderJobs();
}
window.addEventListener("hashchange", route);

async function loadStatus() {
  try { STATUS = await api("/api/status"); } catch { /* server down */ }
  // the Claude step is usable only when the CLI exists and is signed in
  if (STATUS.claude && STATUS.claude_signed_in === false) STATUS.claude = null, STATUS.claude_login_needed = true;
  const b = document.getElementById("claude-badge");
  b.className = `badge ${STATUS.claude ? "ok" : STATUS.claude_login_needed ? "warn" : "muted"}`;
  b.textContent = STATUS.claude ? "Claude Code: gati" : STATUS.claude_login_needed ? "Claude Code: s'je i kyçur" : "Claude Code: s'u gjet";
  b.title = STATUS.claude || "Instalo Claude Code CLI që aplikacioni ta nisë vetë vlerësimin përfundimtar.";
}

// ---------- new audit ----------
function renderNew() {
  const claudeNote = STATUS.claude ? "" : STATUS.claude_login_needed
    ? `<div class="note warn">Claude Code nuk është i kyçur, prandaj raporti me notë nuk shkruhet automatikisht. Hap PowerShell → <code>claude</code> → <code>/login</code>.</div>`
    : `<div class="note warn">Claude Code nuk është i instaluar, prandaj raporti me notë nuk shkruhet automatikisht. Dëshmitë mblidhen gjithsesi.</div>`;
  const tokenNote = STATUS.github_token ? "" :
    `<div class="note">Për kontrollin e plotë të kopjimit në gjithë GitHub-in vendos një herë një GitHub token te <a href="#/settings">Cilësimet</a>. Pa të kërkohen vetëm projektet me emër të ngjashëm.</div>`;
  app.innerHTML = `
  <div class="hero">
    <h1>Kontrollo një projekt</h1>
    <p class="sub">Vendos linkun e projektit në GitHub dhe kërkesat. Pjesën tjetër e bën aplikacioni.</p>
  </div>
  <form id="f" class="card simple">
    <label class="t" for="links">Linku i projektit në GitHub</label>
    <textarea id="links" name="links" class="big" rows="2" placeholder="https://github.com/studenti/projekti
(nëse ka backend dhe frontend veç, vendos të dy linqet)"></textarea>

    <label class="t" style="margin-top:18px">Kërkesat e projektit</label>
    <label class="drop" id="drop">
      <input type="file" id="reqfile" name="requirements_file" accept=".pdf,.docx,.md,.txt">
      <span id="dropText"><strong>Zgjidh skedarin e kërkesave</strong> ose tërhiqe këtu<br><span class="help">PDF, DOCX, MD ose TXT</span></span>
    </label>
    <details class="plain"><summary>ose ngjit tekstin e kërkesave</summary>
      <textarea name="requirements_text" rows="6" placeholder="1. Arkitektura klient-server ...
2. Minimum 20 endpoint-e ..."></textarea></details>

    <div class="checks">
      <div class="help" style="margin-bottom:6px">Çka kontrollohet automatikisht:</div>
      <ul>
        <li>a janë përmbushur kërkesat (secila me dëshmi nga kodi)</li>
        <li>a është kopjuar nga ndonjë projekt tjetër në GitHub</li>
        <li>sa është përdorur AI (vlerësim me nivel besueshmërie)</li>
        <li>kush e ka shkruar kodin dhe a është punuar gjatë gjithë kohës apo në minutën e fundit</li>
        <li>teste, dokumentim, siguria (fjalëkalime në kod), kod i mbetur nga shabllonet</li>
        <li>pyetje për mbrojtjen e projektit</li>
      </ul>
    </div>
    ${tokenNote}${claudeNote}

    <details class="plain" id="adv"><summary>Opsione të avancuara</summary>
      <div class="adv">
        <label>Titulli i auditimit<input type="text" name="title" placeholder="p.sh. Tema e diplomës – Studenti X"></label>
        <label>Afati i dorëzimit<input type="date" name="deadline"></label>
        <label>Data e fillimit<input type="date" name="start"></label>
        <label>Politika e AI<select name="ai_policy">
          <option value="unspecified">E paspecifikuar</option><option value="forbidden">E ndaluar</option>
          <option value="allowed-if-disclosed">Lejohet nëse deklarohet</option><option value="allowed">Lejohet</option></select></label>
        <label>Gjuha e raportit<select name="language"><option value="shqip">Shqip</option><option value="English">English</option></select></label>
        <label class="wide">Shumë projekte njëherësh (zëvendëson linkun më sipër). Një për rresht: <code>Emri: link1, link2</code>
          <textarea name="groups" rows="3" placeholder="Studenti A: https://github.com/a/projekti
Studenti B: https://github.com/b/projekti"></textarea></label>
        <label class="wide">Projekte specifike për krahasim (p.sh. të viteve të kaluara)
          <textarea name="comparison" rows="2" placeholder="https://github.com/..."></textarea></label>
        <label class="wide">Kodi i shabllonit që u është dhënë studentëve (nuk llogaritet si kopjim)
          <textarea name="base" rows="1" placeholder="https://github.com/..."></textarea></label>
        <label class="wide"><input type="checkbox" name="skip_claude" value="true"> Vetëm dëshmitë automatike, pa raportin e Claude</label>
      </div>
    </details>

    <button class="primary big-btn" type="submit" id="go">Kontrollo projektin</button>
    <div id="errs" class="err-list"></div>
  </form>`;
  const file = document.getElementById("reqfile");
  const drop = document.getElementById("drop");
  const showFile = () => {
    if (file.files[0]) document.getElementById("dropText").innerHTML = `<strong>${esc(file.files[0].name)}</strong><br><span class="help">kliko për ta ndryshuar</span>`;
    drop.classList.toggle("has", !!file.files[0]);
  };
  file.addEventListener("change", showFile);
  ["dragover", "dragenter"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("over")));
  drop.addEventListener("drop", (e) => { e.preventDefault(); if (e.dataTransfer.files.length) { file.files = e.dataTransfer.files; showFile(); } });
  document.getElementById("f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("go");
    btn.disabled = true; btn.textContent = "Duke nisur…";
    document.getElementById("errs").innerHTML = "";
    try {
      const res = await api("/api/jobs", { method: "POST", body: new FormData(e.target) });
      location.hash = `#/job/${encodeURIComponent(res.id)}`;
    } catch (err) {
      document.getElementById("errs").innerHTML = err.message.split("\n").map((m) => `<div>• ${esc(m)}</div>`).join("");
      btn.disabled = false; btn.textContent = "Kontrollo projektin";
    }
  });
}

// ---------- settings ----------
async function renderSettings() {
  app.innerHTML = `<div class="empty">Duke u ngarkuar…</div>`;
  const s = await api("/api/settings");
  const gh = s.github || {};
  app.innerHTML = `
  <h1>Cilësimet</h1>
  <p class="sub">Ruhen vetëm në këtë kompjuter (<code>${esc(s.settings_file)}</code>), jo në projekt dhe as në GitHub.</p>
  <div class="card">
    <h3 style="margin-top:0">GitHub token</h3>
    <p>Nevojitet që aplikacioni ta kërkojë kodin e projektit në <strong>gjithë GitHub-in</strong> (kontrolli i kopjimit) dhe të lexojë të gjitha PR-të dhe review-t.
      Pa token GitHub lejon vetëm 60 kërkesa në orë dhe kërkimi i kodit nuk funksionon.</p>
    <p>Statusi: ${s.github_token_saved ? `<span class="badge ok">i ruajtur (${esc(s.github_token_hint)})</span>` : `<span class="badge warn">nuk është vendosur</span>`}
      ${gh.ok ? `<span class="help"> · GitHub API: ${gh.core.remaining}/${gh.core.limit} kërkesa të mbetura këtë orë</span>` : ""}</p>
    <form id="tf" class="inline" style="align-items:flex-end">
      <label style="flex:3">Token i ri<input type="password" name="github_token" autocomplete="off" placeholder="ghp_… ose github_pat_…"></label>
      <div class="actions" style="flex:0 0 auto"><button class="primary" type="submit">Ruaj</button>
        ${s.github_token_saved ? `<button type="button" id="clear">Fshije</button>` : ""}</div>
    </form>
    <div id="terr" class="err-list"></div>
    <details class="plain" style="margin-top:14px"><summary>Si krijohet një token (2 minuta)</summary>
      <ol>
        <li>Hap <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noopener">github.com/settings/tokens</a> (kyçu në GitHub).</li>
        <li>Kliko <strong>Generate new token</strong> (fine-grained).</li>
        <li>Emri: <code>repo-auditor</code>, afati p.sh. 90 ditë. Te <em>Repository access</em> zgjidh <strong>Public repositories (read-only)</strong>.</li>
        <li>Nuk duhen leje të tjera. Kliko <strong>Generate token</strong>, kopjoje dhe ngjite këtu.</li>
      </ol></details>
  </div>
  <div class="card">
    <h3 style="margin-top:0">Claude Code</h3>
    <p>${STATUS.claude ? `<span class="badge ok">gati</span> <span class="help">${esc(STATUS.claude)}</span>`
      : STATUS.claude_login_needed ? `<span class="badge warn">i instaluar, por jo i kyçur</span> Hap PowerShell → <code>claude</code> → <code>/login</code>.`
      : `<span class="badge muted">nuk u gjet</span> Instalimi: <code>npm install -g @anthropic-ai/claude-code</code>`}</p>
    <p class="help">Claude lexon kodin dhe shkruan raportin përfundimtar me notë. Pa të, aplikacioni tregon vetëm dëshmitë automatike.</p>
  </div>`;
  const save = async (fd) => {
    document.getElementById("terr").innerHTML = "";
    try { await api("/api/settings", { method: "POST", body: fd }); await loadStatus(); toast("U ruajt"); renderSettings(); }
    catch (err) { document.getElementById("terr").textContent = err.message; }
  };
  document.getElementById("tf").addEventListener("submit", (e) => { e.preventDefault(); save(new FormData(e.target)); });
  document.getElementById("clear")?.addEventListener("click", () => { const fd = new FormData(); fd.append("clear", "true"); save(fd); });
}

// ---------- jobs list ----------
async function renderJobs() {
  app.innerHTML = `<div class="empty">Duke u ngarkuar…</div>`;
  let jobs = [];
  try { jobs = await api("/api/jobs"); } catch (e) { app.innerHTML = `<div class="note bad">${esc(e.message)}</div>`; return; }
  app.innerHTML = `
    <div class="inline" style="justify-content:space-between;align-items:flex-start">
      <div style="flex:0 1 auto"><h1>Auditimet</h1><p class="sub">${jobs.length} auditime në <code>audit-reports/</code></p></div>
      <a class="btn primary" href="#/new" style="flex:0 0 auto">+ Auditim i ri</a>
    </div>
    ${jobs.length ? `<div class="card table-wrap"><table>
      <thead><tr><th>Titulli</th><th>Data</th><th class="num">Grupe</th><th class="num">Raporte</th><th>Statusi</th></tr></thead>
      <tbody>${jobs.map((j) => `<tr class="click" data-id="${esc(j.id)}">
        <td><strong>${esc(j.title)}</strong>${j.legacy ? ` <span class="badge muted">raport i vetëm</span>` : ""}</td>
        <td>${esc(fmt(j.created && j.created.replace("T", " ")))}</td>
        <td class="num">${j.groups}</td><td class="num">${j.reports}${j.final != null ? ` · nota ${j.final}` : ""}</td>
        <td>${badge(JOB_STATUS, j.status)}</td></tr>`).join("")}</tbody></table></div>`
    : `<div class="card empty">Ende asnjë auditim. <a href="#/new">Nis të parin</a>.</div>`}`;
  app.querySelectorAll("tr[data-id]").forEach((tr) =>
    tr.addEventListener("click", () => (location.hash = `#/job/${encodeURIComponent(tr.dataset.id)}`)));
}

// ---------- job page ----------
async function renderJob(id, groupName, tab) {
  let job;
  try { job = await api(`/api/jobs/${encodeURIComponent(id)}`); }
  catch (e) { app.innerHTML = `<div class="note bad">${esc(e.message)}</div>`; return; }
  const live = ["queued", "running", "claude_running"].includes(job.status);
  const groupNames = Object.keys(job.groups_data || {});
  if (!groupName && groupNames.length === 1) groupName = groupNames[0];
  const scrollY = window.scrollY;
  const openLog = document.querySelector("#logbox")?.open;

  app.innerHTML = `
    <p><a href="#/jobs">← Auditimet</a></p>
    <div class="inline" style="justify-content:space-between;align-items:flex-start">
      <div style="flex:1 1 auto">
        <h1>${esc(job.title)} ${badge(JOB_STATUS, job.status)}</h1>
        <p class="sub">${job.legacy ? "Raport i shkruar drejtpërdrejt nga skill-i." :
          `${esc(fmt(job.created && job.created.replace("T", " ")))} · ${groupNames.length || (job.groups || []).length} grupe · kërkesat: ${esc(job.requirements_name || (job.requirements && job.requirements.length ? "tekst" : "nga README"))}
          ${job.requirements ? ` (${job.requirements.length})` : ""}`}</p>
      </div>
      ${job.legacy ? "" : `<div class="actions" style="flex:0 0 auto">
        ${(job.summary || []).length ? `<a class="btn" href="/api/jobs/${encodeURIComponent(id)}/file?path=summary.csv">Shkarko tabelën (CSV)</a>` : ""}
        <button id="refresh">Rifresko</button></div>`}
    </div>
    ${job.legacy ? "" : progressCard(job, openLog)}
    ${(job.summary || []).length > 1 ? summaryCard(job) : ""}
    ${job.similarity && job.similarity.mode === "groups" && (job.summary || []).length > 1 ? similarityCard(job) : ""}
    <div id="group"></div>`;

  document.getElementById("refresh")?.addEventListener("click", async () => {
    await api(`/api/jobs/${encodeURIComponent(id)}/refresh-summary`, { method: "POST" });
    renderJob(id, groupName, tab);
  });
  app.querySelectorAll("tr[data-group]").forEach((tr) => tr.addEventListener("click", () => {
    location.hash = `#/job/${encodeURIComponent(id)}/g/${encodeURIComponent(tr.dataset.group)}`;
  }));
  if (groupName && job.groups_data[groupName]) renderGroup(job, groupName, tab || "req");
  window.scrollTo(0, scrollY);
  if (live) pollTimer = setTimeout(() => renderJob(id, groupName, tab), 2500);
}

function progressCard(job, openLog) {
  const steps = job.steps || [];
  const done = steps.filter((s) => s.status !== "running").length;
  const running = ["queued", "running", "claude_running"].includes(job.status);
  return `<div class="card">
    <div class="inline" style="justify-content:space-between"><h3 style="margin:0;flex:0 1 auto">Ecuria</h3>
      <span class="badge ${running ? "run" : "muted"}" style="flex:0 0 auto">${done}/${steps.length} hapa</span></div>
    ${running ? `<div class="bar" style="margin:10px 0"><span style="width:${steps.length ? Math.round((done / steps.length) * 100) : 5}%"></span></div>` : ""}
    <details ${running ? "open" : ""}><summary>Hapat</summary>
      <ul class="steps">${steps.map((s) => `<li><span class="dot ${esc(s.status)}"></span>
        <span>${esc(s.name)}${s.group ? ` <span class="badge muted">${esc(s.group)}</span>` : ""}</span>
        <span class="msg" title="${esc(s.message)}">${esc(s.message)}</span></li>`).join("") || "<li>Në pritje…</li>"}</ul></details>
    <details id="logbox" ${openLog ? "open" : ""}><summary>Log-u</summary><pre id="log">…</pre></details>
  </div>`;
}

function summaryCard(job) {
  const rows = job.summary;
  return `<h2>Përmbledhja e grupeve</h2><div class="card table-wrap"><table>
    <thead><tr><th>Grupi</th><th class="num">Nota</th><th class="num">Kërkesat</th><th>Sugjerimet ✓ / ~ / ✗ / ?</th>
      <th class="num">Endpoint</th><th class="num">Modele</th><th class="num">Teste</th><th class="num">Anëtarë</th>
      <th>PR me review</th><th>AI</th><th>Ngjashmëria max</th><th>GitHub</th></tr></thead>
    <tbody>${rows.map((r) => `<tr class="click" data-group="${esc(r.grupi)}">
      <td><strong>${esc(r.grupi)}</strong><div class="help">${esc(r.statusi)}</div></td>
      <td class="num">${r.nota_perfundimtare != null ? `<span class="badge ${scoreColor(r.nota_perfundimtare)}">${r.nota_perfundimtare}</span>` : "–"}</td>
      <td class="num">${r.kerkesat_detyrueshme_pct != null ? `${r.kerkesat_detyrueshme_pct}%` : "–"}</td>
      <td><span class="badge ok">${fmt(r.sugjerime_met, 0)}</span> <span class="badge warn">${fmt(r.sugjerime_partial, 0)}</span>
        <span class="badge bad">${fmt(r.sugjerime_not_found, 0)}</span> <span class="badge info">${fmt(r.sugjerime_manual, 0)}</span></td>
      <td class="num">${fmt(r.endpoint)}</td><td class="num">${fmt(r.modele)}</td><td class="num">${fmt(r.teste)}</td>
      <td class="num">${fmt(r.anetare)}</td><td>${fmt(r.pr_me_review)}</td><td>${esc(fmt(r.ai_vleresim))}</td>
      <td>${r.ngjashmeria_max != null ? `<span class="badge ${r.ngjashmeria_max >= 0.3 ? "bad" : r.ngjashmeria_max >= 0.15 ? "warn" : "ok"}">${pct(r.ngjashmeria_max)}</span> <span class="help">${esc(r.ngjashem_me || "")}</span>` : "–"}</td>
      <td>${r.github_ngjashmeria_max != null ? `<span class="badge ${r.github_ngjashmeria_max >= 0.3 ? "bad" : r.github_ngjashmeria_max >= 0.15 ? "warn" : "ok"}">${pct(r.github_ngjashmeria_max)}</span> <span class="help">${esc(r.github_ngjashem_me || "")}</span>` : "–"}</td>
    </tr>`).join("")}</tbody></table></div>`;
}

function similarityCard(job) {
  const sim = job.similarity;
  const names = Object.keys(sim.matrix || {});
  if (names.length < 2) return "";
  const cell = (v) => {
    const a = Math.min(1, v / 0.6);
    return `<td class="heat" style="background:rgba(196,50,28,${(a * 0.75).toFixed(2)});color:${a > 0.55 ? "#fff" : "inherit"}">${pct(v)}</td>`;
  };
  const top = (sim.pairs || []).filter((p) => p.max >= 0.05).slice(0, 8);
  return `<h2>Ngjashmëria mes grupeve</h2><div class="card">
    <p class="help" style="margin-top:0">Rreshti = sa % e kodit të atij grupi gjendet edhe te grupi i kolonës (pas normalizimit të emrave dhe formatimit).
      Pak përqind vijnë nga boilerplate-i i framework-ut. Mbi ~20% duhet parë me dorë.</p>
    <div class="table-wrap"><table><thead><tr><th></th>${names.map((n) => `<th class="heat">${esc(n)}</th>`).join("")}</tr></thead>
      <tbody>${names.map((a) => `<tr><th>${esc(a)}</th>${names.map((b) => (a === b ? `<td class="heat">—</td>` : cell(sim.matrix[a][b]))).join("")}</tr>`).join("")}</tbody></table></div>
    ${top.length ? `<h3>Çiftet me ngjashmëri më të lartë</h3>${top.map((p) => `<details><summary>${esc(p.a)} ↔ ${esc(p.b)}: ${pct(p.a_in_b)} / ${pct(p.b_in_a)}</summary>
      ${p.matches.length ? `<table><thead><tr><th>Skedari (${esc(p.a)})</th><th>Skedari (${esc(p.b)})</th><th class="num">Përputhja</th><th>Rreshtat</th></tr></thead>
      <tbody>${p.matches.map((m) => `<tr><td class="mono">${esc(m.target_file)}</td><td class="mono">${esc(m.other_file)}</td>
        <td class="num">${pct(m.containment_target)}</td><td class="mono">${esc(m.target_lines.slice(0, 4).map((r) => r.join("-")).join(", "))}</td></tr>`).join("")}</tbody></table>`
        : `<p class="help">Asnjë skedar mbi pragun.</p>`}</details>`).join("")}` : ""}
  </div>`;
}

// ---------- group detail ----------
const TABS = [["req", "Kërkesat"], ["report", "Raporti"], ["copy", "Kopjimi"], ["evidence", "Dëshmitë"], ["history", "Historia"],
  ["github", "GitHub"], ["ai", "AI"]];

function renderGroup(job, name, tab) {
  const g = job.groups_data[name];
  const gs = (job.groups_state || {})[name] || {};
  const el = document.getElementById("group");
  const rep = g.report;
  const scores = rep?.scores || {};
  el.innerHTML = `
    <h2>${esc(name)} ${gs.claude === "running" ? `<span class="badge run">Claude po vlerëson…</span>` : ""}</h2>
    ${verdictTiles(job, name, g, gs)}
    <div class="tabs">${TABS.filter(([k]) => !(job.legacy && ["copy", "evidence", "history", "github", "ai"].includes(k)))
      .map(([k, l]) => `<button data-tab="${k}" class="${k === tab ? "active" : ""}">${l}</button>`).join("")}</div>
    <div id="tab"></div>`;
  el.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
    location.hash = `#/job/${encodeURIComponent(job.id)}/g/${encodeURIComponent(name)}/${b.dataset.tab}`;
  }));
  const body = document.getElementById("tab");
  const render = { req: tabReq, report: tabReport, copy: tabCopy, evidence: tabEvidence, history: tabHistory, github: tabGithub, ai: tabAi }[tab] || tabReq;
  body.innerHTML = render(g, job, name, gs);
  body.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    await navigator.clipboard.writeText(g.prompt || ""); toast("Prompt-i u kopjua");
  }));
  body.querySelector("[data-claude]")?.addEventListener("click", async (e) => {
    e.target.disabled = true;
    try { await api(`/api/jobs/${encodeURIComponent(job.id)}/groups/${encodeURIComponent(name)}/claude`, { method: "POST" }); toast("Claude u nis"); renderJob(job.id, name, "report"); }
    catch (err) { toast(err.message); e.target.disabled = false; }
  });
  loadLog(job);
}

function verdictTiles(job, name, g, gs) {
  const rep = g.report, scores = rep?.scores || {}, inv = g.inventory || {}, hist = g.history || {};
  const tile = (cls, head, big, detail, extra = "") =>
    `<div class="vt ${cls}"><div class="h">${esc(head)}</div><div class="b">${big}</div><div class="d">${detail}</div>${extra}</div>`;
  const tiles = [];

  // 1. requirements
  if (rep?.requirements?.items?.length) {
    const items = rep.requirements.items, c = (s) => items.filter((i) => i.status === s).length;
    const p = rep.requirements.mandatory_compliance_pct;
    tiles.push(tile(p >= 80 ? "ok" : p >= 50 ? "warn" : "bad", "Kërkesat", `${p}% të plotësuara`,
      `${c("Met")} Met · ${c("Partially met")} pjesërisht · ${c("Not met")} jo`));
  } else if (g.hints?.counts) {
    const k = g.hints.counts, n = (g.hints.hints || []).length, r = n ? k.likely_met / n : 0;
    tiles.push(tile(r >= 0.8 ? "ok" : r >= 0.5 ? "warn" : "bad", "Kërkesat (sugjerim automatik)", `${k.likely_met}/${n} duken të plotësuara`,
      `${k.partial} pjesërisht · ${k.not_found} s'u gjetën · ${k.manual} me dorë`));
  } else tiles.push(tile("info", "Kërkesat", "–", "pa dokument kërkesash"));

  // 2. score
  tiles.push(scores.final != null
    ? tile(scoreColor(scores.final), "Nota", `${scores.final} / 10`, `vetëm kërkesat: ${fmt(scores.requirements_only)} · besueshmëria ${esc(fmt(scores.confidence))}`)
    : tile("info", "Nota", gs.claude === "running" ? "Claude po vlerëson…" : "–", gs.claude === "running" ? "zgjat disa minuta" : "jepet nga raporti i Claude"));

  // 3. copying (GitHub + other groups)
  const row = job.similarity?.matrix?.[name] || {};
  const mine = new Set((gs.github_candidates || []).map((c) => `GitHub: ${c.full_name}`));
  const ghPairs = Object.entries(row).filter(([k]) => mine.has(k)).sort((a, b) => b[1] - a[1]);
  const grpPairs = Object.entries(row).filter(([k]) => !k.startsWith("GitHub: ")).sort((a, b) => b[1] - a[1]);
  const top = [...ghPairs, ...grpPairs].sort((a, b) => b[1] - a[1])[0];
  const origRep = rep?.integrity?.originality;
  if (origRep?.originality_pct != null) {
    const o = origRep.originality_pct;
    tiles.push(tile(o >= 85 ? "ok" : o >= 60 ? "warn" : "bad", "Origjinaliteti", `${o}% origjinal`,
      top ? `ngjashmëria më e lartë: ${pct(top[1])} me ${esc(top[0].replace("GitHub: ", ""))}` : "asnjë përputhje e dukshme"));
  } else if (top) {
    tiles.push(tile(top[1] >= 0.3 ? "bad" : top[1] >= 0.15 ? "warn" : "ok", "Kopjimi", `${pct(top[1])} ngjashmëri max`,
      `me ${esc(top[0].replace("GitHub: ", ""))} · ${ghPairs.length} projekte nga GitHub të krahasuara`));
  } else {
    const gsim = g.github_similar;
    tiles.push(tile("info", "Kopjimi", gsim ? "s'u gjet asnjë projekt i ngjashëm" : "–",
      gsim && !gsim.authenticated ? "pa GitHub token u kërkua vetëm sipas emrit" : ""));
  }

  // 4. AI
  const ai = rep?.integrity?.ai_assistance;
  if (ai) {
    tiles.push(tile(ai.estimate_high_pct >= 60 ? "bad" : ai.estimate_high_pct >= 30 ? "warn" : "ok", "Përdorimi i AI", `${ai.estimate_low_pct}–${ai.estimate_high_pct}%`,
      `besueshmëria ${esc(ai.confidence)} · vlerësim, jo provë`));
  } else {
    const strong = Object.values(g.ai || {}).reduce((s, d) => s + (d.lines_by_level?.strong_signals || 0), 0);
    const medium = Object.values(g.ai || {}).reduce((s, d) => s + (d.lines_by_level?.several_medium_signals || 0), 0);
    tiles.push(tile(strong ? "warn" : "ok", "Përdorimi i AI (sinjale)", strong ? `sinjale të forta në ${strong} rreshta` : "asnjë sinjal i fortë",
      `${medium} rreshta me sinjale mesatare · përqindjen e jep raporti`));
  }

  // 5. work over time
  if (hist.weekly?.length) {
    const share = hist.last_7_days_share ?? 0;
    const max = Math.max(...hist.weekly.map((w) => w.lines_added), 1);
    const bars = `<div class="weeks" title="rreshta të shtuar për javë">${hist.weekly.map((w, i) =>
      `<span class="${i === hist.weekly.length - 1 ? "last" : ""}" style="height:${Math.max(3, Math.round((w.lines_added / max) * 100))}%" title="${esc(w.week)}: ${w.lines_added} rreshta, ${w.commits} commit"></span>`).join("")}</div>`;
    tiles.push(tile(share >= 0.6 ? "bad" : share >= 0.4 ? "warn" : "ok", "Puna në kohë", `${hist.active_days} ditë aktive`,
      `${pct(share)} e kodit në 7 ditët e fundit · ${esc(fmt(hist.first_date))} → ${esc(fmt(hist.last_date))}`, bars));
  }

  // 6. authorship
  if (hist.authors?.length) {
    const names = hist.authors.map((a) => `${a.author} ${pct(a.share_of_added)}`).join(", ");
    tiles.push(tile(hist.authors.length > 1 ? "info" : "ok", "Autorësia", `${hist.authors.length} ${hist.authors.length === 1 ? "person" : "persona"}`,
      esc(names)));
  }

  // 7. risks
  if (inv.endpoints) {
    const sec = inv.possible_secrets?.length || 0, left = inv.template_leftovers?.length || 0, tests = inv.tests?.count || 0;
    const issues = [];
    if (sec) issues.push(`${sec} fjalëkalime/çelësa në repo`);
    if (left) issues.push(`${left} mbetje shablloni`);
    if (!tests) issues.push("asnjë test");
    if (!inv.docs?.length) issues.push("pa README");
    tiles.push(tile(sec ? "bad" : issues.length ? "warn" : "ok", "Rreziqe & cilësi", issues.length ? `${issues.length} probleme` : "pa probleme të dukshme",
      issues.length ? esc(issues.join(" · ")) : `${tests} teste · README prezent`));
  }
  return `<div class="verdict">${tiles.join("")}</div>`;
}

function tabCopy(g, job, name, gs) {
  const gsim = g.github_similar;
  const row = job.similarity?.matrix?.[name] || {};
  const pairsByName = Object.fromEntries((job.similarity?.pairs || []).map((p) => [[p.a, p.b].sort().join("|"), p]));
  const cands = gsim?.candidates || [];
  const others = Object.entries(row).filter(([k]) => !k.startsWith("GitHub: ")).sort((a, b) => b[1] - a[1]);
  const matchTable = (other) => {
    const p = pairsByName[[name, other].sort().join("|")];
    const ms = (p?.matches || []).filter((m) => true);
    if (!ms.length) return "";
    return `<details><summary>Skedarët që përputhen</summary><table><thead><tr><th>Skedari</th><th>Skedari tjetër</th><th class="num">Përputhja</th></tr></thead>
      <tbody>${ms.map((m) => `<tr><td class="mono">${esc(m.target_file)}</td><td class="mono">${esc(m.other_file)}</td><td class="num">${pct(m.containment_target)}</td></tr>`).join("")}</tbody></table></details>`;
  };
  return `<div class="note" style="margin-bottom:12px">Kodi normalizohet (emrat e variablave dhe formatimi nuk ndikojnë), pastaj krahasohet.
      Disa përqind ngjashmëri vijnë normalisht nga framework-u. Mbi ~20% duhet hapur dhe krahasuar me dorë.</div>
    <div class="card"><h3 style="margin-top:0">Projekte të ngjashme në GitHub</h3>
      ${gsim ? `<p class="help">${gsim.authenticated ? `U kërkuan ${gsim.queries?.length || 0} rreshta karakteristikë të kodit në gjithë GitHub-in, plus emri i projektit.`
        : "Pa GitHub token: u kërkuan vetëm projekte me emër/përshkrim të ngjashëm. Vendos token-in te Cilësimet për kërkimin e kodit."}</p>` : ""}
      ${cands.length ? `<table><thead><tr><th>Projekti</th><th>Pse u gjet</th><th class="num">Ngjashmëria</th><th>Krijuar</th></tr></thead><tbody>
        ${cands.map((c) => { const v = row[`GitHub: ${c.full_name}`]; return `<tr>
          <td><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.full_name)}</a><div class="help">${esc(c.description || "")}</div></td>
          <td>${esc(c.reason)}${c.matched_lines?.length ? `<details><summary>rreshtat</summary><pre>${esc(c.matched_lines.join("\n"))}</pre></details>` : ""}</td>
          <td class="num">${v != null ? `<span class="badge ${v >= 0.3 ? "bad" : v >= 0.15 ? "warn" : "ok"}">${pct(v)}</span>` : "–"}</td>
          <td class="help">${esc((c.created_at || "").slice(0, 10))}</td></tr>
          <tr><td colspan="4">${matchTable(`GitHub: ${c.full_name}`)}</td></tr>`; }).join("")}</tbody></table>`
        : `<p>Asnjë projekt i ngjashëm nuk u gjet.</p>`}
      ${(gsim?.limitations || []).map((l) => `<div class="note warn" style="margin-top:8px">${esc(l)}</div>`).join("")}
    </div>
    ${others.length ? `<div class="card"><h3 style="margin-top:0">Krahasimi me projektet e tjera në këtë auditim</h3><table><tbody>
      ${others.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num"><span class="badge ${v >= 0.3 ? "bad" : v >= 0.15 ? "warn" : "ok"}">${pct(v)}</span></td></tr>
        <tr><td colspan="2">${matchTable(k)}</td></tr>`).join("")}</tbody></table></div>` : ""}
    ${g.history?.flags?.length ? `<div class="card"><h3 style="margin-top:0">Sinjale nga historia e git-it</h3><ul>${g.history.flags.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></div>` : ""}
    ${g.inventory?.template_leftovers?.length ? `<div class="card"><h3 style="margin-top:0">Kod i mbetur nga shabllonet</h3><ul class="ev">${g.inventory.template_leftovers.map((t) => `<li><strong>${esc(t.template)}</strong> <span class="mono">${esc(t.location)}</span></li>`).join("")}</ul></div>` : ""}`;
}

async function loadLog(job) {
  const pre = document.getElementById("log");
  if (!pre) return;
  try { pre.textContent = (await api(`/api/jobs/${encodeURIComponent(job.id)}/log`)) || "(bosh)"; } catch { pre.textContent = "–"; }
}

function statCard(label, value, sub) {
  return `<div class="stat"><div class="l">${esc(label)}</div><div class="v">${esc(fmt(value))}</div><div class="s help">${esc(sub || "")}</div></div>`;
}

function tabReq(g, job) {
  const rep = g.report;
  const hints = Object.fromEntries((g.hints?.hints || []).map((h) => [h.id, h]));
  const reqText = Object.fromEntries((job.requirements || []).map((r) => [r.id, r]));
  if (rep?.requirements?.items?.length) {
    const items = rep.requirements.items;
    const c = (s) => items.filter((i) => i.status === s).length;
    return `<div class="note" style="margin-bottom:12px">Vlerësimi përfundimtar nga leximi i kodit: <strong>${c("Met")} Met</strong>,
      ${c("Partially met")} Partially met, ${c("Not met")} Not met, ${c("Cannot verify")} Cannot verify.
      Kolona e fundit tregon sugjerimin automatik për krahasim.</div>
      <div class="card table-wrap"><table><thead><tr><th>ID</th><th>Kërkesa</th><th>Vendimi</th><th>Dëshmia / shënime</th><th>Sugjerimi auto</th></tr></thead>
      <tbody>${items.map((i) => `<tr><td><strong>${esc(i.id)}</strong></td><td>${esc(i.text)}</td>
        <td>${badge(VERDICT, i.status)}</td>
        <td><ul class="ev">${(i.evidence || []).map((e) => `<li class="mono">${esc(e)}</li>`).join("")}</ul>${i.notes ? `<div class="help">${esc(i.notes)}</div>` : ""}</td>
        <td>${hints[i.id] ? badge(HINT, hints[i.id].status) : "–"}</td></tr>`).join("")}</tbody></table></div>`;
  }
  if (!g.hints?.hints) return `<div class="note">${job.requirements ? "Sugjerimet nuk janë gati ende." : "Nuk u dha dokument kërkesash. Claude do t'i nxjerrë kërkesat nga README."}</div>`;
  return `<div class="note warn" style="margin-bottom:12px">Këto janë <strong>sugjerime automatike</strong> nga numërimi dhe kërkimi në kod, jo vendim.
      Vendimin përfundimtar Met / Partially met / Not met e jep Claude duke lexuar kodin (skeda "Raporti").</div>
    <div class="card table-wrap"><table><thead><tr><th>ID</th><th>Kërkesa</th><th>Sugjerimi</th><th>Dëshmia automatike</th></tr></thead>
    <tbody>${g.hints.hints.map((h) => `<tr><td><strong>${esc(h.id)}</strong></td>
      <td>${h.section ? `<div class="help">${esc(h.section)}</div>` : ""}<strong>${esc(h.title)}</strong>
        ${reqText[h.id]?.text && reqText[h.id].text !== h.title ? `<div class="help">${esc(reqText[h.id].text)}</div>` : ""}
        ${reqText[h.id] && !reqText[h.id].mandatory ? ` <span class="badge muted">opsionale</span>` : ""}</td>
      <td>${badge(HINT, h.status)}</td>
      <td><ul class="ev">${h.evidence.map((e) => `<li class="mono">${esc(e)}</li>`).join("")}</ul>${h.note ? `<div class="help">${esc(h.note)}</div>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
}

function tabReport(g, job, name, gs) {
  if (g.report_md) {
    const f = (p) => `/api/jobs/${encodeURIComponent(job.id)}/file?path=${encodeURIComponent((job.legacy ? "" : gs.slug + "/") + p)}`;
    return `<div class="actions" style="margin-bottom:12px"><a class="btn" href="${f("audit-report.md")}">Shkarko .md</a>
      ${g.report ? `<a class="btn" href="${f("audit-report.json")}">Shkarko .json</a>` : ""}</div>
      <div class="card markdown">${md(g.report_md)}</div>`;
  }
  const claudeState = gs.claude;
  return `<div class="card">
    <h3 style="margin-top:0">Raporti përfundimtar nuk është shkruar ende</h3>
    ${claudeState === "running" ? `<div class="note">Claude po e lexon kodin dhe po shkruan raportin. Kjo zgjat disa minuta.</div>` :
      claudeState === "error" ? `<div class="note bad">Claude përfundoi pa raport. Shiko log-un më poshtë.</div>` : ""}
    <p>Dëshmitë automatike janë gati. Vendimin për çdo kërkesë dhe notën i jep Claude me skill-in <code>repo-auditor-pro</code>.</p>
    <div class="actions">
      ${STATUS.claude ? `<button class="primary" data-claude ${claudeState === "running" || job.status === "running" ? "disabled" : ""}>Nis Claude për këtë grup</button>` : ""}
      <button data-copy ${g.prompt ? "" : "disabled"}>Kopjo prompt-in për Claude Code</button>
    </div>
    ${STATUS.claude_login_needed ? `<div class="note warn" style="margin-top:12px">Claude Code CLI është i instaluar, por nuk je i kyçur.
      Hap PowerShell, shkruaj <code>claude</code>, pastaj <code>/login</code>. Pas kësaj rifresko faqen.</div>` : ""}
    ${STATUS.claude ? "" : `<p class="help">Claude Code CLI ${STATUS.claude_login_needed ? "nuk është i kyçur" : "nuk është i instaluar"}. Kopjo prompt-in dhe ngjite në Claude Code (desktop ose terminal) në projektin <code>PythonProject</code>.
      Raporti shkruhet automatikisht në dosjen e këtij grupi dhe shfaqet këtu pas rifreskimit.</p>`}
    ${g.prompt ? `<details><summary>Shiko prompt-in</summary><pre>${esc(g.prompt)}</pre></details>` : ""}
    ${g.claude_log ? `<details><summary>Log-u i Claude</summary><pre>${esc(g.claude_log)}</pre></details>` : ""}
  </div>`;
}

function tabEvidence(g) {
  const inv = g.inventory;
  if (!inv?.endpoints) return `<div class="note">Inventari nuk është gati ende.</div>`;
  const tech = Object.entries(inv.technology || {});
  return `<div class="grid two">
    <div class="card"><h3 style="margin-top:0">Repot</h3><table><tbody>${(g.acquire || []).map((r) => `<tr>
      <td><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.repo || r.url)}</a></td>
      <td class="mono">${esc(r.branch || "")} @ ${esc(r.short || "")}</td><td class="num">${esc(fmt(r.commits))} commit</td>
      <td>${r.ok ? "" : `<span class="badge bad">${esc(r.error)}</span>`}</td></tr>`).join("")}</tbody></table>
      <h3>Framework-et</h3><div>${inv.frameworks.map((f) => `<span class="badge info">${esc(f)}</span>`).join(" ") || "–"}</div>
      <h3>Gjuhët (rreshta kodi)</h3><table><tbody>${Object.entries(inv.lines_by_language).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${v.toLocaleString()}</td></tr>`).join("")}</tbody></table>
      <p class="help">Pa migrimet dhe kodin e gjeneruar (${inv.generated_or_migration_files} skedarë).</p></div>
    <div class="card"><h3 style="margin-top:0">Infrastruktura</h3><table><tbody>
      <tr><td>CI</td><td>${inv.ci_files.map((f) => `<div class="mono">${esc(f)}</div>`).join("") || `<span class="badge bad">asnjë</span>`}</td></tr>
      <tr><td>Deploy (CD) në CI</td><td>${inv.ci_has_deploy ? `<span class="badge ok">po</span>` : `<span class="badge warn">jo</span>`}</td></tr>
      <tr><td>Docker</td><td>${inv.docker_files.map((f) => `<div class="mono">${esc(f)}</div>`).join("") || "–"}</td></tr>
      <tr><td>Dokumentim</td><td>${inv.docs.slice(0, 6).map((f) => `<div class="mono">${esc(f)}</div>`).join("") || "–"}</td></tr>
      <tr><td>Teste</td><td>${inv.tests.count} në ${inv.tests.files.length} skedarë</td></tr></tbody></table>
      ${inv.possible_secrets.length ? `<h3>Sekrete të mundshme në repo</h3><div class="note bad">${inv.possible_secrets.length} vende me fjalëkalime ose çelësa në konfigurim (vlerat janë fshehur).</div>
        <ul class="ev">${inv.possible_secrets.map((s) => `<li class="mono">${esc(s.location)} (${esc(s.key)})</li>`).join("")}</ul>` : ""}</div>
  </div>
  <div class="card"><h3 style="margin-top:0">Teknologjitë e gjetura</h3><div class="table-wrap"><table>
    <thead><tr><th>Teknologjia</th><th class="num">Vende</th><th class="num">Në kod</th><th>Shembuj</th></tr></thead>
    <tbody>${tech.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${v.count}</td><td class="num">${fmt(v.code_hits)}</td>
      <td><span class="mono help">${esc(v.examples.slice(0, 3).join("  ·  "))}</span></td></tr>`).join("")}</tbody></table></div>
    <p class="help">"Në kod" numëron gjetjet në skedarë burimorë. Një paketë e deklaruar në konfigurim që nuk përdoret në kod nuk llogaritet si implementim.</p></div>
  <div class="grid two">
    <div class="card"><details><summary><strong>${inv.endpoints.count} endpoint-e</strong> (${Object.entries(inv.endpoints.by_method).map(([k, v]) => `${esc(k || "?")}: ${v}`).join(", ")})</summary>
      <table><tbody>${inv.endpoints.items.map((e) => `<tr><td><span class="badge info">${esc(e.method)}</span></td><td class="mono">${esc(e.route)}</td><td class="mono help">${esc(e.location)}</td></tr>`).join("")}</tbody></table></details></div>
    <div class="card"><details><summary><strong>${inv.models.count} modele</strong>, ${inv.migrations.count} migrime</summary>
      <p>${inv.models.names.map((n) => `<span class="badge muted">${esc(n)}</span>`).join(" ")}</p>
      <ul class="ev">${inv.migrations.files.map((f) => `<li class="mono">${esc(f)}</li>`).join("")}</ul></details></div>
  </div>`;
}

function tabHistory(g) {
  const h = g.history;
  if (!h?.authors) return `<div class="note">Historia nuk është gati ende.</div>`;
  const ids = Object.entries(h.identity_map || {});
  return `<div class="stats">${statCard("Commit-e (pa merge)", h.non_merge_commits, `${h.duplicate_commits} dublikata`)}
      ${statCard("Persona", h.authors.length, `${ids.length} identitete të bashkuara`)}
      ${statCard("Ditë aktive", h.active_days, `${fmt(h.first_date)} → ${fmt(h.last_date)}`)}
      ${statCard("Commit-e me tiketë", h.issue_tracker_keys?.commits_with_key, Object.keys(h.issue_tracker_keys?.projects || {}).join(", "))}</div>
    ${h.flags.length ? `<div class="card" style="margin-top:16px"><h3 style="margin-top:0">Sinjale nga historia</h3><ul>${h.flags.map((f) => `<li>${esc(f)}</li>`).join("")}</ul></div>` : ""}
    <div class="card" style="margin-top:16px"><h3 style="margin-top:0">Kontributi</h3><div class="table-wrap"><table>
      <thead><tr><th>Personi</th><th>Identitetet në git</th><th class="num">Commit-e</th><th class="num">Rreshta +</th><th style="width:22%">Pjesa</th><th>Sipas repos</th></tr></thead>
      <tbody>${h.authors.map((a) => `<tr><td><strong>${esc(a.author)}</strong></td><td class="help">${esc(a.names.join(", "))}</td>
        <td class="num">${a.commits}</td><td class="num">${a.lines_added.toLocaleString()}</td>
        <td><div class="bar"><span style="width:${Math.round(a.share_of_added * 100)}%"></span></div><span class="help">${pct(a.share_of_added)}</span></td>
        <td class="help">${esc(Object.entries(a.commits_by_repo).map(([k, v]) => `${k}: ${v}`).join(", "))}</td></tr>`).join("")}</tbody></table></div>
      <p class="help">${esc(h.note)}</p></div>
    <div class="card"><details><summary>Commit-et më të mëdha</summary><table><tbody>${h.largest_commits.map((c) => `<tr>
      <td class="mono">${esc(c.sha)}</td><td>${esc(c.author)}</td><td class="help">${esc(c.author_date.slice(0, 10))}</td>
      <td>${esc(c.subject)}</td><td class="num">+${c.added}</td><td class="num">${c.files} skedarë</td></tr>`).join("")}</tbody></table></details></div>`;
}

function tabGithub(g) {
  const entries = Object.entries(g.github || {});
  if (!entries.length) return `<div class="note">Të dhënat nga GitHub nuk janë gati ende.</div>`;
  return entries.map(([repo, d]) => {
    const pr = d.pull_requests, rv = d.reviews;
    return `<div class="card"><h3 style="margin-top:0">${esc(repo)}</h3>
      ${d.error ? `<div class="note bad">${esc(d.error)}</div>` : ""}
      ${pr ? `<div class="stats">${statCard("Pull requests", pr.total, `${pr.merged} merged · ${pr.open} open`)}
        ${statCard("PR me review nga tjetër", rv ? `${rv.prs_with_review_by_other}/${rv.prs_checked}` : "–", rv?.sampled ? "mostër" : "të gjitha")}
        ${statCard("Degë", d.branches, "")}${statCard("Issues", d.issues?.total, d.issues ? `${d.issues.closed} të mbyllura` : "")}</div>
        <h3>PR sipas autorit</h3><p>${Object.entries(pr.by_author).map(([k, v]) => `<span class="badge muted">${esc(k)}: ${v}</span>`).join(" ")}</p>
        ${rv && Object.keys(rv.reviewers).length ? `<h3>Review-uesit</h3><p>${Object.entries(rv.reviewers).map(([k, v]) => `<span class="badge ok">${esc(k)}: ${v}</span>`).join(" ")}</p>` : ""}` : ""}
      ${(d.limitations || []).map((l) => `<div class="note ${l.includes("rate limit") ? "warn" : ""}" style="margin-top:8px">${esc(l)}</div>`).join("")}
    </div>`;
  }).join("");
}

function tabAi(g) {
  const rep = g.report?.integrity?.ai_assistance;
  const entries = Object.entries(g.ai || {});
  return `${rep ? `<div class="card"><h3 style="margin-top:0">Vlerësimi në raport</h3>
      <div class="score">${rep.estimate_low_pct}–${rep.estimate_high_pct}% <small>besueshmëria: ${esc(rep.confidence)}</small></div>
      <table style="margin-top:12px"><tbody>${(rep.components || []).map((c) => `<tr><td>${esc(c.path)}</td><td class="num">${c.lines}</td>
        <td>${esc(c.classification)}</td><td class="help">${esc((c.signals || []).join("; "))}</td></tr>`).join("")}</tbody></table></div>` : ""}
    <div class="note warn" style="margin:12px 0">Sinjalet më poshtë janë tregues automatikë, jo provë. Asnjë mjet nuk e dallon me siguri kodin e shkruar nga AI.</div>
    ${entries.map(([repo, d]) => `<div class="card"><h3 style="margin-top:0">${esc(repo)}</h3>
      <div class="stats">${statCard("Skedarë të skanuar", d.files_scanned, `${(d.total_nonblank_lines || 0).toLocaleString()} rreshta`)}
        ${statCard("Me sinjale të forta", d.files_by_level?.strong_signals, `${d.lines_by_level?.strong_signals || 0} rreshta`)}
        ${statCard("Me disa sinjale mesatare", d.files_by_level?.several_medium_signals, `${d.lines_by_level?.several_medium_signals || 0} rreshta`)}
        ${statCard("Me sinjal të dobët", d.files_by_level?.weak_or_single_signal, "")}</div>
      ${Object.keys(d.flagged_files || {}).length ? `<table style="margin-top:12px"><thead><tr><th>Skedari</th><th class="num">Rreshta</th><th>Sinjalet</th></tr></thead>
        <tbody>${Object.entries(d.flagged_files).slice(0, 40).map(([f, i]) => `<tr><td class="mono">${esc(f)}</td><td class="num">${i.lines}</td>
          <td>${i.signals.map((s) => `<span class="badge ${s.strength === "strong" ? "bad" : s.strength === "medium" ? "warn" : "muted"}">${esc(s.name)}${s.lines ? ` (r. ${esc(s.lines.join(", "))})` : ""}</span>`).join(" ")}</td></tr>`).join("")}</tbody></table>` : `<p class="help">Asnjë skedar me sinjale.</p>`}
    </div>`).join("")}`;
}

// ---------- start ----------
loadStatus().then(route);
