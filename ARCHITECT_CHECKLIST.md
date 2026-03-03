# ARCHITECT_CHECKLIST.md

> **Last updated**: March 2, 2026 (onboarding expanded to 7 steps — age, fitness/rehab, goals/wellbeing)
> Detailed working board — synced with `MASTER_CHECKLIST.md` (human summary).

---

## 1. Now Working On

| # | Task | Area | Key Files | Priority |
|---|------|------|-----------|----------|
| 1 | Admin Page CRUD end-to-end QA | Web Dashboard | `AdminPage.tsx`, `api.ts` | P0 — BLOCKER |


---

## 2. Next Up

| # | Task | Area | Priority | Est. |
|---|------|------|----------|------|
| 0 | Admin Page CRUD end-to-end QA | Web Dashboard | P0 | 1-2 days |
| 1 | Close final ~2% test coverage gap | Backend | P1 | 1 day |
| 2 | Edge AI runtime stabilization (offline sync false states) | Mobile | P1 | 2-3 days |
| 3 | Architecture diagrams update (5-tab UX) | Docs | P2 | 1 day |
| 4 | Deployment checklist + production walkthrough | Ops | P2 | 1 day |
| 5 | Password reset SMTP smoke test in deployed environment | Backend/Ops | P3 | 0.5 day |

---

## 3. Backlog / Ideas

- [ ] Top Navigation Drawer — Notifications, Health Insights, Resources *(optional)*
- [ ] Phase 1 Edge AI — Model export pipeline + Flutter TFLite POC *(Q2 2026 if approved)*
- [ ] Push notifications *(future enhancement)*

---

## Known Issues

| # | Issue | Severity | Area | Notes |
|---|-------|----------|------|-------|
| 1 | **Admin page CRUD not QA-tested** | High | Web Dashboard | Implemented but never manually verified. Blocking for production. |
| 2 | **Edge AI offline sync false states** | Medium | Mobile | Still open. Diagnostics now expose `lastSyncErrorType/message/time`; prediction queue retry behavior improved. Remaining gap: no explicit connectivity probe, so status can still show offline/pending incorrectly in some network/auth edge cases. |
| 3 | **No deployment checklist** | Medium | Ops | No formal AWS ALB deployment walkthrough exists. |
| 4 | **SMTP credentials not deployed yet** | Low | Backend/Ops | Password reset SMTP delivery is implemented. Remaining step is production env credential rollout and live smoke verification. |
