# Requirements Document

## Introduction

Luna is a Dockerized search-engine project with a planned microservice architecture. The repository currently contains a partial foundation: an implementation plan, Docker Compose definitions for PostgreSQL, Redis, RabbitMQ, backend services, and the frontend; environment and crawler/ranking/nginx configuration; Alembic migrations for crawl, document, index, analytics, and administration data; Python service Dockerfiles and package metadata; shared Python package structure; and a React/Vite/TypeScript application shell with API, query, theme, store, and type scaffolding. Several service modules are partial, frontend routes reference pages and components that are not present, and the full crawl-to-index-to-rank-to-search path is not yet runnable as one system.

This feature completes the existing Luna architecture rather than replacing the architecture. Completion starts with a reproducible build and runnable local environment, then closes service contracts and the crawl-to-index-to-rank-to-search pipeline, completes frontend pages and API integration, completes authentication, RBAC, administration, and analytics, hardens operational configuration, supplies demo data and documentation, and validates behavior with unit, integration, end-to-end, and optional benchmark tests.

### Foundation Status

The following items are existing foundations and SHALL be preserved unless an implementation change is required to make a foundation buildable or contract-compatible:

- The service boundaries and ports described in `IMPLEMENTATION_PLAN.md` and `docker-compose.yml`.
- PostgreSQL, Redis, RabbitMQ, and Nginx configuration files, including health-check and rate-limit intent.
- Alembic revisions `001_initial_schema.py` and `002_add_pg_trgm_extension.py`, including tables for documents, postings, term statistics, crawl jobs and queue entries, query and click logs, admin users, API keys, and settings.
- Python service Dockerfiles, `pyproject.toml` files, shared package directories, and partial FastAPI, crawler, indexer, gateway, and admin implementations.
- The React/Vite/TypeScript frontend shell, route intent, API client, React Query integration, Zustand stores, theme styles, and search/admin/analytics type intent.
- Crawler and ranking configuration values as configurable defaults rather than proof of measured production performance.

The remaining work is to make the foundations executable, complete, consistent, observable, documented, and tested. No requirement treats a configured scale or latency number as achieved without benchmark infrastructure and a recorded benchmark result.

## Glossary

- **Luna**: The complete search-engine product composed of the Repository, backend services, infrastructure, and Frontend.
- **Repository**: The source tree at the project root, including service code, shared code, migrations, configuration, documentation, and validation code.
- **Build System**: The documented dependency installation, image build, migration, test, and startup process for the Repository.
- **Compose Environment**: The local Docker Compose deployment containing PostgreSQL, Redis, RabbitMQ, API Gateway, Search API, Crawler Service, Indexer Service, Ranker Service, Admin API, and Frontend.
- **API Gateway**: The public FastAPI routing service on port 8000 that authenticates, rate-limits, and forwards public and administrative requests.
- **Search API**: The service on port 8001 that parses queries, retrieves documents, requests or applies ranking, returns results, provides suggestions, and records query activity.
- **Crawler Service**: The service that schedules and fetches web pages, applies URL and robots policies, extracts crawl content, persists crawl state, and emits index tasks.
- **Indexer Service**: The service that consumes crawl tasks, extracts and tokenizes content, builds the inverted index, and maintains term statistics.
- **Ranker Service**: The service that calculates BM25 and PageRank-based relevance scores and returns ranked document candidates.
- **Admin API**: The authenticated service on port 8005 for crawl control, index statistics, analytics, settings, and API-key administration.
- **Authentication Service**: The authentication behavior exposed by the Admin API for administrator login, refresh, token validation, and credential lifecycle handling.
- **Frontend**: The React/TypeScript application on port 3000 containing search, results, administration, analytics, settings, authentication, and shared layout pages.
- **Analytics Dashboard**: The Frontend view that presents query, click, latency, zero-result, crawl, index, and operational metrics.
- **Service Contract**: A versioned request, response, error, authentication, and health behavior shared by a service and its callers.
- **Crawl Job**: A persisted crawl request containing seed URLs, domain policy, depth and page limits, politeness settings, priority, status, and counters.
- **Crawl Queue**: The persisted prioritized URL frontier associated with a Crawl Job.
- **Document**: A crawled page and extracted metadata stored in PostgreSQL.
- **Inverted Index**: A term-to-document mapping containing field, frequency, positions, and score data.
- **Positional Index**: An Inverted Index containing token positions so phrase and proximity matching can be evaluated.
- **BM25**: The configurable lexical relevance scoring algorithm described in the implementation plan.
- **IDF**: Inverse document frequency, the term-statistics value used by BM25 and index scoring.
- **PageRank**: The configurable link-graph authority score described in the implementation plan.
- **Query Pipeline**: The ordered processing flow from input normalization through parsing, retrieval, scoring, filtering, ranking, snippet generation, pagination, and logging.
- **Analytics Pipeline**: The process that aggregates query logs and click logs into dashboard metrics.
- **RBAC**: Role-based access control applied to authenticated administrative operations.
- **JWT**: A signed access or refresh token used for authenticated API requests.
- **Operational Configuration**: Environment variables and YAML/Nginx settings controlling service connections, security, crawling, ranking, caching, logging, and deployment.
- **CORS**: Cross-origin resource sharing policy controlling browser requests from configured Frontend origins.
- **Nginx**: The reverse proxy configuration layer that terminates or forwards external HTTP traffic and applies edge policies.
- **WCAG AA**: The project accessibility conformance target for perceivable, operable, understandable, and robust Frontend behavior.
- **WebSocket or Server-Sent Event Stream**: An authenticated long-lived connection used for optional real-time operational updates.
- **Demo Data Set**: Reproducible documents, crawl metadata, index data, PageRank values, query logs, click logs, and autocomplete data used for local demonstration.
- **Validation Suite**: Unit, integration, end-to-end, and optional benchmark tests executed against the Repository.
- **Benchmark Infrastructure**: A declared environment and load-test tool capable of measuring throughput, latency, or crawl rate; local startup alone does not constitute Benchmark Infrastructure.
- **Performance Goal**: A target used for comparison rather than an achieved guarantee, including the implementation-plan goals of 1,000 search requests per second with p99 below 200 milliseconds, 500 autocomplete requests per second with p99 below 50 milliseconds, and 1,000 crawled pages per minute.
- **Latency Percentile**: A percentile measurement such as p50, p95, or p99 describing the response time below which the stated proportion of measurements falls.

