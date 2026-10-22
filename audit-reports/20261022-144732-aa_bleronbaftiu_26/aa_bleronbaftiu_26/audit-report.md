# Raport auditimi — aa_bleronbaftiu_26

## 1. Kreu

| Fusha | Vlera |
|---|---|
| Repo | https://github.com/bleronbaftiu21/aa_bleronbaftiu_26 |
| Dega | `main` |
| Commit | `4f08cb893b6deb70c13aece55e4692cc218aaf99` (`4f08cb8`) |
| Data e auditimit | 2026-10-22 |
| Auditori | Repo Auditor Pro |
| Burimi i kërkesave | `brief.pdf` — "Dynamic Questionnaire Analysis, Programming Assignment" (5 probleme) |
| Korpusi për krahasim | Asnjë grup tjetër në këtë ekzekutim; asnjë kandidat nga GitHub (shih Kufizimet) |
| Politika e AI | unspecified (pa penalizim) |
| Afati | i pacaktuar |
| Kodi ekzekutuar? | Jo — vetëm analizë statike |

## 2. Përmbledhje ekzekutive

Repo është një projekt konzolë C# (.NET 8) me ushtrime javore të lëndës "Algoritme të avancuara". Detyra e auditimit (analiza e pyetësorit dinamik) është zgjidhur në një skedar të vetëm, `AlgoritmeTeAvancuara/AlgoritmeTeAvancuara/java2/Questionnaire_Dependency_Assignment.cs` (496 rreshta), që përmban të dhënat JSON, modelet dhe pesë funksionet e kërkuara. Gjurmimi statik i kodit tregon se të pesë problemet janë zgjidhur me rekursion dhe japin rezultatet e pritura nga brief-i (6 / 4 / 22 / lista për q2–a2_truck / tabela e probabiliteteve). **Nota përfundimtare: 8.5 / 10** (pa kufizim), **nota vetëm për kërkesat: 9.5 / 10**.

