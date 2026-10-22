# Raport auditimi — Airport_Website (UEB25_Gr3)

## 1. Koka

| Fusha | Vlera |
|---|---|
| Repozitori | https://github.com/bleronbaftiu21/Airport_Website (fork i `olsadomi/Airport_Website-Gr3`) |
| Dega | `main` |
| Commit | `6cca315f22b6b05f6c36a96a02253ed305857db2` (2025-05-25 23:39, "Update README.md") |
| Data e auditimit | 2026-10-22 |
| Auditori | Repo Auditor Pro |
| Burimi i kërkesave | `brief.docx` — "Programimi në ueb II – Udhëzimet për projekt grupor '25" (Faza 1: 13 prill, Faza 2: 17 maj) |
| Korpusi krahasues | Nuk u dha korpus me grupe të tjera; 3 kandidatë nga GitHub (sipas emrit): `jpatokal/openflights`, `everett7623/airport-recommendations-2026`, `FlyBitVIP/FlyBit-Airport-Address` |
| Politika e AI | `unspecified` (vlerësohet pa penalizim) |
| Afati i konfiguruar | `-` (brief-i përmend 17 maj 2025 për fazën 2) |

## 2. Përmbledhje ekzekutive

Projekti është një ueb-faqe në PHP/MySQL për Aeroportin e Prishtinës (6 faqe publike + panel admini), zhvilluar nga 5 studentë si vazhdim i projektit të Ueb I. Shumica e koncepteve të brief-it janë implementuar dhe janë të arritshme nga faqet: OOP me trashëgimi, getter/setter dhe destruktor, sesione me numërim vizitash, cookie për rekomandimin e lajmeve, CRUD me deklarata të përgatitura (prepared statements), AJAX dhe një Web API real (aviationstack) me cache. **Nota përfundimtare: 6.5 / 10.** Nota vetëm për kërkesat është **7.5 / 10**. Përputhshmëria me kërkesat e detyrueshme është 76.8%.

**Pikat e forta:**
1. Mbulim i gjerë i kërkesave të fazës 2: sesione, MySQL CRUD, AJAX, Web API, PHPMailer.
2. Mbrojtje e qëndrueshme nga SQL Injection me prepared statements dhe `password_hash`/`password_verify`.
3. Histori e shëndetshme ekipore: 282 commit-e jo-merge nga 5 anëtarë, me mesazhe përshkruese.

**Problemet kryesore:**
1. Faqet e adminit (`news-insert.php`, `delete-news.php`, `admin_sponsors.php`, `admin_contact.php` etj.) nuk kontrollojnë sesionin/rolin. Çdo vizitor mund të fshijë lajme, të shohë kontaktet dhe të ngarkojë skedarë pa kufizim.
2. Mungojnë disa nën-kërkesa eksplicite: `mail()`, `preg_replace`, kthimi me referencë, referencat ndërmjet anëtarëve të vargut, `fopen/fread/fwrite`, `sort/rsort/ksort/krsort`, fshirja e cookie-t dhe dërgimi nga email i zakonshëm (Gmail etj.).
3. Sekrete të shkruara direkt në kod: çelësi i API-së dhe fjalëkalimi SMTP (në 4 skedarë).

**Flamuj integriteti:**
- Nuk u gjet kopjim. Ngjashmëria me `openflights` është vetëm strukturë boilerplate HTML.
- Vlerësimi i AI-së është i ulët (0–10%, besueshmëri e ulët).
- Gjithë puna e fazës 2 është bërë me commit më 20–25 maj 2025, pas datës 17 maj në brief. Kjo duhet verifikuar.

## 3. Tabela e vlerësimit

**Nota vetëm për kërkesat: 7.5 / 10** (detyrueshme 76.8%, opsionale 100%)

| Kategoria | Pesha | Nota (1–10) | Arsyetimi |
|---|---|---|---|
| Përputhshmëria me kërkesat | 70% | 7.5 | 26 Met, 11 Partially, 4 Not met nga 41 të detyrueshme; të dyja opsionalet Met |
| Cilësia e kodit | 7% | 5 | Gabime funksionale (kolonë e gabuar te sponsorët, `$numberCount` i papërcaktuar, `id`/`request_id`), kod i dyfishuar dhe kod i vdekur |
| Struktura & arkitektura | 5% | 5 | Rrënjë e sheshtë me ~50 skedarë PHP, klasa brenda shablloneve, rrugë absolute `/UEB25_GR3/`; pak ndarje te `helpers/`, `api/`, `includes/` |
| Siguria | 5% | 3 | Prepared statements kudo (+), por mungon autorizimi te endpoint-et e adminit, ngarkim skedarësh pa kufizim, XSS i ruajtur dhe sekrete në kod |
| Testimi | 5% | 3 | Asnjë test i automatizuar; vetëm `test_helpers.php` (skript manual me echo). Brief-i nuk kërkon teste |
| Mirëmbajtja & dokumentimi | 4% | 5 | README përshkruan funksionalitetet dhe ndarjen e punës; mungojnë udhëzimet për instalim dhe DB |
| Gatishmëria për prodhim | 2% | 4 | Projekt kursi: `root` pa fjalëkalim, logje dhe cache të commit-uara, `display_errors=1` në një endpoint |
| Performanca | 1% | 6 | Cache 1 orë për API-në (+); `getFlightsWithCache('arrivals')` thirret dy herë; lajmet ngarkohen pa faqosje (e nxjerrë nga kodi, jo e matur) |
| Varësitë | 1% | 4 | PHPMailer i përfshirë dy herë (`PHPMailer-master/` + `vendor/`); 3 versione jQuery |

