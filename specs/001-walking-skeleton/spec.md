# Feature Specification: Walking Skeleton

**Feature Branch**: `001-walking-skeleton`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "As a developer or evaluator, I can clone the repository and start the whole application with one command, see in the browser that the backend is healthy, and switch between a local LLM and a free hosted LLM through configuration only. Tests never need a real LLM."

## Clarifications

### Session 2026-11-27

- Q: When someone runs the single start command with the default configuration, should it also start a local model service automatically, or only the backend and web interface? → A: Opt-in. The default command starts the backend and web interface only, and uses a local model already running on the host if there is one. A documented flag or variant also starts a local model service in a container.
- Q: If someone runs the start command without first copying the example configuration file, should the application start with the built-in defaults, or stop and ask them to copy the file? → A: Start with the built-in defaults (same values as the example file) and print a one-line notice that no configuration file was found.
- Q: How should the health check decide whether the language model is "available", given that the web interface asks for health every 10 seconds? → A: A lightweight check that generates nothing (the endpoint responds and the configured model exists), with the result cached for 60 seconds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-command start with visible health (Priority: P1)

A developer or evaluator (for example, a potential client reviewing the portfolio) clones the repository, copies the example configuration file, and runs one documented command. The whole application (backend and web interface) starts. They open the web interface in a browser and see a clear indicator that the backend is healthy, inside an application shell that shows where Documents, Search and Chat will live.

**Why this priority**: This is the foundation every later feature builds on, and it is the first thing an evaluator tries. If the app cannot be started reliably from a fresh clone, nothing else can be demonstrated. It also surfaces the riskiest setup problems (container startup, storage with vector search, frontend-to-backend connectivity) while they are cheap to fix.

**Independent Test**: On a machine with only the documented prerequisites installed, clone the repository into an empty folder, copy the example configuration, run the single start command, and open the web interface: it shows "Backend: healthy".

**Acceptance Scenarios**:

1. **Given** a fresh clone and a copy of the example configuration with no edits, **When** the user runs the single documented start command, **Then** the web interface becomes reachable at the documented address (default port 5173, or the configured port) and shows "Backend: healthy".
2. **Given** the application is running, **When** the backend is stopped or unreachable, **Then** within 10 seconds the web interface shows "Backend: unreachable" instead of a blank page or a raw error, and it returns to "Backend: healthy" on its own once the backend is back.
3. **Given** the application starts for the first time, **When** startup finishes, **Then** the application's data store has been created automatically and its vector-search capability has passed a self-check, both when run directly on the developer's machine and when run with the single start command.
4. **Given** the application has already been started once, **When** it is stopped and started again, **Then** it starts without errors and the existing data store is reused, not recreated or wiped.
5. **Given** the application is running, **When** the user looks at the web interface, **Then** it shows an application shell with navigation entries for Documents, Search and Chat, each leading to a placeholder that says the section is not available yet.
6. **Given** a fresh clone where the example configuration has not been copied, **When** the user runs the single documented start command, **Then** the application starts with the built-in defaults, prints a one-line notice that no configuration file was found, and the web interface shows "Backend: healthy".

---

### User Story 2 - Switch language model provider by configuration only (Priority: P2)

A developer chooses which language model the application uses by editing configuration only: a model running locally on their own machine (the default, zero cost, no account needed), a free-tier hosted model reached through a widely used, standard API format, or a built-in fake provider that returns canned replies. No code changes and no rebuild of application code are needed to switch; a restart is enough.

**Why this priority**: The constitution requires zero cost and a provider abstraction. The local option is free for development, and the hosted free-tier option is needed later for a public demo where a local model is not available. Establishing the switch now prevents later features from coupling to one provider.

**Independent Test**: Set the provider setting to each supported value in turn, restart, and check the health information: it names the active provider and model and reports whether that provider is reachable.

**Acceptance Scenarios**:

1. **Given** the provider setting is "fake", **When** the backend asks for a completion, **Then** a canned reply is returned and no network call is made.
2. **Given** the provider setting is "local" and the local model service is running, **When** a completion is requested through the development check described in FR-010, **Then** a reply generated by the local model is returned.
3. **Given** the provider setting is "hosted" with a valid endpoint, model name and API key, **When** a completion is requested through the same check, **Then** a reply generated by the hosted model is returned.
4. **Given** the selected provider is configured but not reachable (for example, the local model service is not running), **When** the application starts, **Then** the application still starts, the backend reports itself healthy, and the health information marks the language model as "unavailable" with a readable reason. The web interface shows this as a separate, secondary status and does not show the whole backend as unhealthy.
5. **Given** the provider setting is present but empty or has an unknown value, or "hosted" is selected without the required endpoint, model or key, **When** the backend starts, **Then** it refuses to start and prints a message naming the setting that is wrong and the allowed values. It never falls back silently to another provider.
6. **Given** any provider is active, **When** the health information or logs are displayed, **Then** the API key never appears in them.

