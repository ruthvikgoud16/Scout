# HackTrack — PRD

## Problem statement (verbatim)
Build a website that tracks upcoming hiring hackathons from companies like Myntra and Meesho — showing company name, date, registration link/status, plus a "Prep" section for each with typical rounds, requirements, preparation checklist. Should keep itself updated in the backend with international hackathons (Indian, online, hybrid, offline) by itself — be a live website updating itself to the newly introduced system or world.

Follow-up: not only students but working professionals; in-person invites, events, conferences — each and everything should be on the website.

## User choices
- AI model: **Gemini** (gemini-3-flash-preview via emergentintegrations + EMERGENT_LLM_KEY).
- Audience: students AND working professionals.
- Scope: hackathons + conferences + summits + workshops + meetups + invite-only.
- Auth: none (public).
- App must be advanced & useful, with real working links.

## Architecture
- **Backend**: FastAPI + MongoDB (motor), Gemini via emergentintegrations LlmChat streaming.
- **Frontend**: React 19 + React Router + Tanstack Query + Tailwind + shadcn/ui + framer-motion.
- **Data flow**: idempotent seed on boot + `/api/hackathons/refresh` background task using Gemini to discover new events + on-demand `/api/hackathons/{id}/prep` for AI prep playbooks.
- **Streaming**: SSE chat (`/api/chat/stream`) with persistent message history.

## Personas
1. **Students** — looking for hiring hackathons (PPOs), early career resources.
2. **Working professionals** — senior hackathons, conferences, summits, meetups, invite-only programs.

## Core requirements (static)
- Live, self-updating catalog of opportunities.
- AI-generated prep for each event (rounds, requirements, checklist, resources).
- Filters by type, audience, region, mode, status, company + free-text search.
- Streaming AI assistant for personalised guidance.
- Curated resource hub (DSA, SD, behavioral, hackathon platforms, conferences, career growth, startup).

## Implemented (2026-06-24)
- ✅ Backend models, idempotent seed (~22 entries), Gemini-powered prep + refresh + chat.
- ✅ Endpoints: `/api/hackathons` (with 7 query filters), `/api/hackathons/{id}`, `/api/hackathons/{id}/prep`, `/api/hackathons/refresh`, `/api/stats`, `/api/companies`, `/api/event-types`, `/api/resources`, `/api/chat/stream`, `/api/chat/history/{sid}`.
- ✅ Frontend: Home (hero + bento stats + kinetic marquee + featured grid + how-it-works), Hackathons (6 filters + 3 status groups), HackathonDetail (rounds, requirements, interactive checklist with progress, resources), Resources hub (7 categories), AI Assistant streaming chat.
- ✅ Logo fallback (coloured initial avatar), event_type & audience badges on every card.
- ✅ Testing agent run: 100% backend / 95% frontend pass.

## Prioritised backlog
- P0 — Done.
- P1 — Bookmark/save (anonymous via localStorage) & "remind me 24h before deadline" (email).
- P1 — Periodic auto-refresh (cron-style background scheduler every 6h).
- P2 — Auth (Emergent Google) for personal dashboards.
- P2 — Calendar export (ICS) per event.
- P2 — Personalised feed based on resume/skills upload.

## Next tasks
- Add cron-based auto-refresh.
- Add bookmarks + email reminders.
- Add ICS calendar download per event.