- **Nota e ponderuar:** 6.53 → **6.5**
- **Kufizim (cap) i aplikuar:** asnjë. Kufizimi për sekret/cenueshmëri kritike vlen vetëm për projekte të orientuara drejt prodhimit, ndërsa ky është projekt kursi. Përputhshmëria e detyrueshme është mbi 40%.
- **Nota përfundimtare:** **6.5 / 10**
- **Besueshmëria:** Medium. Analiza është vetëm statike: kodi nuk u ekzekutua, nuk pati korpus me grupe të tjera dhe kërkimi i kodit në GitHub u anashkalua pa token.

## 4. Përshkrimi i projektit

- **Qëllimi:** faqe informative e Aeroportit Ndërkombëtar të Prishtinës: Ballina, Fluturime, Shërbimet, Lajme, Rreth Nesh, Kontakt. Ka edhe regjistrim/kyçje, rezervim parkingu me email dhe panel superadmini.
- **Stack-u:** PHP procedural + klasa inline, MySQL (mysqli), jQuery/JS vanilla, CSS, PHPMailer (SMTP te Ethereal), API-ja aviationstack.
- **Pikat hyrëse:**
  - Publike: `index.php`, `flights.php`, `services.php`, `news.php`, `post-details.php`, `about_us.php`, `contact.php`, `login.php`, `signup.php`, `parkingReservation.php`.
  - Admin: `admin_dashboard.php`, i cili ngarkon me `fetch` këto faqe: `news-admin.php`, `admin_contact.php`, `admin_newsletter.php`, `admin_rental_requests.php`, `admin_sponsors.php`.
  - Endpoint-e AJAX/POST: `process_contact.php`, `process_signup.php`, `process-newsletter.php`, `process_rental_requests.php`, `parkingReservationAJAX.php`, `helpers/play_audio.php`.
- **Arkitektura:**
  ```
  Shfletuesi ──(HTML/jQuery .load nav.php/footer.php)──> faqet PHP
       │ AJAX (fetch/$.ajax)
       ▼
  process_*.php ──> db.php (mysqli, root@localhost/airport) ──> MySQL
  flights.php ──> helpers/cache_helpers.php ──> api/flight_api.php ──> aviationstack (HTTP)
  *_sender.php ──> PHPMailer ──> smtp.ethereal.email
  ```
- **Kufijtë e besimit:** vizitori anonim ↔ endpoint-et PHP. Kontrolli i rolit `admin` bëhet vetëm te `admin_dashboard.php`, `news-admin.php` dhe `edit-news.php`.
- **Ruajtja e të dhënave:** MySQL `airport`, me tabelat `users`, `news`, `contacts`, `newsletter_subscribers`, `rental_requests`, `sponsors` (krijohen nga skriptet `create_*_table.php`). Skedarët ruhen në `fotot/`, `Photos/`, `uploads/`, `cache/` dhe `logs/`.
- **Integrimet:** aviationstack (çelësi i shkruar në kod), Ethereal SMTP, CDN për jQuery/FontAwesome/Swiper, Google Maps iframe.
- **Build/Deploy:** asnjë; projekti ekzekutohet nën XAMPP te `/UEB25_GR3/`.
- **Teste/CI:** asnjë.

## 5. Përputhshmëria me kërkesat

Parser-i automatik nuk nxori asnjë kërkesë (`items: []`). Lista u ndërtua me dorë nga teksti i brief-it. Të gjitha pikat janë të detyrueshme, përveç atyre që brief-i i shënon "Opsionale".

