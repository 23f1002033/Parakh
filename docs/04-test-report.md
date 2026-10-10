# Parakh - Test Report

Date: 10 Oct 2026. Test plan: docs/03-test-plan.md version 1.3. Design 1.5.

## Environment

| Item | Value |
|---|---|
| OS | macOS 14 (Darwin 23.6.0), Apple Silicon |
| Python | 3.12.11 (uv) |
| Backend libraries | FastAPI 0.143.0, SQLAlchemy 2.1.4, Pydantic 2.14.0, httpx 0.28.1 |
| Node.js | 24.7.0 |
| Frontend | Vue 3.5, vue-router 5.4, Vite 8.3 (`npm run build`: no warnings) |
| SerpApi mode for automated tests | none (mocked HTTP) and replay (recorded fixtures) |

## pytest result

Command: `cd backend && uv run pytest -q`. Result: **92 passed, 0 failed, 0
skipped**. One warning comes from a library (Starlette notes that its test
client uses httpx); it does not affect results.

| File | Tests | Passed |
|---|---|---|
| tests/test_api.py | 12 | 12 |
| tests/test_api_meta.py | 1 | 1 |
| tests/test_engines.py | 6 | 6 |
| tests/test_limits.py | 3 | 3 |
| tests/test_normalize.py | 6 | 6 |
| tests/test_record_tool.py | 1 | 1 |
| tests/test_runner.py | 6 | 6 |
| tests/test_serp_client.py | 13 | 13 |
| tests/test_signals_account.py | 7 | 7 |
| tests/test_signals_complaints.py | 8 | 8 |
| tests/test_signals_photo.py | 5 | 5 |
| tests/test_signals_price.py | 14 | 14 |
| tests/test_signals_verdict.py | 8 | 8 |
| tests/test_spa.py | 2 | 2 |
| **Total** | **92** | **92** |

## Results by test ID

### Unit

| ID | Test function | Result |
|---|---|---|
| T-NORM-1 | test_normalize.py::test_norm_1_instagram_handle | Pass |
| T-NORM-2 | test_normalize.py::test_norm_2_website_domain | Pass |
| T-NORM-3 | test_normalize.py::test_norm_3_inr_price | Pass |
| T-NORM-4 | test_normalize.py::test_norm_4_usd_dropped | Pass |
| T-NORM-5 | test_normalize.py::test_norm_5_caption_date | Pass |
| T-PRICE-1 | test_signals_price.py::test_price_1_bad_markup | Pass |
| T-PRICE-2 | test_signals_price.py::test_price_2_warn | Pass |
| T-PRICE-3 | test_signals_price.py::test_price_3_good | Pass |
| T-PRICE-4 | test_signals_price.py::test_price_4_not_enough | Pass |
| T-PRICE-5 | test_signals_price.py::test_price_5_containment_and_model_number | Pass |
| T-PRICE-6 | test_signals_price.py::test_price_6_far_below_with_brand_listing | Pass |
| T-PRICE-7 | test_signals_price.py::test_price_7_no_product_name | Pass |
| T-PRICE-8 | test_signals_price.py::test_price_8_refurbished_dropped | Pass |
| T-PRICE-9 | test_signals_price.py::test_price_9_far_below_without_brand_is_info_not_good | Pass |
| T-PHOTO-1 | test_signals_photo.py::test_photo_1_marketplace | Pass |
| T-PHOTO-2 | test_signals_photo.py::test_photo_2_no_matches_is_never_good | Pass |
| T-PHOTO-3 | test_signals_photo.py::test_photo_3_many_sites | Pass |
| T-COMP-1 | test_signals_complaints.py::test_comp_1_two_not_delivered_is_bad | Pass |
| T-COMP-2 | test_signals_complaints.py::test_comp_2_unrelated_scam_not_counted | Pass |
| T-COMP-3 | test_signals_complaints.py::test_comp_3_nothing_is_info_not_good | Pass |
| T-COMP-4 | test_signals_complaints.py::test_comp_4_positive_is_good | Pass |
| T-COMP-5 | test_signals_complaints.py::test_comp_5_boat_nirvana_product_threads_do_not_count | Pass (see note 1) |
| T-ACC-1 | test_signals_account.py::test_acc_1_private | Pass |
| T-ACC-2 | test_signals_account.py::test_acc_2_very_new | Pass |
| T-ACC-3 | test_signals_account.py::test_acc_3_bio_link_differs | Pass |
| T-ACC-4 | test_signals_account.py::test_acc_4_verified | Pass |
| T-ACC-5 | test_signals_account.py::test_acc_5_missing_posts_info_only | Pass |
| T-VERD-1 | test_signals_verdict.py::test_verd_1_one_signal | Pass |
| T-VERD-2 | test_signals_verdict.py::test_verd_2_high_risk | Pass |
| T-VERD-3 | test_signals_verdict.py::test_verd_3_careful | Pass |
| T-VERD-4 | test_signals_verdict.py::test_verd_4_clear | Pass |
| T-VERD-5 | test_signals_verdict.py::test_verd_5_reports_capped | Pass |

