# Raporti i auditimit — ssh-Eventix (Grupi 18)

## 1. Koka

| Fusha | Vlera |
|---|---|
| Repot | https://github.com/ssh-Eventix/Grupi18-SSH-Eventix-Backend (branch `main`, commit `bbcc1a627d14fd79be8be5bce2a1f66fb34f86e5`)<br>https://github.com/ssh-Eventix/Grupi18-SSH-Eventix-Frontend (branch `main`, commit `11e9ee2656314bb32b83f70f388ea661d7aca5e9`) |
| Data e auditimit | 2026-10-22 |
| Auditori | Repo Auditor Pro |
| Burimi i kërkesave | `kerkesa_projekti_sistemet_shperndara.pdf` (brief.pdf), "Sistemet e Shpërndara 2025/26", 20 kërkesa (R1–R20), të gjitha të detyrueshme |
| Korpusi i krahasimit | Asnjë grup tjetër; 3 kandidatë publikë nga GitHub (indestudio/Eventix, sholajegede/eventix, Eventix/omnipay-first-atlantic-commerce) |
| Politika e AI | `unspecified` (raportohet pa penalizim) |
| Afati | i pa specifikuar |
| Ekzekutimi | Kodi i projektit **nuk** u ekzekutua; analizë statike vetëm |

## 2. Përmbledhje ekzekutive

Eventix është një platformë multi-tenant për menaxhimin e eventeve (ASP.NET Core 8 + EF Core/PostgreSQL në backend, React + Vite në frontend), me skemë PostgreSQL të veçantë për çdo tenant, JWT + leje të bazuara në role, Hangfire për punë në background, cache të shpërndarë dhe një modul AI. Projekti i plotëson shumicën e kërkesave të brief-it: 145 endpoint-e, 31 modele me 21 migrime, Swagger, middleware për logging/tenant, React Context, 36 teste me CI në GitHub Actions. **Nota përfundimtare: 8.1 / 10** (pa kufizim). Nota vetëm për kërkesat është **9.0 / 10**.

**Pikat e forta:** (1) arkitekturë e shtresuar e qartë (Api/Application/Domain/Infrastructure) me multi-tenancy skemë-për-tenant dhe provisionim automatik; (2) autorizim i detajuar me leje (`Permission:*`), BCrypt për fjalëkalime, refresh/reset token-a të ruajtur si hash; (3) teste unit/integrimi/API që ekzekutohen në CI.

**Problemet kryesore:** (1) `[AllowAnonymous]` në nivel klase te `AuthController` anashkalon `[Authorize]` të endpoint-eve `refresh-tokens`, `revoke-all`, `logout`, `revoke-refresh-token`, kështu që ato janë të qasshme pa autentikim; (2) audit log-u global (me vlera të vjetra/të reja të entiteteve) lexohet nga çdo përdorues i autentikuar, edhe nga një Buyer i regjistruar vetë; (3) moduli AI përdor **Ollama** (LLM lokal), jo OpenAI API siç kërkon R16 dhe siç pretendon README; paketa `OpenAI` është e instaluar por nuk përdoret.

**Integriteti:** nuk u gjet kopjim (ngjashmëria me kandidatët nga GitHub është boilerplate JSX). Vlerësimi i ndihmës nga AI: 0–30%, besueshmëri e ulët. README përmban disa pretendime që kodi nuk i ka (shih §6.2 dhe F-07).

## 3. Tabela e notave

**Nota vetëm për kërkesat: 9.0 / 10** (detyrueshme 92.1%: 16 Met, 3 Partially met, 1 Cannot verify)

| Kategoria | Pesha | Nota | Arsyetimi |
|---|---|---|---|
| Plotësimi i kërkesave | 70% | 9.0 | 16/19 Met, 3 Partially met (R13, R16, R20); R15 nuk u verifikua (GitHub API) |
| Cilësia e kodit | 7% | 6.0 | Controller-a që flasin direkt me DbContext, defekt i scope-it në `PaymentRetryJob`, çelësa cache që nuk përputhen, endpoint debug i mbetur |
| Struktura & arkitektura | 5% | 7.0 | Shtresa të qarta dhe DI; por Api varet direkt nga Infrastructure dhe migrimet janë në 3 dosje të ndryshme |
| Siguria | 5% | 4.0 | Dy defekte autorizimi të konfirmuara statikisht (F-01, F-02), izolim tenant-i i dyshimtë (F-03), kredenciale në repo (F-04) |
| Testimi | 5% | 7.0 | 36 teste në 12 skedarë (unit, integrim me PostgreSQL, API në nivel controller-i), ekzekutohen në CI |
| Mirëmbajtja & dokumentimi | 4% | 6.0 | README të gjata me arkitekturë dhe API, por me pasaktësi dhe pa variablat e mjedisit që kërkon backend-i |
| Gatishmëria për prodhim | 2% | 7.0 | Konfigurim me env, docker-compose për DB, health endpoint, CI; Redis i fiksuar në `localhost` |
| Performanca | 1% | 6.0 | Cache në GET-et kryesore; pagination vetëm te audit log-u; N+1 në punët e background-it (e nxjerrë, jo e matur) |
| Varësitë | 1% | 6.0 | Paketa të papërdorura (OpenAI, FluentValidation, Hangfire.SqlServer); versione të përziera (.NET 8 kundrejt SDK 9 në CI, Redis 10.x) |