| ID | Kërkesa | E detyrueshme | Statusi | Dëshmia | Shënime |
|---|---|---|---|---|---|
| R1 | Variablat, qasja, `var_dump()`, funksionet, funksionet e string-ut, konstantet, operatorët | Po | Partially met | `includes/config.php:3-13` (define), `news.php:211` (substr), `news.php:253` (ucfirst), `services.php:86` (funksion), `flights.php:3` (global) | Nuk u gjet `var_dump()` |
| R2 | Kushtëzimet (if..else, switch) | Po | Met | `services.php:127-145`, `news.php:218-235`, `flights.php:108-113` | |
| R3 | Vargjet numerike, asociative dhe shumëdimensionale | Po | Met | `about_us.php:4-12`, `helpers/flight_helpers.php:39-46`, `flights.php:34-51` | Vargu `$airlines` te about_us nuk përdoret më tej |
| R4 | Sortimet `sort, rsort, asort, ksort, arsort, krsort` | Po | Partially met | `news.php:161-183` (asort/arsort), `flights.php:200,223`, `post-details.php:97` (usort) | Mungojnë `sort`, `rsort`, `ksort`, `krsort` |
| R5 | Variablat globale të PHP-së | Po | Met | `about_us.php:2` ($GLOBALS), `$_SERVER`, `$_SESSION`, `$_COOKIE` (`post-details.php:12`), `$_FILES` | |
| R6 | Klasa me veti dhe metoda | Po | Met | `news.php:93-197` (Post, PostManager), `index.php:34-54`, `services.php:332-393` | |
| R7 | Konstruktorët (destruktorët) | Po | Met | `services.php:338` (__construct), `services.php:375` (__destruct) | |
| R8 | Atributet e klasës me Get dhe Set | Po | Met | `services.php:345-373` | |
| R9 | Modifikatorët public, private, protected | Po | Partially met | `news.php:95-101` (private), `services.php:338` (public) | `protected` nuk përdoret askund |
| R10 | Trashëgimia | Po | Met | `services.php:381` (CarRental extends Rentals), `process_contact.php:5` | |
| R11 | RegEx për validim/kontroll para dërgimit në server | Po | Met | `process_signup.php:23-61`, `process_contact.php:21-35` | |
| R12 | Validime me RegEx për email, data dhe vlera numerike | Po | Partially met | Email: `about_us.php:17`; numerike: `process_contact.php:33`, `process_signup.php:61` | Mungon RegEx për datë. Dega `about_us.php:14-22` nuk arrihet, sepse forma dërgohet me AJAX te `process-newsletter.php`, i cili përdor `filter_var` |
| R13 | Manipulime me numra me RegEx (ndarje, "-" në mes) | Po | Partially met | `process_contact.php:55-56` (preg_match_all për shifrat) | Rezultati nuk kthehet; `contact.php:97` përdor `$numberCount` të papërcaktuar. Nuk ka ndarje/formatim me "-" |
| R14 | RegEx për rregullimin e përmbajtjes së string-ut | Po | Not met | — | U kërkua `preg_replace`/`preg_split`: 0 rezultate në kodin e projektit |
| R15 | Faza 1: struktura me menu dhe faqe, të dhëna dummy | Po | Met | `nav.php:25-31` (6 faqe), `index.php:56-60`, `services.php:395-399` | |
| R16 | Cookies: krijimi, fshirja, ruajtja në varg | Po | Partially met | `post-details.php:12-20` (varg JSON në cookie, setcookie) | Nuk ka fshirje cookie (setcookie me kohë të kaluar) |
| R17 | Ndryshimi i përmbajtjes sipas cookie-t | Po | Met | `post-details.php:97-103` ("Lajme tjera" renditen sipas shikimeve në cookie) | Ndryshon përmbajtjen, jo background/foto |
| R18 | SESSIONS: krijimi, ruajtja dhe leximi i vlerave | Po | Met | `login.php:2,31-33`, `admin_dashboard.php:2-9`, `nav.php:10-16` | |
| R19 | Sesione për numërim (vizita) | Po | Met | `services.php:85-105` | |
| R20 | Funksion brenda sesionit | Po | Met | `services.php:86-95` (`visitsCounter(&$_SESSION[...])`) | |
| R21 | Manipulimi i sesioneve (ruajtje, ndryshim, fshirje) | Po | Met | `services.php:95-98` (unset në 50), `logout.php:3-4` | |
| R22 | Kodi PHP për koneksion me DB | Po | Met | `db.php:3-12` | |
| R23 | Krijimi i tabelave përmes PHP-së | Po | Met | `create_users_table.php:4`, `create_news_table.php:13`, `create_contact_table.php:3`, `create_newsletter_subscribers_table.php:13`, `create_rental_requests_table.php:6` | `create_sponsors_table.php:10` fut te kolona `sponsor_name`, që nuk ekziston (F-06) |
| R24 | Insertimi, fshirja, update-imi nga PHP | Po | Met | `news-insert.php:17`, `delete-news.php:7`, `edit-news.php:26-31`, `admin_sponsors.php:25,39` | |
| R25 | (Opsionale) Lidhja me DB përmes skripte të jashtme | Jo | Met | `db.php` i përfshirë me `require` në shumë faqe (p.sh. `news.php:60`) | |
| R26 | Përcjellja me referencë / funksione me referencë | Po | Met | `services.php:86` (`function visitsCounter(&$visits)`), `email_sender.php:12` (`global $conn`) | |
| R27 | Referencat ndërmjet anëtarëve të vargut | Po | Not met | — | U kërkua `=&` / `= &$`: 0 rezultate |
| R28 | Kthimi përmes referencës (p.sh. qasje në variablat globale) | Po | Not met | — | U kërkua `function &`: 0 rezultate |
| R29 | Largimi i referencës / `unset()` | Po | Partially met | `services.php:98` (`unset($_SESSION[...])`) | `unset()` përdoret, por jo për të larguar një referencë |
| R30 | Mbrojtja nga SQL Injection (demonstrim) | Po | Met | `login.php:21-23`, `process_signup.php:68-77`, `process_contact.php:58-60`, `post-details.php:22-26` | Të gjitha query-t me input përdorin prepared statements |
| R31 | Funksionet për fajlla: include, require, fopen, fclose, filesize, fread, fwrite | Po | Partially met | include/require kudo; `helpers/cache_helpers.php:28,56` (file_get/put_contents) | Mungojnë `fopen`, `fread`, `fwrite`, `fclose`, `filesize` |
| R32 | Funksion error_handler me parametrat (errno, errstr, errfile, errline…) | Po | Met | `helpers/error_handlers.php:4,51`, regjistruar te `includes/config.php:15-18` | Pa `errcontext` (hequr në PHP 8). Aktiv vetëm te `flights.php` |
| R33 | Gabime të definuara në mënyrë custom, të paraqitura në shqip | Po | Partially met | `process_contact.php:5,52,71-73` + `contact.php:285-290` | Klasa e gabimit shfaq mesazhe në shqip, por error_handler shkruan tipet në anglisht dhe vetëm në log |
| R34 | Përjashtimet me try, catch, throw | Po | Met | `process_contact.php:9-79`, `api/flight_api.php:17-57`, `helpers/cache_helpers.php` | |
| R35 | Funksioni `mail()` me të gjithë parametrat | Po | Not met | — | `mail(` nuk gjendet; përdoret vetëm PHPMailer |
| R36 | Dërgimi i email-eve përmes një forme standarde | Po | Met | `reply.php:10-43` + `reply_sender.php:9-36`, `admin_newsletter.php:38` → `send_newsletter.php` | |
| R37 | (ME RËNDËSI) Dërgimi nga email i zakonshëm (gmail, yahoo, hotmail) | Po | Partially met | `email_sender.php:17-23` (SMTP) | Konfiguruar te `smtp.ethereal.email`, një kuti testimi ku email-et nuk dorëzohen realisht |
| R38 | (Opsionale) `FILTER_SANITIZE` për mbrojtje | Jo | Met | `reply.php:5,11-13`, `reply_rental.php:6,25-27` | |
| R39 | AJAX për lexim/update nga një skriptë PHP | Po | Met | `contact.php:269-304` → `process_contact.php`; `script/parkingReservation.js:147` → `parkingReservationAJAX.php` | |
| R40 | AJAX për lexim/update nga DB | Po | Met | `signup.php:76` (INSERT), `about_us.php:320` → `process-newsletter.php:21`; `admin_dashboard.php:50` (lexim nga DB) | |
| R41 | Të paktën një Web API | Po | Met | `api/flight_api.php:6-48`, `flights.php:20-27` | Me cache (`helpers/cache_helpers.php:68-89`) |
| R42 | Grup me 4–5 studentë | Po | Met | `README.md:4-9`, `history.json` (5 autorë) | |
| R43 | Dokumentimi bazuar në kërkesat specifike | Po | Partially met | `README.md:27-72` | Përshkruan funksionalitetet, por nuk i lidh me kërkesat dhe nuk ka udhëzime instalimi/DB |

