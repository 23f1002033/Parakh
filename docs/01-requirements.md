# Parakh - Software Requirements Specification

Version 1.0, 9 Oct 2026

## 1. Purpose

Small sellers on Instagram, WhatsApp and one-page websites take payment by UPI
before shipping. The buyer has no seller rating, no return policy they can
enforce, and no easy way to check the seller. Common problems:

- Dropshipping at large markup: a Rs 399 marketplace item sold as Rs 2,499.
- Stolen product photos: the store shows a brand's or another seller's images.
- Non-delivery: payment taken, nothing shipped, account blocks the buyer.
- New or bought-follower accounts with little real history.

Parakh takes what the buyer already has (handle or link, a product photo, the
quoted price) and returns an evidence report built from live search data.

## 2. Users

| User | Need |
|---|---|
| Buyer (primary) | A clear answer in under 30 seconds, with proof they can open |
| Buyer who already ordered | Report the outcome so the next buyer sees it |
| Judge / reviewer | Run it locally without spending credits (replay mode) |

Expected audience for the MVP: up to about 50 users and 100 checks per day.

## 3. Scope

In scope: Instagram stores and website stores selling physical products in India.
Out of scope: WhatsApp bots, browser extensions, payment integration, user
accounts, any automated contact with sellers.

## 4. Functional requirements

Priority uses MoSCoW: M = Must, S = Should, C = Could.

### Input

| ID | Requirement | P |
|---|---|---|
| FR-1 | User can submit a check with an Instagram handle or profile URL, a website URL, or both. At least one is required. | M |
| FR-2 | User can attach a product image (JPG, PNG, WebP, up to 5 MB) or paste an image URL. Optional. | M |
| FR-3 | User can enter the quoted price in INR and an optional product name. | M |
| FR-4 | Handles and URLs are normalized (strip @, query strings, trailing slashes, "www.", case) so the same store maps to one record. | M |

### Signals

Each signal produces zero or more evidence items. Every evidence item has a
severity (good, info, warn, bad), a one-line finding, and at least one source
link the user can open.

| ID | Requirement | P |
|---|---|---|
| FR-5 | Price check: find the same product in Google Lens results for India, report the lowest and median price of matched listings with links, and compare against the quoted price. | M |
| FR-6 | Price check flags a quote that is far above matched listings (markup) and a branded item quoted far below matched listings (possible counterfeit). | M |
| FR-7 | Price check makes no price claim when fewer than 3 matched listings with INR prices are found, and says so. | M |
| FR-8 | Photo check: report other websites that show an exact match of the product photo, grouped by domain, marking marketplaces and brand sites. | M |
| FR-9 | Complaint check: search Google and Google Forums for the store name together with complaint terms; count only results that mention the store; show each counted result with its link. | M |
| FR-10 | Complaint check reports "no public discussion found" as info, never as a positive signal. | M |
| FR-11 | Account check (Instagram): followers, following, private flag, verified flag, professional flag, bio link domain, number and date range of visible recent posts. | M |
| FR-12 | Account check flags: private account, very new activity (oldest visible post under 60 days), and bio link domain that differs from the website the user gave. | M |
| FR-13 | Website footprint: search Google for the domain and report whether it has any presence beyond its own pages. | S |
| FR-14 | Physical shop claim: if the user says the store claims a shop in a city, look it up in Google Maps and report rating and review count. | C |

### Verdict and history

| ID | Requirement | P |
|---|---|---|
| FR-15 | The report shows one of: "High risk", "Be careful", "No red flags found", "Not enough data". The rules are fixed, documented, and shown on an About page. | M |
| FR-16 | "Not enough data" is shown when fewer than 2 signals returned usable data. | M |
| FR-17 | The report shows progress per signal while the check runs (pending, done, unavailable). | M |
| FR-18 | Each store has a page listing past checks and community reports. | M |
| FR-19 | Any user can file an outcome report for a store: delivered, not delivered, product differs from photo, other; with an optional short note (max 280 chars). | M |
| FR-20 | Community reports count toward the verdict, capped so a few reports cannot decide it alone. | M |
| FR-21 | User can share a report by link. | S |
| FR-22 | An optional plain-language summary written by an LLM from the evidence items only. | C |

## 5. Non-functional requirements

| ID | Requirement | P |
|---|---|---|
| NFR-1 | A check completes in under 30 s at p95 with live SerpApi calls, under 2 s when fully cached. | M |
| NFR-2 | A check spends at most 6 SerpApi searches; repeated identical searches within the cache TTL (default 24 h) spend none. | M |
| NFR-3 | A daily credit cap (config) stops new live searches when reached; cached and replay checks still work. | M |
| NFR-4 | Replay mode runs the whole app from recorded fixtures with no API key, for judges and tests. | M |
| NFR-5 | The SerpApi key lives only in server environment variables; it never appears in responses, logs, fixtures or the repo. | M |
| NFR-6 | One failing engine does not fail the check; that signal is marked unavailable. | M |
| NFR-7 | Per-IP limits: 10 checks per hour, 5 reports per hour. | M |
| NFR-8 | Wording: the app never labels a store a scam or fraud. It reports signals and sources. | M |
| NFR-9 | No personal data about the buyer is stored. Reports store a salted hash of the IP for rate limiting only. | M |
| NFR-10 | Works on a phone-width screen (360 px). | M |
| NFR-11 | ASCII-only source and docs, minimal comments, small files. | M |
| NFR-12 | Setup from a fresh clone in under 5 commands, documented in README. | M |

## 6. Constraints and assumptions

- SerpApi free plan: 250 searches per month. Hackathon credits may add more.
- Image API accepts JPG, PNG, WebP up to 500 KB; an uploaded image_id expires
  after 10 minutes. The server must downscale larger images before upload.
- Instagram Profile API returns the first page of recent posts only; post dates
  are read from the accessibility caption text. Older history is not visible.
- Google Lens results depend on country; all Lens calls use country=in.
- Prices from Lens are seller listings, not verified prices.

## 7. Acceptance criteria (MVP)

1. A check with handle + photo + price returns a report with all four Must
   signals, each item linked to a source, in under 30 s.
2. Running the same check again within 24 h spends 0 credits (visible in the
   credit panel).
3. With SERPAPI_MODE=replay and no key, the 3 demo checks produce the same
   reports as when recorded.
4. Turning off one engine (simulated error) still returns a report with that
   signal marked unavailable.
5. A filed "not delivered" report appears on the store page and changes the
   verdict input on the next check.
6. `pytest` passes; frontend builds with no errors.
