# Implementation Plan: Complete Luna Search Engine

## Overview

Complete the existing Luna Dockerized microservice repository in the design’s order: stabilize the repository and build path, establish migrations and shared contracts, make the crawl-to-index-to-rank-to-search vertical slice executable, finish the frontend, add authentication/RBAC/administration/analytics, harden operations, provide offline demo data and documentation, and finish with layered validation. Preserve the declared services, ports, PostgreSQL source of truth, Redis cache/coordination role, RabbitMQ asynchronous transport, and Python 3.13/FastAPI plus React 18/TypeScript implementation choices.

Tasks marked `*` are optional test or capability work. Required implementation tasks must be completed before optional work is attempted. Each checkpoint below is an executable gate: its required verification leaf task has one exact command, an exit-0 requirement, and a named report artifact that later waves depend on. The dependency graph at the end contains every leaf task, including optional tasks and gate tasks, and schedules independent work in waves.

## Tasks

- [ ] 1. Phase 0 — Repository stabilization and buildability
  - [ ] 1.1 Reconcile repository inventory, package metadata, imports, Docker contexts, and service entrypoints
    - Inspect `services/*`, `shared/python`, `frontend`, `migrations`, `docker-compose.yml`, and the existing partial implementations.
    - Make each declared backend image buildable, each Python entrypoint importable, and each service use the target `src/<service>` layout without duplicating ownership logic.
    - Add the supported Python/Node toolchain commands and deterministic dependency installation used by later tasks.
    - Validate every backend package import, frontend package install, TypeScript compile, and Docker build context independently.
    - _Requirements: 1.1, 1.2, 1.6_

  - [ ] 1.2 Correct Compose startup and introduce the single Alembic migration gate
    - Update `docker-compose.yml` so PostgreSQL receives only database initialization, while a one-shot migration service or equivalent gate runs `alembic upgrade head` after PostgreSQL readiness.
    - Make application services depend on migration completion/readiness rather than `service_started`; preserve declared ports and service names.
    - Add migration locking or an equivalent single-run guard and actionable startup failure messages containing service, dependency, and remediation details.
    - Validate clean startup against an empty volume, migration completion before application startup, and expected local ports/health dependencies.
    - _Requirements: 1.2, 1.3, 1.4, 8.3_

  - [ ] 1.3 Implement shared runtime primitives for configuration, logging, request context, lifecycle, and health
    - Extend `shared/python/luna_shared` with typed settings loading, redacted effective-config reporting, structured logging, `X-Request-ID` propagation, bounded startup retries, dependency status, and graceful shutdown helpers.
    - Add service adapters under each service’s `config.py`/`observability.py` without moving service use cases into the shared package.
    - Validate missing dependency, invalid configuration, liveness, readiness, correlation ID, redaction, and shutdown behavior with focused tests.
    - _Requirements: 1.4, 2.5, 2.6, 8.1, 8.2, 8.3_

  - [ ] 1.4 Complete the frontend compilation shell and route-safe module boundaries
    - Fill the missing modules referenced by `frontend/src/App.tsx`, including page, layout, protected-route, UI, and toaster boundaries, or update stale references consistently.
    - Keep the existing Vite, React Query, Zustand, router, theme, and API-client intent; do not add feature behavior before the shell compiles.
    - Validate `npm run build`/TypeScript compilation and verify search, results, authentication, admin, analytics, settings, and unknown-route imports resolve.
    - _Requirements: 1.1, 1.6, 5.1_

  - [ ] 1.5 Add the repository’s first build and health smoke checks
    - Add `scripts/validate_foundation.py` (or an equivalent documented module entrypoint) that builds all declared images, applies migrations, probes `/health/live` and `/health/ready`, and verifies the frontend route bundle.
    - Make `python -m scripts.validate_foundation --report artifacts/validation/foundation.json` the repeatable foundation validation command; capture actionable service/dependency context when a smoke check fails instead of silently skipping it.
    - Include image/build results, migration-head evidence, import results, frontend build output, health responses, and expected ports in the JSON report.
    - Validate the clean-checkout foundation gate before moving to contract work.
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 10.4_

- [ ] 2. Checkpoint — Foundation gate
  - [ ] 2.1 Execute the foundation gate verification
    - Run `python -m scripts.validate_foundation --report artifacts/validation/foundation.json` from a clean checkout.
    - Require exit code 0 and attach `artifacts/validation/foundation.json` as evidence containing successful declared-image builds, empty-volume migration completion at the Alembic head, import checks for every service entrypoint, frontend production/TypeScript build success, live/readiness probes, expected ports, and actionable failure context.
    - Do not start Phase 1 implementation until the report exists and every required foundation check is passing.