## Requirements

### Requirement 1: Reproducible build and runnable foundation

**User Story:** As a developer, I want a reproducible build and local startup path, so that I can run Luna before implementing or evaluating feature behavior.

#### Acceptance Criteria

1. WHEN a developer follows the documented setup commands on a supported host, THE Build System SHALL install or resolve all backend, shared-library, frontend, and test dependencies without missing package, import, or generated-file errors.
2. WHEN a developer builds the Compose Environment, THE Build System SHALL build every declared service image from the Repository and SHALL expose the documented local ports for the API Gateway, Search API, Ranker Service, Admin API, Frontend, PostgreSQL, Redis, and RabbitMQ.
3. WHEN the Compose Environment starts against an empty PostgreSQL volume, THE Build System SHALL apply the Alembic migrations in dependency order and SHALL leave the database schema ready for service startup.
4. WHEN a service cannot connect to a required dependency, THE Build System SHALL report the service name, dependency name, and remediation-oriented failure reason in startup logs.
5. THE Repository SHALL provide documented commands for dependency setup, migration, Compose startup, service health checks, unit tests, integration tests, and end-to-end tests.
6. IF a referenced source module, page, component, entrypoint, or test is absent, THEN THE Build System SHALL provide the required implementation or update the reference so that the declared build and test commands complete successfully.

### Requirement 2: Stable public and internal service contracts

**User Story:** As an application integrator, I want stable service contracts, so that the Frontend, gateway, workers, and operational tools can communicate predictably.

#### Acceptance Criteria

1. THE API Gateway SHALL route public search and suggestion requests to the Search API and SHALL route authenticated administrative requests to the Admin API using the configured service URLs.
2. WHEN a client submits a search request containing `q`, pagination, site, language, safe-search, or date-range parameters, THE Search API SHALL validate the parameters and SHALL return a documented response containing query normalization, optional correction, results, result count, pagination, elapsed time, and cache status.
3. WHEN a client submits a suggestion request containing a partial query and limit, THE Search API SHALL return ordered suggestions with a type for every suggestion and SHALL enforce the configured limit range.
4. WHEN a client submits a crawl-job create, list, detail, update, or queue-statistics request, THE Admin API SHALL validate the request and SHALL return the documented Crawl Job or queue-statistics schema.
5. WHEN a downstream service is unavailable or exceeds the configured timeout, THE API Gateway SHALL return a documented 502 or 504 error response and SHALL record a correlation identifier in gateway logs.
6. THE API Gateway, Search API, Crawler Service, Indexer Service, Ranker Service, and Admin API SHALL expose health and readiness responses that identify service status and required dependency status.
7. IF a request violates a documented schema, authentication rule, authorization rule, or rate limit, THEN THE responsible API SHALL return a stable error shape with an appropriate HTTP status and an actionable error code or message.

