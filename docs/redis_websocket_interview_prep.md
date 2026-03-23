# Redis & WebSocket: Technical Deep Dive for Interviews

This document outlines the architecture, rationale, and implementation of the caching and real-time layers in the AdaptiFocus backend.

---

## 🚀 Part 1: Caching Layer (Redis + Upstash)

### 1. Architecture: The "Safe-Fallback" Pattern

The caching layer follows a **factory pattern** that prioritizes performance but guarantees availability.

- **Primary**: **Redis** (via Upstash) for distributed, persistent caching.
- **Fallback**: **In-Memory Dictionary** for local development or when Redis is unreachable.
- **Client**: Uses `redis.asyncio` for non-blocking I/O, ensuring the API remains responsive.

### 2. Why use Redis here? (The Rationale)

- **Performance**: Fetching complex analytics (e.g., focus summaries for 7 days) involves multiple SQL aggregations. Caching reduces response time from **~200ms to <10ms**.
- **Database Relief**: Scales by offloading repetitive read queries from the main PostgreSQL/SQLite database.
- **Persistence**: Unlike pure In-Memory fallback, Redis survives application restarts (common on Render's free tier).

### 3. Real-world Implementation Example

In `analytics.py`, we cache focus summaries with a **TTL (Time To Live)** of 60 seconds.

- **Cache Invalidation**: On every new browsing event (`events.py`), we call `cache.invalidate_pattern(f"analytics:user:{user_id}:*")`. This ensures the dashboard always shows up-to-date data while still benefiting from cache during "heavy" dashboard viewing.

---

## ⚡ Part 2: Real-time Layer (WebSockets)

### 1. Architecture: The "Connection Manager"

FastAPI handles the WebSocket lifecycle, but we use a custom `ConnectionManager` class to track active users.

- **Concurrency**: Manages hundreds/thousands of concurrent connections using asynchronous Python.
- **User-Centric**: Maps `user_id` to socket instances, allowing targeted "push" notifications.

### 2. Why use WebSockets? (The Rationale)

- **Zero Latency**: Traditional HTTP polling (checking for updates every few seconds) is slow and wastes server resources.
- **Push vs. Pull**: When the AI agent decides to trigger an intervention (e.g., a "Nudge"), it needs to tell the browser extension **immediately**. WebSockets enable the server to initiate communication.
- **Stateful Connection**: Keeps a persistent link between the extension and the server during a study session.

### 3. Protocol & Security

- **Auth**: JWT tokens are passed via query parameters during the handshake (`/ws?token=...`).
- **Heartbeat**: Uses a `ping-pong` mechanism to detect "zombie" connections and free up server memory.
- **Payloads**: All data is exchanged in **structured JSON**, containing `type` (e.g., `stats_update`) and `data`.

### 4. Real-world Implementation Example: Proactive Intervention

In `interventions.py`, when the `CoordinatorAgent` decides a user is too distracted:

1. The server records the intervention in the database.
2. It calls `await ws_manager.send(user_id, {...})` to push a message.
3. The browser extension receives this message instantly via the open WebSocket and pops up a nudge or block screen.

*This avoids the need for the extension to "ask" the server every second, saving battery and bandwidth.*

---

## 🎓 Expected Interview Questions

**Q: Why choose Upstash instead of Render's managed Redis?**
> "Upstash is serverless and offers a generous free tier with zero cold-start issues for this scale. Most importantly, it supports both Redis and REST, providing flexibility if we ever need to fetch data from an edge function."

**Q: How do you handle WebSocket disconnections?**
> "We use a `try...except...finally` block in the endpoint and a `ConnectionManager` to remove stale connections. We also have a `ping/pong` heartbeat to verify the client is still there."

**Q: What happens if Redis goes down? Does the app crash?**
> "No. I implemented a factory that detects connection failures and falls back to a local in-memory dictionary. This ensures high availability at the cost of some performance, but the user experience remains intact."

**Q: Why invalidate the cache on every event? Isn't that expensive?**
> "It's a trade-off. For an attention-management app, data accuracy is critical. By using `invalidate_pattern`, we ensure the user sees their 'Live' focus score immediately after stopping a distraction. Because Redis is extremely fast, these invalidations are negligible in terms of performance impact."