- [ ] 3. Phase 1 — Migration and contract foundation
  - [ ] 3.1 Reconcile SQLAlchemy models with the baseline Alembic revisions and add only required additive migrations
    - Align `migrations/versions/001_initial_schema.py`, `002_add_pg_trgm_extension.py`, shared models, and service repositories for documents, postings, term statistics, crawl jobs/queue, query/click logs, administrators, API keys, settings, and audit events where absent.
    - Add explicit constraints/indexes or compatible support columns for canonical identifiers, document versions, audit correlation, click integrity, statuses, roles, and idempotent postings.
    - Keep changes forward-compatible and additive; test downgrade behavior for local development and empty/baseline upgrade paths.
    - _Requirements: 1.3, 4.3, 6.9, 9.1_

  - [ ] 3.2 Define versioned shared HTTP contracts and generated/mirrored TypeScript contracts
    - Add Pydantic models for common success/error/health envelopes, search, suggestions, clicks, auth, crawl jobs, queue statistics, index stats, settings, API keys, analytics, and audit responses under `/api/v1`.
    - Add `shared/typescript` or generated frontend contract output so `frontend/src/services/contracts.ts` cannot drift from Python field names and nullability.
    - Add the required `python -m scripts.validate_contracts --report <path>` command used by gate 3.7; it must emit schema, envelope, readiness, and migration/model compatibility evidence without requiring optional integration tests.
    - Validate UTC timestamps, bounded pagination/limits, opaque query contexts, stable error codes, and safe `details` fields with schema tests.
    - _Requirements: 2.2, 2.3, 2.4, 2.7, 5.2, 6.5, 7.2_

  - [ ] 3.3 Implement canonical RabbitMQ envelopes, queue constants, publisher confirms, retries, and dead-letter handling
    - Add shared queue/exchange/routing-key constants for `crawl.commands`, `crawl.results`, `document.index.requested`, `document.index.dead-letter`, and `operational.events`.
    - Implement versioned event envelopes with `event_id`, `schema_version`, `correlation_id`, `idempotency_key`, and durable acknowledgement-after-commit semantics.
    - Add bounded delivery retries, reconnect behavior, and failure details without acknowledging uncommitted work.
    - Validate serialization, routing, duplicate delivery keys, retry limits, and dead-letter placement with broker-free unit tests and protocol-level integration fixtures.
    - _Requirements: 3.7, 4.3, 8.4_

  - [ ] 3.4 Align API Gateway, Search API, and Admin API route adapters to the shared contracts
    - Implement the gateway’s public search/suggest/click and authenticated admin/auth forwarding using configured service URLs, propagated request IDs, bounded timeouts, and stable 502/504 mapping.
    - Make direct Search API and Admin API routes use the same request/response/error schemas as gateway calls.
    - Validate invalid schemas, missing/invalid auth, rate limits, downstream failures, timeout behavior, and correlation logging.
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.7, 8.5_

  - [ ] 3.5 Add consistent health/readiness endpoints and dependency probes to every application service
    - Implement `/health/live` and `/health/ready` for gateway, Search API, crawler, indexer, ranker, and Admin API using the shared health envelope.
    - Report required PostgreSQL, Redis, RabbitMQ, and downstream Ranker status without claiming readiness when dependencies are unavailable.
    - Validate healthy, degraded, and unavailable dependency responses plus service/version/request ID fields.
    - _Requirements: 2.6, 8.3, 10.2_

  - [ ]* 3.6 Add migration and contract integration tests against empty and baseline databases
    - Exercise `alembic upgrade head`, schema/model compatibility, OpenAPI or contract snapshots, common error envelopes, health responses, and gateway-to-service stubs.
    - Report migration, service, dependency, and fixture context for every failure.
    - _Requirements: 1.3, 2.1–2.7, 10.2, 10.4_

  - [ ] 3.7 Execute the contract-foundation gate verification
    - Run `python -m scripts.validate_contracts --report artifacts/validation/contracts.json` after required Phase 1 tasks complete; this command is added by the contract implementation work and must not depend on optional task 3.6.
    - Require exit code 0 and attach `artifacts/validation/contracts.json` as evidence containing migration/model compatibility, versioned HTTP schema checks, RabbitMQ envelope/queue checks, gateway and direct-service contract checks, and healthy/degraded/unavailable readiness response checks.
    - Do not start Phase 2 until the report proves the shared contracts and service boundaries are aligned; optional integration-test results may be recorded separately as skipped.
    - _Requirements: 1.3, 2.1–2.7, 3.7, 8.3, 10.2, 10.4_

