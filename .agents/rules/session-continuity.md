---
description: Ensures persistent context and seamless continuity across daily chat sessions.
always_on: true
---

# Session Continuity & Active Context Rule

1. **Always Read Active Context First**:
   - At the beginning of every new conversation turn or when resuming work, check and read [ACTIVE_CONTEXT.md](file:///r:/Repositories/medical-learning-intelligence/ACTIVE_CONTEXT.md).
   - Align all code changes, architectural decisions, and answers with the current milestone indicated in `ACTIVE_CONTEXT.md` (currently [MileStone7.md](file:///r:/Repositories/medical-learning-intelligence/MileStones/MileStone7.md)).

2. **Never Force the User to Re-Explain Setup**:
   - The user runs a dual-stack setup: FastAPI backend + Next.js frontend managed via `dev.py` / `bun`.
   - Refer to `ACTIVE_CONTEXT.md` for the exact scripts, test commands, and paths.

3. **Session Handoff & Maintenance**:
   - Whenever completing a significant task, milestone step, or when the user says they are ending for the day, proactively summarize progress and update the **Daily Continuity & Handoff Log** section in [ACTIVE_CONTEXT.md](file:///r:/Repositories/medical-learning-intelligence/ACTIVE_CONTEXT.md).
