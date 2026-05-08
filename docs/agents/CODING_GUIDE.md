<!-- L9_META
l9_schema: 1
origin: l9-template
engine: golden-repo
layer: [docs, agents]
tags: [L9_TEMPLATE, agents, coding_guide]
owner: platform
status: active
/L9_META -->

# Agent Coding Guide

> Canonical law for AI-authored code in L9 repos. Every PR — human or agent — is reviewed against this guide.

## 1. System Identity

| Property | Value |
|---|---|
| Repo role | L9 Constellation node template |
| Ingress | `POST /v1/execute` and `GET /v1/health` only |
| Egress | `TransportPacket` via gate-client SDK only |
| Node-name format | `{domain}-engine` or `{domain}-{function}` — lowercase, hyphenated |
| Nature | A node inside the Constellation, never a standalone app |

## 2. Immutable Laws

### LAW-01 — Single Ingress
- Only `POST /v1/execute` and `GET /v1/health`. No other HTTP routes, websockets, gRPC, or alternate surfaces.
- Engines must NEVER import FastAPI, Starlette, or any HTTP library.

### LAW-02 — Handler Interface
- Engines expose handlers only:

  ```python
  async def handle_<action>(packet: TransportPacket) -> TransportPacket
  ```

- Register in `engine/handlers.py` via `chassis.router.register_handler("<action>", handle_<action>)`.
- `handlers.py` is the **only** file that imports chassis modules.

### LAW-03 — Tenant Isolation
- Tenant is resolved by the chassis. Engines receive it as a string. Never resolve tenant in engine code. No cross-tenant reads or writes.

### LAW-04 — Observability Is Inherited
- Engines never configure structlog, Prometheus, or logging handlers. Use `structlog.get_logger(__name__)` and nothing else.

### LAW-05 — Infrastructure Is Template
- Engines never create Dockerfiles, compose files, CI pipelines, or Terraform modules. Add engine env vars to `.env.template` only.

### LAW-06 — TransportPacket Is The Only Container
- Every inter-service payload is a `TransportPacket`. `inflate_ingress()` at boundary entry, `deflate_egress()` at boundary exit. Engine code between boundaries works with typed Pydantic — never raw envelopes.

### LAW-07 — Immutability + Content Hash
- `TransportPacket` is frozen. Mutations create new packets via `.derive()`. `transport_hash` and `payload_hash` are sha256. Idempotency uses `header.idempotency_key`.

### LAW-08 — Lineage + Audit
- Every derived packet sets `parent_id`, `root_id`, increments `generation`. `hop_trace` is append-only. `delegation_chain` carries scoped authorization.

### LAW-09 — Cypher / SQL Injection Prevention
- All Neo4j labels and relationship types pass `sanitize_label()` before interpolation (regex `^[A-Za-z_][A-Za-z0-9_]*$`).
- VALUES are always parameterized (`$batch`, `$query`).
- Never `eval()`, `exec()`, `pickle.load()`, or `yaml.load()` without `SafeLoader`.

### LAW-10 — Prohibited Factors
- `race`, `ethnicity`, `religion`, `gender`, `age`, `disability`, `familial_status`, `national_origin`, `marital_status`, `genetic_information` are blocked at compile-time during gate validation. Violations fail compilation, not runtime.

### LAW-11 — PII Handling
- PII fields declared in `domain.compliance.pii.fields`. Modes: `hash` · `encrypt` · `redact` · `tokenize`. Engine never logs PII values.

### LAW-12 — Domain Spec Is Source of Truth
- Matching behavior comes from `domains/<id>/spec.yaml`. `DomainPackLoader` reads YAML → Pydantic. Downstream consumes `DomainSpec` — never raw YAML, never raw dicts.

### LAW-13 — Gate-Then-Score Architecture
- Matching is two-phase: gates (hard filter) → scoring (soft rank). All gate logic compiles to Cypher `WHERE`; all scoring to a single `WITH/ORDER BY`. Zero post-filtering in Python.

### LAW-14 — Null Semantics Are Deterministic
- Every gate declares `null_behavior: pass | fail`. The compiler — not the caller — applies the rule.

### LAW-15 — Bidirectional Matching
- Gates with `invertible: true` swap `field` ↔ `query_param` when match direction reverses. Gate implementations are direction-unaware; the compiler handles it.

### LAW-16 — File Structure Is Fixed
- Top-level engine directories are pre-defined. New top-level directories require architectural review.