- [ ] 4. Phase 2 — Crawl, index, rank, and search pipeline
  - [ ] 4.1 Implement crawler URL identity, domain policy, frontier ordering, robots decisions, and politeness controls
    - Complete crawler domain modules around `config/crawler.yaml` for URL normalization, canonical identity, allowed/blocked domains, duplicate suppression, depth/page limits, priority/scheduled ordering, robots caching, per-domain delay/concurrency, and global concurrency.
    - Persist accepted/rejected frontier decisions and ensure rejected URLs never reach the fetch set.
    - Validate deterministic frontier ordering, policy decisions, duplicate collapse, robots behavior, and concurrency permit release without external websites.
    - _Requirements: 3.2, 3.3, 3.4_

  - [ ]* 4.2 Write Property 3 tests for URL policy and duplicate elimination
    - Generate valid and invalid URLs plus crawl policies and assert stable normalization, one frontier identity for duplicates, recorded rejection reasons, and no fetch for blocked/out-of-policy/robots-disallowed URLs.
    - Tag the test `Feature: complete-search-engine-project, Property 3: URL policy and duplicate elimination`.
    - **Validates: Requirements 3.4**

  - [ ] 4.3 Implement bounded crawler fetch/retry state machines and HTML extraction
    - Add the configured user agent, timeout, redirect, content-type, response-size, transient-status, retry/backoff, and terminal-failure behavior.
    - Complete extraction of title, metadata, headings, cleaned body, canonical URL, language/content fields, content hash, and normalized outlinks while removing configured non-content elements.
    - Validate controlled HTTP fixtures for accepted HTML, invalid content, redirects, retry exhaustion, response limits, and deterministic extraction.
    - _Requirements: 3.3, 3.5, 3.6_

  - [ ]* 4.4 Write Property 4 tests for bounded crawler retry state transitions
    - Generate retryable/terminal outcome sequences and configuration limits and assert retries occur only within bounds, backoff is bounded, and one final persisted failure retains its reason.
    - Tag the test `Feature: complete-search-engine-project, Property 4: Bounded crawler retry state machine`.
    - **Validates: Requirements 3.5**

  - [ ]* 4.5 Write Property 5 tests for HTML extraction facts
    - Generate supported HTML metadata, headings, body, canonical links, and outlinks with non-content elements and assert required facts, normalized links, deterministic hashes, and cleaned text.
    - Tag the test `Feature: complete-search-engine-project, Property 5: HTML extraction preserves required document facts`.
    - **Validates: Requirements 3.6**

  - [ ] 4.6 Implement durable crawl-job execution, document upsert, discovered-link enqueueing, and post-commit index-task emission
    - Add crawler repositories/workers for job creation/start/pause/resume/cancel/completion/failure, queue claims, counters, timestamps, and failure reasons.
    - Upsert documents by normalized/canonical URL and content identity, enqueue discovered URLs within policy, and publish exactly one versioned idempotent index event only after the document transaction commits.
    - Validate state transitions, duplicate seeds, cancellation, failure persistence, durable commit-before-publish behavior, and queue counters.
    - _Requirements: 3.1, 3.2, 3.7, 3.8_

  - [ ] 4.7 Implement Indexer field processing, positional postings, term statistics, and dead-letter consumption
    - Complete `services/indexer` to consume the shared event, remove non-content data, tokenize/normalize configured fields, apply stopwords/stemming, preserve positions, replace prior postings transactionally, and update DF/TF/IDF.
    - Support title, heading, body, metadata, anchor, structured-data/image-alt, and URL-relevant fields where present.
    - Acknowledge only after commit and route malformed/exhausted messages to the durable dead-letter queue.
    - Validate repeatable postings, term statistics, transaction rollback, malformed messages, and acknowledgement timing.
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 4.8 Write Property 6 tests for postings and term-statistics consistency
    - Generate document collections and text-processing policies and assert postings’ frequencies/positions and term DF/TF/IDF match the processed field model.
    - Tag the test `Feature: complete-search-engine-project, Property 6: Index postings and statistics match the document model`.
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 4.9 Write Property 7 tests for idempotent index delivery
    - Apply each generated index task once and repeatedly and assert one logical document version, no duplicate `(term, document, field)` postings, and equivalent final statistics.
    - Tag the test `Feature: complete-search-engine-project, Property 7: Index delivery is idempotent`.
    - **Validates: Requirements 3.7, 4.3**

  - [ ] 4.10 Implement Ranker BM25, PageRank, score composition, and bounded HTTP API
    - Complete `services/ranker` with field-aware BM25 using configured `k1`, `b`, IDF, field weights, and length normalization; persist/read PageRank over the document link graph with dangling-node and convergence handling.
    - Add freshness, phrase, prefix, and diversification composition from `config/ranking.yaml`; keep learning-to-rank behind a disabled-by-default flag.
    - Expose bounded candidate-scoring requests and a scheduled/worker PageRank update path; return controlled degraded behavior rather than unbounded calls.
    - Validate direct BM25 references, graph edge cases, configuration weights, timeout behavior, and persisted authority values.
    - _Requirements: 4.4, 4.5, 4.6, 8.4_

  - [ ]* 4.11 Write Property 8 tests for BM25 reference equivalence
    - Generate valid corpora, query terms, frequencies, lengths, and configurations and compare Ranker scores with the direct configured BM25 formula within documented floating-point tolerance.
    - Tag the test `Feature: complete-search-engine-project, Property 8: BM25 agrees with the configured reference formula`.
    - **Validates: Requirements 4.4**

  - [ ]* 4.12 Write Property 9 tests for PageRank graph invariants
    - Generate finite directed graphs including dangling nodes and assert termination within the iteration bound, non-negative normalized scores, configured damping behavior, and one persisted score per participating document.
    - Tag the test `Feature: complete-search-engine-project, Property 9: PageRank graph invariants`.
    - **Validates: Requirements 4.5**

  - [ ]* 4.13 Write Property 10 tests for configured score composition
    - Generate candidate feature vectors and ranking configurations and assert only enabled weighted signals affect the final score and each signal follows its configured weight.
    - Tag the test `Feature: complete-search-engine-project, Property 10: Configured score composition`.
    - **Validates: Requirements 4.6**

  - [ ] 4.14 Implement Search API normalization, parsing, retrieval, filters, snippets, pagination, cache, and logging
    - Complete `services/search-api` in the documented order: validation, Unicode/whitespace/operator normalization, optional correction/expansion, Boolean/phrase/field parsing, positional postings retrieval, Ranker request, safe/site/language/date filtering, diversification, snippets/highlights, pagination, and response shaping.
    - Add Redis caching for eligible non-personalized responses, bounded suggestion lookup with deterministic types/order, opaque query contexts, and query/click logging hooks.
    - Return successful honest zero-result responses and controlled dependency errors; never make an unbounded Ranker request.
    - Validate search/suggest/click schemas, filters, phrases/operators, pagination metadata, snippets, cache hit/miss, zero results, and failure mapping.
    - _Requirements: 2.2, 2.3, 4.6, 4.7, 4.8, 4.9, 7.1_

  - [ ]* 4.15 Write Property 1 tests for contract-complete search responses
    - Generate valid queries, pagination, and filters and assert normalized query, optional correction, result collection, counts, bounded pagination, elapsed time, cache status, and opaque query context; invalid input must use the common validation error.
    - Tag the test `Feature: complete-search-engine-project, Property 1: Contract-complete search responses`.
    - **Validates: Requirements 2.2, 2.7**

  - [ ]* 4.16 Write Property 2 tests for bounded typed suggestions
    - Generate partial queries and valid limits and assert every suggestion has a non-empty type, deterministic order, and count no greater than the effective limit.
    - Tag the test `Feature: complete-search-engine-project, Property 2: Bounded typed suggestions`.
    - **Validates: Requirements 2.3**

  - [ ]* 4.17 Write Property 11 tests for query pipeline stage invariants
    - Generate supported query syntax and indexed corpora and assert normalization precedes parsing, constraints affect retrieval, ranking sees only candidates, snippets/highlights reference returned documents, and pagination is a disjoint ordered slice with unpaginated counts.
    - Tag the test `Feature: complete-search-engine-project, Property 11: Query pipeline stage invariants`.
    - **Validates: Requirements 4.7**

  - [ ]* 4.18 Write Property 12 tests for honest empty-result responses
    - Generate normalized queries with no matching documents and assert successful zero-result responses preserve the normalized query and include only available correction/suggestion information.
    - Tag the test `Feature: complete-search-engine-project, Property 12: Empty-result responses are successful and honest`.
    - **Validates: Requirements 4.8, 7.3**

  - [ ] 4.19 Wire and verify the minimal offline vertical slice
    - Connect crawler fixture input → durable document → RabbitMQ index task → Indexer postings/statistics → Ranker score → Search API result/cache/query log.
    - Add deterministic small-corpus fixtures and the repeatable command `python -m scripts.validate_vertical_slice --report artifacts/validation/core-pipeline.json` that proves the full path without an external website.
    - Make the command emit stage-by-stage evidence for document commit, one idempotent index event, postings/statistics, Ranker scoring, Search API ordering/cache behavior, and query analytics; validate duplicate delivery, cache behavior, search result ordering, and analytics records at the pipeline boundary.
    - _Requirements: 3.7, 4.1–4.9, 9.1, 10.2_

