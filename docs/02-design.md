# Parakh - Design

Version 1.0, 9 Oct 2026. Implements docs/01-requirements.md.

## 1. Architecture

```
Vue 3 SPA  --HTTP JSON-->  FastAPI  --> CheckRunner (background task)
                              |              |
                              |              +--> signals/*  (pure functions over normalized data)
                              |              +--> serp/client (cache -> ledger -> SerpApi)
                              v
                           SQLite (SQLAlchemy 2.0)
```

- One Python process. Checks run as FastAPI background tasks; the SPA polls.
- Engine calls inside one check run concurrently with httpx.AsyncClient.
- Signals are pure functions: normalized engine data in, evidence items out.
  They never call the network. This keeps them unit-testable from fixtures.
- In production the built SPA is served by FastAPI from `frontend/dist`.

## 2. Repository layout

```
parakh/
  backend/
    app/
      main.py            app factory, routers, static files
      config.py          pydantic-settings
      db.py              engine, session, create_all
      models.py          ORM tables
      schemas.py         request/response models
      normalize.py       handle, domain, price, text helpers
      serp/
        client.py        SerpClient: cache, ledger, cap, modes
        engines.py       one function per engine -> normalized dataclasses
        images.py        resize + Image API upload
      signals/
        price.py  photo.py  complaints.py  account.py  community.py
        verdict.py
      checks/
        runner.py        orchestrates one check
      api/
        checks.py  stores.py  reports.py  meta.py
      tools/
        record.py        record fixtures for demo inputs
    tests/
      fixtures/serp/     recorded responses, key stripped
      test_*.py
    pyproject.toml
  frontend/              Vite + Vue 3 + vue-router
  docs/
  README.md
  .env.example
```

## 3. SerpApi usage

All calls go through `SerpClient.search(engine, params, check_id)`.

| Signal | Engine | Key params | Fields used |
|---|---|---|---|
| Price | google_lens, type=all | url or image_id, country=in, hl=en, q=product_name (optional) | visual_matches[].title, link, source, price.extracted_value, price.currency, in_stock, condition, exact_matches |
| Photo | google_lens, type=exact_matches | url or image_id, country=in | exact_matches[] title, link, source |
| Complaints | google | q, gl=in, hl=en | organic_results[] title, link, snippet, date, source |
| Complaints | google_forums | q, gl=in, hl=en | organic_results[] title, link, snippet, date, source, displayed_meta |
| Account | instagram_profile | profile_id | profile_results: followers, following, is_private, is_verified, is_professional_account, biography, external_url, bio_links, posts[].accessibility_caption, posts[].shortcode |
| Website (S) | google | q=domain, gl=in | organic_results[] link |
| Shop (C) | google_maps | q, type=search | verify fields from a recorded fixture in M1 |

Image upload: `POST https://serpapi.com/image` multipart field `image` plus
`api_key`. Returns `image_id`, valid 10 minutes. Server converts any upload to
JPEG and downscales until it is at most 480 KB. Whether the upload counts as a
search is checked once in M1 using the account endpoint and written to the
README.

Searches per full check: Lens all (1) + Lens exact (1) + Instagram (1) + Google
(1) + Forums (1) = 5. Website footprint adds 1.

### Modes (env SERPAPI_MODE)

| Mode | Behaviour |
|---|---|
| live | cache -> network; writes cache |
| record | live, and also writes the response to tests/fixtures/serp/<cache_key>.json |
| replay | fixture file only; missing fixture raises FixtureMissing; no key needed |

### Cache key

`sha256(engine + "|" + canonical_json(params without api_key, no_cache, output))`.
For Lens with an uploaded image the `image_id` changes on every upload, so the
param is replaced by `image_sha256:<hex of JPEG bytes>` before hashing. The
upload itself is skipped when a Lens response for that sha is already cached.

Fixtures must never contain the key: the client deletes `api_key` from
`search_parameters` and scrubs `search_metadata` URLs before writing.

### Credit ledger and cap