### Requirement 3: Crawl job execution and polite acquisition

**User Story:** As a search operator, I want crawl jobs to fetch permitted pages safely and reliably, so that Luna can acquire content without violating configured crawl policies.

#### Acceptance Criteria

1. WHEN an authorized operator creates a Crawl Job, THE Admin API SHALL persist the job configuration, enqueue normalized seed URLs, and expose a pending job status.
2. WHEN a Crawl Job is running, THE Crawler Service SHALL select URLs by priority and schedule time, enforce maximum depth and page limits, track attempts and counters, and persist queue status transitions.
3. WHILE a Crawl Job is running, THE Crawler Service SHALL apply robots.txt decisions, configured user-agent identity, per-domain delay, per-domain concurrency, global concurrency, redirect limits, content-type limits, and response-size limits.
4. IF a URL is invalid, blocked, outside the allowed-domain policy, duplicated after normalization, or disallowed by robots.txt, THEN THE Crawler Service SHALL record the decision and SHALL keep the URL out of the fetch set.
5. IF a fetch receives a retryable status or configured transient error, THEN THE Crawler Service SHALL retry within the configured attempt and backoff limits and SHALL persist the final failure when retry attempts are exhausted.
6. WHEN the Crawler Service accepts an HTML response, THE Crawler Service SHALL extract title, metadata description, heading hierarchy, cleaned body text, canonical URL information, content hash, language field, and outlinks into a Document record.
7. WHEN a Crawler Service finishes a Document write, THE Crawler Service SHALL emit one idempotent index task containing the document identifier, source URL, and crawl content for the Indexer Service.
8. WHEN a Crawl Job is paused, resumed, cancelled, completed, or failed, THE Crawler Service SHALL persist the terminal or current status, timestamps, counters, and failure reason when a failure reason exists.

### Requirement 4: Crawl-to-index-to-rank-to-search pipeline

**User Story:** As a search user, I want crawled content to become searchable and ranked, so that a query returns relevant results from the indexed corpus.

#### Acceptance Criteria

1. WHEN the Indexer Service receives an index task, THE Indexer Service SHALL parse the content, remove configured non-content elements, tokenize and normalize supported text fields, apply configured stopword and stemming behavior, and persist repeatable postings.
2. WHEN the Indexer Service processes a Document, THE Indexer Service SHALL maintain a Positional Index for title, heading, body, metadata, anchor, and configured URL-relevant fields and SHALL update document frequency, total frequency, and IDF statistics.
3. IF the same index task is delivered more than once, THEN THE Indexer Service SHALL update the existing document and postings idempotently without creating duplicate primary records or duplicate postings.
4. WHEN the Ranker Service receives a query and candidate documents, THE Ranker Service SHALL calculate BM25 using the configured `k1`, `b`, IDF, field weights, and document-length normalization values.
5. WHEN a link graph is available, THE Ranker Service SHALL calculate PageRank with configured damping, dangling-node handling, convergence, normalization, and update interval values and SHALL persist the resulting document authority score.
6. WHEN the Query Pipeline ranks candidates, THE Ranker Service and Search API SHALL combine lexical relevance, PageRank, freshness, phrase, prefix, and configured diversification signals according to Operational Configuration.
7. WHEN a client submits a query, THE Search API SHALL execute normalization, correction or expansion when enabled, Boolean and phrase parsing, field/operator filters, postings retrieval, ranking, snippet generation, highlighting metadata, filtering, and pagination in the documented order.
8. WHEN a query produces no matching documents, THE Search API SHALL return a successful empty result response containing the normalized query and available suggestions or correction information.
9. WHEN a Search API request completes, THE Search API SHALL cache eligible results using the configured Redis policy and SHALL record query data including normalized query, result count, pagination, elapsed time, cache status, filters, session context, and request metadata.

### Requirement 5: Frontend search and shared experience

**User Story:** As a search user, I want a complete accessible search experience, so that I can discover, inspect, and revisit results on desktop and mobile layouts.

#### Acceptance Criteria