- [ ] 5. Checkpoint — Core pipeline gate
  - [ ] 5.1 Execute the core pipeline gate verification
    - Run `python -m scripts.validate_vertical_slice --report artifacts/validation/core-pipeline.json` with controlled offline fixtures and required PostgreSQL, Redis, and RabbitMQ dependencies.
    - Require exit code 0 and attach `artifacts/validation/core-pipeline.json` as evidence containing document persistence, post-commit index-event publication, repeatable postings/term statistics, bounded Ranker scoring, ordered Search API results, eligible-cache behavior, and query/click analytics records.
    - Do not start Phase 3 frontend work until the report proves the crawl-to-index-to-rank-to-search path; a failed or missing stage blocks all later waves.

- [ ] 6. Phase 3 — Frontend search and shared experience
  - [ ] 6.1 Implement shared UI primitives, layout, pages, protected routing, login route, settings route, and unknown-route fallback
    - Complete `frontend/src/components/ui`, `layout`, `search`, `pages`, and the route table in `App.tsx` using semantic elements and the existing Tailwind/theme conventions.
    - Add `SearchPage`, `ResultsPage`, `LoginPage`, `AdminDashboard`, `AnalyticsDashboard`, `SettingsPage`, and `NotFoundPage` without unresolved imports.
    - Keep protected routing as a client presentation guard while retaining server-side authorization as the source of truth.
    - Validate production build and route rendering for every declared path.
    - _Requirements: 1.6, 5.1, 6.7_

  - [ ] 6.2 Connect typed API contracts to React Query hooks, URL state, and transient stores
    - Complete `frontend/src/services/api.ts`/`contracts.ts`, `useSearch`, `useAutocomplete`, and the search store so query/filter/page/per-page state is shareable in the URL.
    - Keep React Query responsible for server state/cache and Zustand responsible for transient input, suggestion focus, theme, sidebar, and session UI state.
    - Initialize theme through a store initializer or dedicated effect rather than an unconditional render side effect.
    - Validate query submission, browser back/forward, cache state, and typed request/response fields.
    - _Requirements: 5.2, 5.3, 5.6_

  - [ ] 6.3 Implement search results, autocomplete keyboard/pointer behavior, pagination, zero-results, and recoverable errors
    - Render titles, URLs, snippets, scores/metadata, highlights, loading skeletons, pagination, correction/suggestion paths, and failure recovery without losing the current query.
    - Debounce suggestions and disable them below the configured minimum; make Arrow keys, Enter, Escape, and pointer selection share one selection model.
    - Preserve the typed value until explicit suggestion selection and use replace/push URL semantics as designed.
    - Validate search, suggestions, no results, API failure, pagination, and keyboard flows with component tests.
    - _Requirements: 5.2, 5.3, 5.5, 5.7_

  - [ ] 6.4 Implement click tracking with opaque query context and non-blocking navigation
    - Add `useClickTracking` and result-card integration to send document ID, query context, position, and optional dwell time through the click contract.
    - Ensure click logging failures do not prevent navigation and do not expose database identifiers beyond the documented opaque context.
    - Validate payloads, position/context association, request failure recovery, and navigation behavior.
    - _Requirements: 5.4, 7.1_

  - [ ] 6.5 Complete responsive, dark/light, focus-visible, keyboard, reduced-motion, and WCAG AA-targeted behavior
    - Apply semantic labels, visible focus states, contrast-safe theme tokens, responsive desktop/mobile layouts, and reduced-motion behavior to search, login, admin, and analytics surfaces.
    - Validate automated accessibility rules and responsive rendering at the project’s desktop/mobile breakpoints; record target limitations rather than claiming unmeasured conformance.
    - _Requirements: 5.6_

  - [ ]* 6.6 Add frontend component and accessibility tests for search flows
    - Test routes, URL state, loading/error/empty states, suggestion selection, click tracking, keyboard navigation, theme behavior, focus visibility, and accessible names.
    - _Requirements: 5.1–5.7, 10.3_

