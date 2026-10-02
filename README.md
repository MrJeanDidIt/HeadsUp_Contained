# heads-up

Watches Canvas and mail, scores what actually matters, and pushes a notification.
Answers "what's due?" on demand.

Built with FastAPI, Postgres, Redis, and ntfy. Runs on a K3s homelab cluster.

## Why it exists

Canvas notifications fire for everything, so they get muted, so deadlines get missed.
This ingests the same data, applies scoring rules you control, and only interrupts you
when the score clears a threshold.

## How it works

```
sources ──► normalize ──► rules ──► notify
Canvas       one Item       score      ntfy
Gmail        shape          from       push
Graph                       rules
```

Every source produces a `RawItem`. Everything downstream is source-agnostic, so adding
Gmail is one file, not a refactor.

**Scoring** is deliberately deterministic — rules are rows in a table with a field, a
match type, and a weight. Urgency is scored separately, so a dull assignment due in two
hours still gets through. When a notification misfires you can see exactly which rules
fired and adjust the weight.

**Idempotency** is enforced by a unique constraint on `(item_id, stage)` in the
`notifications` table, not by an in-memory set. A retried poll, a restart, or a second
replica cannot notify you twice for the same thing. The row is written *before* the send,
so a failed push is skipped rather than retried forever at 2am.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness — no dependency checks |
| GET | `/readyz` | Readiness — verifies the database |
| GET | `/items` | Everything ingested, filterable by source, kind, score |
| GET | `/items/due?days=7` | What's due and when |
| GET | `/rules` | Current scoring rules |
| POST | `/rules` | Add a rule |
| DELETE | `/rules/{id}` | Remove a rule |

Interactive docs at `/docs`.

## Local setup

```bash
cp .env.example .env          # set CANVAS_TOKEN and NTFY_TOPIC
docker compose up -d db redis
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Canvas token: Canvas → Account → Settings → New Access Token.
ntfy topic: pick a long random string, subscribe to it in the ntfy mobile app. The topic
name is the only thing protecting it, so treat it as a secret.

```bash
pytest -q
```

## Build order

1. **Canvas → ntfy end to end.** Assignments arriving, scored, notified. Done first
   because a Canvas token takes 30 seconds and OAuth takes an evening.
2. **Due reminders.** T-48h and T-2h stages.
3. **Tune the rules for a week** against real data before adding anything clever.
4. **Gmail.** OAuth consent, refresh token storage, `app/sources/gmail.py`.
5. **Entra ID auth** on the API itself — set `AUTH_DISABLED=false`.
6. **Microsoft Graph mail.** Same token-refresh module as Gmail.
7. **Deploy to K3s.** Manifests in `k8s/`.

## Known limits

- Single replica by design — the scheduler runs in-process, so two replicas double-poll.
  Split the poller into its own Deployment before scaling.
- The cluster runs on a dorm network. Keep Canvas's own notifications enabled until this
  has run clean for a few weeks; don't make an unproven service the only thing standing
  between you and a missed deadline.
- Rules are keyword matching, not comprehension. An LLM classifier is a reasonable v2 —
  and having a rules baseline to compare against makes it a much better story.
