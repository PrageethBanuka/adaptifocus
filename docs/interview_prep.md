# AdaptiFocus — Interview Prep

## Q1: "Why 3 agents? What does each do?"

**Model answer:**

> Each agent has a **single responsibility** — this is the key design principle.
>
> 1. **Context Agent** — Classifies the *current page* as study, distraction, or neutral. Uses domain matching + Gemini API for ambiguous cases (e.g., is YouTube educational or distracting?). Runs on **every tab change** — needs to be fast and stateless.
>
> 2. **Pattern Agent** — Analyzes **14 days of browsing history** to discover behavioral patterns like time-of-day vulnerability windows or distraction chains (YouTube → Reddit → Instagram spirals). Runs periodically — it's CPU-heavy and doesn't need real-time data.
>
> 3. **Intervention Agent** — Makes the **decision of when and how to intervene** using a 4-level graduated system (nudge → warn → soft_block → hard_block). It takes input from both other agents but makes its own independent decision.
>
> **Why not one agent?** If classification and intervention were coupled, a bug in classification would crash interventions too. More importantly, they run at different frequencies — Context runs per-tab-change (milliseconds), Pattern runs every 5 minutes (seconds), and Intervention checks every 30 seconds. A monolith would force them onto the same schedule.

**Follow-up "How do they communicate?"** → Through the **Coordinator** ([coordinator.py](file:///Users/banukarajapaksha/Developer/Projects/research_project/backend/agents/coordinator.py)), which orchestrates them. The coordinator calls Context Agent first, feeds its output to the Intervention Agent along with Pattern Agent data. This is the **pipeline pattern** — each agent is independently testable.

---

## Q2: "94.3% accuracy — how'd you measure it? What fails?"

**Model answer:**

> I used **5-fold stratified cross-validation** on the [PatternClassifier](file:///Users/banukarajapaksha/Developer/Projects/research_project/backend/ml/pattern_classifier.py#27-230) — not a simple train/test split, because with behavioral data the distribution matters. The classifier is a Random Forest trained on 14 engineered features extracted from browsing sessions.
>
> **What's in the 5.7% that fails:**
> - **Mixed-use domains** — YouTube is the biggest offender. A lecture on algorithms vs. cat videos are the same domain. We handle this with a Gemini API fallback that analyzes the page *title*, but it's not perfect.
> - **New/unknown domains** — Sites not in our domain lists default to "neutral," which can be wrong in both directions.
> - **Context-dependent sites** — Stack Overflow during a study session = productive. Same site while procrastinating = distraction. We partially solve this by checking if a study session is active.
>
> **Does 5.7% error matter?** Not critically, because the *cost of error is low*. If we misclassify a productive site as distraction, the user gets a gentle nudge (level 1) — not a hard block. They dismiss it once, and our feedback loop learns from that. If we miss a distraction, the graduated system catches it on the next 30-second check. The system is designed to be **resilient to classification errors** through its 4-level escalation.

---

## Q3: "Walk me through the 80% latency reduction."

**Model answer:**

> Two independent optimizations, each solving a different bottleneck:
>
> **ONNX Runtime (ML inference speed):**
> - **Before:** scikit-learn's `model.predict()` loads the full Python model into memory each call — ~15-20ms for a Random Forest with 100 trees.
> - **After:** We export the model to ONNX format using `skl2onnx`, then run inference with `onnxruntime` which is a C++ engine. Inference drops to ~2-3ms.
> - **Contribution:** ~80% reduction in ML inference time specifically.
>
> **Redis Caching (DB query elimination):**
> - **Before:** Every dashboard refresh hits the DB — `focus-summary` aggregates all browsing events, `hourly-breakdown` does 24-bucket aggregation. Each query was ~50-100ms on PostgreSQL.
> - **After:** Cache results for 60 seconds (TTL). Second request within 60s returns instantly from Redis (~1ms). Cache auto-invalidates when new events arrive via `cache.invalidate_pattern()`.
> - **Contribution:** Eliminates DB queries entirely for repeat requests within the TTL window.
>
> **How I measured:** I timed the API response using the `/docs` Swagger UI response times and browser DevTools Network tab — before and after each change. Not a formal benchmark, but consistent across multiple runs. In production, Sentry's performance tracing would give exact P50/P95 numbers.

> [!TIP]
> If they push further: "The 80% claim is specifically about analytics endpoint latency. On a cache hit, response goes from ~120ms (DB query + ML) to ~5ms (Redis get + serialization). The ONNX optimization mostly helps the `/classify` and `/interventions/check` endpoints which run ML inference on every call."

---

## Q4: "What about user privacy?"

**Model answer:**

> This is something I thought carefully about because a browser extension that monitors activity is inherently sensitive.
>
> **What data leaves the browser:**
> - Domain name (e.g., `youtube.com`) — NOT the full URL path
> - Page title
> - Time spent (duration in seconds)
> - Timestamp
>
> **What we explicitly do NOT collect:**
> - Page content, form data, passwords
> - Browsing history on non-active tabs
> - Any data when the user is not logged in
>
> **Privacy safeguards we built:**
> 1. **Explicit consent flow** — Users must click "I Agree" on a consent screen before any tracking starts. This is stored as `consent_given` in the DB.
> 2. **GDPR delete endpoint** — `DELETE /auth/data` wipes all user data (events, sessions, interventions, patterns) permanently.
> 3. **Privacy policy** — Shipped with the extension (`privacy_policy.html`), accessible before sign-up.
> 4. **JWT auth** — Data is per-user, isolated, and only accessible with a valid token.
>
> **Trade-off I'd acknowledge:** We do send the page title to the backend for classification, which could contain sensitive info (e.g., "My Bank Account - Chase"). In a production version, I'd consider doing more classification locally in the extension before sending data to the server right now we use a hybrid approach — domain matching happens locally, only ambiguous cases hit the Gemini API.

---

## Q5: "How would you scale to 10,000 users?"

**Model answer — think in order of what breaks first:**

> **1. WebSocket connections (breaks first)**
> - Current: Single Uvicorn process, all WS connections in-memory dict.
> - Problem: Each WS connection holds an open TCP socket. One process handles maybe ~1,000 connections before memory/file descriptor limits.
> - Fix: **Horizontal scaling** with multiple Uvicorn workers behind a load balancer. Use **Redis Pub/Sub** as a message bus so any server instance can push to any user's connection. This is the standard pattern — Discord and Slack use it.
>
> **2. ML inference (CPU bottleneck)**
> - Current: Classification runs synchronously in the request handler.
> - Problem: 10,000 users × classification every 30s = ~333 requests/second of ML inference.
> - Fix: **Celery task queue** with dedicated ML worker processes. The API endpoint returns immediately, the worker runs inference async, and pushes results via WebSocket. ONNX already helps — but at this scale, you'd want GPU inference or batch predictions.
>
> **3. Database writes (I/O bottleneck)**
> - Current: Every browsing event is a single INSERT.
> - Problem: 10,000 users × event every 30s = ~333 writes/second constantly.
> - Fix: **Batch inserts** — buffer events in Redis, flush to PostgreSQL every 5 seconds in bulk. Add **read replicas** for the analytics queries so reads don't compete with writes. Consider **TimescaleDB** (PostgreSQL extension optimized for time-series data) since our events are fundamentally time-series.
>
> **4. Redis cache**
> - Current: Single Redis instance.
> - This actually scales well — Redis handles 100K+ operations/second. A Redis Cluster would handle 10K users easily with no changes.

---

## 🎯 Meta-Strategy for the Interview

The pattern is always: **Claim → Challenge → Depth**

- **Don't start with implementation details.** Start with the *why*.
- **Own the limitations.** Saying "the 5.7% fails on mixed-use domains like YouTube" is 10x more impressive than claiming 100% accuracy.
- **Connect to real-world patterns.** "This is similar to how Discord handles WebSocket scaling" shows you think beyond your project.
- **Have numbers ready.** Even approximate ones like "~120ms before, ~5ms after" are better than "it got faster."