- **Nota e peshuar:** 6.30 + 0.42 + 0.35 + 0.20 + 0.35 + 0.24 + 0.14 + 0.06 + 0.06 = **8.12 → 8.1**
- **Kufizim (cap):** asnjë. Kufizimi për sekretet vlen vetëm për projekte të orientuara drejt prodhimit; ky është projekt kursi dhe kredencialet janë për sandbox/DB lokale.
- **Nota përfundimtare: 8.1 / 10**
- **Besueshmëria:** Medium (pa ekzekutim, GitHub API i kufizuar, board-i Jira i padukshëm)

## 4. Përshkrimi i projektit

- **Qëllimi:** platformë SaaS për organizata (tenant) që krijojnë evente, vende (venue), lloje biletash, rezervime, pagesa, kupona, check-in dhe review; blerësit (Buyer) shfletojnë eventet publike nga të gjithë tenant-ët.
- **Stack-u:** C# / ASP.NET Core 8 (`Eventix.Api/Eventix.Api.csproj:4`), EF Core + Npgsql, PostgreSQL 16, Hangfire (PostgreSQL storage), IDistributedCache (memorie në Development, StackExchange Redis jashtë Development), JWT Bearer, BCrypt, Ollama HTTP client; React 18 + Vite + React Router + Axios.
- **Pikat hyrëse:** `Eventix.Api/Program.cs` (backend, port i parazgjedhur 5225 sipas frontend-it), `src/main.jsx` (frontend).
- **Arkitektura:**

```
React (Vite, AuthContext, Axios + X-Tenant-Slug)
        │  HTTP/JSON (REST)
        ▼
ASP.NET Core API ─ RequestLoggingMiddleware → Authentication → TenantMiddleware → Authorization(Permission:*)
        │ Controllers → Application Services → Repositories
        ▼
PostgreSQL: skema "public" (Tenants, PublicUsers, Roles, AuditLogs, RefreshTokens…)
            + një skemë për tenant (Events, Venues, Bookings, Tickets, Payments…)
Hangfire (recurring jobs për çdo tenant) · Ollama (LLM lokal) · SMTP Mailtrap
```

- **Kufijtë e besimit:** klienti dërgon JWT dhe header-in `X-Tenant-Slug`; tenant-i zgjidhet nga header-i ose nga claim-i `tenantId` (`Eventix.Infrastructure/MultiTenancy/TenantMiddleware.cs:41-46`).
- **Ruajtja e të dhënave:** PostgreSQL, me `TenantDbContext` që ndërron skemën përmes `TenantModelCacheKeyFactory` (`Program.cs:171-183`).
- **Integrimet:** Ollama `/api/generate` (`Eventix.Infrastructure/Services/OllamaClient.cs:28`), SMTP Mailtrap (`appsettings.Development.json:8-14`).
- **Build/deploy:** `docker-compose.yml` vetëm për PostgreSQL; nuk ka Dockerfile apo CD.
- **Testet & CI:** `Eventix.Tests/{UnitTests,IntegrationTests,ApiTests}`; `.github/workflows/ci.yml` build + test me shërbim PostgreSQL.

## 5. Plotësimi i kërkesave