Every call writes an `api_calls` row with `cache_hit`. Live calls today are
counted from this table. If the count reaches `DAILY_SEARCH_CAP` (default 40)
the client raises `CapReached`; the runner marks the affected signals
unavailable with reason "daily limit reached".

## 4. Data model

```
stores
  id PK, kind TEXT (instagram|website), key TEXT, display TEXT,
  created_at, last_checked_at
  UNIQUE(kind, key)

checks
  id TEXT PK (uuid4 hex), created_at, finished_at,
  instagram_store_id FK nullable, website_store_id FK nullable,
  product_name TEXT, quoted_price INTEGER (rupees) nullable,
  image_sha256 TEXT nullable, image_url TEXT nullable,
  status TEXT (running|done|failed),
  signal_status JSON  {"price":"done","photo":"unavailable",...},
  verdict TEXT nullable, risk_points INTEGER nullable,
  live_searches INTEGER, cached_searches INTEGER, duration_ms INTEGER

evidence
  id PK, check_id FK, signal TEXT, severity TEXT (good|info|warn|bad),
  finding TEXT, detail TEXT, sources JSON [{"title","url","engine"}],
  data JSON, position INTEGER

serp_cache
  key TEXT PK, engine TEXT, params JSON, response JSON, fetched_at

api_calls
  id PK, check_id nullable, engine TEXT, cache_key TEXT, cache_hit BOOL,
  ok BOOL, error TEXT nullable, created_at

reports
  id PK, store_id FK, outcome TEXT (delivered|not_delivered|differs|other),
  note TEXT (<=280), ip_hash TEXT, created_at
```

Store keys: Instagram handle lowercased without "@"; website registrable
domain lowercased without "www.".

## 5. REST API

All under `/api`. JSON. Errors: `{"error": {"code": "...", "message": "..."}}`.

| Method | Path | Body / query | Response |
|---|---|---|---|
| POST | /checks | multipart: instagram, website, product_name, quoted_price, image (file) or image_url | 202 `{"id": "..."}` |
| GET | /checks/{id} | | check with status, signal_status, verdict, evidence grouped by signal, stores, credit use |
| GET | /stores/{kind}/{key} | | store, last 20 checks (id, date, verdict), report counts by outcome, last 20 reports |
| POST | /stores/{kind}/{key}/reports | JSON: outcome, note | 201 report |
| GET | /meta/credits | | live searches today, cap, cache hit rate today, mode |
| GET | /meta/rules | | verdict rules as data, for the About page |
| GET | /health | | `{"ok": true}` |

Validation: quoted_price 1 to 10,000,000; product_name up to 120 chars; image
up to 5 MB and must decode with Pillow; image_url must be http(s). The server
never downloads image_url itself; it is passed to Lens as `url` (no SSRF path).

## 6. Signal rules

Constants live in `signals/rules.py` so tests and the About page read the same
values.

### 6.1 Price (FR-5, 6, 7)

1. Take Lens type=all `visual_matches` whose `price.currency` is Indian
   rupees ("Rs", "INR", or the rupee sign U+20B9) -> store as INR integer.
   `normalize.parse_currency` handles this; source files stay ASCII by
   writing the sign as the escape `\u20b9`.
2. Same-product filter. Keep a match if `exact_matches` is true, or if the
   token Jaccard similarity between normalized title and product_name is
   at least 0.35. Without product_name, keep exact-match items only.
3. Need n >= 3 kept items, else evidence info "Not enough priced matches".
4. ratio = quoted / median.
   - ratio >= 3.0 -> bad "Quoted price is Nx the median of N matching listings"
   - 1.8 <= ratio < 3.0 -> warn
   - ratio <= 0.4 and any kept listing is from a brand or major retailer
     domain -> warn "Far below other listings; check if genuine"
   - else -> good "Price is in line with N listings"
5. Always attach the 5 cheapest kept listings as sources.

### 6.2 Photo (FR-8)

From Lens type=exact_matches, drop results whose domain is the store's own
domain or instagram.com/<handle>. Group by domain.
- any domain in MARKETPLACES (aliexpress, alibaba, temu, dhgate, meesho,
  indiamart, shein) -> warn "Same photo appears on <marketplace>"
