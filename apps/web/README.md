# DocEdge — Web Client (Next.js 14)

The primary web portal for **DocEdge Medical Exam AI Platform**, containing the **Student Practice Hub**, **Universal Timed Exam Runner**, and **Admin Question Bank Curation Desk**.

## Key Routes

- `/` — Platform Launchpad & overview metrics
- `/student` — Student Practice Hub (1-click exam presets & blueprint generation)
- `/student/exam/[attemptId]` — Interactive timed exam runner with live heartbeat sync
- `/student/results/[attemptId]` — Performance scorecard with +4 / -1 NEET marking penalties
- `/student/review/[attemptId]` — Detailed review with Robbins & WHO Blue Books evidence citations
- `/admin` — Question bank curation, search, filtering, and status transitions

## Development

```bash
bun dev
```
Runs the web client on `http://localhost:3000`.