**Pikat e forta:** (1) të gjitha kërkesat e detyrueshme plotësohen, me rekursion të vërtetë dhe mbrojtje nga ciklet; (2) kod i pastër, modern (records, local functions, `checked`, rrumbullakim i qartë); (3) validim i të dhënave hyrëse (ID të dyfishta, referenca që mungojnë).
**Problemet kryesore:** (1) asnjë test i automatizuar — vetëm një demonstrim që printon rezultatet për shembullin; (2) README bosh dhe higjienë e dobët e repos (dosja `.vs/` e komituar, mesazhe commit si `//`, `detyra`); (3) i gjithë zgjidhja në një skedar me emër dosjeje mashtrues (`java2` për kod C#).
**Integriteti:** asnjë sinjal kopjimi; puna shpërndahet në 4 javë (34% e rreshtave në 7 ditët e fundit); një autor i vetëm. Vlerësimi i AI: 0–44% (besueshmëri e ulët) — skedari i detyrës ka stil dukshëm më të sofistikuar se ushtrimet e mëparshme; duhet verifikuar me pyetje gojore.

## 3. Tabela e notave

**Nota vetëm për kërkesat: 9.5 / 10** (detyrueshme 100%, opsionale 0%).

| Kategoria | Pesha (fillestare → e rinormalizuar) | Nota | Arsyetimi |
|---|---|---|---|
| Përputhja me kërkesat | 70% → 75.3% | 9.5 | 19/19 kërkesa të detyrueshme Met; mungon vetëm memoizimi opsional në P1/P2. |
| Cilësia e kodit | 7% → 7.5% | 8 | Kod i lexueshëm, i validuar, pa kod të vdekur në skedarin e detyrës; disa vargje magjike ("radio", "select") dhe klasë `Program` e dyfishuar. |
| Struktura & arkitektura | 5% → 5.4% | 6 | Të dhëna, modele, algoritme dhe runner në një skedar; dosje `java2` për C#; `Program.cs` thërret të gjitha ushtrimet njëherësh. |
| Siguria | 5% → — | N/A | Program konzolë offline, pa hyrje nga përdoruesi, rrjet apo sekrete; nuk ka sipërfaqe sulmi. |
| Testimi | 5% → 5.4% | 2 | 0 teste; vetëm printim në konzolë për shembullin e brief-it. |
| Mirëmbajtja & dokumentimi | 4% → 4.3% | 4 | README përmban vetëm titullin; `.vs/` i komituar; mesazhe commit jo-përshkruese. |
| Gatishmëria për prodhim | 2% → — | N/A | Detyrë algoritmike kursi; nuk kërkohet deploy/konfigurim. |
| Performanca | 1% → 1.1% | 7 | P3 me memo (O(n·m)); P1/P2/P5 rritet me numrin e rrugëve (i nxjerrë, jo i matur) — i pranueshëm për brief-in. |
| Varësitë | 1% → 1.1% | 9 | Asnjë paketë e jashtme; vetëm BCL e .NET 8. |

- **Nota e peshuar:** 8.53 → **8.5**
- **Kufizim (cap):** asnjë
- **Nota përfundimtare:** **8.5 / 10**
- **Besueshmëria:** Medium (analizë statike pa ekzekutim; pa korpus krahasimi dhe pa kërkim kodi në GitHub)

## 4. Përshkrimi i projektit

- **Qëllimi:** zgjidhje e ushtrimeve të lëndës; për këtë auditim — analiza e grafit të pyetësorit (rruga më e gjatë/shkurtër, numri i rrugëve, pyetjet e arritshme, probabilitetet).
- **Stack:** C# 12, .NET 8 konzolë (`AlgoritmeTeAvancuara.csproj:5`), `System.Text.Json`.
- **Pika hyrëse:** `Program.cs` (top-level statements) → `AlgoritmeTeAvancuara.java2.Program.Run()` (`Program.cs:26`), e cila deserializon JSON-in e brief-it (`java2/Questionnaire_Dependency_Assignment.cs:20-105`) dhe printon rezultatet e 5 problemeve (`:107-121`).
- **Arkitektura:**
  ```
  Program.cs ──► java1 (DFS, fuqia) ─ java2.Program.Run ─ java3 ─ java4 (ushtrime të tjera)
                                     │
                                     ├─ records: Answer, Question, Questionnaire, QuestionPath, ReachableQuestion, QuestionProbability
                                     └─ Analyzer: BuildIndex, NextSteps, FindBestPath, HasCycle, CountAllPossiblePaths,
                                                  FindReachableQuestions, CalculateQuestionProbabilities
  ```
- **Kufijtë e besimit / ruajtja e të dhënave / integrimet:** asnjë — të dhënat janë të ngulitura në kod.
- **Build/deploy, teste, CI/CD:** vetëm `.sln`/`.csproj`; pa teste, pa CI.
- Skedarët `java1`, `java3`, `java4` janë ushtrime të tjera të lëndës dhe nuk vlerësohen për kërkesat; merren parasysh vetëm për krahasimin e stilit.

## 5. Përputhja me kërkesat

> Ndarja automatike në `requirements.json` (R1–R20) kishte copëtuar komentet `@param/@returns` të brief-it në kërkesa të veçanta. Lista më poshtë është rindërtuar nga teksti i plotë i brief-it në kërkesa atomike; numërimi R1–R20 këtu zëvendëson atë automatik.
> Rrugët relative janë nga `AlgoritmeTeAvancuara/AlgoritmeTeAvancuara/`; `Q.cs` = `java2/Questionnaire_Dependency_Assignment.cs`.

| ID | Kërkesa | E detyrueshme | Statusi | Dëshmia | Shënime |
|---|---|---|---|---|---|
| R1 | Çdo problem zgjidhet me rekursion (cikle vetëm për indeksim/iterim përgjigjesh/renditje) | Po | Met | `Q.cs:259-294`, `:307-335`, `:350-365`, `:393-408`, `:441-467` | Edhe kontrolli i komponentëve në `HasCycle` bëhet rekursivisht (`:326-333`). |
| R2 | Modeli i të dhënave sipas ndërfaqeve (Answer, Question, Questionnaire) dhe JSON snake_case | Po | Met | `Q.cs:10-14`, `:133-147` | `SnakeCaseLower` jep `next_question_id`, `start_question_id`. |
| R3 | P1: `findLongestQuestionPath` kthen `length`, `question_ids`, `answer_path` | Po | Met | `Q.cs:149-152`, `:240-244` | `length` = `QuestionIds.Length` nga ndërtimi (`:276-278`). |
| R4 | P1: rruga më e gjatë = pyetja + më e gjata nga pasardhësit (rekursiv) | Po | Met | `Q.cs:269-288` | Për shembullin jep gjatësi 6 (q1,q2,q3,q6,q8,q9 — e pranuar nga brief-i). |
| R5 | P1: trajton pyetje me shumë përgjigje dhe pyetje me "next" të pakushtëzuar | Po | Met | `Q.cs:225-237` | |
| R6 | P1: ndjek ID-të e përgjigjeve; vetëm radio/select kontribuojnë në `answer_path` | Po | Met | `Q.cs:279-281` | |
| R7 | P1: mbrojtje nga ciklet me bashkësinë e pyetjeve në rrugën aktuale | Po | Met | `Q.cs:257`, `:264-265`, `:291` | |
| R8 | P1/P2: memoizim i rezultatit më të mirë për pyetje | Jo (opsionale) | Not met | `Q.cs:253-299` | Kërkuar: nuk ka cache në `FindBestPath`; memo ekziston vetëm në P3. |
| R9 | P2: rruga më e shkurtër, rekursive, duke shqyrtuar të gjitha degët | Po | Met | `Q.cs:247-251`, `:269-288` | Jep q1,q5,q6,q8 (gjatësi 4). |
| R10 | P2: kthen çdo rrugë të vlefshme më të shkurtër; mbrojtje nga ciklet | Po | Met | `Q.cs:283-285`, `:264` | |
| R11 | P3: numërim rekursiv; `null` = 1 rrugë e përfunduar | Po | Met | `Q.cs:350-365` | Për shembullin: 22. |
| R12 | P3: çdo përgjigje numërohet si degë më vete, edhe kur shkojnë te e njëjta pyetje | Po | Met | `Q.cs:360-361` | |
| R13 | P3: zbulon ciklin dhe kthen −1 | Po | Met | `Q.cs:301-336`, `:344-345` | Kontrollon gjithë grafin (edhe pjesë të paarritshme) — në përputhje me formulimin "questionnaire contains a cycle". |
| R14 | P4: rekursion me thellësi; përditëson thellësinë minimale dhe rirekurson; ndalon kur thellësia ≥ | Po | Met | `Q.cs:393-408` | Implementim fjalë për fjalë i rregullit të brief-it. |
| R15 | P4: kthen `[]` kur përgjigja përfundon pyetësorin ose ID-të nuk ekzistojnë | Po | Met | `Q.cs:378-388` | `("q2","a9_nope")` → `[]`. |
| R16 | P4: fushat `question_id`, `question_text`, `min_depth`; secila pyetje një herë; renditje min_depth↑ pastaj id↑ | Po | Met | `Q.cs:154-157`, `:412-419` | |
| R17 | P5: probabilitete me përgjigje njëlloj të mundshme, përhapje rekursive, akumulim nga disa degë | Po | Met | `Q.cs:441-469` | Akumulim në hartë sipas ID (opsioni i dytë i brief-it). |
| R18 | P5: text/checkbox përcjell gjithë probabilitetin; pyetja e parë 1.0 dhe pozicion 1.0 | Po | Met | `Q.cs:455-458`, `:469` | |
| R19 | P5: `expected_position` i kushtëzuar; pyetjet e paarritshme → 0 / 0 | Po | Met | `Q.cs:471-479` | q6: (0.5·3+0.25·4+0.125·4)/0.875 = 3.4286 ✓. |
| R20 | P5: rrumbullakim në 4 shifra dhe renditje probabilitet↓ pastaj id↑ | Po | Met | `Q.cs:484-492` | |

- **Përputhja e detyrueshme:** 19 Met / 19 → **100%**
- **Përputhja opsionale:** 0 Met / 1 → **0%**
- Totali: Met 19 · Partially met 0 · Not met 1 (opsionale) · Cannot verify 0

Shënim: rezultatet janë verifikuar me gjurmim manual të kodit mbi të dhënat e brief-it, jo me ekzekutim.

## 6. Integriteti

### 6.1 Origjinaliteti

- **Metoda:** `similarity.json` nuk u krijua (vetëm një grup në këtë ekzekutim dhe asnjë kandidat GitHub). `github_similar.json`: kërkimi i kodit në GitHub u anashkalua (mungon `GITHUB_TOKEN`); kërkimi sipas emrit (`bleronbaftiu`) nuk ktheu asnjë kandidat. Nuk ka kandidatë mbi ~20% për t'u krahasuar.
- **Përputhjet kryesore:**

| Skedari i projektit | Skedari tjetër | Containment | Rreshtat | Verdikti |
|---|---|---|---|---|
| — | — | — | — | Asnjë përputhje e disponueshme |

- Emrat e funksioneve dhe të fushave (`FindLongestQuestionPath`, `question_ids`, …) vijnë nga brief-i → ngjashmëri e pritur.
- **Sinjalet e historisë git:** 9 commit-e nga një autor i vetëm (`bleronbaftiu21`), 2026-09-28 → 2026-10-21, në 5 ditë aktive dhe 4 javë (W40: 699, W41: 212, W42: 924, W43: 308 rreshta). `last_7_days_share` = 34% (< 60%, pa flamur për punë në minutën e fundit). Asnjë commit i hershëm/i vonë, asnjë autor i huaj, jo fork, jo template. Commit-i më i madh i detyrës duket të jetë "detyra 4" (2026-10-12, 2 skedarë, +498) — madhësia përputhet me skedarin java2 (496 rreshta), por kjo është nxjerrë nga `history.json`, jo e verifikuar me `git log` për skedar.
- **Kod i jashtëm pa atribuim:** asnjë kokë licence, URL apo emër projekti të huaj. `Program.cs:1-2` përmban vetëm komentin e shabllonit të Visual Studio ("new-console-template") — boilerplate. `template_leftovers` = [] dhe `possible_secrets` = [].
- **Originaliteti i përgjithshëm:** 100% e kodit nuk ndodhet në rajone të kopjuara të konfirmuara/dyshuara (1125/1125 rreshta) — me besueshmëri të kufizuar sepse nuk pati korpus dhe kërkim kodi.

### 6.2 Vlerësimi i ndihmës nga AI

**Intervali: 0–44% · Besueshmëria: Low**

| Komponenti | Rreshta | Klasifikimi | Sinjalet |
|---|---|---|---|
| `java2/Questionnaire_Dependency_Assignment.cs` | 496 (≈85 janë JSON i brief-it) | Mixed/uncertain | Mesatar: ndryshim i dukshëm stili kundrejt `java1` (emra shqip, C# klasik → emra anglisht, C# 12 me collection expressions, `checked`, `MidpointRounding`, records); validim i gjerë përtej brief-it (`:171-223`); rekursion artificial për iterimin e komponentëve (`:326-333`) për të respektuar rregullin "vetëm rekursion". Kundërsinjale: komente të shkurtra shqip ("//problemi 1", "// modelet"), mesazhe gabimi shqip pa diakritikë, pa komente tutorial, pa artefakte asistenti; `ai_signals.py` nuk gjeti asnjë sinjal. |
| `java1/*.cs`, `Program.cs` | ≈150 | Likely human | Emra shqip, komente personale ("//mire eshte", shënim i detyrës në fund të `Rekurzioni.cs:92-93`), stil i thjeshtë. |
| `java3/*.cs`, `java4/Detyra.cs` | ≈480 | Likely human (jashtë fushës) | Nuk u lexuan në detaj; pa sinjale automatike. |

- Llogaritja: low = 0/1125; high = 496/1125 ≈ 44%.
- **Politika:** unspecified — raportohet pa penalizim; `needs_human_review` = false.

*"Ky është një vlerësim probabilistik nga sinjale indirekte, jo provë autorësie. Duhet konfirmuar nga një vlerësues njerëzor, p.sh. duke i kërkuar autorit të shpjegojë kodin."*

### 6.3 Ndarja e kontributeve

Projekt individual: `bleronbaftiu21` — 9 commit-e, +2143 / −713 rreshta (100%). Pa PR, pa issues, 1 degë.

## 7. Gjetjet

### Medium

**F-01 — Mungojnë testet e automatizuara**
- Kategoria: testing · Statusi: Confirmed
- Vendndodhja: i gjithë repo (`inventory.json`: 0 teste); demonstrimi te `Q.cs:107-121`
- Dëshmia: nuk ka projekt testesh (xUnit/NUnit/MSTest) as asert; rezultatet vetëm printohen.
- Ndikimi: korrektësia mbështetet vetëm në kontroll vizual të një shembulli; rastet kufitare (cikle, ID të panjohura, pyetje të paarritshme) nuk provohen. Brief-i sugjeron që testet të kontrollojnë gjatësinë dhe vlefshmërinë e rrugës.
- Rekomandimi: shtoni një projekt xUnit me teste për 5 problemet (shembulli i brief-it, një graf me cikël, ID të panjohura, pyetje e paarritshme).

### Low

**F-02 — README bosh dhe higjienë e dobët e repos**
- Kategoria: maintainability · Statusi: Confirmed
- Vendndodhja: `README.md:1`; `.vs/AlgoritmeAvancuara/v17/.wsuo`, `.vs/VSWorkspaceState.json`; `.gitignore` vetëm në `AlgoritmeTeAvancuara/`
- Dëshmia: README ka vetëm titullin; skedarët e IDE-së janë komituar sepse `.gitignore` nuk është në rrënjë; mesazhe commit si `//`, `detyra`, `java3`.
- Ndikimi: lexuesi nuk di ku është secila detyrë dhe si ekzekutohet.
- Rekomandimi: përshkruani dosjet/detyrat dhe `dotnet run`; zhvendosni `.gitignore` në rrënjë dhe hiqni `.vs/`; përdorni mesazhe commit përshkruese.

**F-03 — Zgjidhja e plotë në një skedar me emërtim mashtrues**
- Kategoria: structure · Statusi: Confirmed
- Vendndodhja: `java2/Questionnaire_Dependency_Assignment.cs:8-495`; `Program.cs:26-29`
- Dëshmia: të dhënat JSON, modelet, algoritmet dhe runner-i në një skedar; klasa quhet `Program` (njësoj si programi kryesor); dosja quhet `java2` ndonëse kodi është C#; `Program.cs` ekzekuton të gjitha ushtrimet çdo herë.
- Ndikimi: vështirëson leximin, ripërdorimin dhe testimin.
- Rekomandimi: ndani në `Models.cs`, `Analyzer.cs` dhe ngarkoni JSON nga skedar; emërtoni dosjet sipas temës.

### Info

**F-04 — P1/P2 dhe P5 eksplorojnë çdo rrugë (pa memo)**
- Kategoria: performance · Statusi: Potential (i nxjerrë, jo i matur)
- Vendndodhja: `Q.cs:259-294`, `:441-467`
- Dëshmia: `FindBestPath` nuk ruan rezultatin për pyetje; `CalculateQuestionProbabilities` viziton çdo rrugë (22 për shembullin).
- Ndikimi: kosto eksponenciale në grafe të mëdha; i parëndësishëm për të dhënat e brief-it. Memo është opsionale sipas brief-it (shih R8).
- Rekomandimi: cache për ID në P1/P2; renditje topologjike ose memo i kontributeve në P5.

**F-05 — Vargje magjike për tipet e pyetjeve**
- Kategoria: code_quality · Statusi: Confirmed
- Vendndodhja: `Q.cs:183`, `:197`, `:227`, `:379`, `:456`
- Rekomandimi: përdorni `enum` ose konstante.

## 8. Shënime sipas kategorive

- **Struktura & arkitektura (6):** ndarje e mirë logjike brenda skedarit (records → `Analyzer` → runner) dhe funksione ndihmëse të përbashkëta (`BuildIndex`, `NextSteps`, `FindBestPath` për P1 dhe P2), por gjithçka në një skedar dhe struktura e dosjeve e paqartë (F-03).
- **Siguria (N/A):** asnjë hyrje e jashtme, rrjet, skedar apo sekret; `possible_secrets` bosh.
- **Cilësia e kodit (8):** nullable i aktivizuar, `checked` kundër tejmbushjes (`Q.cs:361`), përjashtime të qarta për të dhëna të pavlefshme. Pa kod të vdekur në detyrë. Pikat e dobëta: vargje magjike (F-05), `Answers!` mbështetet në validimin paraprak.
- **Testimi (2):** asnjë test (F-01).
- **Mirëmbajtja & dokumentimi (4):** README bosh, komente minimale, `.vs/` i komituar (F-02). README nuk pretendon asgjë që kodi nuk e ka (nuk pretendon asgjë fare).
- **Gatishmëria për prodhim (N/A):** detyrë algoritmike kursi.
- **Performanca (7, e nxjerrë):** P3 O(n·m) me memo; P4 i kufizuar nga rregulli i thellësisë minimale; P1/P2/P5 proporcionale me numrin e rrugëve (F-04).
- **Varësitë (9):** vetëm .NET 8 BCL; `JsonNamingPolicy.SnakeCaseLower` ekziston në .NET 8.

## 9. Pyetje për mbrojtjen gojore

1. Pse `FindBestPath` kthen `null` kur `active.Add(id)` dështon dhe çfarë ndodh me degën përkatëse? Pse `active.Remove(id)` duhet në fund?
2. Në P4, pse rirekursoni kur pyetja arrihet me thellësi më të vogël? Jepni një shembull nga grafi ku kjo ndryshon rezultatin.
3. Pse `HasCycle` përdor tri gjendje (0/1/2) dhe jo thjesht një bashkësi "të vizituara"?
4. Pse `CheckComponent` është shkruar rekursivisht në vend të një `foreach`? A do të ishte në rregull sipas brief-it një cikël?
5. Si llogaritet `expected_position` për q8 = 4.5? Pse pjesëtohet `weightedPositions` me probabilitetin?
6. Çfarë bën `checked(...)` në `CountAllPossiblePaths` dhe kur do të hidhej përjashtim?
7. Si do të shtonit memoizim në P1 pa prishur mbrojtjen nga ciklet?
8. Çfarë kthen `FindReachableQuestions` për një pyetje të tipit `text` dhe pse?
9. Pse për P5 hidhni përjashtim kur ka cikël, ndërsa P3 kthen −1?

## 10. Kufizimet

- Kodi nuk u ekzekutua; rezultatet u verifikuan me gjurmim manual mbi shembullin e brief-it.
- Pa `GITHUB_TOKEN`: kërkimi i kodit në GitHub (kontrolli më i fortë për kopjim) u anashkalua; API GitHub pa autentikim.
- Vetëm një grup në këtë ekzekutim → nuk ka `similarity.json` dhe asnjë krahasim me grupe të tjera.
- `git log` për skedar nuk u ekzekutua (leja nuk u dha); datat e commit-eve vijnë nga `history.json`.
- Skedarët `java3` dhe `java4` (ushtrime të tjera) u lexuan vetëm pjesërisht, për krahasim stili.
- Lista e kërkesave u rindërtua manualisht sepse ndarja automatike ishte e gabuar.

## 11. Shtojca

- **Inventari:** C# 7 skedarë, 1125 rreshta burimi; 0 endpoint, 0 migrime, 0 teste, pa CI/Docker; docs: `README.md`.
- **Skedarët:** `Program.cs`, `java1/Funksione.cs`, `java1/Rekurzioni.cs`, `java2/Questionnaire_Dependency_Assignment.cs`, `java3/Detyra.cs`, `java3/Task2.cs`, `java4/Detyra.cs`, `.sln`, `.csproj`.
- **Të përjashtuara:** `.git/`, `.vs/` (skedarë IDE, `.wsuo` binar), `.sln`/`.csproj` (konfigurim).
- **Dëshmitë e përdorura:** `acquire.json`, `requirements.json`, `hints.json`, `inventory.json`, `history.json`, `ai-aa_bleronbaftiu_26.json`, `github-aa_bleronbaftiu_26.json`, `github_similar.json`, `brief.pdf` (tekst i nxjerrë).
- **Komandat:** vetëm lexim skedarësh (pipeline-i u ekzekutua më parë nga aplikacioni); asnjë ndryshim në repon e klonuar.
