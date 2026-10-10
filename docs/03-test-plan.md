# Parakh - Test Plan

Version 1.6, 10 Oct 2026 (matches design 1.6). Results go in docs/04-test-report.md.

## Levels

| Level | Tool | Network | Where |
|---|---|---|---|
| Unit | pytest | none | backend/tests/test_normalize.py, test_signals_*.py |
| Integration | pytest + replay fixtures | none | test_serp_client.py, test_runner.py |
| API | pytest + FastAPI TestClient, replay mode | none | test_api.py |
| End to end | manual, browser, live mode | SerpApi | checklist below |

Rule: a failing test is reported as failing. No test is edited to pass without
a written reason in the test report.

## Unit tests

| ID | Case | Expected |
|---|---|---|
| T-NORM-1 | "@Some.Store", "instagram.com/some.store/?hl=en", "SOME.STORE" | all -> "some.store" |
| T-NORM-2 | "https://www.Shop.in/products/x?ref=1" | "shop.in" |
| T-NORM-3 | price {"value": "Rs 1,299.00", "extracted_value": 1299} | 1299 INR |
| T-NORM-4 | price with USD currency | dropped |
| T-NORM-5 | accessibility caption "Photo by X on September 05, 2026. May be..." | date 2026-09-05 |
| T-PRICE-1 | 5 kept matches median 500, quote 2000 | bad, ratio 4.0 |
| T-PRICE-2 | median 500, quote 1000 | warn |
| T-PRICE-3 | median 500, quote 550 | good |
| T-PRICE-4 | 2 priced matches | info "Not enough priced matches", no ratio |
| T-PRICE-5 | product "boAt Rockerz 110": titles "boAt Rockerz 255 Pro" and "Rockerz neckband" dropped, "BoAt Rockerz 110 Wireless Neckband" kept | model-number rule and containment work |
| T-PRICE-7 | no product_name | info "Add the product name", no ratio |
| T-PRICE-8 | listing with condition "Refurbished" | dropped |
| T-PRICE-6 | quote 150, median 2000, one listing on brand domain | warn below-market |
| T-PRICE-9 | quote 150, median 2000, no brand or major-retailer listing | info "Much cheaper than other listings", never good |
| T-PRICE-10 | kept listings include the store's own domain | own listings dropped before counting |
| T-PRICE-11 | claimed_mrp 1999, median 500 | extra warn "The original price shown ... may be overstated"; none below 2.0x or without a median |
| T-PHOTO-1 | exact match on aliexpress | warn naming marketplace |
| T-PHOTO-2 | 0 exact matches | info "No exact copies found...", never good |
| T-PHOTO-3 | 4 unrelated domains | info with count 4 |
| T-COMP-1 | 2 relevant results with "not delivered" | bad |
| T-COMP-2 | result mentions "scam" but not the store key | not counted |
| T-COMP-3 | 0 relevant results | info, not good |
| T-COMP-4 | 3 relevant results with "received" and "genuine" | good |
| T-COMP-5 | recorded boat.nirvana forum results (boAt Nirvana product threads) | product threads are not counted as store mentions |
| T-COMP-6 | results on the store's own domain and instagram.com/<handle> | dropped before counting |
| T-ACC-1 | is_private true | warn |
| T-ACC-2 | 5 posts, oldest 20 days ago | warn very new |
| T-ACC-3 | bio link domain differs from given website | warn |
| T-ACC-4 | verified | good |
| T-ACC-5 | missing posts field | no crash, info only |
| T-ACC-6 | instagram_profile answers "Instagram profile not found" | account done with one warn; other errors stay unavailable |
| T-VERD-1 | one signal with data | Not enough data |
| T-VERD-2 | 1 bad + 2 warn | High risk (5) |
| T-VERD-3 | 2 warn | Be careful |
| T-VERD-4 | 3 good, 1 warn | No red flags found |
| T-VERD-5 | 10 not_delivered reports, all signals good | report points capped at 6, Be careful or higher |

## Integration tests

| ID | Case | Expected |
|---|---|---|
| T-SERP-1 | cache key with and without api_key | equal |
| T-SERP-2 | two identical calls in live mode (mocked HTTP) | 1 network call, 2 ledger rows, second cache_hit true |
| T-SERP-3 | replay mode, fixture missing | FixtureMissing raised, no network |
| T-SERP-4 | record mode writes fixture | file has no "api_key" substring |
| T-SERP-5 | cap reached | CapReached; cached call still succeeds |
| T-SERP-6 | Lens cache keyed by image sha | second check with same image skips upload |
| T-RUN-1 | demo 1 (boat.nirvana, boAt Rockerz 110, Rs 699) in replay | status done, verdict "No red flags found", price ratio near 1, prices from Google Lens or Google Shopping |
| T-RUN-2 | forums engine raises | complaints still uses google; status done |

## API tests

| ID | Case | Expected |
|---|---|---|
| T-API-1 | POST with neither handle nor website | 422 |
| T-API-2 | POST with 6 MB image | 413 |
| T-API-3 | POST with non-image file | 422 |
| T-API-4 | POST valid, then GET until done | done with evidence |
| T-API-5 | POST report, GET store | report listed, counts updated |
| T-API-6 | report note 300 chars | 422 |
| T-API-7 | GET unknown store | 404 |
| T-API-8 | 11 checks in one hour from one IP | 11th is 429 |

## End-to-end checklist (manual, before G4)

| ID | Step | Pass when |
|---|---|---|
| T-E2E-1 | Fresh clone, follow README | app running in under 5 commands |
| T-E2E-2 | Run demo check 1 in browser | signals appear one by one, verdict shown |
| T-E2E-3 | Run same check again | 0 live searches shown in footer |
| T-E2E-4 | Open every source link in one report | all open the cited page |
| T-E2E-5 | File a report, reload store page | report visible |
| T-E2E-6 | Phone width 360 px | no horizontal scroll, all text readable |
| T-E2E-7 | SERPAPI_MODE=replay, key removed | demo checks work |
| T-E2E-8 | grep repo for the key and for non-ASCII | no matches |
