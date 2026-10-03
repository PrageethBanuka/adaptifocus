# AdaptiFocus — Notion Product and Delivery Plan

> Notion-ready planning document. Import this Markdown into Notion and convert the milestone headings into a board or timeline.

## Product thesis

AdaptiFocus is a privacy-first, context-aware attention platform that helps people stay focused without using opaque, binary blocking. It combines local-first browser signals, deterministic agent workflows, explainable interventions, and user-controlled privacy.

The long-term product should be positioned as a **personal attention operating system**:

- Personal users get a focus companion that understands context without collecting page content.
- Researchers get consented, anonymized evaluation data.
- Teams and education providers can deploy governed focus programs without receiving raw browsing histories.
- Platform engineers get a reference implementation for secure, observable AI workflows on Kubernetes.

## Current product snapshot

### Current users and surfaces

- Chrome Manifest V3 extension for tracking, classification, intervention delivery, and authentication.
- FastAPI backend for event ingestion, authentication, sessions, analytics, ML feedback, and WebSockets.
- React/Vite dashboard for focus metrics and patterns.
- SQLite locally and PostgreSQL in deployment.
- Random Forest/ONNX ML pipeline plus rule-based classification and optional Gemini classification.

### Current agent workflow

```text
Pattern Agent → Context Agent → Intervention Agent
                    ↓
             Coordinator Agent
```

The workflow is deterministic and sequential. This is intentional: it is easier to test, explain, secure, and evaluate than a free-form autonomous agent swarm.

### Current risks to resolve

- Agent inputs and outputs use untyped dictionaries.
- Raw URLs and page titles are persisted.
- Page titles may be sent to Gemini, but the README currently emphasizes that page content is never collected.
- The intervention proposal is not separated from the final policy authorization.
- Production defaults include unsafe fallbacks for JWT secrets and development login.
- There is no complete retention model for raw events, derived patterns, caches, logs, or model traces.
- Observability is not yet privacy-aware or correlated across request, agent, policy, and intervention.

## Product principles

1. **Local first** — classify locally whenever confidence is sufficient.
2. **Model proposes, software decides** — external models may suggest classifications, but deterministic policy code controls side effects.
3. **Data minimization by default** — retain the smallest representation needed for the feature.
4. **Explainable by design** — every intervention should have a human-readable reason.
5. **User-owned data** — consent, export, deletion, retention, and external-model opt-out are first-class features.
6. **Open platform thinking** — expose stable APIs and capability-scoped integrations rather than provider-specific internals.
7. **Operational maturity** — every production workflow needs health, metrics, auditability, rollback, and failure behavior.

## Target architecture

```text
Browser extension
    ↓
API gateway and identity
    ↓
Privacy boundary
    ├── normalize domain and title
    ├── remove search and personal identifiers
    ├── local classifier
    └── external-model permission check
    ↓
Typed coordinator
    ├── pattern analysis
    ├── context classification
    └── intervention proposal
    ↓
Policy gateway
    ├── consent and tenant authorization
    ├── confidence and safety rules
    ├── cooldown and quota rules
    └── audit event
    ↓
Intervention executor
    ├── WebSocket delivery
    ├── extension overlay
    └── user response
    ↓
Privacy-aware telemetry and retention workers
```

## Delivery milestones

### Milestone 0 — Trust and production baseline

**Outcome:** The system can be piloted without misleading privacy claims or unsafe production defaults.

**Deliverables**

- Production configuration validation.
- No default JWT secret in production.
- Development login disabled outside local development.
- Explicit consent enforcement before event ingestion.
- Correct privacy policy and README data-flow description.
- Trusted proxy and CORS configuration.
- Sentry and application logs scrubbed of page-derived data.

**Definition of done**

- Security configuration tests pass.
- A user without consent cannot submit tracking events.
- Documentation matches the actual URL/title/Gemini data flow.

### Milestone 1 — Typed decision platform

**Outcome:** Agents become reliable, versioned components instead of loosely coupled dictionary functions.

**Deliverables**

- Pydantic models for context, pattern, intervention, and coordinator state.
- Validation of all agent outputs.
- Versioned decision schema.
- Explicit error and fallback contracts.
- Regression tests for malformed and incomplete results.

**Definition of done**

- No unvalidated dictionary crosses an agent boundary.
- Invalid external-model output fails closed.
- API and internal decision schemas are consistent.

### Milestone 2 — Privacy boundary and data lifecycle

**Outcome:** The platform stores and transmits only the minimum required data.

**Deliverables**

- Domain-first event representation.
- Optional salted hashes instead of raw URLs.
- Title normalization/redaction.
- Search-query exclusion.
- User-configurable local-only classification.
- Retention jobs for raw events, derived patterns, feedback, cache, and audit data.
- Complete export and deletion workflow.

**Definition of done**

- Deleting an account removes raw, derived, feedback, and cached data.
- Retention policies are automated and tested.
- External model use is visible and opt-out capable.

### Milestone 3 — Policy gateway and intervention quality

**Outcome:** Agent output is separated from intervention authorization.

**Deliverables**