- [ ] 7. Phase 4 — Authentication, RBAC, administration, and analytics
  - [ ] 7.1 Implement secure administrator login, refresh rotation, token validation, and authentication failure behavior
    - Complete Admin API authentication with adaptive password hashing, signed access/refresh JWT claims, issuer/audience/type/expiry/active-user checks, configured lifetimes, and refresh rotation/revocation policy.
    - Use indistinguishable invalid-credential/inactive-account errors, development-only secret labeling, and no secret leakage in logs or responses.
    - Complete frontend auth storage/session handling so authentication failures clear credentials, preserve no usable secret in page state, and redirect recoverably to login.
    - Validate login, refresh, malformed/expired token, inactive user, timestamp update, and frontend logout/redirect behavior.
    - _Requirements: 6.1, 6.2, 6.3, 6.7, 8.6_

  - [ ] 7.2 Centralize the role/permission matrix and enforce protected Admin API dependencies
    - Implement `viewer`, `operator`, and `admin` permissions in the shared security primitive while keeping endpoint-specific required permissions in Admin API dependencies.
    - Enforce 401 for missing/invalid principals and 403 for insufficient privileges using authenticated identity rather than client-supplied roles.
    - Validate read-only, crawl-control, settings, API-key, administrator-management, and audit permissions.
    - _Requirements: 6.4, 6.5, 6.6_

  - [ ]* 7.3 Write Property 13 tests for consistent RBAC enforcement
    - Generate endpoint/principal combinations and assert missing principals receive 401, insufficient active principals receive 403, and permitted roles can execute only matrix-approved operations.
    - Tag the test `Feature: complete-search-engine-project, Property 13: Permission matrix is enforced consistently`.
    - **Validates: Requirements 6.4, 6.5, 6.6**

  - [ ] 7.4 Complete Admin API crawl controls, queue/index stats, safe settings, API-key lifecycle, and audit events
    - Implement create/list/detail/pause/resume/cancel/status/queue statistics, index statistics, typed allowlisted setting reads/updates, and role-restricted API-key create/list/revoke operations.
    - Return a plaintext API key only at creation, persist only secure hash/prefix plus owner/IP/rate/active/expiry/last-use metadata, and update last use without logging key material.
    - Record actor, role, action, target, timestamp, correlation ID, outcome, and safe reason for setting, key, role, and crawl-state changes.
    - Validate CRUD schemas, legal state transitions, key redaction/expiry/revocation, setting allowlists, and audit persistence.
    - _Requirements: 2.4, 6.5, 6.6, 6.8, 6.9_

  - [ ] 7.5 Implement analytics aggregation contracts and Admin API read models
    - Aggregate query/click logs by bounded requested range for volume, top queries, CTR when clicks exist, zero-result queries, latency statistics/percentiles, and supported filters.
    - Return explicit empty/unavailable values and the requested range when samples do not exist; never fabricate metrics.
    - Validate query/click persistence, range boundaries, filter dimensions, percentile calculations, and unavailable metrics.
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 7.6 Write Property 17 tests for analytics sample truthfulness
    - Generate query/click logs and date ranges and assert only in-range records contribute, supported metrics use available samples, filter dimensions remain intact, and unsupported samples return explicit empty/unavailable values.
    - Tag the test `Feature: complete-search-engine-project, Property 17: Analytics aggregation reflects available samples`.
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [ ] 7.7 Complete frontend authentication, admin controls, settings, and analytics dashboard integration
    - Add `useAuth`, `useAdmin`, and `useAnalytics`; connect login, protected routes, crawl mutations, queue/index KPI views, settings/API-key actions, date-range controls, query-volume/top-query/zero-result/latency views, and explicit loading/empty/error states.
    - Invalidate React Query data after admin mutations and preserve last successful analytics data when appropriate.
    - Validate role-specific controls, auth expiry recovery, dashboard query parameters, mutation invalidation, and honest empty states.
    - _Requirements: 5.1, 6.5–6.7, 7.4_

  - [ ]* 7.8 Implement optional authenticated SSE/WebSocket operational updates
    - Add a disabled-by-default Admin API stream for documented queue/crawl/index/latency snapshots and a frontend client that marks stale data, retries with backoff, and keeps the last snapshot on disconnect.
    - Keep the authoritative analytics query path functional when streaming is disabled or unavailable.
    - Validate authentication, event schema, disconnect/retry behavior, stale status, and manual refresh.
    - _Requirements: 7.5, 7.6_

