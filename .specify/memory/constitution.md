<!--
Sync Impact Report:
- Version change: 2.0.0 -> 2.0.1
- Modified principles: none
- Added sections: rationale paragraphs for principles I-VIII
- Removed sections: none
- Templates requiring follow-up: none
- Deferred TODOs: none
-->

# Company Knowledge Assistant Constitution

## Core Principles


### I. Zero Cost

No paid services. Every external dependency has a free tier or a local alternative. LLM access goes through a provider abstraction.

Rationale: avoiding paid dependencies keeps the project accessible for local use and prevents
operating costs or vendor lock-in from becoming hidden requirements.

### II. Grounded answers only

Every answer cites source chunks. If the documents don't contain the answer, the system says so. It never invents.

Rationale: source citations make retrieval verifiable and refusing unsupported answers preserves
trust more effectively than plausible invention.

### III. Simple by default

One SQLite file, no queues, no auth, no extra services unless a spec proves the need.

Rationale: keeping infrastructure minimal reduces operational burden and lets the project
validate its core knowledge-assistant behavior before introducing complexity.

### IV. Test what matters

Pure logic (chunking, diffing, retrieval fusion, citation parsing) has unit tests. The RAG quality is measured by the  evaluation harness.

Rationale: testing deterministic core logic and measuring retrieval quality target the areas most
likely to affect answer correctness and catch regressions where they matter most.

### V. No framework magic for core logic

Retrieval and prompting are written by hand so behaviour is explainable.

Rationale: explicit retrieval and prompting behavior makes decisions inspectable, debuggable, and
easier to evaluate than opaque framework orchestration.

### VI. Reproducible

`docker compose up` runs everything. Config via environment variables. No secrets in git.

Rationale: a single reproducible startup path and environment-based configuration let contributors
run the same system consistently without committing credentials.

### VII. Documented decisions

Significant choices get a short ADR in docs/adr/.

Rationale: concise architecture decision records preserve the reasons behind major choices and
prevent future contributors from repeating or accidentally reversing established work.

### VIII. Scope is fixed

Out of scope: auth, multi-tenant, OCR, integrations, paid APIs, workflows.

Rationale: explicit exclusions prevent unbounded scope, keep implementation effort focused, and
ensure new capabilities require deliberate specification before expansion.

### IX. Clear and Stable Contracts

Backend APIs and shared data types MUST use explicit, validated schemas. API changes MUST preserve
backward compatibility unless an approved migration and deprecation plan is documented. Frontend
and backend contracts MUST be exercised by automated tests.

Rationale: FastAPI, Pydantic, SQLModel, and React integration depend on reliable contracts across
service boundaries.

### X. Test-First Quality Gate (NON-NEGOTIABLE)

Behavior changes MUST begin with a failing test or a reproducible regression case. Implementations
MUST pass focused tests and the relevant backend or frontend quality checks before merge.
Integration boundaries, retrieval behavior, document parsing, and data migrations MUST receive
coverage appropriate to their risk.

Rationale: test-first development makes expected behavior explicit and prevents regressions in
retrieval, indexing, and user-facing workflows.

### XI. Security and Data Stewardship

Secrets, credentials, private documents, and personal data MUST NOT be committed or logged.
Untrusted document content and external input MUST be treated as data, not instructions, and MUST
be validated before use. Access controls and data retention decisions MUST be implemented
explicitly and documented for features that handle restricted knowledge.

Rationale: organizational knowledge can contain confidential or sensitive information that requires
defense in depth.

### XII. Maintainable Simplicity

Implementations MUST favor the smallest design that satisfies the stated requirement. New
dependencies, abstractions, background services, and infrastructure MUST be justified by a concrete
need. Code MUST be self-contained, documented at system boundaries, and free of avoidable
complexity.

Rationale: a smaller, understandable system is easier to test, operate, and evolve.

## Technology Constraints

The backend MUST use Python 3.12 or newer, FastAPI, Pydantic settings, SQLModel, SQLite with
vector extensions where required, and uv-managed dependencies. The frontend MUST use React,
TypeScript, Vite, and Tailwind CSS. Ruff MUST be used for Python linting, pytest for backend tests,
TypeScript compilation and Vite builds for frontend validation, and existing CI workflows MUST
remain the merge gate unless a replacement provides equivalent coverage.

## Development Workflow

Feature work MUST follow the repository's Spec Kit workflow: define requirements before
implementation, produce an implementation plan and dependency-ordered tasks, then implement and
validate the result. Pull requests MUST include tests or a documented reason tests are not
applicable, summarize behavioral changes, and verify compatibility with the CI workflow.

Documentation that changes setup, user behavior, configuration, or operational assumptions MUST
be updated in the same change. Scope that introduces substantial complexity MUST include an
explicit rationale and migration or rollback considerations.

## Governance

This constitution supersedes informal project practices for repository engineering decisions.
Amendments require a documented proposal, review and approval, and a migration plan when existing
work or interfaces are affected. Every pull request and review MUST verify compliance with these
principles and flag justified exceptions explicitly.

Constitution versions MUST follow semantic versioning: MAJOR for backward-incompatible governance
or principle removals and redefinitions, MINOR for new principles or materially expanded guidance,
and PATCH for clarifications, wording improvements, and non-semantic refinements. The final
Governance line MUST match the version and dates reported in the Sync Impact Report.

Compliance reviews MUST cover test evidence, source attribution, security and privacy concerns,
API compatibility, dependency changes, and clarity of operational documentation. Ratification and
amendment dates MUST use ISO 8601 format.

**Version**: 2.0.1 | **Ratified**: 2026-11-26 |
**Last Amended**: 2026-11-26