- Policy gateway between coordinator and executor.
- Per-user and per-session cooldowns.
- Daily intervention limits.
- Idempotency for repeated checks.
- Experiment-group policy enforcement.
- Explainability payload for every intervention.

**Definition of done**

- Repeated extension polling cannot create duplicate interventions.
- Low-confidence predictions cannot trigger hard blocks.
- Every intervention records the policy decision and reason.

### Milestone 4 — Local-first intelligence

**Outcome:** The product becomes cheaper, faster, and more private while keeping external AI as an optional fallback.

**Deliverables**

- Classifier gateway abstraction.
- Local rules/ONNX model as the first path.
- Gemini only for low-confidence mixed-domain cases.
- Timeout, circuit breaker, and quota handling.
- Model version and confidence calibration.
- Privacy-safe classification cache.

**Definition of done**

- Backend remains functional when Gemini is unavailable.
- External model call rate is measurable.
- Local-only mode provides a complete user experience.

### Milestone 5 — Research-grade evaluation

**Outcome:** Product decisions and papers are supported by trustworthy metrics.

**Deliverables**

- Evaluation dataset with mixed-domain and adversarial cases.
- Precision, recall, calibration, and subgroup metrics.
- Intervention acceptance and annoyance metrics.
- A/B experiment instrumentation.
- Statistical analysis pipeline.
- Reproducible model and policy versions.

**Definition of done**

- Every experiment can be reproduced from a versioned configuration.
- Results report false positives, false negatives, effect size, and confidence intervals.
- No research dashboard exposes individual browsing history.

### Milestone 6 — OpenChoreo-native platformization

**Outcome:** AdaptiFocus becomes a credible platform engineering portfolio product and a deployable service.

**Deliverables**

- Containerized services with health/readiness probes.
- Kubernetes-native deployment manifests or Helm chart.
- OpenChoreo component and environment definitions.
- CI workflow and GitOps deployment path.
- OpenTelemetry traces, metrics, and logs.
- Backstage/OpenChoreo catalog metadata.
- Capability-scoped integration APIs.
- Runbooks and disaster recovery documentation.

**Definition of done**

- A new environment can be created through a documented golden path.
- Deployment, rollback, observability, and policy checks are automated.
- The system can run across development, staging, and production environments without code changes.

## Product roadmap

### Now

- Privacy and production hardening.
- Typed agent contracts.
- Policy gateway.
- Local-only mode.

### Next

- Better explainability.
- Offline-first extension behavior.
- Research-grade evaluation.
- Consent and privacy dashboard.

### Later

- Calendar and task integrations.
- Read-only MCP analytics tools.
- Federated or differentially private research learning.
- Team/education administration.
- OpenChoreo deployment productization.

## Success metrics

### User value

- Focus-time ratio.
- Distraction episode reduction.
- Intervention acceptance rate.
- False-positive rate.
- Weekly retained users.
- User-reported annoyance.

### Engineering quality

- Classification p50/p95 latency.
- Intervention decision p50/p95 latency.
- External-model call percentage.
- API error rate.
- WebSocket delivery success.
- Event ingestion durability.
- Data deletion completion time.

### Platform maturity

- Mean time to detect and recover.
- Deployment frequency.
- Change failure rate.
- Rollback time.
- OpenTelemetry trace coverage.
- Policy violations blocked before execution.

## Startup positioning

### Initial wedge

Privacy-first focus assistance for students, researchers, and knowledge workers who want context-aware support without surrendering raw browsing history.

### Expansion path

1. Personal focus companion.
2. University/research pilot with privacy-preserving analytics.
3. Team focus and learning programs.
4. SDK/API for productivity applications.
5. Governed AI workflow reference platform for platform engineering teams.

### Differentiation

- Context-aware instead of binary blocking.
- Local-first and transparent.
- Explainable interventions.
- User-owned retention and deletion.
- Research-grade experimentation.
- Kubernetes/OpenChoreo operational maturity.

## Notion database suggestions

Create these databases after importing:

### Roadmap database

Properties:

- `Name`
- `Milestone`
- `Status`
- `Priority`
- `Owner`
- `Target date`
- `Success metric`
- `GitHub issue`

### Architecture decision record database

Properties:

- `Decision`
- `Status`
- `Context`
- `Decision`
- `Alternatives`
- `Consequences`
- `Date`

### Privacy register

Properties:

- `Data field`
- `Source`
- `Purpose`
- `Stored?`
- `External processor?`
- `Retention`
- `User control`
- `Risk`

## Reference links

- OpenChoreo: https://openchoreo.dev/
- OpenChoreo documentation: https://openchoreo.dev/docs/
- OpenChoreo architecture: https://openchoreo.dev/docs/overview/architecture/
- OpenChoreo GitHub: https://github.com/openchoreo/openchoreo
- OpenTelemetry: https://opentelemetry.io/
- MCP specification: https://github.com/modelcontextprotocol/modelcontextprotocol
- NIST AI RMF: https://www.nist.gov/artificial-intelligence/ai-risk-management-framework
- OWASP Agentic Applications: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
