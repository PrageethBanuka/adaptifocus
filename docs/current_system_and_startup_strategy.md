# AdaptiFocus — Current System, Target Architecture, and Startup Strategy

## Executive summary

AdaptiFocus is a Chrome extension, FastAPI backend, React dashboard, and machine-learning pipeline for adaptive digital wellbeing. Its novel research idea is to replace binary website blocking with a context-aware, graduated intervention loop:

```text
observe browsing context
    → classify study/distraction/neutral
    → learn personal patterns
    → propose intervention level
    → deliver nudge/warn/soft-block/hard-block
    → observe user response
```

The codebase already has a valuable architectural property: the agent workflow is deterministic. The `CoordinatorAgent` runs Pattern, Context, and Intervention agents in a fixed sequence rather than allowing an unconstrained agent swarm to take actions.

The next stage should not be “add more agents.” It should be to make the existing system typed, privacy-preserving, policy-governed, observable, and deployable as a reliable platform product.

## 1. Current repository map

```text
research_project/
├── backend/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── context_agent.py
│   │   ├── coordinator.py
│   │   ├── intervention_agent.py
│   │   └── pattern_agent.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── models/schemas.py
│   │   └── routes/
│   │       ├── events.py
│   │       ├── interventions.py
│   │       ├── analytics.py
│   │       ├── sessions.py
│   │       ├── ml.py
│   │       ├── reports.py
│   │       ├── streaks.py
│   │       ├── admin.py
│   │       └── ws.py
│   ├── database/
│   │   ├── db.py
│   │   └── models.py
│   ├── ml/
│   │   ├── feature_extractor.py
│   │   ├── pattern_classifier.py
│   │   ├── train_pipeline.py
│   │   └── export_onnx.py
│   ├── services/pattern_service.py
│   ├── cache.py
│   ├── rate_limiter.py
│   └── main.py
├── extension/
│   ├── background.js
│   ├── content.js
│   ├── manifest.json
│   └── popup/
├── dashboard/
│   └── src/
├── docs/
└── paper/
```

## 2. Runtime flow

### Extension observation

The service worker in `extension/background.js`:

- Tracks active tabs and URL changes.
- Extracts domains.
- Measures dwell time.
- Queues events in Chrome local storage.
- Sends batches to `/events/batch`.
- Polls `/interventions/check` when WebSockets are unavailable.
- Connects to `/ws` for real-time intervention delivery.
- Stores the authentication token and pending events locally.

### Event ingestion

`backend/api/routes/events.py`:

1. Authenticates the user.
2. Extracts the domain.
3. Runs the Context Agent.
4. Applies known-distraction-domain fallback rules.
5. Persists the browsing event.
6. Invalidates analytics cache.
7. Schedules pattern updates.

### Intervention decision

`backend/api/routes/interventions.py`:

1. Reads the current user’s events for the day.
2. Builds historical event dictionaries.
3. Calculates recent domains and distraction time.
4. Reads recent intervention compliance.
5. Loads the active session.
6. Calls the Coordinator Agent.
7. Persists a triggered intervention.
8. Sends the decision through WebSocket.

### Agent responsibilities

#### Context Agent

The Context Agent combines:

- Domain classification.
- Title keyword scoring.
- Optional Gemini classification for mixed domains.
- Study-topic relevance.
- Recent-domain trajectory.
- Adult-content detection.

It produces a classification, confidence, score, reasons, and safety flags.

#### Pattern Agent

The Pattern Agent analyzes history for:

- Hourly vulnerability.
- Domain risk.
- Distraction chains.
- Long dwell times.

It currently performs deterministic statistical analysis over event history.

#### Intervention Agent

The Intervention Agent:

- Maps context and pattern signals to intervention levels.
- Adjusts thresholds by domain risk.
- Tightens thresholds during study sessions.
- Adapts based on compliance and dismiss streaks.
- Produces the final intervention proposal.

#### Coordinator Agent

The Coordinator is a small hierarchical orchestrator. It is not autonomous and does not discover or invoke arbitrary tools. That makes it a good base for a safe workflow system.

## 3. Current strengths

### Product strengths

- Clear user problem and measurable outcomes.
- Strong context-aware differentiation from static blockers.
- Graduated interventions are easier to accept than binary blocking.
- Personalization is understandable to users.
- Existing control/static/adaptive experiment groups support research.

### Engineering strengths

- FastAPI and SQLAlchemy provide a sensible service foundation.
- Async database access is already used.
- Alembic migration support exists.
- Redis caching and WebSockets are present.
- Offline event queueing exists in the extension.
- ML export to ONNX creates a path toward local inference.
- Tests cover agent behavior and context overrides.