---

### User Story 3 - Trustworthy automated checks without a real model (Priority: P3)

A developer runs the automated test suite on a laptop or in continuous integration with no language model installed and no network access to any model provider. All tests pass, run quickly and give the same result every time. Continuous integration also fails if the web interface's copy of the backend's data contract has fallen out of date.

**Why this priority**: The constitution requires test-first development and stable, tested contracts between the frontend and the backend. Every later feature depends on fast, deterministic tests that never call a real model, and on catching contract drift automatically instead of in the browser.

**Independent Test**: Run the full test suite with no local model service running and with outbound network access to model providers blocked: every test passes. Then change a backend response shape without updating the frontend's contract and push: continuous integration fails with a message that the contract is stale.

**Acceptance Scenarios**:

1. **Given** no language model is installed or reachable, **When** the full automated test suite runs, **Then** all tests pass and none of them attempts a network call to a model provider.
2. **Given** any test that exercises language model behavior, **When** it runs, **Then** it uses the fake provider, and running it repeatedly gives identical results.
3. **Given** a change to the backend's public data contract, **When** the frontend's generated contract types are not regenerated, **Then** continuous integration fails and names the contract check as the cause.
4. **Given** the contract types are regenerated and committed, **When** continuous integration runs, **Then** the contract check passes.

---

### Edge Cases

- The configured web interface port or backend port is already in use: startup fails with a message naming the port and how to change it, rather than hanging.
- The example configuration was not copied: the application starts with built-in defaults identical to the example configuration and prints a one-line notice that no configuration file was found. Every setting has a defined default, so it never starts in an undefined state.
- The local model service runs on the host machine while the application runs inside containers: the documented default configuration reaches it on Windows (WSL2), macOS and Linux, and the troubleshooting notes cover the case where it does not.
- The configured local model has not been downloaded yet: the language model status is "unavailable" and the reason tells the user how to download the model.
- The hosted provider rejects the request (invalid key, free-tier rate limit or quota reached): the error is reported with the provider's reason and without the key, and the backend stays healthy.
- The vector-search capability cannot be loaded in the current environment: startup fails with a clear message, because later features depend on it. The app does not run in a half-working state.
- The data directory is not writable: startup fails with a message naming the directory.
- The browser cannot reach the backend because of cross-origin restrictions: the documented default configuration allows the web interface's own address, so this does not happen with the defaults.

## Requirements *(mandatory)*

### Functional Requirements

**Startup and health**

- **FR-001**: The repository MUST provide one documented command that starts the complete application (backend and web interface) from a fresh clone, whether or not the example configuration file has been copied.
- **FR-002**: Starting the application MUST NOT require any paid service, account or API key. The default configuration MUST work with free, local components only.
- **FR-003**: The backend MUST expose a health check that reports at least: overall status, data store status (including the vector-search self-check) and language model status (active provider, model name, and whether it is reachable, as decided by FR-012).
- **FR-004**: The web interface MUST show the backend health as "Backend: healthy" or "Backend: unreachable", refresh it at least every 10 seconds, and show the language model status separately.
- **FR-005**: On startup, the backend MUST create the data store if it does not exist, bring its structure up to the current version automatically and without losing existing data, and verify that vector search works with a smoke query.
- **FR-006**: The web interface MUST present an application shell with navigation for Documents, Search and Chat. In this feature each section shows a placeholder.
- **FR-007**: The default start command MUST start only the backend and the web interface, and MUST use a local language model service already running on the host machine when there is one. A documented opt-in variant of the same command MUST also start a local model service alongside the application. The default command MUST NOT download a language model.

**Configuration and providers**