| ID | Kërkesa | Detyrueshme | Statusi | Dëshmia | Shënime |
|---|---|---|---|---|---|
| R1 | Arkitektura klient-server, komunikim vetëm përmes API | Po | Met | `Frontend/src/api/axios.js:3-6`; `Backend/Eventix.Api/Program.cs:283-291` (CORS për React) | Dy repo të ndara; frontend-i flet vetëm me `/api`. |
| R2 | HTTP/HTTPS sipas REST | Po | Met | `Program.cs:604-607` (`UseHttpsRedirection` jashtë Development); `Controllers/EventsController.cs:34-168` (GET/POST/PUT/DELETE, 201/204/404) | Disa rrugë në stil RPC (`/activate`, `/validate`, `/redeem`) dhe emërtim njëjës/shumës i përzier; nuk ndikon në thelb. |
| R3 | Minimum 20 endpoint-e | Po | Met | 145 endpoint-e në 28 controller-a (inventory); p.sh. `Controllers/VenueController.cs:34-123` | GET 73, POST 42, PUT 15, DELETE 15. |
| R4 | Framework REST (FastAPI/DRF/Node/Spring/.NET) | Po | Met | `Eventix.Api.csproj:1,4`; `Program.cs:61,619` | ASP.NET Core 8 Web API. |
| R5 | Programim OOP | Po | Met | `Eventix.Domain/Common/BaseEntity.cs`, `TenantBaseEntity.cs`, `Interfaces/ITenantEntity.cs`; ndërfaqe repo/servisi + DI `Program.cs:198-276` | Trashëgimi, ndërfaqe, injektim i varësive, enkapsulim në servise. |
| R6 | Swagger UI për të gjitha endpoint-et | Po | Met | `Program.cs:63-120` (SwaggerGen me Bearer + X-Tenant-Slug), `Program.cs:596-600` | Swagger UI aktiv vetëm në Development; controller-at dokumentohen automatikisht. |
| R7 | ORM dhe modele të strukturuara | Po | Met | `Infrastructure/Persistence/Database/TenantDbContext.cs:21-623` (çelësa, indekse unike, check constraints, FK me DeleteBehavior) | Konfigurim i kujdesshëm i modeleve. |
| R8 | Login/register + autorizim me role | Po | Met | `Controllers/AuthController.cs:171-251` (register), `:253-409` (login); `Program.cs:293-568` (role + 80+ policy lejesh); `Infrastructure/Auth/PermissionHandler.cs:16-30` | Funksionaliteti ekziston; defektet e autorizimit numërohen te Siguria (F-01/F-02), jo këtu. |
| R9 | Middleware për logging dhe autentikim | Po | Met | `Eventix.Api/Middleware/RequestLoggingMiddleware.cs:18-55`; `Program.cs:611-617` (`UseAuthentication`, `TenantMiddleware`) | |
| R10 | Frontend me React dhe Context API | Po | Met | `Frontend/src/auth/AuthContext.jsx:6,15-…`; `src/main.jsx:1` | Vetëm një Context (Auth); `TenantContext.jsx` që përmend README nuk ekziston. |
| R11 | Unit teste dhe API teste (+CI) | Po | Met | 36 teste në 12 skedarë, p.sh. `Eventix.Tests/Eventix.UnitTests/Services/DiscountCouponServiceTests.cs:12-43`, `Eventix.Tests/Eventix.ApiTests/Events/EventsControllerApiTests.cs:25-111`; `.github/workflows/ci.yml:68-75` | "API testet" thërrasin controller-in direkt, jo përmes HTTP (WebApplicationFactory). Testet nuk u ekzekutuan. |
| R12 | Minimum 20 modele + migrime | Po | Met | 31 entitete (`TenantDbContext.cs:21-46`, `PublicDbContext.cs:13-25`); 21 migrime në `Eventix.Infrastructure/Migrations/**` dhe `Persistence/Migrations/**` | Migrimet janë në 3 dosje të ndryshme (shih Struktura). |
| R13 | Dokumentim i plotë: arkitektura, API, udhëzime | Po | Partially met | `Backend/README.md:54-95` (arkitektura), `:473-527` (API), `:606-645` (instalimi); `Frontend/README.md` | README nuk përmend variablat e mjedisit të detyrueshme (`POSTGRES_*`, `JWT_*`, `Program.cs:31-50`), pa to backend-i nuk niset; struktura e dosjeve dhe disa teknologji të përshkruara nuk përputhen me kodin (F-07). |
| R14 | Jira / GitHub Projects | Po | Met | 84 commit-e me çelësa Jira (`EVENTIX` 43, `SCRUM` 40, `EVENTICX` 1) në history.json | Board-i Jira nuk ishte i dukshëm; vlerësimi bazohet te çelësat në commit-e. |
| R15 | GitHub me Pull Requests dhe Code Reviews | Po | Cannot verify | 90 merge commit-e nga 220 në backend; subjekte si "added services (#14)", "… (#39)", "fixed (#41)" | GitHub API arriti kufirin (pa `GITHUB_TOKEN`), ndaj review-t nuk u panë. PR-të duken nga historia. |
| R16 | Modul AI që komunikon me **OpenAI API** dhe ekspozon endpoint-e | Po | Partially met | `Controllers/AiController.cs:21-112` (chat, buyer/chat, recommendations, generate-event-description, review-summary, generate-marketing); `Infrastructure/Services/OllamaClient.cs:19-40`; `appsettings.json:18-21` (`qwen2.5:0.5b`) | Endpoint-et AI ekzistojnë dhe funksionojnë me LLM, por thirrjet shkojnë te Ollama lokal, jo te OpenAI API. Paketa `OpenAI` 2.10.0 (`Eventix.Infrastructure.csproj:32`) nuk përdoret askund. |
| R17 | Caching (Redis ose i ngjashëm) | Po | Met | `Program.cs:185-196`; `Helpers/CacheHelper.cs:8-34`; përdorim në controller-a, p.sh. `EventsController.cs:62-69`, `BookingController.cs:17-22` | Redis vetëm jashtë Development dhe me adresë të fiksuar `localhost:6379`; disa çelësa invalidimi nuk përputhen (F-06). |
| R18 | Detyra asinkrone / background jobs | Po | Met | `Program.cs:571-579` (Hangfire + PostgreSQL); `Infrastructure/BackgroundJobs/JobScheduler.cs:9-47` (8 punë periodike); `TenantJobRunner.cs:69-100` | `PaymentRetryJob` ka defekt (F-05); punët janë përpunim të dhënash, jo email/AI. |
| R19 | Multi-tenancy (ndarja e të dhënave) | Po | Met | Skemë për çdo tenant: `TenantDbContext.cs:19,50`; `MultiTenancy/TenantSchemaProvisioner.cs`; `TenantMiddleware.cs:16-65`; test `IntegrationTests/MultiTenancy/TenantSchemaProvisionerTests.cs` | Struktura është e mirë; mungesa e lidhjes tenant↔token dhe audit log-u global trajtohen te Siguria (F-02, F-03). |
| R20 | Kërkim dhe filtrim i avancuar në API | Po | Partially met | Filtrim i avancuar + pagination vetëm te audit log-u: `Persistence/Repositories/AuditLogRepository.cs:19-76`, `DTOs/AuditLog/AuditLogQueryDTO.cs:5-25`; eventet kanë vetëm kërkim teksti: `EventRepository.cs:19-39`, `PublicEventRepository.cs:150-165` | Te entitetet kryesore (evente, rezervime, bileta) mungojnë filtrat sipas kategorisë/datës/çmimit dhe pagination. |