1. THE Frontend SHALL provide working routes for search, results, administration, analytics, settings, authentication, and an unknown-route fallback without importing absent modules.
2. WHEN a user submits a non-empty query, THE Frontend SHALL update shareable URL state, request the Search API through the API client, show loading and failure states, and render result titles, URLs, snippets, scores or relevant metadata, and pagination controls from the Service Contract.
3. WHEN a user types at least the configured minimum suggestion length, THE Frontend SHALL request autocomplete suggestions through the API client and SHALL support keyboard and pointer selection of a suggestion.
4. WHEN a result is selected, THE Frontend SHALL record the selected document, query context, result position, and available dwell-time data through the documented click-logging contract.
5. WHEN a search response contains zero results, THE Frontend SHALL render a no-results state with the normalized query, correction or suggestion information, and a path to edit the query.
6. WHILE the Frontend is rendered, THE Frontend SHALL provide responsive layouts, dark and light theme behavior, visible focus states, semantic labels, keyboard navigation, and color and interaction contrast meeting the project accessibility target of WCAG AA.
7. IF a Search API or suggestion request fails, THEN THE Frontend SHALL render a recoverable error state without losing the current query or causing an unhandled browser exception.

### Requirement 6: Authentication, RBAC, and administration

**User Story:** As a search operator, I want secure administration controls, so that only authorized personnel can operate crawls, inspect analytics, and change settings.

#### Acceptance Criteria

1. WHEN a valid administrator submits credentials, THE Authentication Service SHALL return a signed JWT access token and refresh token, update the administrator login timestamp, and apply the configured token lifetimes.
2. IF credentials are invalid, an account is inactive, or a token is expired or malformed, THEN THE Authentication Service SHALL return the documented authentication error and SHALL avoid revealing whether a credential or account lookup failed.
3. WHEN an authenticated client presents a refresh token, THE Authentication Service SHALL validate token type and administrator status before issuing replacement tokens.
4. WHILE an administrative request is processed, THE RBAC layer SHALL enforce the administrator role required by the operation and SHALL return 401 for missing authentication or 403 for insufficient privilege.
5. WHEN an authorized administrator uses crawl controls, THE Admin API SHALL support crawl-job creation, listing, detail, pause, resume, cancel, queue statistics, and status inspection.
6. WHEN an authorized administrator uses index and configuration controls, THE Admin API SHALL expose index statistics, ranking or crawler settings, safe setting updates, and API-key creation, listing, and revocation according to role policy.
7. WHEN the Frontend receives an authentication failure, THE Frontend SHALL clear stored access credentials, preserve no usable secret in page state, and navigate to the authentication route with a recoverable message.
8. WHEN an API key is created, THE Admin API SHALL return the plaintext key only in the creation response, persist only a secure hash and display prefix, enforce active and expiry status, and update last-use metadata after authenticated use.
9. IF an administrative action changes a setting, access key, role, or crawl state, THEN THE Admin API SHALL record the actor, action, target, timestamp, and outcome in an auditable log.

### Requirement 7: Analytics and real-time operational views

**User Story:** As a product or search operator, I want query and system analytics, so that I can identify usage patterns, zero-result gaps, ranking issues, and service health.

#### Acceptance Criteria

1. WHEN the Search API serves a query or receives a result click, THE Analytics Pipeline SHALL persist a query log or click log containing the identifiers and measurements defined by the database schema.
2. WHEN an authorized administrator requests analytics for a time range, THE Admin API SHALL return query volume, top queries, click-through rate when click data exists, zero-result queries, average and percentile latency when sample data exists, and filter dimensions supported by the schema.
3. WHEN analytics data is unavailable for a requested metric or time range, THE Analytics Pipeline SHALL return an explicit empty or unavailable value with the requested range rather than fabricating a measurement.
4. WHEN the Analytics Dashboard loads, THE Frontend SHALL render date-range controls, query-volume visualization, top-query results, zero-result analysis, latency views, and loading, empty, and error states from the Analytics Service Contract.
5. WHERE real-time metrics are enabled in Operational Configuration, THE Admin API and Frontend SHALL provide an authenticated WebSocket or server-sent event stream for documented queue, crawl, index, and latency updates.
6. IF a real-time stream disconnects, THEN THE Frontend SHALL show stale-data status and SHALL retry or provide a manual refresh without breaking the dashboard.

### Requirement 8: Operational configuration, resilience, and security

**User Story:** As a deployer, I want explicit and safe operational configuration, so that local and deployment environments can run the same architecture with controlled differences.