- **FR-008**: All runtime settings (provider choice, model names, endpoints, API keys, ports, data location) MUST come from environment-based configuration. An example configuration file listing every setting with a safe default and a one-line explanation MUST be committed, and the real configuration file MUST be excluded from version control. When no configuration file is present, the application MUST start with built-in defaults identical to the example file and print a one-line notice saying so.
- **FR-009**: The system MUST support exactly three language model providers selectable by one setting: "fake" (canned replies, no network), "local" (a model running on the user's machine) and "hosted" (any free-tier service that speaks the widely used standard chat-completion API format, identified by endpoint, model name and key). The setting's accepted values are `fake`, `ollama` (the "local" provider) and `openai_compat` (the "hosted" provider); any other value is invalid under FR-011.
- **FR-010**: All three providers MUST offer the same two capabilities to the rest of the system: return a complete reply, and return a reply progressively as it is generated. The repository MUST include a documented development check that sends one short prompt through the active provider and prints the reply.
- **FR-011**: Invalid or incomplete provider configuration MUST stop the backend at startup with a message naming the faulty setting and its allowed values. The system MUST NOT fall back silently to a different provider.
- **FR-012**: An unreachable but correctly configured provider MUST NOT stop the application from starting. It MUST be reported as "unavailable" with a readable reason in the health information. Availability MUST be decided by a lightweight check that generates no text and uses no generation quota: the provider's endpoint responds and the configured model exists there. The result MUST be cached for 60 seconds, so health refreshes within that window do not contact the provider again. The "fake" provider is always available.
- **FR-013**: API keys and other secrets MUST NOT appear in health information, logs, error messages or committed files.

**Testing and contracts**

- **FR-014**: The automated test suite MUST pass with no language model installed and with no network access to any model provider. Every test that involves language model behavior MUST use the fake provider.
- **FR-015**: The fake provider MUST be deterministic: the same input always gives the same output. Tests MUST be able to set its canned replies.
- **FR-016**: The web interface MUST use data types generated from the backend's published contract rather than hand-written copies.
- **FR-017**: Continuous integration MUST fail when the committed generated types do not match the backend's current contract, and MUST run the backend tests, the backend lint check and the frontend tests and build.

**Documentation**

- **FR-018**: The README MUST document the prerequisites, the copy-configuration step, the single start command, how to switch providers, how to run the tests and the development check, and troubleshooting for reaching a local model from inside containers.
- **FR-019**: The choice of default local model MUST be recorded as a short decision record. It MUST compare at least two candidate models on the same five fixed prompts and report how often each one follows the numbered citation format (`[n]`) the project will use for grounded answers.

### Key Entities

- **Health Report**: The backend's answer to "am I working?". It has an overall status, a data store status (reachable, vector-search self-check passed) and a language model status (provider name, model name, available or unavailable, reason). It contains no secrets.
- **Application Configuration**: The set of named settings read at startup: provider choice, per-provider endpoint, model and key, ports and data location. It is validated as a whole before the application starts.
- **Language Model Provider**: An interchangeable source of model replies (fake, local or hosted) that offers "complete reply" and "progressive reply" and reports whether it is reachable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An evaluator with the documented prerequisites installed goes from a fresh clone to seeing "Backend: healthy" in the browser in under 10 minutes, using only the README and without editing any file except the copied configuration. Time spent downloading a local model is excluded.
- **SC-002**: After the first build, the application starts and reports healthy within 60 seconds of running the start command.
- **SC-003**: Switching between the fake, local and hosted providers takes one setting change plus a restart, with zero code changes, and the health information shows the new provider within 60 seconds of the restart.
- **SC-004**: 100% of automated tests pass on a machine with no language model installed, and the full suite finishes in under 2 minutes.
- **SC-005**: Running the full test suite 10 times in a row gives identical results every time (no flaky tests).
- **SC-006**: In a deliberate check, a contract change without regenerated types makes continuous integration fail 100% of the time, and regenerating the types makes it pass.
- **SC-007**: A search of the repository and its history finds zero committed API keys or other secrets.
- **SC-008**: When the local model service is stopped or started, the web interface shows the new language model status within 70 seconds (60-second cache plus one 10-second refresh). An hour of continuous health refreshes sends at most 60 availability checks and zero generation requests to the provider.

## Assumptions

- The audience is developers and technical evaluators. The setup assumes they have installed the documented prerequisites (git, the container tooling and, optionally, a local model runtime) as described in the development plan.
- The supported environments are Linux, macOS and Windows through WSL2. Native Windows without WSL2 is not supported.
- The "hosted" provider covers free-tier services that offer the standard chat-completion API format (for example, the free tiers of common providers). This feature only requires that one such service works with configuration alone; choosing the one used for the public demo belongs to Feature 010.
- The default provider in the example configuration is "local", because it is free and needs no account. Automated tests always set the provider to "fake" themselves and do not depend on the example configuration.
- An unreachable language model is treated as a degraded state, not a failure, because the later features that need a model are not part of this feature and the evaluator should still be able to see the app running.
- No authentication is added. The application runs on the user's own machine (Constitution III and VIII).
- The placeholders for Documents, Search and Chat contain no functionality. Upload, search and chat are delivered by Features 002, 003 and 004.
- Performance targets assume a typical developer laptop (at least 8 GB RAM) with container images already built. Response speed of the local model is outside this feature's success criteria.