- **Të detyrueshme (41):**
  - Met 26 · Partially 11 · Not met 4 · Cannot verify 0
  - Përputhshmëria: (26 + 0.5×11) / 41 = **76.8%**
- **Opsionale (2):** Met 2 → **100%**

## 6. Integriteti

### 6.1 Origjinaliteti

**Metoda:**
- Gjurmë (fingerprints) të normalizuara (`similarity.json`, k=12) kundrejt 3 kandidatëve nga GitHub, të gjetur sipas emrit.
- Kandidatët u hapën dhe u krahasuan me dorë.
- U analizua historia e git-it dhe u kërkuan koka licencash dhe identifikues të huaj.
- Nuk pati korpus me grupe të tjera, prandaj kërkimi i kodit në GitHub nuk u bë (pa `GITHUB_TOKEN`).

Ngjashmëria e përgjithshme me `jpatokal/openflights` është 7%. Me dy kandidatët e tjerë është 0–2%.

| Skedari i projektit | Skedari tjetër | Containment | Rreshtat | Vendimi |
|---|---|---|---|---|
| `footer.php` | `openflights/test/server/fixtures/fm-standard.html` | 0.633 | 2–39 | Expected/boilerplate similarity |
| `footer.php` | `openflights/test/server/fixtures/fm-kilometer.html` | 0.600 | 4–39 | Expected/boilerplate similarity |
| `nav.php` | `openflights/test/server/fixtures/fm-newairlines.html` | 0.553 | 2–7, 19–41 | Expected/boilerplate similarity |
| `nav.php` | `openflights/html/settings.php` | 0.383 | 2–41 | Expected/boilerplate similarity |
| `parkingReservation.php` | `openflights/index.php` | 0.284 | 2–84 | Expected/boilerplate similarity |

**Pse u hodh poshtë ngjashmëria me openflights:**
- Përputhjet janë mbi skedarë të vegjël (30–81 gjurmë) dhe përbëhen nga struktura HTML e njëjtë pas normalizimit: `<!DOCTYPE>`, `<meta>`, `<link rel=stylesheet href=…>` dhe lista `<a href=…>…</a>`.
- Përmbajtja ndryshon plotësisht. `fm-standard.html` është faqe gjermane e "FlightMemory" (HTML 4.01, ISO-8859-1, menu HOME/FLIGHTDATA/STATISTICS). `nav.php`/`footer.php` janë në shqip me lidhje te faqet e projektit.
- `openflights` është krijuar më 2015-06-05, ndërsa commit-i i parë i projektit është 2024-12-09. Edhe pse kandidati është më i vjetër, nuk ka logjikë apo tekst të përbashkët. **Nuk ka kopjim.**

**Sinjalet nga historia e git-it:**
- 449 commit-e (282 jo-merge) gjatë 36 ditëve aktive, 2024-12-09 → 2025-05-25, nga 5 persona pas bashkimit të 8 identiteteve. Të gjithë përputhen me anëtarët në README.
- Repo-ja është **fork** i `olsadomi/Airport_Website-Gr3`, repo-s origjinale të ekipit (fork-u u krijua më 2025-06-21). Kjo është e pritshme.
- Faza 2 fillon me commit-in `c22608f` (2025-05-20, "FAZA 2 BEGINS HERE"). Të gjitha commit-et e fazës 2 janë më 20–25 maj 2025, ndërsa brief-i jep **17 maj** si datë dorëzimi. Shih F-05.
- `last_7_days_share` = 51%. Shumë nga këto rreshta janë PHPMailer i përfshirë: `700d4d0` me 12 061 rreshta (composer) dhe `3302972` me 10 844 rreshta / 78 skedarë.
- Shpërndarja e punës është iterative (shumë commit-e të vogla nga të gjithë), jo një "dump" i vetëm.

