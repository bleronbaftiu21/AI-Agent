# Raport auditimi — Eventix (Grupi 18, Sistemet e Shpërndara 2025/26)

## 1. Të dhënat e auditimit

| | |
|---|---|
| Repo backend | https://github.com/ssh-Eventix/Grupi18-SSH-Eventix-Backend — `main` @ `bbcc1a627d14fd79be8be5bce2a1f66fb34f86e5` |
| Repo frontend | https://github.com/ssh-Eventix/Grupi18-SSH-Eventix-Frontend — `main` @ `11e9ee2656314bb32b83f70f388ea661d7aca5e9` |
| Data e auditimit | 2026-10-22 |
| Auditori | Repo Auditor Pro (vetëm lexim, analizë statike) |
| Burimi i kërkesave | `kerkesa_projekti_sistemet_shperndara.pdf` (20 kërkesa) |
| Korpusi për krahasim | Nuk u dha. Ngjashmëria me grupet e tjera nuk u kontrollua. |
| Politika e AI | E paspecifikuar. Vlerësimi jepet pa penalizim. |
| Ekzekutimi | Asnjë build/test/install nuk u ekzekutua (nuk u kërkua). |

## 2. Përmbledhje ekzekutive

Eventix është platformë multi-tenant për menaxhimin e eventeve. Backend-i është ASP.NET Core 9 + EF Core + PostgreSQL + Hangfire, ndërsa frontend-i është React 19 + Vite. Projekti është i madh dhe serioz për nivelin e lëndës: 144 endpoint-e, 31 entitete, skemë për çdo tenant, 8 punë në background, autorizim me leje (permission policies), cache me çelësa sipas tenant-it, 36 teste dhe CI në GitHub Actions. Përmbushja e kërkesave të detyrueshme është **85%** (14 Met, 6 Partially met, 0 Not met).

**Nota përfundimtare: 7.8 / 10** (pa kufizim, besueshmëria: Mesatare). **Nota vetëm për kërkesat: 8.5 / 10.**

> Rillogaritur më 2026-10-22: kërkesat peshojnë 70% dhe pjesa teknike 30%. Gjykimi teknik është proporcional me një projekt kursi. Versioni i parë (6.6) i peshonte kërkesat vetëm 30% dhe e gjykonte kodin si softuer prodhimi.

**Pikat e forta**
1. Arkitekturë e shtresëzuar (Domain / Application / Infrastructure / Api) dhe multi-tenancy me skemë për çdo tenant.
2. Shumë mbi minimumin: 144 endpoint-e, 31 modele, migrime për të dy DbContext-et.
3. Proces ekipor i dukshëm: mbi 145 PR, çelësa Jira (`SCRUM-…`) në 40 commit-e, 8 javë zhvillim.

**Problemet kryesore**
1. **Izolimi mes tenant-ëve (potencial, i mbështetur fort):** tenant-i zgjidhet nga header-i `X-Tenant-Slug` që e kontrollon klienti, dhe nuk krahasohet kurrë me claim-in `tenantId` të JWT-së (F-01).
2. **Sekrete në repo:** fjalëkalimi i DB, kredencialet SMTP (Mailtrap) dhe çelësi JWT i CI-së janë në skedarë të commit-uar (F-02).
3. **Kërkesa 16 (OpenAI) nuk plotësohet ashtu si kërkohet:** moduli AI përdor **Ollama** lokal (`qwen2.5:0.5b`), jo OpenAI API. README-ja megjithatë shkruan "OpenAI Integration — Completed" (F-03).

**Integriteti:** nuk u gjet asnjë shenjë kopjimi në dëshmitë e disponueshme. Pjesa e vlerësuar si e ndihmuar nga AI është **5–25%** (besueshmëri e ulët). Sinjali më i qartë është README-ja (§6.2).

## 3. Karta e vlerësimit

**Nota vetëm për kërkesat: 8.5 / 10** (14 Met, 6 Partially met, 0 Not met nga 20).

