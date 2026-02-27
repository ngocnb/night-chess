# Vision Owner — MEMORY.md

## Project: Night Chess

**Vision document**: `/home/baongoc/workspaces/night-chess/.aiwg/requirements/vision-document.md` (v1.0, 2026-02-27)

**Key facts to carry across sessions**:
- Solo developer, 4-6 week timeline (aggressive)
- Developer is new to FastAPI and Next.js (budget ramp-up in weeks 1-2)
- Top priority: chess UX correctness (make-or-break — any chess bug is a launch blocker)
- Profile: MVP (see solution-profile.md)
- GDPR: awareness only; account deletion endpoint required before EU marketing, not MVP launch
- Personas: Guest Puzzle Solver (dominant) + Registered Practitioner (minority in v1)
- North Star metric: guest-to-registered conversion signals the core loop is working
- Data pipeline prototype is Sprint 0 first task (before any other backend work)

**Scope decisions recorded**:
- Redis: deferred (add only under real load, not MVP)
- E2E tests (Playwright): deferred post-MVP
- Puzzle filtering, streaks, social: all post-MVP
- Custom puzzle creation: never (scope creep)

**Intake sources**:
- `/home/baongoc/workspaces/night-chess/.aiwg/intake/project-intake.md`
- `/home/baongoc/workspaces/night-chess/.aiwg/intake/solution-profile.md`

**Outstanding decisions** (as of 2026-02-27):
- Hosting provider (Render vs AWS vs Fly.io)
- Next.js rendering strategy for puzzle page
- JWT storage (recommend httpOnly cookie)
- Email verification at registration (recommend skip for MVP)