- else 3 or more other domains -> info "Photo is used on N other sites"
- else none -> good "No other site uses this exact photo"

### 6.3 Complaints (FR-9, 10)

Queries: google `"<key>" scam OR fraud OR fake OR "not delivered" OR refund`;
google_forums `"<key>"`.
A result counts as relevant if its title or snippet contains the store key
(or display name) after normalization. A relevant result is negative if it
contains a NEGATIVE term (scam, fraud, fake, not delivered, never received,
no refund, blocked me, cheated, duplicate) and positive if it contains a
POSITIVE term (received, genuine, legit, delivered on time, original) and no
negative term.
- negatives >= 2 -> bad; negatives == 1 -> warn
- negatives == 0 and positives >= 2 -> good
- no relevant results -> info "No public discussion found" (not good)

### 6.4 Account (FR-11, 12)

From instagram_profile. Post dates parsed from accessibility_caption with
`on (January|...|December) (\d{1,2}), (\d{4})`.
- is_private -> warn "Account is private"
- oldest visible post younger than 60 days and fewer than 12 visible posts ->
  warn "Very new activity"
- website given and bio link domain present and different -> warn
- followers >= 10,000 and visible posts < 6 -> info "Large following, few posts"
- is_verified -> good
- always one info item with the raw numbers and the profile link

### 6.5 Community (FR-19, 20)

Reports for the store(s) in the check. not_delivered and differs count as
negative, delivered as positive. Contributes to points (below); evidence item
lists the counts and links to the store page.

### 6.6 Verdict (FR-15, 16)

points = 3 x bad + 1 x warn - 1 x good (good capped at 3)
       + min(2 x negative_reports - positive_reports, 6) floored at 0
- signals with usable data < 2 -> "Not enough data"
- points >= 5 -> "High risk"
- points >= 2 -> "Be careful"
- else -> "No red flags found"

## 7. Check flow

1. POST validates, normalizes, upserts stores, saves image to memory,
   computes sha256, creates check (status running), schedules runner, returns
   id.
2. Runner: if image, ensure image_id (skip when Lens result is cached by sha).
   Gather engine calls concurrently with a 20 s timeout each. Each failure is
   caught per engine.
3. Run signal functions; write evidence rows and signal_status after each.
4. Compute verdict; set status done, durations, search counts.
5. GET /checks/{id} returns whatever is stored so far, so the SPA shows
   signals as they land.

## 8. Frontend

Routes: `/` check form, `/c/:id` report, `/s/:kind/:key` store page, `/about`.
Report page polls every 1.5 s until status is done or failed. Sections in fixed
order: verdict banner, price (listing table with links), photo (domains),
complaints (list with links and dates), account (numbers), community (counts
and report form). Footer shows searches used for this check and cache hits.
Plain CSS, mobile first, no UI framework.

## 9. Security and limits

- Key in `.env` only; `.env` gitignored; `.env.example` has placeholders.
- Per-IP rate limit in memory (NFR-7), keyed by salted IP hash.
- Reports: note stripped to plain text, 280 chars, rendered as text.
- CORS only for the Vite dev origin.
- Logs never print params dicts that contain api_key.

## 10. Traceability

| Requirement | Design section | Test IDs (docs/03-test-plan.md) |
|---|---|---|
| FR-1..4 | 5, 7 | T-API-1..4, T-NORM-1..5 |
| FR-5..7 | 6.1 | T-PRICE-1..6 |
| FR-8 | 6.2 | T-PHOTO-1..3 |
| FR-9, 10 | 6.3 | T-COMP-1..4 |
| FR-11, 12 | 6.4 | T-ACC-1..5 |
| FR-15, 16, 20 | 6.6 | T-VERD-1..5 |
| FR-17 | 7, 8 | T-E2E-2 |
| FR-18, 19 | 5 | T-API-5..7 |
| NFR-2, 3, 4, 5 | 3 | T-SERP-1..6 |
| NFR-6 | 7 | T-RUN-2 |
| NFR-7 | 9 | T-API-8 |