#### Acceptance Criteria

1. THE Operational Configuration SHALL define environment-variable overrides and documented defaults for database, Redis, RabbitMQ, JWT, CORS, rate limits, cache TTLs, crawler policy, ranking weights, service URLs, logging, and frontend API URL.
2. WHEN a service starts, THE service SHALL validate required configuration, reject invalid security or connection values, and log effective non-secret configuration without logging passwords, tokens, or key material.
3. WHILE the Compose Environment is running, THE infrastructure services and application services SHALL expose health checks, dependency readiness checks, structured request or worker logs, and graceful shutdown behavior.
4. WHEN a worker or service temporarily loses Redis, RabbitMQ, PostgreSQL, or an HTTP downstream dependency, THE affected service SHALL apply bounded retry or reconnect behavior and SHALL preserve idempotent processing or a durable failure state.
5. THE API Gateway and Nginx configuration SHALL enforce documented CORS, request-size, connection, endpoint rate-limit, security-header, and internal-admin access policies consistently with application authorization.
6. IF a secret uses a development default, THEN THE Build System SHALL label the default as development-only and SHALL require an explicit production value before a production-mode startup.
7. WHERE TLS termination and external deployment are enabled, THE operational configuration SHALL document certificate paths, trusted proxy behavior, secure headers, health endpoints, metrics access, and deployment-specific upstream names.

### Requirement 9: Demo data, documentation, and operator workflows

**User Story:** As a reviewer or portfolio user, I want reproducible demo content and clear documentation, so that I can understand and demonstrate Luna without reverse-engineering the source tree.

#### Acceptance Criteria

1. WHEN a developer runs the documented demo-data command against a migrated database, THE Demo Data Set loader SHALL insert deterministic documents, crawl metadata, postings, term statistics, PageRank values, query logs, click logs, and autocomplete source data without duplicate records on repeated runs.
2. WHEN the Demo Data Set loader runs without network access, THE loader SHALL use bundled or generated fixture content and SHALL report the number of records inserted, skipped, and updated.
3. WHERE external source crawling is enabled for a demonstration, THE Crawler Service SHALL use explicit seed and domain configuration, respect robots policy, and record source and retrieval metadata for each imported Document.
4. THE Repository documentation SHALL describe architecture, local setup, environment variables, migrations, service contracts, crawl operations, ranking configuration, analytics, deployment, troubleshooting, and known performance-goal limitations.
5. WHEN a reviewer follows the documented demo workflow, THE Build System SHALL provide a path from clean startup through demo-data loading to a successful search, suggestion request, administrative login, crawl-job inspection, and analytics view.
6. THE Documentation SHALL identify the completed foundations, remaining implementation boundaries, optional capabilities, and every performance value that remains a goal rather than a measured result.

### Requirement 10: Comprehensive validation and performance goals

**User Story:** As a maintainer, I want layered automated validation, so that service behavior and cross-service integration remain correct while the project evolves.

#### Acceptance Criteria

1. THE Validation Suite SHALL include unit tests for URL normalization, tokenization and stemming, HTML extraction, query parsing, BM25, PageRank, rate limiting, authentication, and configuration validation.
2. WHEN integration tests run against disposable or configured PostgreSQL, Redis, and RabbitMQ dependencies, THE Validation Suite SHALL verify Search API behavior with seeded data, Crawler Service to Indexer Service delivery, Indexer Service to Ranker Service data flow, and Admin API CRUD and authorization behavior.
3. WHEN end-to-end tests run against the Compose Environment, THE Validation Suite SHALL verify startup readiness, authentication, search, autocomplete, result click logging, crawl-job control, analytics rendering, and recoverable downstream failure behavior.
4. IF a test fails, THEN THE Validation Suite SHALL report the test name, service or layer, failure reason, and required dependency or fixture without silently skipping the failure.
5. WHERE Benchmark Infrastructure is available, THE Validation Suite SHALL provide repeatable load scenarios for search, autocomplete, and crawl throughput and SHALL report achieved throughput, Latency Percentiles, error rate, and test environment against the Performance Goals.
6. WHERE Benchmark Infrastructure is unavailable, THE Validation Suite SHALL mark the Performance Goals as unmeasured goals and SHALL still execute functional unit, integration, and end-to-end validation.
7. THE Repository SHALL provide a validation summary that distinguishes passing functional behavior, known limitations, and benchmark measurements from unmeasured performance goals.
