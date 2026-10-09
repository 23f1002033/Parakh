# Parakh - Project Plan

Parakh helps a buyer in India check an Instagram or website store before paying.
It turns live search data from SerpApi into an evidence report: what the same
product costs elsewhere, whether the product photos are reused, what people
say about the store, and how old and active the account is.

- Event: SerpApi India Hackathon 2026
- Track: Commerce & Market Intelligence
- Team: solo (Ishank Gupta)
- Hard deadline: 10 Oct 2026, 23:59 IST
- Internal deadline: 10 Oct 2026, 21:00 IST (submitted, links tested in incognito)

## Process

The project follows a compressed waterfall SDLC with a review gate at the end of
each phase. A phase starts only after the previous gate passes. Implementation
runs in milestones; each milestone ends with a stop, a test run by the owner, and
a written report against its "done when" list.

| Phase | Output | Gate (owner signs off) | Target (IST) |
|---|---|---|---|
| P1 Requirements | docs/01-requirements.md | G1: scope and MoSCoW agreed | Fri 9 Oct 20:30 |
| P2 Design | docs/02-design.md | G2: schema, API contract, scoring rules agreed | Fri 9 Oct 21:00 |
| P3 Implementation | code, milestones M1 to M4 | each milestone's "done when" met | Sat 10 Oct 15:00 |
| P4 Testing | docs/03-test-plan.md executed, results in docs/04-test-report.md | G4: all Must tests pass or are listed as known issues | Sat 10 Oct 17:30 |
| P5 Release | README, demo video, submission | G5: repo and video open in incognito | Sat 10 Oct 21:00 |
| P6 Maintenance | docs/05-backlog.md | none | after submission |

## Milestones (inside P3)

| ID | Scope | Target (IST) |
|---|---|---|
| M1 | Backend foundation: config, DB schema, SerpApi client with cache, credit ledger, record/replay modes, engine adapters, fixtures for 3 demo stores | Fri 9 Oct 23:59 |
| M2 | Analysis engine: signals, product matcher, verdict rules, check pipeline, REST API | Sat 10 Oct 06:00 |
| M3 | Frontend (Vue 3): check form, live report, store page, community reports | Sat 10 Oct 12:00 |
| M4 | Hardening: rate limits, input validation, error states, README, tests green | Sat 10 Oct 15:00 |

## Roles

- Ishank: product owner, reviewer, tester, all git operations, submission.
- Claude (chat): requirements, design, milestone prompts, review of each milestone.
- Claude Code: implementation inside the limits in CLAUDE.md.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Free plan has 250 searches per month | Development and demo run out of credits | Response cache in DB, replay mode from recorded fixtures, daily credit cap, about 5 searches per check |
| Google Forums API uptime is lower than other engines | Complaint signal missing | Treat each engine as optional; report "source unavailable" instead of failing the check |
| Lens returns look-alike products, not the same product | Wrong price comparison | Same-product filter (exact-match flag plus title similarity), minimum sample size before any price claim |
| Naming a real small seller as a scam in public | Defamation and fairness risk | Report shows signals with sources, never the word "scam" as a verdict; demo uses stores with public complaint trails or our own test pages |
| Time | Unfinished entry | Must-have scope only until M4 is done; Should items only after G4 |