- [ ] 8. Phase 5 — Operations, resilience, and security hardening
  - [ ] 8.1 Expand typed operational configuration and `.env.example` with safe production-mode validation
    - Cover database, Redis, RabbitMQ, JWT issuer/audience/secret, CORS, rate limits, cache TTLs, timeouts, crawler/ranking overrides, service URLs, logging, migration mode, frontend API URL, and production mode.
    - Apply defaults in the documented order: code defaults, YAML policy, environment overrides, then allowlisted persisted runtime settings.
    - Reject placeholder/weak production secrets and invalid URLs, ranges, ports, timeouts, origins, and weights before readiness; log effective non-secret values only.
    - Validate defaults, override precedence, production rejection, and redaction.
    - _Requirements: 8.1, 8.2, 8.6_

  - [ ]* 8.2 Write Property 14 tests for configuration validation and redaction
    - Generate supported override sets and assert valid values resolve defaults/overrides, invalid security/connection/range values fail before readiness, and logs contain no password, token, private key, or API-key material.
    - Tag the test `Feature: complete-search-engine-project, Property 14: Configuration is validated and redacted`.
    - **Validates: Requirements 8.1, 8.2, 8.6**

  - [ ] 8.3 Implement bounded dependency retry, reconnect, circuit protection, graceful shutdown, and durable failure behavior
    - Apply explicit HTTP connect/read/total timeouts, safe-operation retries, bounded PostgreSQL/Redis/RabbitMQ reconnects, RabbitMQ confirms/ack timing, Redis cache degradation, and durable crawler/indexer failure states.
    - Add worker stop/negative-ack/in-flight handling and service shutdown within configured grace periods.
    - Validate transient dependency loss, duplicate commands/deliveries, retry exhaustion, cache degradation, and no-ack-before-commit behavior.
    - _Requirements: 2.5, 3.5, 4.3, 8.3, 8.4_

  - [ ]* 8.4 Write Property 15 tests for transient dependency loss and durable work
    - Generate bounded PostgreSQL, Redis, RabbitMQ, and downstream HTTP failures plus duplicate deliveries and assert bounded recovery, one idempotent durable result or terminal failure, and no premature acknowledgement.
    - Tag the test `Feature: complete-search-engine-project, Property 15: Transient dependency loss does not duplicate durable work`.
    - **Validates: Requirements 8.4, 4.3**

  - [ ] 8.5 Finalize gateway/Nginx edge policy and structured operational visibility
    - Align `config/nginx.conf` and gateway middleware for CORS, request/body size, endpoint rate limits, connection limits, security headers, trusted proxies, internal-admin restrictions, TLS/deployment profile settings, metrics access, and health exposure.
    - Add structured request/worker logs, redaction, service/dependency labels, and correlation IDs suitable for failure diagnosis.
    - Validate policy parity, rate limiting, headers, trusted-proxy rejection, log redaction, and protected direct service ports.
    - _Requirements: 2.5, 2.7, 8.3, 8.5, 8.7, 10.4_