**Kod i jashtëm:** PHPMailer (`PHPMailer-master/` me `LICENSE`, plus `vendor/phpmailer/phpmailer/` me `LICENSE`) është bibliotekë e atribuar (**Attributed reuse**) dhe përjashtohet nga llogaritja. Nuk u gjetën koka licencash të huaja, emra të huaj projektesh apo URL tutorialesh në kodin e grupit.

**Origjinaliteti i përgjithshëm: ~100%** e rreshtave të kodit të grupit. Rreth 9 780 rreshta (PHP 4 640 në 49 skedarë, JS 872, CSS ~4 256, SQL 14) nuk kanë rajone të kopjuara të konfirmuara apo të dyshuara. PHPMailer përjashtohet.

### 6.2 Vlerësimi i asistencës nga AI

- **Vlerësimi:** **0–10%** · **Besueshmëria: Low**
- `ai-*.json`: 0 skedarë me sinjale të forta. Sinjalet mesatare janë vetëm te PHPMailer (dokumentim i bibliotekës, jo i grupit) dhe te `README.md` (6 emoji ✅).

| Komponenti | Rreshta | Klasifikimi | Sinjalet |
|---|---|---|---|
| `helpers/flight_helpers.php`, `helpers/cache_helpers.php`, `helpers/error_handlers.php`, `api/flight_api.php` | 364 | Mixed/uncertain | `try/catch` + `error_log` uniform edhe rreth operacioneve trivial (p.sh. lookup në varg te `flight_helpers.php:38-57`), stil ndryshe nga pjesa tjetër. Gjithsesi ka gjurmë njerëzore: `}{}` te `flight_api.php:58`, debug-u `path_debug.log`, kod i dyfishuar te `error_handlers.php:53-59` |
| `process_signup.php`, `signup.php` | 208 | Mixed/uncertain | Validime shumë të rregullta, "(e.g., !@#$%^&*)" në mesazh shqip, `async/await` me template |
| `README.md` (pjesa e fazës 2) | ~50 | Mixed/uncertain | Emoji ✅ dhe seksione gjenerike "Rezultati" |
| Faqet kryesore (`index.php`, `news.php`, `services.php`, `flights.php`, `contact.php`, `about_us.php`), admin, sender-at, JS | ~4 900 | Likely human | Komente në shqip, emërtim i përzier shqip/anglisht, gabime tipike studentore (`$numberCount`, `sponsor_name`, `qmimi = qmimi`), kod i komentuar, iteracione të dukshme në commit-e |

- **Llogaritja:** Likely AI = 0 rreshta → kufiri i poshtëm 0%; Mixed ≈ 572 nga ~5 500 rreshta PHP+JS → kufiri i sipërm ≈ 10%.
- **Politika:** `unspecified`. Nuk ka penalizim. Nuk ka deklarim të përdorimit të AI-së në README.
- **Needs human review:** jo.

*"Ky është një vlerësim probabilistik nga sinjale indirekte, jo provë e autorësisë. Duhet konfirmuar nga një vlerësues njerëzor, p.sh. duke i kërkuar autorit të shpjegojë kodin."*

### 6.3 Ndarja e kontributeve

| Autori | Commit-e | Rreshta + | Rreshta − | Pjesa e shtuar | Fokusi (README + commit-e) |
|---|---|---|---|---|---|
| oltikrasniqi21 (Olti Krasniqi) | 38 | 15 580 | 2 823 | 43.2%* | Ballina, Navbar, rezervimi i parkingut + email, sponsorët |
| Olsa Domi | 121 | 6 832 | 2 902 | 18.9% | Shërbimet, Kontakti, signup, sesionet, reply me PHPMailer, rental requests |
| Valmir Mustafa | 39 | 5 630 | 3 856 | 15.6% | Fluturimet, Web API, cache, error handler |
| bleronbaftiu21 (Bleron Baftiu) | 45 | 4 931 | 3 559 | 13.7% | Lajmet, post-details, cookie, edit/delete i lajmeve |
| Rreze Ejupi | 38 | 3 108 | 1 089 | 8.6% | Rreth Nesh, Footer, login, newsletter, dashboard |

\* Pjesa e oltikrasniqi21 është e fryrë nga commit-i `3302972` (10 844 rreshta / 78 skedarë, kryesisht kopja e `PHPMailer-master/`). Pa të, kontributet janë më të balancuara. Squash-et dhe programimi në çift i shtrembërojnë këto shifra.

## 7. Gjetjet

### Critical

**F-01 — Ngarkim skedarësh pa kufizim tipi, pa autentifikim (mundësi ekzekutimi kodi)**
- **Kategoria:** security · **Statusi:** Potential
- **Vendndodhja:** `news-insert.php:12-16`, `admin_sponsors.php:19-24`, `edit-news.php:18-21`
- **Dëshmia:** Emri origjinal i skedarit (`basename($_FILES[...]['name'])`) ruhet direkt në `fotot/`, `Photos/` ose `uploads/`. Nuk kontrollohet as prapashtesa, as MIME-tipi. `news-insert.php` dhe `admin_sponsors.php` nuk kërkojnë sesion admini (F-02).
- **Ndikimi:** Një vizitor anonim mund të ngarkojë `x.php` në një dosje publike. Nën XAMPP/Apache, skedari ekzekutohet. Statusi është Potential sepse varet nga konfigurimi i serverit, dhe kodi nuk u ekzekutua.
- **Rekomandimi:** Lejo vetëm `jpg/png/webp` (kontrollo `finfo_file` + prapashtesën), gjenero emër të rastësishëm dhe ndalo ekzekutimin e PHP-së në dosjet e ngarkimit.