**Plotësimi i kërkesave të detyrueshme:** (16 + 0.5 × 3) / 19 = **92.1%** (R15 përjashtohet si Cannot verify).
**Kërkesa opsionale:** asnjë në brief — N/A.

## 6. Integriteti

### 6.1 Origjinaliteti

**Metoda:** `similarity.py` (fingerprinting i normalizuar, k=12, window=8) mes projektit dhe 3 kandidatëve publikë nga GitHub; leximi manual i përputhjeve; historia e git-it; kërkim për kokë licencash/emra të huaj. Kërkimi i kodit në GitHub (code search) **nuk** u bë sepse mungonte `GITHUB_TOKEN`; kandidatët u gjetën vetëm sipas emrit (code_hits = 0).

| Skedari i kandidatit | Skedari i projektit | Containment | Rreshtat | Verdikti |
|---|---|---|---|---|
| sholajegede-eventix/app/page.tsx | Frontend/src/pages/buyer/BuyerPages.jsx | 0.344 (kandidati te projekti); 0.024 në drejtim të kundërt | 5-7, 12-18, 20-25, 33-37 | Expected/boilerplate similarity |
| sholajegede-eventix/components/header.tsx | Frontend/src/pages/buyer/BuyerPages.jsx | 0.329 / 0.052 | 6-8, 11-23, 34-88 | Expected/boilerplate similarity |
| sholajegede-eventix/app/page.tsx | 8 faqe të tjera JSX (DashboardPage, HomePage, TenantsPage…) | 0.25–0.31 / ≤0.06 | të njëjtat | Expected/boilerplate similarity |
| indestudio/Eventix | ssh-Eventix | 0.013 / 0.002 | — | No concern |
| Eventix/omnipay-first-atlantic-commerce | ssh-Eventix | 0.0 | — | No concern |

**Krahasimi manual:** `sholajegede/eventix/app/page.tsx` është një faqe Next.js/TypeScript me Kinde Auth dhe komponentë shadcn (`<Button asChild>`, `<CardDescription>`), 39 rreshta. Përputhja vjen nga struktura e përgjithshme JSX (`<section className=…><div><article>…`) që pas normalizimit (identifikuesit → ID, literalet → LIT) bëhet identike me çdo faqe React. Nuk ka asnjë logjikë, emër apo tekst të përbashkët. Kandidati u krijua më 2024-12-19, para commit-it të parë të projektit (2026-04-06), por me stack tjetër (Next.js + Convex + Kinde) dhe vetëm 1.1% e kodit të projektit përputhet me të. **Nuk ka shenja kopjimi.**

**Sinjalet nga historia e git-it:**
- 311 commit-e (200 jo-merge) mes 2026-04-06 dhe 2026-05-30, 36 ditë aktive, puna rritet gradualisht (W15 → W22).
- 5 persona pas bashkimit të 8 identiteteve git; të gjithë duken anëtarë të ekipit (2 me email `@student.uni-pr.edu`).
- `last_7_days_share` = 52% (nën pragun 60% të metodës). Java W21 ka 27,752 rreshta, ku hyn commit-i `cc9521bce5` (Yllka, 2026-05-24, "SCRUM-241 Added port 5174", **266 skedarë, +11,049 rreshta**). Mesazhi nuk përputhet me madhësinë e commit-it, ndaj duhet sqaruar në mbrojtje.
- Nuk ka commit-e me autorë të huaj apo data para publikimit të detyrës.