- [ ] 9. Phase 5 — Offline demo data and operator documentation
  - [ ] 9.1 Implement deterministic offline demo-data loading and repeatable fixture reporting
    - Create `scripts/seed_demo_data.py` or an equivalent module entrypoint with stable fixture IDs/upserts for documents, crawl jobs/frontier, postings, term statistics, PageRank, query/click logs, autocomplete sources, and one active admin for each documented role.
    - Use bundled/generated content without network access and report inserted, skipped, updated, and total counts by category.
    - Validate clean and repeated loads, migrated baseline compatibility, complete category coverage, and no duplicate logical records.
    - _Requirements: 9.1, 9.2, 9.5_

  - [ ]* 9.2 Write Property 16 tests for deterministic repeatable demo loading
    - Run the offline loader against clean and already-loaded databases and assert stable fixture identities, complete categories, and no duplicate documents, postings, logs, or suggestions on repeat runs.
    - Tag the test `Feature: complete-search-engine-project, Property 16: Demo loading is deterministic and repeatable`.
    - **Validates: Requirements 9.1, 9.2**

  - [ ]* 9.3 Add the optional controlled external-crawl demo path
    - Require explicit seeds/domains and configuration, respect robots and politeness policy, and persist source/retrieval metadata; keep offline fixtures as the default.
    - Validate configuration refusal when external crawling is not explicitly enabled and controlled HTTP behavior when it is enabled.
    - _Requirements: 9.3_

  - [ ] 9.4 Write architecture, API, deployment, operations, troubleshooting, demo, and known-limitations documentation
    - Add/update `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/deployment.md`, `docs/operations.md`, and `docs/troubleshooting.md` with service ownership, setup/migration commands, environment variables, contracts, crawl/ranking operations, analytics, security, health checks, and failure recovery.
    - Document the clean-start → migrate → readiness → seed → search/suggest → login → crawl inspection → analytics workflow, optional capabilities, implementation boundaries, and every performance target as measured or unmeasured.
    - Add the required `python -m scripts.validate_demo_workflow --report <path>` command used by gate 10; it must exercise the documented offline workflow and write machine-readable evidence without external network access.
    - Validate all commands, paths, route names, environment variables, and internal documentation links against the repository.
    - _Requirements: 1.5, 8.7, 9.4, 9.5, 9.6_

- [ ] 10. Checkpoint — Demo and operations gate
  - [ ] 10.1 Execute the demo and operations gate verification
    - Run `python -m scripts.validate_demo_workflow --report artifacts/validation/demo-operations.json` using the documented clean-start workflow and offline fixtures.
    - Require exit code 0 and attach `artifacts/validation/demo-operations.json` as evidence containing migration/readiness results, deterministic seed counts, successful search and suggestion responses, authentication, crawl/index inspection, analytics rendering/API results, documentation-command checks, and any explicitly unavailable optional capability.
    - Do not start Phase 6 validation work until the report proves the reviewer workflow is executable; external crawling and real-time streaming remain optional and must be labeled as such.

- [ ] 11. Phase 6 — Layered validation and optional benchmarks
  - [ ]* 11.1 Complete unit/property coverage for pure algorithms and policy state machines
    - Cover URL normalization/filtering, extraction, tokenization/stemming/positions, query parsing, snippets/highlights, BM25, PageRank, score composition, frontier/retry/politeness, rate limits, auth/token validation, RBAC, configuration, error mapping, and redaction.
    - Require at least 100 generated cases per correctness property and use the feature/property tags from the design.
    - Validate deterministic fixtures, floating-point tolerances, edge cases, and no external network/cloud dependencies.
    - _Requirements: 10.1, 10.4_

  - [ ]* 11.2 Add disposable-dependency integration tests for service data flow and failures
    - Run against disposable/configured PostgreSQL, Redis, and RabbitMQ and verify migrations, seeded Search API behavior, crawler persistence, crawler→Indexer delivery, dead letters, Indexer→Ranker data, Admin CRUD/auth/RBAC/API-key/audit/analytics behavior, and health/dependency error mappings.
    - Use controlled HTTP fixtures rather than external websites and report service/layer/dependency/fixture context on failure.
    - _Requirements: 10.2, 10.4_

  - [ ]* 11.3 Add Compose-backed end-to-end/browser tests
    - Verify startup readiness, authentication, search, URL state, autocomplete, result click logging, crawl control, analytics rendering, optional stream behavior when enabled, unknown routes, and recoverable Search API/suggestion failures.
    - Capture gateway/service logs by request ID and fail explicitly when a dependency or fixture is unavailable.
    - _Requirements: 10.3, 10.4_

  - [ ] 11.4 Implement a validation summary that distinguishes functional truth from limitations and unmeasured goals
    - Add `scripts/validate_release.py` (or an equivalent documented module entrypoint) and make `python -m scripts.validate_release --report artifacts/validation/release-readiness.json` the repeatable final validation command.
    - Make the command run or collect build, migration, smoke, contract, core-pipeline, demo-workflow, unit/property, integration, end-to-end, and documentation-link results; record test name, layer, service, dependency, fixture, failure reason, known limitations, and functional pass/fail state.
    - Explicitly mark optional tests/capabilities as skipped and benchmark goals unmeasured when Benchmark Infrastructure is unavailable; never silently skip failures or claim targets from configuration alone.
    - Validate the summary against passing, failing, unavailable-dependency, and optional-test cases.
    - _Requirements: 10.4, 10.6, 10.7_

  - [ ]* 11.5 Add repeatable search, autocomplete, and crawl benchmark scenarios
    - Add `scripts/benchmark_search.py`, Locust, or an equivalent harness with declared environment, dataset size, concurrency, throughput, error rate, p50/p95/p99, and comparison to the implementation-plan goals.
    - Keep benchmark execution separate from functional validation and report search (1,000 req/s, p99 < 200 ms), autocomplete (500 req/s, p99 < 50 ms), and crawl (1,000 pages/minute) as goals unless measured.
    - Validate repeatability and report unmeasured status when required infrastructure is absent.
    - _Requirements: 10.5, 10.6, 9.6_

  - [ ]* 11.6 Write Property 18 tests for validation diagnostic truth
    - Generate validation runs containing passing, failing, unavailable-dependency, and optional-benchmark cases and assert complete diagnostic context, functional/limitation separation, and unmeasured benchmark status.
    - Tag the test `Feature: complete-search-engine-project, Property 18: Validation preserves diagnostic truth`.
    - **Validates: Requirements 10.4, 10.5, 10.6, 10.7**