### LAW-17 — Test Requirements
- Unit tests cover gate compilation, scoring math, parameter resolution, null semantics per gate.
- Integration tests use `testcontainers-neo4j` — never mock the Neo4j driver.
- Compliance tests verify prohibited factors are blocked at compile time.
- Performance: <200ms p95 match latency.

### LAW-18 — L9_META On Every File
- Every tracked file carries an L9_META header (schema version 1) — `l9_schema · origin · engine · layer · tags · owner · status`.
- Format varies by filetype. Injected by `tools/l9_meta_injector.py`, never manually.

### LAW-19 — Declarative GDS Jobs
- Graph Data Science algorithms are declared in `spec.gds_jobs`. Schedule type: `cron | manual`. Scheduler reads spec — no hardcoded calls.

### LAW-20 — KGE Embeddings (CompoundE3D)
- Default 256-dim. Beam search width=10, depth=3. Ensemble: weighted_average | rank_aggregation | mixture_of_experts. Embeddings are domain-specific, never shared cross-tenant.

## 3. Code Style

- **Language** Python 3.12+, `async/await` for all I/O.
- **Type hints** Every signature, every class attribute, every ambiguous variable.
- **Models** Pydantic v2 `BaseModel(frozen=True)` for structured data.
- **Formatter** `ruff format` (88-char line length).
- **Linter** `ruff check` + `mypy --strict engine/`.
- **Logging** `structlog.get_logger(__name__)`. Include `tenant`, `trace_id`, `action` in context.
- **Naming** `snake_case` everywhere. No Pydantic `Field(alias=...)`. YAML keys identical to Python field names.
- **Exceptions** Always assign message to a variable first to avoid EM101/EM102.
- **Nullable params** `def f(x: str | None = None)` — never implicit Optional.
- **Datetime** Always timezone-aware: `datetime.now(tz=UTC)`.
- **Magic values** Named constants in `engine/`; literals OK in `tests/`.

## 4. Banned Patterns (CI fails the build)

| ID | Pattern | Contract |
|---|---|---|
| SEC-001 | f-string Cypher MATCH without `sanitize_label()` | LAW-09 |
| SEC-002 | `eval()` | LAW-09 |
| SEC-003 | `exec()` | LAW-09 |
| SEC-004 | f-string `LIMIT` interpolation | LAW-09 |
| SEC-005 | f-string SQL interpolation | LAW-09 |
| SEC-006 | `pickle.load(s)` | LAW-09 |
| SEC-007 | `yaml.load()` without `SafeLoader` | LAW-09 |
| ARCH-001 | `from fastapi import` in `engine/` | LAW-01 |
| ARCH-002 | `from starlette import` in `engine/` | LAW-01 |
| ARCH-003 | `import uvicorn` in `engine/` | LAW-01 |
| DEL-001 | `httpx.{post,get,...}` in `engine/` | LAW-08 |
| DEL-002 | `requests.{post,get,...}` in `engine/` | LAW-08 |
| MEM-001 | Direct `INSERT INTO packetstore` in `engine/` | LAW-07 |
| STUB-001 | `raise NotImplementedError` outside `tests/` | zero-stub |
| OBS-001 | `structlog.configure()` in `engine/` | LAW-04 |
| OBS-002 | `logging.basicConfig()` in `engine/` | LAW-04 |
| NAME-001 | Pydantic `Field(alias=...)` | naming |
| PKT-001 | Uppercase `packet_type` value | LAW-06 |

## 5. Enforcement Pipeline

1. **Pre-commit** — `ruff` · `mypy --strict` · `tools/contract_scanner.py` · `tools/verify_contracts.py`
2. **CI Lint** — same as pre-commit, repo-wide
3. **CI Tests** — pytest (unit · integration · compliance · performance)
4. **CI Audit** — `tools/verify_contracts.py` (all contracts present and wired)
5. **LLM Review** — CodeRabbit · Qodo · Claude (contract-aware instructions)

Branch protection: all 5 status checks required. No bypass.

## 6. Reference Reading

- [`docs/architecture/OVERVIEW.md`](../architecture/OVERVIEW.md)
- [`docs/contracts/TRANSPORT_PACKET.md`](../contracts/TRANSPORT_PACKET.md)
- [`docs/boundaries/`](../boundaries/)
- [`docs/agents/ORCHESTRATION_PATTERNS.md`](ORCHESTRATION_PATTERNS.md)
- [`docs/agents/LIFECYCLE.md`](LIFECYCLE.md)