### Integration

| ID | Test function | Result |
|---|---|---|
| T-SERP-1 | test_serp_client.py::test_serp_1_cache_key_ignores_api_key | Pass |
| T-SERP-2 | test_serp_client.py::test_serp_2_second_identical_call_is_cached | Pass |
| T-SERP-3 | test_serp_client.py::test_serp_3_replay_missing_fixture | Pass |
| T-SERP-4 | test_serp_client.py::test_serp_4_record_writes_scrubbed_fixture | Pass |
| T-SERP-5 | test_serp_client.py::test_serp_5_cap_reached_but_cache_still_works | Pass |
| T-SERP-6 | test_serp_client.py::test_serp_6_lens_cache_keyed_by_image_sha | Pass |
| T-RUN-1 | test_runner.py::test_run_1_demo_in_replay | Pass (see note 2) |
| T-RUN-2 | test_runner.py::test_run_2_forums_failure_keeps_google | Pass |

### API

| ID | Test function | Result |
|---|---|---|
| T-API-1 | test_api.py::test_api_1_needs_handle_or_website | Pass |
| T-API-2 | test_api.py::test_api_2_image_too_large | Pass |
| T-API-3 | test_api.py::test_api_3_not_an_image | Pass |
| T-API-4 | test_api.py::test_api_4_post_then_get_done | Pass |
| T-API-5 | test_api.py::test_api_5_report_then_store_page | Pass |
| T-API-6 | test_api.py::test_api_6_long_note | Pass |
| T-API-7 | test_api.py::test_api_7_unknown_store | Pass |
| T-API-8 | test_api.py::test_api_8_check_rate_limit | Pass |

### Notes

1. T-COMP-5: 9 of the 10 recorded boat.nirvana forum threads (boAt Nirvana
   product threads) are not counted. One thread, "Wrong product recived", still
   counts: it is a complaint form whose "Seller Name" and "Website Name" fields
   match the store-context words "seller" and "website". The owner reviewed
   this and kept the rule as specified; the test asserts this exact outcome.
2. T-RUN-1 on demo 1 (boat.nirvana, boAt Rockerz 110, Rs 699): status done,
   verdict "No red flags found", prices from Google Lens, 6 of 30 INR listings
   kept, median Rs 824, ratio 0.85.

### Test changes with reasons

- test_record_tool: expected searches changed from 7 to 8 when google_shopping
  was added to the record tool (M2).
- test_signals_complaints::test_store_terms_variants: rewritten when the
  relevance rule changed in design 1.3 (M2 review).
- test_signals_price helpers: listings given distinct URLs when kept listings
  started to be deduplicated by URL (M3); the old helper gave every listing the
  same URL.

## Other automated checks (M4)

| Check | Result |
|---|---|
| ASCII only (backend, frontend/src, docs) | Pass, no matches |
| "scam" or "fraud" in frontend/src | Pass, no matches |
| Marketing words in code and docs | Pass, no matches |
| SerpApi key or "api_key" in fixtures | Pass, no matches |
| Headless screenshots at 1280 px and 360 px (docs/img) | Taken from demo 1 in replay; no horizontal scroll at 360 px |
| Error states (unknown check id, failed check, unavailable signals, server down on submit) | Checked in a headless browser and with the Vite proxy; all render a message |

## Manual end-to-end

To be filled by owner.

| ID | Step | Result | Notes |
|---|---|---|---|
| T-E2E-1 | Fresh clone, follow README | to be filled by owner | |
| T-E2E-2 | Run demo check 1 in browser | to be filled by owner | |
| T-E2E-3 | Run same check again | to be filled by owner | |
| T-E2E-4 | Open every source link in one report | to be filled by owner | |
| T-E2E-5 | File a report, reload store page | to be filled by owner | |
| T-E2E-6 | Phone width 360 px | to be filled by owner | |
| T-E2E-7 | SERPAPI_MODE=replay, key removed | to be filled by owner | |
| T-E2E-8 | grep repo for the key and for non-ASCII | to be filled by owner | |