**Kod i jashtëm pa atribuim:** nuk u gjetën kokë licencash, emra projektesh të huaja apo URL tutorialesh në kodin burimor. `template_leftovers` = [] (s'ka mbetje nga shabllonet Vite/ASP.NET).

**Origjinaliteti i përgjithshëm: ~100%** (0 nga 28,432 rreshta burimorë në rajone të kopjuara të konfirmuara apo të dyshuara).

### 6.2 Vlerësimi i ndihmës nga AI

**Vlerësimi: 0–30%, besueshmëri: Low**

| Komponenti | Rreshta | Klasifikimi | Sinjalet |
|---|---|---|---|
| Backend: domain, repositories, services, controllers (C#) | ~14,250 | Likely human | Asnjë sinjal i fortë (`ai-*.json` = 0 skedarë të shënuar); stil jo uniform (dhëmbëzim i përzier, p.sh. `AuthController.cs:203-207`, `Program.cs:437-438`); `using` të dyfishuar (`EventsControllerApiTests.cs:2-3`); histori iterative me commit-e të vogla në shqip. |
| `Infrastructure/Services/AiService.cs` | ~450 | Mixed/uncertain | Prompt-e shumë të gjata e të strukturuara me rregulla (`AiService.cs:124-149`), heuristika të shumta të detektimit të kategorisë/qytetit/datës. |
| Frontend: faqet nga commit-i `a7f08dc08f` "Build Eventix frontend dashboards and buyer flow" | ~4,360 | Mixed/uncertain | 39 skedarë dhe 4,358 rreshta në një commit të vetëm, të lëmuar (sinjal mesatar); më vonë u ndryshuan (p.sh. "SCRUM-242 Fixed buyer flow"). |
| Frontend CSS | ~3,130 | Mixed/uncertain | Temë e plotë e shkruar në pak commit-e të mëdha. |
| Pjesa tjetër e frontend-it (services, routes, layouts, auth) | ~6,240 | Likely human | Interceptor-i Axios me rregulla ad-hoc dhe dhëmbëzim të çrregullt (`axios.js:23-79`) tregon punë iterative njerëzore. |
| README (backend dhe frontend) — dokumentim, jashtë llogaritjes | — | Likely AI-assisted | Seksione uniforme ("… Included Functionality" me nga 6 pika), fraza gjenerike ("This module represents the core business functionality"), pretendime pa mbulesë në kod: OpenAI API, FluentValidation/Validators, Mailtrap si e vetmja dorëzim, aplikacion mobil React Native (nuk ndodhet në asnjërin repo), `TenantContext.jsx`, `authService.js`/`reportService.js` (nuk ekzistojnë). README-ja e backend-it e rendit "QR Code Check-In / Mobile Application" edhe si veçori të përfunduar, edhe si "Future Improvements" (`README.md:358-369` kundrejt `:718-719`). |

Llogaritja: low = 0 / 28,432 = 0%; high = (450 + 4,360 + 3,130) / 28,432 ≈ 28% → **0–30%**. Përmbajtja e commit-it `cc9521bce5` (11k rreshta) nuk u inspektua në detaje, ndaj mbetet e paklasifikuar. Ky është një kufizim.

**Politika:** `unspecified`, raportohet pa penalizim. `needs_human_review`: jo.

*"Ky është një vlerësim probabilistik nga sinjale indirekte, jo provë e autorësisë. Duhet të konfirmohet nga një vlerësues njerëzor, p.sh. duke i kërkuar autorit të shpjegojë kodin."*

### 6.3 Kontributi i anëtarëve

| Autori | Commit-e | Rreshta + | Rreshta − | Pjesa e shtuar | Repo (BE/FE) |
|---|---|---|---|---|---|
| Viola Resyli | 73 | 26,535 | 10,056 | 40.7% | 52 / 21 |
| Yllka Fejzullahu | 23 | 20,298 | 3,218 | 31.1% | 16 / 7 |
| bleronbaftiu21 | 45 | 12,805 | 2,959 | 19.6% | 28 / 17 |
| RigaZubaku | 12 | 3,401 | 746 | 5.2% | 10 / 2 |
| Olti Krasniqi | 25 | 2,131 | 747 | 3.3% | 24 / 1 |

Shënim: squash merge dhe commit-et e mëdha (p.sh. `cc9521bce5` me 11k rreshta te Yllka) i shtrembërojnë shifrat. Kontributet e Riga Zubaku dhe Olti Krasniqi janë të vogla në rreshta, megjithëse Riga ka bërë commit-in JWT/Authorization (`6fe11d4736`, 92 skedarë).

## 7. Gjetjet

### High

**F-01 — `[AllowAnonymous]` në nivel klase anashkalon `[Authorize]` në endpoint-et e token-ave**
- Kategoria: security · Severiteti: High · Statusi: Confirmed (analizë statike, pa ekzekutim)
- Vendndodhja: `Eventix.Api/Controllers/AuthController.cs:17`, `:551-552`, `:578-579`, `:605-606`, `:627-628`; `Infrastructure/MultiTenancy/TenantMiddleware.cs:29-33`
- Dëshmia: klasa ka `[AllowAnonymous]`; veprimet `GetRefreshTokens`, `RevokeAllUserTokens`, `Logout`, `RevokeRefreshToken` kanë `[Authorize(Policy = "Permission:…")]`. Në ASP.NET Core, `IAllowAnonymous` në metadata e endpoint-it e anashkalon çdo `[Authorize]`.
- Ndikimi: kushdo pa token mund të thërrasë `GET /api/auth/refresh-tokens` (lista e të gjitha refresh token-ave me email-et e përdoruesve dhe hash-et) dhe `POST /api/auth/revoke-all/{publicUserId}` (çregjistron çdo përdorues nga sesionet e tij).
- Rekomandimi: hiqni `[AllowAnonymous]` nga klasa dhe vendoseni vetëm te `login`, `register`, `refresh`, `forgot-password`, `reset-password`.

**F-02 — Audit log-u global lexohet nga çdo përdorues i autentikuar**
- Kategoria: security · Severiteti: High · Statusi: Confirmed (analizë statike)
- Vendndodhja: `Eventix.Api/Controllers/AuditLogController.cs:11,21-42`; `Persistence/Repositories/AuditLogRepository.cs:26-32`; `TenantMiddleware.cs:34`
- Dëshmia: controller-i ka vetëm `[Authorize]` pa policy, ndërkohë që `Permission:ViewAuditLogs` ekziston (`Program.cs:473`). Repository-ja lexon `PublicDbContext.AuditLogs` pa filtër tenant-i, përveç nëse klienti e jep vetë `TenantId`.
- Ndikimi: një Buyer i regjistruar vetë (`/api/auth/register`) mund të lexojë log-et e të gjithë tenant-ëve, përfshirë `OldValues`/`NewValues`, email-et dhe emrat e tenant-ëve. Kjo cenon izolimin që kërkon R19.
- Rekomandimi: `[Authorize(Policy = "Permission:ViewAuditLogs")]` dhe filtrim i detyrueshëm sipas tenant-it për jo-SuperAdmin.

### Medium

**F-03 — Tenant-i zgjidhet nga header-i pa u krahasuar me claim-in `tenantId` të token-it**
- Kategoria: security · Severiteti: Medium · Statusi: Needs manual verification
- Vendndodhja: `Infrastructure/MultiTenancy/TenantMiddleware.cs:41-46`; `Infrastructure/Auth/PermissionHandler.cs:20-26`
- Dëshmia: nëse dërgohet `X-Tenant-Slug`, ai ka përparësi ndaj `tenantId` të token-it. `PermissionHandler` kontrollon vetëm rolet. Përputhja tenant↔token verifikohet vetëm për token-at e impersonimit (`ImpersonationTokenValidation.cs:44`).
- Ndikimi i mundshëm: një Admin i tenant-it A që dërgon `X-Tenant-Slug: B` mund të veprojë mbi skemën e tenant-it B. Duhet konfirmuar me ekzekutim.
- Rekomandimi: në middleware, refuzoni kërkesën kur `tenantId` i token-it ≠ tenant-i i zgjidhur (përveç SuperAdmin/impersonimit).

**F-04 — Kredenciale të commit-uara në repo**
- Kategoria: security · Severiteti: Medium · Statusi: Confirmed
- Vendndodhja: `Eventix.Api/appsettings.Development.json:11-12` (username/password SMTP Mailtrap: `[REDACTED]`); `docker-compose.yml:9` dhe `.github/workflows/ci.yml:23,38` (fjalëkalimi i PostgreSQL: `[REDACTED]`, i njëjtë në të dy vendet); `.github/workflows/ci.yml:39` (`JWT_SECRET_KEY`: `[REDACTED]`)
- Ndikimi: kredencialet e sandbox-it Mailtrap janë publike; fjalëkalimi i DB-së lokale dhe çelësi JWT i CI-së janë të njohur. Rreziku është i ulët sepse janë mjedise test/lokale, por praktika është e gabuar.
- Rekomandimi: rrotulloni kredencialet e Mailtrap, përdorni GitHub Secrets në CI dhe `.env` (jo në git) për docker-compose.

**F-05 — `PaymentRetryJob` krijon scope të ri dhe humbet kontekstin e tenant-it**
- Kategoria: code-quality · Severiteti: Medium · Statusi: Confirmed (analizë statike)
- Vendndodhja: `Infrastructure/BackgroundJobs/PaymentRetryJob.cs:19-20`; krahaso `TenantJobRunner.cs:80-90`
- Dëshmia: `TenantJobRunner` vendos `TenantId`/`SchemaName` në scope-in e tij, por job-i hap `CreateScope()` të ri. Aty `ITenantContext` është bosh, ndaj `TenantDbContext` përdor skemën `"public"` (`TenantDbContext.cs:19`).
- Ndikimi: job-i nuk prek pagesat e tenant-ëve (ose dështon), dhe ekzekutohet N herë mbi të njëjtën skemë. Edhe kur funksionon, vetëm e kthen statusin `Failed → Pending` pa ndonjë riprovë reale.
- Rekomandimi: injektoni `TenantDbContext` direkt si në `BookingCleanupJob.cs:11-14`.

**F-06 — Invalidimi i cache-it përdor çelësa që nuk vendosen kurrë**
- Kategoria: code-quality · Severiteti: Low · Statusi: Confirmed
- Vendndodhja: `Eventix.Api/Controllers/EventsController.cs:62,80` (vendos `events:public:search:*`, `events:public:{id}`) kundrejt `:118-120,137-143,159-165` (fshin `tenant:{id}:events:search:all`, `tenant:{id}:event:{id}`)
- Ndikimi: pas krijimit, ndryshimit ose fshirjes, lista publike e eventeve mbetet e vjetër deri në 5 minuta.
- Rekomandimi: përdorni të njëjtën skemë çelësash për vendosje dhe invalidim.

**F-07 — README pretendon veçori/teknologji që kodi nuk i ka**
- Kategoria: documentation · Severiteti: Medium · Statusi: Confirmed
- Vendndodhja: `Backend/README.md:7,46,109,153,343-354` (OpenAI); `:107,388` (FluentValidation/Validators; asnjë `AbstractValidator` në kod); `:358-369` (aplikacion mobil React Native, mungon në repo) kundrejt `:718-719`; `:380` (`Extensions`, `Middlewares`; dosja reale është `Middleware`); `:575-581` (portet 5001/5000; frontend-i pret 5225, `axios.js:4`); `Frontend/README.md:158-188` (`contexts/TenantContext.jsx`, `authService.js`, `reportService.js` nuk ekzistojnë); `Frontend/README.md:445` ("Pages never call Axios directly", ndërsa 4 faqe e importojnë direkt, p.sh. `pages/tenant/MoreEntityPages.jsx`)
- Ndikimi: dokumentimi e mbivlerëson projektit dhe e vështirëson instalimin (variablat e detyrueshme `POSTGRES_*`/`JWT_*` nga `Program.cs:31-50` nuk përmenden).
- Rekomandimi: përditësoni README-të që të përputhen me kodin dhe shtoni një `.env.example`.

### Low

**F-08 — Endpoint debug dhe mesazhe që zbulojnë ekzistencën e llogarive**
- Kategoria: security · Severiteti: Low · Statusi: Confirmed
- Vendndodhja: `Controllers/AiController.cs:125-134` (`GET /api/ai/debug-claims`); `AuthController.cs:280,283` ("Tenant user not found." kundrejt "Invalid password.")
- Rekomandimi: hiqni endpoint-in debug; përdorni të njëjtin mesazh për email/fjalëkalim të gabuar.

**F-09 — Varësi të papërdorura dhe versione të përziera**
- Kategoria: dependencies · Severiteti: Low · Statusi: Confirmed
- Vendndodhja: `Eventix.Infrastructure.csproj:32` (OpenAI), `Eventix.Api.csproj:22` (FluentValidation), `:27` (Hangfire.SqlServer), `:33` (StackExchangeRedis 10.0.8 në net8.0); `ci.yml:51` (SDK 9.0.x për projekt net8.0)
- Rekomandimi: hiqni paketat e papërdorura dhe njësoni versionet.

**F-10 — Lista pa pagination dhe N+1 në punët e background-it (e nxjerrë, jo e matur)**
- Kategoria: performance · Severiteti: Low · Statusi: Potential
- Vendndodhja: `Persistence/Repositories/EventRepository.cs:19-39` (pa Skip/Take); `BackgroundJobs/BookingCleanupJob.cs:37-41` (query për çdo item)
- Rekomandimi: shtoni pagination dhe ngarkoni `TicketType`-t me një query të vetme.

## 8. Shënime sipas kategorive

- **Struktura & arkitektura (7):** Clean architecture me katër projekte, DI e plotë dhe repository/service pattern. Problemet: controller-at varen direkt nga Infrastructure (`EventsController.cs:8`, `AuthController.cs:6,28-29` me `PublicDbContext`/`TenantDbContext` direkt, kështu që logjika e autentikimit (~640 rreshta) jeton në controller); migrimet ndodhen në `Migrations/`, `Migrations/Public|TenantDb/` dhe `Persistence/Migrations/Public|Tenant/`; `Program.cs` ka 80+ policy të shkruara me dorë që mund të gjenerohen nga enum-i `Permission`.
- **Siguria (4):** Aspekte pozitive: BCrypt (`Program.cs:226`), JWT me validim të plotë dhe `ClockSkew = 0` (`Program.cs:144-158`), reset token-a dhe refresh token-a të ruajtur si hash SHA-256 (`AuthController.cs:63-67`), forgot-password që nuk zbulon ekzistencën e llogarisë (`:73-90`), SQL i parametrizuar në kërkimin publik (`PublicEventRepository.cs:164`), FallbackPolicy që kërkon autentikim (`Program.cs:295-297`). Negative: F-01, F-02 (të konfirmuara statikisht), F-03 (për t'u verifikuar), F-04, F-08. Dashboard-i i Hangfire (`Program.cs:594`) përdor filtrin e parazgjedhur (vetëm localhost); kjo është në rregull për projekt kursi.
- **Cilësia e kodit (6):** Kodi lexohet mirë dhe ka validime bazë, por ka defekte reale (F-05, F-06), `Console.WriteLine` në vend të `ILogger` në punët e background-it (`TenantJobRunner.cs:94-97`), `_logRepository` që injektohet në `AiService` por thirrjet `ChatAsync` nuk logohen (`AiService.cs:30-50`) edhe pse README pretendon "Request Logging", dhëmbëzim jo konsistent dhe `using` të dyfishuar.
- **Testimi (7):** 36 teste: unit (JWT, refresh token, leje, impersonim, cache, check-in, kupona), integrim me PostgreSQL real (provisionim skeme, background jobs, EventService), dhe "API" në nivel controller-i. CI i ekzekuton në push/PR. Mungojnë testet HTTP end-to-end (që do ta kishin kapur F-01) dhe teste për frontend-in. Testet nuk u ekzekutuan në këtë auditim.
- **Mirëmbajtja & dokumentimi (6):** README të gjata me diagram arkitekture, tabela API, role dhe udhëzime ekzekutimi, por me pasaktësi (F-07) dhe pa konfigurimin e mjedisit. Commit-et kanë çelësa Jira, por disa mesazhe nuk përshkruajnë ndryshimin ("fixed", "Added port 5174" për 266 skedarë).
- **Gatishmëria për prodhim (7):** konfigurim nga env me kontroll të qartë (`Program.cs:42-50`), health endpoint (`:621-629`), docker-compose për DB, CI, Hangfire me storage të qëndrueshëm. Si këshillë (pa penalizim për projekt kursi): Redis i fiksuar në `localhost:6379` (`Program.cs:193`), URL e reset-it e fiksuar në `http://localhost:5173` (`AuthController.cs:108`), CORS vetëm localhost, s'ka Dockerfile/CD.
- **Performanca (6, e nxjerrë):** cache me TTL 5 min në GET-et publike/të shpeshta; pagination vetëm te audit log-u; F-10. Nuk u bë asnjë matje.
- **Varësitë (6):** versione të fiksuara në `.csproj`, por me paketa të papërdorura dhe versione të përziera (F-09). Nuk u ekzekutua asnjë audit CVE.

## 9. Pyetje për mbrojtjen

1. Pse `AuthController` ka `[AllowAnonymous]` në nivel klase? Çfarë ndodh me `[Authorize(Policy = "Permission:ViewRefreshTokens")]` te `GET /api/auth/refresh-tokens` kur thirret pa token?
2. Brief-i kërkon OpenAI API. Pse zgjodhët Ollama (`qwen2.5:0.5b`) dhe pse paketa `OpenAI` është në `Eventix.Infrastructure.csproj` pa u përdorur? Pse README thotë "OpenAI Integration"?
3. Si siguron `TenantMiddleware` që një Admin i tenant-it A nuk mund të qaset në të dhënat e tenant-it B duke ndryshuar header-in `X-Tenant-Slug`?
4. Kush duhet ta shohë `/api/auditlog`? Pse controller-i nuk përdor policy-n `Permission:ViewAuditLogs`?
5. Shpjegoni si funksionon `TenantModelCacheKeyFactory` dhe pse duhet për multi-tenancy me skemë për tenant.
6. `PaymentRetryJob` hap scope të ri me `IServiceScopeFactory`. Në cilën skemë punon `TenantDbContext` brenda tij?
7. Commit-i `cc9521bce5` "SCRUM-241 Added port 5174" shton 266 skedarë dhe ~11,000 rreshta. Çfarë përmbante në të vërtetë dhe nga erdhi ai kod?
8. README përshkruan një aplikacion mobil skaneri në React Native/Expo. Ku ndodhet ai kod?
9. Pse çelësat që fshihen në `EventsController.Create/Update/Delete` nuk përputhen me ata që vendosen te `PublicSearch`?
10. Si i keni organizuar Pull Request-et dhe code review-t? Tregoni një PR me komente review-i.

## 10. Kufizimet

- Kodi i projektit nuk u ekzekutua (as build, as teste, as aplikacioni). Gjetjet F-01, F-02, F-05 janë të konfirmuara nga leximi i kodit dhe semantika e njohur e ASP.NET Core, jo nga ekzekutimi.
- GitHub API arriti kufirin pa `GITHUB_TOKEN`: PR-të, review-t, issues dhe branch-et nuk u lexuan (R15 = Cannot verify). Kërkimi i kodit në GitHub nuk u bë; kandidatët u gjetën vetëm sipas emrit.
- Board-i Jira/GitHub Projects nuk ishte i dukshëm; R14 bazohet te çelësat në commit-e.
- Nuk kishte korpus me grupe të tjera të kursit për krahasim.
- Commit-i `cc9521bce5` (11k rreshta) nuk u inspektua skedar për skedar; leximi i kodit u bë me mostër (entry points, auth, multi-tenancy, AI, cache, jobs, teste, frontend auth/API), jo i të 437 skedarëve.
- Nuk u ekzekutua asnjë audit CVE për varësitë.
- Vlerësimi i AI-së është indirekt dhe me besueshmëri të ulët.

## 11. Shtojca

**Inventari:** C# 349 skedarë / 14,704 rreshta; JSX 44 / 9,302; CSS 4 / 3,126; JS 36 / 1,287; HTML 1 / 13 — gjithsej 28,432 rreshta burimorë. 45 skedarë migrimesh/të gjeneruar u përjashtuan nga llogaritjet. Framework-e: ASP.NET Core, EF Core, React, Vite. 145 endpoint-e, 31 modele, 21 migrime, 36 teste, 1 workflow CI, 1 docker-compose.

**Shtigje të përjashtuara:** `.git`, `bin/`, `obj/`, `node_modules/`, `dist/`, migrimet dhe `*.Designer.cs`/snapshot-et e EF (të gjeneruara), lockfile-t, imazhet.

**Dëshmitë e përdorura (të mbledhura më parë nga pipeline, pa riklonim):** `evidence/acquire.json`, `inventory.json`, `history.json`, `hints.json`, `ai-*.json`, `github-*.json`, `github_similar.json`, `../similarity.json`, `../requirements.json`.

**Komandat e ekzekutuara në këtë auditim:** vetëm lexim skedarësh (Read/Grep/Glob) mbi klonet në `C:\Users\bleron.baftiu\AppData\Local\RepoAuditor\ws\20261022-141814\ssh-Eventix\`. Asnjë komandë git, build ose test nuk u ekzekutua dhe repot nuk u ndryshuan.