- [ ] 12. Final checkpoint — Release-readiness validation
  - [ ] 12.1 Execute the final release-readiness gate verification
    - Run `python -m scripts.validate_release --report artifacts/validation/release-readiness.json` after all required implementation and validation tasks complete.
    - Require exit code 0 and attach `artifacts/validation/release-readiness.json` as the auditable final artifact. It must include passing evidence or explicit status for foundation, contracts, core pipeline, demo/operations, build, migration, smoke, unit/property, integration, end-to-end, documentation-link, and benchmark checks.
    - The report must distinguish required functional failures from optional skipped tasks, known limitations, unavailable dependencies, and measured versus unmeasured performance goals; a missing upstream gate artifact or silently skipped failure is a release-readiness failure.
    - Do not claim release readiness until the report exists, all required gate nodes are green, and optional/unmeasured status is explicit.

## Notes

- Tasks follow the design’s required phase order. Do not start a later phase until the prior checkpoint’s exit condition is met.
- The five required gates are foundation (`2.1` → `artifacts/validation/foundation.json`), contract foundation (`3.7` → `artifacts/validation/contracts.json`), core pipeline (`5.1` → `artifacts/validation/core-pipeline.json`), demo and operations (`10.1` → `artifacts/validation/demo-operations.json`), and final release readiness (`12.1` → `artifacts/validation/release-readiness.json`). Each gate requires its exact command to exit 0 and its artifact to exist; later waves are ordered after the corresponding gate node.
- `*` marks optional test tasks or optional capabilities. Optional capabilities are SSE/WebSocket operational updates, learning-to-rank, controlled external crawling, analytics rollups if later introduced, TLS/external deployment profiles, and benchmark execution; the offline core remains required.
- Property-based tests are complementary to example/unit/integration tests. Each design property has its own task and must use at least 100 generated cases when implemented.
- PostgreSQL remains the durable source of truth; Redis failure may disable cache/live snapshots but must not lose crawl/index/job state. RabbitMQ messages are acknowledged only after durable effects commit.
- The implementation-plan throughput/latency figures are goals, not guarantees. Only benchmark evidence may mark them measured.
- This document contains coding and automated-testing work only. It does not include deployment execution, manual acceptance testing, training, or presentation work.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.4"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.5"] },
    { "id": 3, "tasks": ["2.1"] },
    { "id": 4, "tasks": ["3.1", "3.2", "3.3"] },
    { "id": 5, "tasks": ["3.4", "3.5"] },
    { "id": 6, "tasks": ["3.6", "3.7"] },
    { "id": 7, "tasks": ["4.1", "4.3"] },
    { "id": 8, "tasks": ["4.2", "4.4", "4.5", "4.7", "4.10"] },
    { "id": 9, "tasks": ["4.6", "4.8", "4.9", "4.11", "4.12", "4.13"] },
    { "id": 10, "tasks": ["4.14"] },
    { "id": 11, "tasks": ["4.15", "4.16", "4.17", "4.18"] },
    { "id": 12, "tasks": ["4.19"] },
    { "id": 13, "tasks": ["5.1"] },
    { "id": 14, "tasks": ["6.1", "6.2", "7.1", "7.2", "8.1", "9.1"] },
    { "id": 15, "tasks": ["6.3", "6.4", "6.5", "7.4", "7.5", "8.3", "8.5", "9.4"] },
    { "id": 16, "tasks": ["6.6", "7.3", "7.6", "7.7", "8.2", "8.4", "9.2", "9.3"] },
    { "id": 17, "tasks": ["7.8"] },
    { "id": 18, "tasks": ["10.1"] },
    { "id": 19, "tasks": ["11.1", "11.2"] },
    { "id": 20, "tasks": ["11.3", "11.5"] },
    { "id": 21, "tasks": ["11.4"] },
    { "id": 22, "tasks": ["11.6"] },
    { "id": 23, "tasks": ["12.1"] }
  ]
}
```