### Platform strengths

- The system has natural service boundaries.
- The coordinator can become a policy-controlled workflow.
- It can be deployed as a containerized service.
- It has a clear relationship to OpenChoreo’s platform concerns: component lifecycle, environments, observability, CI/GitOps, policy, and multi-tenancy.

## 4. Current weaknesses and risks

### Privacy

The current database model stores full URLs, page titles, exact timestamps, feedback URLs, and intervention trigger URLs. The extension also temporarily extracts Google search queries as study topics.

The Context Agent can send titles to Gemini for mixed-domain classification. This is a material external-processing boundary and must be disclosed clearly.

The product should not claim “only domains and time” while retaining or transmitting titles and URLs.

### Security

Production configuration needs stronger guarantees:

- Require a strong `JWT_SECRET`.
- Disable development authentication by default.
- Restrict proxy trust.
- Restrict CORS and extension origins.
- Validate consent before ingestion.
- Avoid logging URLs, titles, tokens, or raw model payloads.
- Add explicit cross-user authorization tests.

### Correctness

Agent contracts use `Dict[str, Any]`. A missing field can silently turn into a default. A malformed external-model response could influence intervention behavior without a shared schema.

The event routes duplicate classification and persistence logic between single-event and batch ingestion.

### Reliability

- External model failures need bounded timeout and circuit-breaker behavior.
- Intervention checks need idempotency because the extension polls repeatedly.
- Background pattern updates need job status and retry visibility.
- Cache degradation should be observable rather than only printed.
- Scheduled retraining needs a production job boundary instead of an in-process infinite loop.

### Research quality

The reported model accuracy is not enough for deployment decisions. Evaluation should include calibration, class-specific precision/recall, false-positive cost, intervention acceptance, user annoyance, and subgroup/domain performance.

## 5. Target architecture

### Plane-inspired structure

OpenChoreo’s official architecture separates experience, control, data, workflow/CI, and observability concerns. AdaptiFocus can apply the same separation without copying OpenChoreo’s implementation:

```text
Experience plane
    Extension, dashboard, CLI/export, privacy controls

Control plane
    Identity, consent, policies, experiment assignment,
    agent workflow definitions, feature flags

Data plane
    Event ingestion, local/browser queue, event store,
    pattern features, intervention delivery

Workflow plane
    Pattern updates, model training, retention deletion,
    export generation, research aggregation

Observability plane
    Redacted traces, metrics, logs, audit events,
    model and policy evaluation
```

### Typed workflow

```text
PrivacyInput
    → PatternContext
    → ContextResult
    → PatternResult
    → InterventionProposal
    → PolicyDecision
    → InterventionEvent
```

Every object should include:

- Schema version.
- Run ID.
- User pseudonym or tenant ID.
- Agent/model version.
- Timestamp.
- Confidence and reason fields.

### Policy boundary

Agents may propose. A deterministic policy gateway must authorize:

- Whether the user has consented.
- Whether the session belongs to the user.
- Whether an intervention is allowed by experiment group.
- Whether confidence is sufficient.
- Whether a cooldown or daily quota blocks the action.
- Whether the level is safe for the current context.
- Whether an external model was permitted.

## 6. Privacy architecture

### Data classification

| Data | Current status | Target |
|---|---|---|
| User identity | Stored centrally | Keep, protect with normal identity controls |
| Full URL | Stored in events/interventions | Avoid by default; store normalized domain and optional salted hash |
| Domain | Stored | Keep only when needed, with retention |
| Page title | Stored and may go to Gemini | Redact, minimize, local-first, explicit opt-out |
| Search query | Temporarily stored as topic | Do not persist raw query |
| Dwell time | Stored | Keep as coarse/derived feature where possible |
| Exact timestamp | Stored | Use only where required; bucket for long-term analytics |
| Pattern data | Stored | Keep derived, explainable, and deletable |
| Research metrics | Not fully separated | Aggregate and anonymize before long-term retention |
| Debug traces | Provider-dependent | Redact, sample, and TTL-delete |

### Retention tiers

```text
Raw event buffer: short retention
Session features: study-period retention
User patterns: user-controlled retention
Aggregates: long-term only if anonymized
Audit events: limited retention
Debug traces: short TTL and redacted
```

### External model policy

The external classifier should receive only:

- A normalized title or safe feature representation.
- No URL query string.
- No account or user identity.
- No raw event history.
- No authentication token.

The system should support:

- Local-only mode.
- External model disabled by default for sensitive deployments.
- Provider selection through configuration.
- A visible privacy setting.
- Call count and latency metrics without raw prompt logging.