### High

**F-02 — Faqet dhe veprimet e adminit pa kontroll autorizimi**
- **Kategoria:** security · **Statusi:** Confirmed
- **Vendndodhja:** `delete-news.php:4-12`, `news-insert.php:3-6`, `admin_sponsors.php:11-48`, `admin_contact.php:1-5`, `admin_newsletter.php:1-5`, `send_newsletter.php:5`, `admin_rental_requests.php:1-5`, `reply.php:1-20`, `reply_rental.php:1-43`
- **Dëshmia:**
  - Vetëm `admin_dashboard.php:4`, `news-admin.php:5` dhe `edit-news.php:5` kontrollojnë `$_SESSION['user_role'] === 'admin'`.
  - `delete-news.php?id=N` fshin lajmin me GET, pa sesion.
  - `news-insert.php:6` përdor `?? 1`, pra lajmi i atribuohet përdoruesit 1 kur nuk ka sesion.
- **Ndikimi:** Çdo vizitor mund të fshijë/shtojë lajme dhe sponsorë, të lexojë të dhënat personale të kontakteve (emër, email, telefon, mesazh) dhe të dërgojë email/newsletter në emër të aeroportit.
- **Rekomandimi:** Krijo `require_admin.php` (session_start + kontroll roli) dhe përfshije në krye të çdo skedari admin/veprimi. Fshirjen bëje me POST + token CSRF.

### Medium

**F-03 — Sekrete të shkruara në kod**
- **Kategoria:** security · **Statusi:** Confirmed
- **Vendndodhja:** `includes/config.php:3` (çelësi aviationstack `ef21…fcb`), `email_sender.php:20-21`, `reply_sender.php:17-18`, `reply_sender_rental.php:16-17`, `sendNewsletter.php:16-17` (fjalëkalimi SMTP `Re2j…`), `create_superadmin.php:14-15` (fjalëkalimi i superadminit)
- **Dëshmia:** vlerat janë literale në repo publike. Skaneri automatik (`possible_secrets: []`) nuk i kapi.
- **Ndikimi:** Çelësi i API-së mund të keqpërdoret. Llogaria Ethereal është vetëm për testim, kështu që rreziku për të është i ulët. Fjalëkalimi i superadminit është publik.
- **Rekomandimi:** Zhvendosi sekretet në `.env`/`config.local.php` jashtë git-it, rotullo çelësin dhe hiqe fjalëkalimin nga skripti.

**F-04 — XSS i ruajtur në listën e lajmeve dhe të sponsorëve**
- **Kategoria:** security · **Statusi:** Confirmed
- **Vendndodhja:** `news.php:251-256`, `index.php:144-145`, `post-details.php:60`, `edit-news.php:85`
- **Dëshmia:** `<?= $post->getTitle() ?>`, `getDescription()`, `getCategory()` dhe `$row->name` shfaqen pa `htmlspecialchars`.
- **Ndikimi:** Bashkë me F-02, një vizitor anonim mund të injektojë JavaScript që ekzekutohet te çdo lexues i faqes së lajmeve.
- **Rekomandimi:** Përdor `htmlspecialchars()` në çdo dalje, ashtu siç bëhet tashmë te `post-details.php:67-72`.

**F-05 — Puna e fazës 2 u bë pas datës së dorëzimit në brief**
- **Kategoria:** process · **Statusi:** Needs manual verification
- **Vendndodhja:** historia e git-it, commit-et `c22608f` (2025-05-20) … `6cca315` (2025-05-25)
- **Dëshmia:** Brief-i: "Faza 2: 17 maj dorëzimi, 20, 21 maj prezantimi". Commit-i i parë i fazës 2 është i datës 2025-05-20, ndërsa 51 commit-e janë më 25 maj (p.sh. `dcd1e64` "shtimi i cookie", `68f0314` "added sponsors_admin").
- **Ndikimi:** Nëse nuk pati shtyrje afati, pjesa më e madhe e funksionaliteteve të vlerësuara këtu (DB, cookie, email, admin) u shtua pas dorëzimit. Afati në konfigurim është "-", prandaj nota nuk u ndryshua.
- **Rekomandimi:** Verifiko afatin real me mësimdhënësit. Nëse duhet, vlerëso commit-in e fundit para afatit.