| Kategoria | Pesha | Nota | Arsyetimi |
|---|---|---|---|
| **Përmbushja e kërkesave** | **70%** | **8.5** | 85% e kërkesave të detyrueshme. Asnjë "Not met". 6 të pjesshme (OpenAI, code review, CD, filtrim i avancuar, REST, dokumentim). |
| Cilësia e kodit | 7% | 6 | 27 `throw new Exception(...)` gjenerike pa handler global. DTO të dyfishuara. Program.cs ka mbi 90 regjistrime policy të përsëritura. |
| Struktura & arkitektura | 5% | 7 | Clean architecture e qartë. Disa kontrollerë/shërbime e anashkalojnë shtresën (DbContext direkt). Migrimet ndahen në dy dosje. |
| Siguria | 5% | 6 | Sekrete dev/test në repo (konfirmuar). Izolimi mes tenant-ëve është *potencial*, prandaj llogaritet me gjysmë peshe. BCrypt, tokenat e reset-it me hash dhe refresh-token-at janë të mira. |
| Testimi | 5% | 5 | 36 teste (unit/integration/API) që ekzekutohen në CI. Mbulim i hollë kundrejt 144 endpoint-eve. Frontend pa asnjë test. |
| Mirëmbajtja & dokumentimi | 4% | 6 | README e gjatë (730 rreshta), por me pasaktësi (OpenAI, instruksione migrimi). Commit-e me mesazhe gjenerike. |
| Gatishmëria për prodhim | 2% | 7 | Për projekt kursi është mjaftueshëm: env vars, health endpoint, CI, migrime. `localhost`-et e shkruara në kod dhe mungesa e CD-së jepen si këshilla. |
| Performanca (e nxjerrë) | 1% | 6 | Cache prezent. Listat pa pagination. `ToLower().Contains` nuk përdor indekse. |
| Varësitë | 1% | 7 | Versione të fiksuara në .csproj, lockfile në frontend. CVE nuk u kontrolluan. |
| **Nota e peshuar** | | **7.8** | 5.95 nga kërkesat + 1.83 nga pjesa teknike |
| Kufizimi (cap) | | — | Asnjë kusht kufizimi nuk vlen. |
| **Nota përfundimtare** | | **7.8 / 10** | Besueshmëria: **Mesatare** |

Për ta ngritur notën, rruga më e shkurtër është të plotësohen 6 kërkesat e pjesshme. Secila kalon nga "Partially met" në "Met" dhe e ngre notën e kërkesave me ~0.25 (≈ +0.18 në notën përfundimtare). Më të lehtat: klient OpenAI (R16), review në PR (R15), filtra + pagination për eventet (R20), korrigjimi i README-së (R13).

## 4. Përshkrimi i projektit

- **Qëllimi:** platformë SaaS për organizata (tenant-ë) që krijojnë evente, shesin bileta dhe menaxhojnë rezervime, pagesa, check-in, kuponë dhe review. Blerësit (buyers) janë globalë.
- **Stack-u:** ASP.NET Core (.NET 9), EF Core + Npgsql, PostgreSQL 16, Hangfire (PostgreSQL storage), JWT + refresh tokens, BCrypt, IDistributedCache (memory në Development, Redis jashtë Development), Swashbuckle, Ollama HTTP client, SMTP. Frontend: React 19, React Router 7, Axios, Context API, Recharts.
- **Pikat hyrëse:** `Eventix.Api/Program.cs` dhe `src/main.jsx` → `App.jsx` → `routes/AppRoutes.jsx`.
- **Arkitektura:** `Domain` (entitete, enum-e) → `Application` (DTO, ndërfaqe, shërbime) → `Infrastructure` (DbContext, repo, auth, multi-tenancy, jobs, AI) → `Api` (kontrollerë, middleware).
- **Multi-tenancy:** `PublicDbContext` (skema `public`: tenantët, përdoruesit publikë, rolet, audit) dhe `TenantDbContext` (një skemë PostgreSQL për çdo tenant, `TenantModelCacheKeyFactory`). Tenant-i zgjidhet në `TenantMiddleware`.
- **Kufijtë e besimit:** shfletuesi ↔ API (JWT në `localStorage`, header `X-Tenant-Slug`), API ↔ PostgreSQL, API ↔ Ollama (HTTP), API ↔ SMTP.
- **Build/CI:** `.github/workflows/ci.yml` bën build dhe ekzekuton 3 projekte testesh me një shërbim PostgreSQL. Nuk ka CD. `docker-compose.yml` ngre vetëm PostgreSQL.