## 7. OpenChoreo and WSO2-aligned startup direction

OpenChoreo is an open-source, Kubernetes-native internal developer platform developed from WSO2 experience. Its official documentation describes a modular multi-plane architecture, declarative platform APIs, golden paths, GitOps, observability, RBAC, and built-in platform agents.

That creates a strong personal-startup angle for AdaptiFocus:

### Product concept

**AdaptiFocus Platform** — a privacy-first attention intelligence platform delivered as a governed, observable, Kubernetes-native product.

### Customer segments

1. Students and knowledge workers.
2. Universities and research labs.
3. Developer productivity teams.
4. HR/wellbeing programs that need aggregate insights without employee surveillance.
5. Platform engineering teams evaluating safe AI workflow patterns.

### Initial business wedge

Sell the product as a privacy-preserving focus assistant, not as employee monitoring. The first paid capability could be:

- Personal and team focus programs.
- Aggregate dashboards.
- Configurable intervention policies.
- Self-hosted deployment for universities.
- Audit and retention controls.

### OpenChoreo portfolio opportunity

Use the project to demonstrate platform engineering skills:

- Package backend, dashboard, and worker services as deployable components.
- Define dev/staging/prod environments.
- Add CI and GitOps workflows.
- Expose health, readiness, metrics, traces, and logs.
- Add policy checks before deployment.
- Provide a golden path for adding a new agent/classifier.
- Use declarative configuration for intervention policies.
- Document tenant and data-plane isolation.

This makes the project relevant to both digital wellbeing and platform engineering rather than being only a browser extension demo.

### Potential revenue paths

- Self-hosted university/research deployment.
- Hosted personal premium tier.
- Team aggregate analytics.
- Privacy and governance package.
- Platform SDK for third-party productivity tools.
- Professional services for deployment and policy customization.

### What not to build first

- A general-purpose autonomous agent marketplace.
- Arbitrary MCP tool execution.
- Employee-level surveillance dashboards.
- A large microservice fleet before product-market evidence.
- Federated learning before retention, consent, and evaluation are correct.

## 8. Industry-level operating model

### Reliability objectives

- 99.9% API availability for production pilot.
- Event ingestion must tolerate temporary backend failure.
- Intervention decisions must have bounded latency.
- No duplicate intervention for the same decision window.
- Deletion requests must be verifiable.

### Security baseline

- OIDC/OAuth-based identity.
- Short-lived access tokens and refresh-token rotation if needed.
- Secret manager integration.
- Per-tenant authorization.
- Database encryption at rest and TLS in transit.
- Signed, redacted audit events.
- Dependency and container scanning.
- Threat model based on OWASP agentic risks and NIST AI RMF.

### Delivery baseline

- CI runs tests, lint, migration checks, security checks, and image scans.
- GitOps controls deployment promotion.
- Staging mirrors production topology.
- Feature flags control model providers and intervention policies.
- Every model/policy release is versioned and rollbackable.

### Observability baseline

Correlate:

```text
request_id
→ coordinator_run_id
→ agent execution
→ model call
→ policy decision
→ intervention delivery
→ user response
```

Never include raw page titles or URLs in default traces.

## 9. Recommended implementation sequence

### Stage 1: Trust foundation

- Configuration validation.
- Consent enforcement.
- Privacy documentation.
- Secret and proxy hardening.
- Redacted logging.

### Stage 2: Core correctness

- Typed agent contracts.
- Shared classifier gateway.
- Policy gateway.
- Idempotent intervention checks.

### Stage 3: Privacy and cost

- Local-first inference.
- URL/title minimization.
- Retention workers.
- Complete export/deletion.

### Stage 4: Evidence

- Evaluation dataset.
- Model calibration.
- A/B metrics.
- Research reporting.

### Stage 5: Platform product

- Containers and Kubernetes packaging.
- OpenChoreo environment definitions.
- CI/GitOps.
- OpenTelemetry.
- Runbooks and SLOs.

## 10. Reference architecture sources

- OpenChoreo home: https://openchoreo.dev/
- OpenChoreo documentation: https://openchoreo.dev/docs/
- OpenChoreo architecture: https://openchoreo.dev/docs/overview/architecture/
- OpenChoreo repository: https://github.com/openchoreo/openchoreo
- OpenTelemetry: https://opentelemetry.io/
- Model Context Protocol: https://github.com/modelcontextprotocol/modelcontextprotocol
- NIST AI RMF: https://www.nist.gov/artificial-intelligence/ai-risk-management-framework
- OWASP Top 10 for Agentic Applications: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