**F-06 — Gabime funksionale të identifikuara statikisht**
- **Kategoria:** correctness · **Statusi:** Confirmed
- **Vendndodhja dhe problemet:**
  - `create_sponsors_table.php:10` / `tabelat/tabelat.sql:7`: INSERT te kolona `sponsor_name`, ndërsa tabela ka `name`, kështu që insertimi dështon. `tabelat.sql:3` ka edhe `\` të tepërt.
  - `contact.php:97`: përdor `$numberCount`, i cili përcaktohet vetëm te `process_contact.php`.
  - `admin_rental_requests.php:40`: dërgon `request_id`, ndërsa `reply_rental.php:7` lexon `id`. Si pasojë, `replied_at` nuk përditësohet kurrë.
  - `parkingReservation.php:59,65,69`: emrat e fushave (`data-exit`, `time-entry`, `time-exit`) nuk përputhen me çelësat që lexohen (`data-dalje`, `koha-hyrje`, `koha-dalje`).
  - `flights.php:215`: rithirr i API-së anashkalon të dhënat fallback dhe sortimin e mëparshëm (rreshtat 200-211).
  - `api/flight_api.php:58`: `}{}` i tepërt.
  - `script/parkingReservation.js:118-134`: çdo klik në navbar e çkyç përdoruesin.
- **Ndikimi:** Disa veçori (sponsorët fillestarë, numri i shifrave në mesazh, statusi "replied") nuk funksionojnë siç pretendohet.
- **Rekomandimi:** Rregullo emrat e kolonave/fushave dhe hiq kodin e vdekur.

### Low

**F-07 — Kod dhe konfigurim i dyfishuar; varësi të dyfishta**
- **Kategoria:** maintainability · **Statusi:** Confirmed
- **Vendndodhja:**
  - Kredencialet e DB përsëriten në `login.php:4-9`, `process-newsletter.php:9-14`, `create_superadmin.php:2-7`, `create_news_table.php:2-7`, `create_users_table.php` dhe `db.php`.
  - Konfigurimi SMTP përsëritet 4 herë.
  - PHPMailer gjendet si te `PHPMailer-master/`, ashtu edhe te `vendor/`, por kodi përdor vetëm `PHPMailer-master`.
  - jQuery ngarkohet në 3.6.0, 3.6.4 dhe 3.7.1, disa herë në të njëjtën faqe (`services.php:294,532,574`).
- **Rekomandimi:** Një `db.php` dhe një `mailer.php` i vetëm; një version i vetëm i PHPMailer përmes `vendor/autoload.php`.

**F-08 — Artefakte debug dhe logje në repo**
- **Kategoria:** production-readiness · **Statusi:** Confirmed
- **Vendndodhja:**
  - `logs/*.log`, `logs/error_log_2025-05-25.txt`, `cache/*.cache`
  - `includes/config.php:21-22`: shkruan log në çdo ngarkim
  - `helpers/error_handlers.php:6-10`: rishkruan `path_debug.log` në çdo gabim
  - `process_rental_requests.php:3,7-8,12`: CORS `*`, `display_errors=1`, logon `$_POST`
  - `test_db.php`, `test_helpers.php`
- **Rekomandimi:** `.gitignore` për `logs/` dhe `cache/`, heqja e debug-ut dhe e skripteve të testimit nga rrënja publike.

**F-09 — README pa udhëzime instalimi**
- **Kategoria:** documentation · **Statusi:** Confirmed
- **Vendndodhja:** `README.md`
- **Dëshmia:** Pretendimet e README përputhen me kodin: cookie për lajmet, Web API për fluturimet, sesione për numërim dhe login, AJAX te format, superadmin. Nuk u gjetën pretendime të rreme. Mungojnë hapat për krijimin e DB-së `airport`, renditja e skripteve `create_*`, rruga `/UEB25_GR3/` dhe kredencialet demo të adminit.
- **Rekomandimi:** Shto seksionin "Instalimi". Pretendimi "Pagesa… vetëm për përdoruesit e kyçur" vlen vetëm për dërgimin e email-it (`parkingReservationAJAX.php:11`), jo për faqen.

## 8. Shënime sipas kategorive

- **Cilësia e kodit (5):** Logjika është e kuptueshme, me validime të mira në shqip (`process_signup.php`, `process_contact.php`). Megjithatë ka gabime konkrete (F-06), kod të komentuar (`services.php:72-81,311-328`), kod të vdekur (`about_us.php:14-22`, `helpers/play_audio.php`, i cili vetëm kthen "success") dhe dyfishime (F-07).
- **Struktura & arkitektura (5):** Ka ndarje të pjesshme (`helpers/`, `api/`, `includes/`, `script/`, `style/`), por shumica e skedarëve janë në rrënjë dhe përziejnë PHP, CSS dhe JS. Klasat janë brenda shablloneve (`news.php:93`, `services.php:332`). Rrugët janë absolute dhe të ngurta (`/UEB25_GR3/...`). Navbar-i ngarkohet me jQuery `.load`, prandaj `nav.php` hap një sesion të veçantë.
- **Siguria (3):** Pozitive janë prepared statements në çdo query me input, `password_hash`, `htmlspecialchars` në shumicën e tabelave të adminit dhe `FILTER_SANITIZE`. Negative janë F-01 deri në F-04. Projekti nuk ka CSRF, ndërsa `session_regenerate_id` mungon pas login-it.
- **Testimi (3):** Nuk ka teste të automatizuara apo CI. `test_helpers.php` printon rezultate pa asertime. Brief-i nuk kërkon teste, kështu që pesha mbetet e vogël.
- **Mirëmbajtja & dokumentimi (5):** README i qartë për ndarjen e punës. Mesazhet e commit-eve janë përshkruese, p.sh. "modified visitsCounter function by using reference parameter". Mungon dokumentimi i instalimit (F-09).
- **Gatishmëria për prodhim (4):** Konfigurimi është i ngurtë (`root` pa fjalëkalim, localhost), ka logje në repo (F-08) dhe asnjë faqe gabimi. Kjo është e pranueshme për projekt kursi; këshillat jepen pa penalizim të madh.
- **Performanca (6, e nxjerrë nga kodi):** Cache-i me skedar për API-në (1 orë) shmang thirrjet e tepërta. `flights.php:215` dhe ndoshta pjesa e departures thërrasin sërish `getFlightsWithCache`. `news.php:202` dhe `post-details.php:85` lexojnë të gjitha lajmet pa limit. Ndikimi është i papërfillshëm në këtë shkallë.
- **Varësitë (4):** PHPMailer është i dyfishuar dhe i commit-uar. `composer.json` ekziston, por nuk përdoret nga kodi. Ka shumë versione jQuery dhe CDN pa SRI, përveç FontAwesome.

## 9. Pyetje për mbrojtje

1. (Olsa) Te `services.php:86`, pse funksioni `visitsCounter` merr `&$visits`? Çfarë do të ndodhte me `$_SESSION['services_visits']` pa `&`?
2. (Bleron) Te `post-details.php:12-20`, si ruhet vargu `viewed_posts` në cookie dhe si ndikon te "Lajme tjera"? Si do ta fshinit këtë cookie?
3. (Valmir) Te `helpers/cache_helpers.php`, çfarë ndodh kur API-ja kthen gabim dhe cache-i ka skaduar? Pse `flights.php:215` e thërret sërish `getFlightsWithCache`?
4. (Valmir) Shpjegoni parametrat e `error_handler` te `helpers/error_handlers.php:4`. Pse mungon `errcontext`, dhe si do t'i shfaqnit gabimet në shqip te përdoruesi?
5. (Olti) Si e di `parkingReservationAJAX.php` që përdoruesi është i kyçur, kur ky skedar vetë nuk thërret `session_start()`?
6. (Rreze/Olti) Çfarë e pengon një vizitor pa llogari të hapë direkt `delete-news.php?id=3` apo `admin_contact.php`?
7. (Olsa) Te `process_contact.php:5`, pse krijuat `CustomValidationException`? Si i ndani gabimet me `implode('|')`/`explode`?
8. (Çdokush) Pse PHPMailer gjendet edhe te `PHPMailer-master/`, edhe te `vendor/`? Cilin përdor kodi?
9. (Çdokush) Brief-i jep 17 maj si datë dorëzimi për fazën 2, por commit-et e fazës 2 fillojnë më 20 maj. Cili ishte afati real?
10. Ku në projekt përdoret `mail()` i PHP-së, `preg_replace` apo kthimi me referencë (`function &f()`)?

## 10. Kufizimet

- Asnjë ekzekutim: kodi, DB-ja, API-ja dhe dërgimi i email-eve nuk u testuan. Të gjitha vendimet janë statike.
- Parser-i i kërkesave nuk nxori asnjë pikë; lista R1–R43 u ndërtua me dorë nga teksti i brief-it. Ndarja në pika atomike është gjykim i auditorit.
- Nuk pati korpus me projekte të grupeve të tjera të të njëjtit kurs, prandaj kopjimi ndërmjet grupeve nuk u kontrollua.
- Pa `GITHUB_TOKEN`: kërkimi i rreshtave karakteristikë në GitHub u anashkalua. Kandidatët u gjetën vetëm sipas emrit, dhe API-ja e GitHub ishte e kufizuar (pa review/PR; 0 PR, 1 degë).
- Afati në konfigurim ishte "-". Data 17 maj merret nga brief-i dhe nuk u aplikua në notë.
- Skanimi i sekreteve nga pipeline-i nuk i kapi kredencialet. Ato u gjetën me kërkim manual dhe mund të ketë të tjera në historinë e git-it (`git log -p` nuk u skanua plotësisht).
- Nuk u kontrollua asnjë bazë të dhënash për CVE të varësive.
- Commit-et e projektit janë nga llogari GitHub me emra të ngjashëm me përdoruesin që kërkoi auditimin (`bleronbaftiu21`). Auditori nuk e trajtoi këtë ndryshe; vlerësuesi njerëzor duhet ta ketë parasysh.

## 11. Shtojca

**Inventari (`inventory.json`):**
- PHP 115 skedarë / 12 910 rreshta, CSS 23 / 4 256, JS 9 / 872, SQL 1 / 14. Gjithsej 18 052 rreshta, duke përfshirë `PHPMailer-master/`.
- Kodi i grupit: 49 skedarë PHP (~4 640 rreshta), 9 JS, 23 CSS, 1 SQL.
- 0 framework, 0 migrime, 0 teste, 0 CI/Docker. `template_leftovers`: asnjë. `possible_secrets`: asnjë sipas skanerit (shih F-03 për ato të gjetura me dorë).

**Shtigjet e përjashtuara:**
- `PHPMailer-master/` dhe `vendor/`: bibliotekë e jashtme me LICENSE.
- `.git/` dhe `.vscode/`.
- `Photos/`, `fotot/`, `audio/`, `misc/` (media/PDF).
- `cache/` dhe `logs/` (artefakte runtime).

**Komandat e ekzekutuara (vetëm lexim):**
- Leximi i `acquire.json`, `requirements.json`, `hints.json`, `inventory.json`, `history.json`, `ai-Airport_Website.json`, `github-Airport_Website.json`, `github_similar.json`, `similarity.json`.
- `git -C <repo> -c core.hooksPath=/dev/null log --no-merges --since=2025-05-17 --shortstat`
- Kërkime me ripgrep (Grep) për: `class|extends|__construct|__destruct|protected`, `sort|asort|ksort|krsort|var_dump|define|switch|$GLOBALS`, `setcookie|$_COOKIE|fopen|fread|fwrite|mail(|FILTER_SANITIZE|&$|unset(|set_error_handler|throw|$_SESSION|CREATE TABLE|INSERT|UPDATE|DELETE`, `preg_replace|function &|=&`, `->Password|Username`.
- Leximi manual i rreth 45 skedarëve PHP/JS të projektit dhe i `openflights/test/server/fixtures/fm-standard.html` + `html/settings.php` për krahasim.