## 5. Përmbushja e kërkesave

| ID | Kërkesa | Detyr. | Statusi | Dëshmia | Shënime |
|---|---|---|---|---|---|
| R1 | Klient-server të pavarur, komunikim vetëm përmes API | Po | Met | Dy repo të ndara. `Frontend/src/api/axios.js:3-6` | — |
| R2 | HTTP/HTTPS sipas REST (full) | Po | Partially met | `Program.cs:604-607` (HTTPS vetëm jashtë Development). Rrugë RPC: `AiController.cs:75,101`, `AuthController.cs:627` | Gabimet e validimit kthehen si 500 (`throw new Exception`), jo 400/404. `GET /events` dhe `GET /events/search` dublikohen (`EventsController.cs:34-54`). |
| R3 | Minimum 20 endpoint-e | Po | Met | 144 atribute `[Http*]` në 28 kontrollerë | — |
| R4 | Framework (FastAPI/DRF/Node/Spring/.NET) | Po | Met | ASP.NET Core, `Eventix.Api.csproj` | — |
| R5 | OOP | Po | Met | Ndërfaqe + implementime, `BaseEntity`/`TenantBaseEntity`, repo bazë `TenantBaseRepository.cs` | — |
| R6 | Swagger UI për të gjitha endpoint-et | Po | Met | `Program.cs:65-120, 598-599` | Aktiv vetëm në Development. |
| R7 | ORM dhe modele të strukturuara | Po | Met | EF Core, `PublicDbContext.cs`, `TenantDbContext.cs` | — |
| R8 | Login/register + role-based authorization | Po | Met | `AuthController.cs:171,253`. Policy-t `Program.cs:293-568`. `PermissionHandler.cs` | Shih F-01 për izolimin e tenant-ëve. |
| R9 | Middleware për logging dhe autentikim | Po | Met | `RequestLoggingMiddleware.cs`, `TenantMiddleware.cs`, `Program.cs:611-617` | — |
| R10 | React + Context API | Po | Met | `src/auth/AuthContext.jsx` | Vetëm një context (auth). Minimal, por i mjaftueshëm. |
| R11 | Unit teste + API teste (+ CI/CD) | Po | Partially met | 36 teste në `Eventix.Tests/*`. CI: `.github/workflows/ci.yml` | Nuk ka CD. Frontend pa teste. Mbulim i vogël. |
| R12 | Minimum 20 modele + migrime | Po | Met | 31 entitete në `Eventix.Domain/Entities`, 23 migrime | Migrimet janë të shpërndara në `Migrations/` dhe `Persistence/Migrations/`. |
| R13 | Dokumentim i arkitekturës, API-së dhe udhëzimeve | Po | Partially met | `README.md` (730 rreshta) | Pretendon OpenAI (`README.md:153,345`). `dotnet ef database update` pa `--context` dështon me 2 DbContext (krahaso `Makefile:13-15`). Env vars e nevojshme (`JWT_*`, `POSTGRES_*`) nuk janë të dokumentuara në Installation. |
| R14 | Jira / GitHub Projects | Po | Met | 40 commit-e me `SCRUM-<n>` | Vetë board-i Jira nuk u pa. |
| R15 | GitHub me Pull Requests dhe Code Reviews | Po | Partially met | ≥104 PR (backend), 41 PR (frontend), shumica e merged | 0 review formale në 12 PR të kontrolluara (#10, 23, 40, 60, 80, 95, 104 BE; #8, 15, 25, 35, 41 FE). |
| R16 | Modul AI me **OpenAI API** + endpoint-e chatbot/analizë | Po | Partially met | `AiController.cs` (7 endpoint-e AI), `AiService.cs`, `OllamaClient.cs:28` | Përdoret Ollama lokal (`appsettings.json:18-21`), jo OpenAI. Funksionaliteti ekziston, por ofruesi nuk është ai që kërkohet. |
| R17 | Caching (Redis ose i ngjashëm) | Po | Met | `CacheHelper.cs`, `Program.cs:185-196`, çelësa `tenant:{id}:…`, 51 thirrje invalidimi | Redis host i shkruar `localhost:6379` (`Program.cs:193`). |
| R18 | Background jobs | Po | Met | Hangfire, 8 punë periodike (`JobScheduler.cs`), `TenantJobRunner.cs` | — |
| R19 | Multi-tenancy | Po | Met | Skemë për tenant: `TenantSchemaProvisioner.cs`, `TenantMiddleware.cs` | Shih F-01. |
| R20 | Kërkim dhe filtrim i avancuar në API | Po | Partially met | `EventRepository.cs:27-39` (vetëm tekst). `AuditLogQueryDTO` (filtra + pagination) | Për eventet, entitetin kryesor, nuk ka filtra sipas kategorisë/datës/çmimit dhe as pagination. |

**Përmbushja:** detyrueshme **85%** = (14 + 0.5×6) / 20. Opsionale: nuk ka në dokument.

## 6. Integriteti

### 6.1 Origjinaliteti

- **Metoda:** historia e git-it (`git_history.py`), kërkim për header-a licence/copyright dhe URL burimesh të jashtme, lexim manual. **Krahasimi me grupe të tjera (similarity) nuk u bë**, sepse nuk u dha korpus.
- **Historia:**
  - Backend: 220 commit-e (144 jo-merge), 34 ditë aktive, 2026-04-07 → 2026-05-30.
  - Frontend: 91 commit-e, 18 ditë aktive, 2026-04-06 → 2026-05-30.
  - Zhvillimi është gradual, përmes PR dhe me çelësa Jira. Asnjë commit pas datës së dorëzimit nuk u gjet (data e afatit nuk u dha).
- **Sinjale të shqyrtuara dhe të sqaruara:**
  - Commit-i `cc9521bce5` ("SCRUM-241 Added port 5174") shton 27,300 rreshta në 300 skedarë. Shkaku është bashkimi i një dege me histori të veçantë (repoja ka 2 root commit-e), jo kod i ri nga jashtë. Përmbajtja është e njëjta kod-bazë.
  - Commit-e të dyfishuara (p.sh. `8a7d4d1e71` / `4fd87e81f1` "entitetet") vijnë nga squash/rebase. Kjo e fryn statistikën e kontributit.
- **Kod i jashtëm i paatribuar:** nuk u gjet (0 header-a copyright/licence ose lidhje StackOverflow/CodePen në kodin burimor).
- **Përfundimi:** `No concern` në bazë të dëshmive të disponueshme. **Origjinaliteti: 100% e kodit pa shenja kopjimi**, me kufizimin e madh që nuk u bë krahasim me projekte të tjera.

### 6.2 Vlerësimi i ndihmës nga AI

**Vlerësimi: 5–25% e kodit burimor (pa migrimet e gjeneruara), besueshmëria: E ulët.**

| Komponenti | Rreshta | Klasifikimi | Sinjalet |
|---|---|---|---|
| `Backend/README.md` | 531 | Likely AI-assisted | Tekst gjenerik dhe deklarativ ("This satisfies the AI integration requirement of the course. The architecture allows future AI enhancements.", `README.md:345`). Tabelë "Completed" për çdo kërkesë, përfshirë një që nuk përputhet me kodin (OpenAI). Pretendon "Repository Tests" që nuk ekzistojnë. "Email Notification Service" renditet si "Future Improvement", ndërkohë që SMTP është implementuar. U shtua ditën e fundit (2026-05-30). |
| Frontend: pjesa nga commit-i `a7f08dc08f` (~4,000 rreshta në 40 skedarë, përfshirë 2,063 rreshta CSS) | ~4,000 | Mixed/uncertain | Një commit i madh dhe i lëmuar me mesazh në stil agjenti ("Build Eventix frontend dashboards and buyer flow"), me të dhëna mock (`buyerData.js`) që u hoqën më vonë. Pjesa më e madhe u rishkrua në commit-et pasuese. |
| Backend (14,479 rreshta C# pa migrime) | 14,479 | Likely human | Asnjë artefakt AI. Stil jo uniform (mesazhe gabimesh të ndryshme, `throw new Exception` krahas `UnauthorizedAccessException`, indentim jokonsistent). Mesazhe commit-esh në shqip ("entitetet", "fixed"). Logjikë domain-specifike (qytete të Kosovës, Jira keys). |
| Frontend tjetër | ~9,600 | Likely human | Indentim jokonsistent (`axios.js:25-30`), zgjidhje ad-hoc në interceptor, `eslint-disable`. |

Llogaritja: e ulëta = 531 / ~28,700 ≈ 2%, e larta = (531 + ~4,000) / ~28,700 ≈ 16%. Intervali u zgjerua në **5–25%** sepse mjetet e asistencës (Copilot, autocomplete) nuk lënë gjurmë të dukshme. Sinjale "strong" nuk u gjetën në kod. I vetmi i shënuar automatikisht ishte fjala "OpenAI" në README, që është përmbajtje legjitime dhe jo artefakt.

> *Ky është një vlerësim probabilistik nga sinjale indirekte, jo provë autorësie. Duhet konfirmuar nga një vlerësues njerëzor, p.sh. duke i kërkuar autorit ta shpjegojë kodin.*

### 6.3 Kontributi i anëtarëve (pas bashkimit të identiteteve të dukshme)

| Anëtari (identitetet në git) | Commit-e BE | Rreshta + BE | Commit-e FE | Rreshta + FE |
|---|---|---|---|---|
| Viola Resyli | 60 | 35,738 | 23 | 8,710 |
| Yllka Fejzullahu ("Yllka", "Yllka Fejzullahu") | 17 | 48,031 | 7 | 6,599 |
| Bleron Baftiu ("bleronbaftiu21") | 33 | 11,375 | 23 | 12,302 |
| Olti Krasniqi ("oltikrasniqi21", "Olti Krasniqi") | 24 | 12,689 | 1 | 2 |
| Riga Zubaku ("ZubakuRiga", "RigaZubaku") | 10 | 3,079 | 2 | 322 |

Kujdes: rreshtat përfshijnë migrimet e gjeneruara, merge-t e degëve me histori të veçantë (`cc9521bce5` = 27,300 rreshta) dhe squash-et e dyfishuara, prandaj nuk janë masë e drejtpërdrejtë e punës. Bashkimi i identiteteve bazohet në emra të ngjashëm dhe duhet konfirmuar.

## 7. Gjetjet

### High

**F-01 — Tenant-i nga header-i nuk verifikohet kundrejt tenant-it të token-it** · Siguria · Statusi: *Potential (i mbështetur fort), kërkon verifikim manual*
- **Vendndodhja:** `Eventix.Infrastructure/MultiTenancy/TenantMiddleware.cs:41-46, 61-62`, `Eventix.Infrastructure/Auth/PermissionHandler.cs:20-24`. Frontend: `src/api/axios.js:8-21, 57`.
- **Dëshmia:** kur ekziston `X-Tenant-Slug`, middleware-i zgjedh atë tenant dhe vendos `tenantContext.SchemaName`. Claim-i `tenantId` lexohet vetëm kur header-i mungon. `PermissionHandler` kontrollon vetëm rolet në claims. I vetmi krahasim tenant ↔ token ndodh për token-at e impersonation (`ImpersonationTokenValidation.cs:44`). Slug-u merret nga `localStorage`, pra klienti mund ta ndryshojë lirisht.
- **Ndikimi:** një Admin/Staff i tenant-it A me token të vlefshëm mund të dërgojë `X-Tenant-Slug: <tenant-B>` dhe të lexojë ose ndryshojë të dhënat e tenant-it B me lejet e rolit të vet. Kjo prish kërkesën R19 për ndarjen e të dhënave.
- **Rekomandimi:** pas autentikimit, nëse `tenantId` në token nuk përputhet me tenant-in e zgjidhur (dhe nuk është SuperAdmin/impersonation), kthe 403. Ose zgjidhe tenant-in vetëm nga token-i. Shto një test API për këtë rast.

**F-02 — Kredenciale të commit-uara në repo** · Siguria · *Confirmed*
- **Vendndodhja:** `Eventix.Api/appsettings.Development.json:11-12` (SMTP Mailtrap Username/Password = `[REDACTED]`), `docker-compose.yml:9` (POSTGRES_PASSWORD = `[REDACTED]`), `.github/workflows/ci.yml:23,38,39` (DB password dhe `JWT_SECRET_KEY` = `[REDACTED]`).
- **Ndikimi:** kredencialet e sandbox-it Mailtrap janë të përdorshme nga kushdo që sheh repon. I njëjti fjalëkalim DB përdoret në docker-compose dhe CI, kështu që po të ripërdoret diku tjetër, ekspozohet. Rreziku është i kufizuar sepse janë vlera dev/test.
- **Rekomandimi:** rrotullo (rotate) kredencialet e Mailtrap. Përdor GitHub Actions Secrets dhe `.env` (jashtë git-it) me `.env.example`. Pastro historinë nëse repo është publike.

**F-03 — Moduli AI përdor Ollama, jo OpenAI, ndërsa README pretendon OpenAI** · Kërkesat / Dokumentimi · *Confirmed*
- **Vendndodhja:** `Eventix.Infrastructure/Services/OllamaClient.cs:8-40`, `Eventix.Api/appsettings.json:18-21`, `Program.cs:277-281`. `README.md:7,46,109,153,343-345`.
- **Shtesë (u gjet nga skripti `inventory.py`):** paketa NuGet `OpenAI` 2.10.0 është e deklaruar në `Eventix.Infrastructure/Eventix.Infrastructure.csproj:32`, por nuk përdoret në asnjë skedar `.cs`. Integrimi me OpenAI ka nisur, por nuk është lidhur.
- **Ndikimi:** kërkesa R16 kërkon shprehimisht OpenAI API. Dokumentimi nuk përputhet me implementimin.
- **Rekomandimi:** shto një `OpenAiClient : IOllamaClient` (ose riemërto ndërfaqen në `ILlmClient`) dhe zgjidh ofruesin nga konfigurimi. Ose korrigjo README-në dhe arsyetoje zgjedhjen para mësimdhënësit.

### Medium

**F-04 — Gabime gjenerike pa handler global → 500 për gabime validimi** · Cilësia e kodit / REST · *Confirmed*
- **Vendndodhja:** 27 raste të `throw new Exception(...)`, p.sh. `BookingService.cs:60,65,91`. Nuk ka `UseExceptionHandler`/ProblemDetails në `Program.cs`. Vetëm 1 `catch (Exception)` në kontrollerë.
- **Ndikimi:** inputi i gabuar ("Event not found", "Quantity must be greater than zero") kthehet si 500 dhe jo si 400/404. Kjo bie ndesh me "REST full" (R2).
- **Rekomandimi:** krijo përjashtime domain-i (`NotFoundException`, `ValidationException`) dhe një middleware që i kthen në ProblemDetails me statusin e duhur.

**F-05 — Mbishitje (overselling) e mundshme e biletave në kërkesa paralele** · Korrektësia · *Potential*
- **Vendndodhja:** `Eventix.Application/Services/BookingService.cs:104, 130-131`. Nuk u gjet asnjë `ConcurrencyCheck`/`RowVersion`/`xmin` në domain ose DbContext.
- **Ndikimi:** dy blerje njëkohësore mund ta kalojnë kontrollin `QuantityAvailable < item.Quantity` dhe të shesin më shumë bileta se sa ka. Migrimi `FixTicketTypeSoldQuantityConstraint` mund të ketë shtuar një constraint në DB që e zbut këtë, por nuk u verifikua.
- **Rekomandimi:** token konkurrence (`xmin` në Npgsql) ose `UPDATE … WHERE QuantityAvailable >= @q` atomik, brenda një transaksioni.

**F-06 — Mungojnë code reviews formale në PR** · Procesi · *Confirmed (mostër)*
- **Dëshmia:** 0 review në 12 PR të kontrolluara përmes GitHub API (shih R15).
- **Rekomandimi:** branch protection në `main` me ≥1 review të detyrueshëm.

**F-07 — Konfigurime të shkruara si localhost** · Gatishmëria për prodhim · *Confirmed*
- **Vendndodhja:** Redis `Program.cs:193`, CORS `Program.cs:287`, URL e reset-it `AuthController.cs:108`.
- **Ndikimi:** në çdo mjedis jashtë Development, cache-i dhe linqet e reset-it nuk funksionojnë pa ndryshim kodi.
- **Rekomandimi:** lexoji nga konfigurimi/env vars.

**F-08 — Kërkim i thjeshtë dhe lista pa pagination** · Performanca / R20 · *Inferred*
- **Vendndodhja:** `EventRepository.cs:27-39` (`ToLower().Contains`, pa `Skip/Take`). `AiService.cs:57,290` ngarkon të gjitha eventet publike dhe filtron në memorie.
- **Rekomandimi:** filtra (kategori, datë, çmim, qytet), pagination dhe `ILIKE`/indekse trigram në PostgreSQL.

### Low

**F-09 — Endpoint-i `GET /api/ai/debug-claims` ka mbetur në kod** · `AiController.cs:125-134`. Kthen të gjitha claims të përdoruesit. Hiqe ose kufizoje në Development.

**F-10 — Politikë e dobët fjalëkalimi** · `AuthController.cs:126` (minimumi 6 karaktere, pa kompleksitet).

**F-11 — JWT në `localStorage`** · `src/auth/AuthContext.jsx:37`. Rrezik vjedhjeje përmes XSS. Pranueshëm për projekt kursi, por duhet përmendur.

**F-12 — Dokumentim jo i saktë** · `README.md`: komanda e migrimit pa `--context` dështon me 2 DbContext (shih `Makefile:13-15`). Env vars nuk dokumentohen. Pretendime "Repository Tests" pa teste të tilla.

### Info

- Hangfire dashboard (`Program.cs:594`) përdor filtrin default që lejon vetëm kërkesa lokale. Nuk është problem për momentin.
- Testet ekzistojnë dhe ekzekutohen në CI, por nuk u ekzekutuan gjatë këtij auditimi.

## 8. Shënime sipas kategorive

- **Arkitektura:** ndarje e mirë e shtresave dhe DI e plotë. Shmangie të shtresave: `AuthController` injekton `PublicDbContext`/`TenantDbContext` direkt (`AuthController.cs:28-29`). `AiService` përdor `TenantDbContext` direkt në vend të repove. DTO-të e login/register janë dyfishuar në `DTOs/Auth` dhe `DTOs/User`.
- **Cilësia:** kod i lexueshëm, async kudo, `CancellationToken` i përcjellë. `Program.cs` ka mbi 270 rreshta regjistrimesh policy të përsëritura, që mund të gjenerohen me një cikël mbi enum-in `Permission`.
- **Siguria:** BCrypt për fjalëkalimet, token-at e reset-it ruhen të hash-uar (SHA-256) dhe skadojnë pas 30 min, mesazhi i forgot-password nuk zbulon nëse llogaria ekziston, refresh tokens me revokim, `FallbackPolicy = RequireAuthenticatedUser`. Dobësitë janë te F-01, F-02, F-09, F-10.
- **Testimi:** 36 teste (23 unit, 6 integration, 7 API): unit (auth, cache, check-in, kupona), integration (jobs, event service, provisioner), API (events, email domains). Nuk mbulojnë booking, pagesat ose izolimin mes tenant-ëve.
- **Varësitë:** paketat NuGet kanë versione të fiksuara. npm përdor `^` me `package-lock.json`. Auditimi i CVE-ve nuk u bë.
- **Performanca (e nxjerrë, jo e matur):** cache 5-minutësh për lexime të shpeshta, me invalidim. Mungon pagination. Kërkimi me `ToLower()` nuk përdor indekse.
- **Gatishmëria për prodhim:** ka health endpoint, CI dhe migrime. Mungojnë CD, Dockerfile për API/frontend dhe konfigurimi i jashtëm (F-07).

## 9. Pyetje për mbrojtjen e projektit

1. Si e zgjedh `TenantMiddleware` tenant-in kur kërkesa ka edhe JWT edhe `X-Tenant-Slug`? Çfarë ndodh nëse ato nuk përputhen?
2. Pse `TenantDbContext` ka nevojë për `TenantModelCacheKeyFactory`? Çfarë do të ndodhte pa të?
3. Pse zgjodhët Ollama në vend të OpenAI? Si do ta ndërronit ofruesin pa ndryshuar `AiService`?
4. Si i ekzekuton `TenantJobRunner` punët Hangfire për secilin tenant (skema)?
5. Ku dhe si invalidohet cache-i kur ndryshon një `TicketType`? Pse çelësi përmban `tenant:{TenantId}`?
6. Çfarë ndodh nëse dy blerës rezervojnë njëkohësisht biletën e fundit (`BookingService.CreateBooking`)?
7. Si funksionon impersonation-i i SuperAdmin-it dhe si revokohet një sesion?
8. Shpjegoni rrjedhën e refresh token-it, nga login deri te `revoke-all`.
9. Pse ka migrime në dy dosje (`Migrations/` dhe `Persistence/Migrations/`)? Cila përdoret?
10. Çfarë bën commit-i `a7f08dc08f` dhe si u ndërtua `MoreEntityPages.jsx` (1,728 rreshta)?

## 10. Kufizimet

- Nuk u ekzekutua asnjë build, test, linter ose aplikacion. Të gjitha përfundimet janë nga analiza statike.
- **Nuk u bë krahasim ngjashmërie me grupe të tjera**, sepse nuk u dha korpus. Origjinaliteti vlerësohet vetëm nga historia dhe gjurmët e brendshme.
- Code reviews u kontrolluan në një mostër prej 12 PR. Board-i Jira dhe GitHub Projects nuk u panë.
- Nuk u bë auditim CVE i varësive, sepse `dotnet list package --vulnerable`/`npm audit` nuk u ekzekutuan.
- `gh` CLI nuk ishte i instaluar. Metadatat e PR u morën nga GitHub API publik (pa autentikim).
- Gjatë checkout-it në Windows, 15 skedarë migrimesh dështuan fillimisht nga gjatësia e rrugës. U rikuperuan me `core.longpaths`. Ishte problem mjedisi, jo i projektit.
- Vlerësimi i AI-së është indikativ dhe ka besueshmëri të ulët.

## 11. Shtojca

- **Inventari:** Backend 380 skedarë teksti burimor (14,479 rreshta C# pa migrime, 21,077 rreshta migrime të gjeneruara), 28 kontrollerë, 31 entitete, 23 migrime, 14 skedarë testesh. Frontend 86 skedarë (13,661 rreshta në `src`), 0 teste.
- **Të përjashtuara:** `node_modules`, `bin/obj`, `package-lock.json`, asete binare. Migrimet u përjashtuan nga vlerësimi i AI-së dhe i cilësisë (kod i gjeneruar).
- **Komandat:** `git clone --no-checkout` + `checkout` me `core.hooksPath=/dev/null`, `git log/show/ls-files`, `grep`, `scripts/git_history.py`, `scripts/ai_signals.py`, `curl` GET te `api.github.com` (pulls, reviews), `pypdf` për leximin e PDF-së së kërkesave.
- **Të dhënat e papërpunuara:** `history-Backend.json`, `history-Frontend.json`, `ai-Backend.json`, `ai-Frontend.json` në këtë dosje.
