# Company Knowledge Assistant: Development Plan

Beginner-friendly, zero-cost, built with Spec Driven Development (SDD).

> **Version warning.** Install commands and tool versions change quickly. Where a command comes from a third-party project, the official page is linked or named. If a command fails, check that page before debugging.

---

## 0. How to read this plan

1. **Part A**: What Spec Driven Development is and how you will work (read first, 15 min).
2. **Part B**: Set up your computer from scratch (one evening).
3. **Part C**: Create the repo and project skeleton (one evening).
4. **Part D**: The roadmap: 8 features, each built spec → plan → tasks → code → verify.
5. **Part E**: Working loop, git workflow, testing, troubleshooting.

Time budget: about 1 setup weekend + 4–5 build weekends (roughly 8–10 focused hours each).

---

# PART A: Spec Driven Development (SDD)

## A1. The idea in one paragraph

With AI coding assistants, the bottleneck is no longer typing code; it is **being precise about what you want**. "Build a document upload feature" produces plausible but arbitrary code. SDD flips the order: you write a **specification** (what and why, with testable acceptance criteria), then a **technical plan** (how), then a **task list**, and only then let the AI implement, one small task at a time. The spec is the source of truth. When code and spec disagree, you fix one of them on purpose, never by accident.

## A2. The workflow (applied to every feature)

```
Constitution (once)  →  principles that never change
        │
For each feature:
   1. SPECIFY   what & why, user stories, acceptance criteria (no tech choices)
   2. CLARIFY   resolve ambiguities and open questions
   3. PLAN      how: architecture, data model, API contracts, libraries
   4. TASKS     small, ordered, individually testable steps
   5. IMPLEMENT one task at a time, tests first when possible
   6. VERIFY    check every acceptance criterion; update the spec if reality changed
```

**Rules that make it work**

- A spec says **what** and **why**. A plan says **how**. Don't mix them.
- Every requirement must be **testable**. If you can't say how you'd check it, rewrite it.
- Mark unknowns as `[NEEDS CLARIFICATION: ...]` instead of guessing.
- Tasks should take 15–60 minutes and end in something you can run or test.
- **You review everything the AI produces** against the spec. This is also how you learn the tech (your secondary goal).
- Commit specs to git. They are part of the portfolio. Reviewers can see how you think.

## A3. Two ways to do it

**Option 1: GitHub Spec Kit (recommended; it's free and open source).** A CLI called `specify` creates a scaffold and gives your AI assistant slash commands:

| Command | Purpose |
|---|---|
| `/speckit.constitution` | Write the project's non-negotiable principles |
| `/speckit.specify` | Turn a feature idea into a spec |
| `/speckit.clarify` | Ask you questions about gaps in the spec |
| `/speckit.plan` | Produce the technical plan |
| `/speckit.tasks` | Break the plan into tasks |
| `/speckit.analyze` | Check spec, plan and tasks for inconsistencies |
| `/speckit.implement` | Execute the tasks |

It works with several AI assistants (Claude Code, GitHub Copilot, Gemini CLI and others). Command names and options evolve, so confirm in the repo README: https://github.com/github/spec-kit

**Option 2: Manual SDD (works with any chat AI, including free ones).** You keep the same structure in a `specs/` folder using the templates in A5 and paste them into your AI assistant. Choose this if you have no coding-agent access. **Recommendation:** use the manual templates for Feature 001 to understand the mechanics, then switch to Spec Kit if your assistant supports it.

> **Which AI assistant at zero cost?** Claude Code is not part of the free Claude plan. Free options include GitHub Copilot Free in VS Code (limits apply; check current terms), the free chat tiers of Claude/Gemini/ChatGPT (copy and paste, slower but fully workable), and local models via Ollama (weaker for coding). The method is the same whichever you use.

## A4. The project constitution

Create this first (as `.specify/memory/constitution.md` with Spec Kit, or `docs/constitution.md` manually). Starting draft; edit it to match your beliefs:

```markdown
# Constitution: Company Knowledge Assistant

1. **Zero cost.** No paid services. Every external dependency has a free tier
   or a local alternative. LLM access goes through a provider abstraction.
2. **Grounded answers only.** Every answer cites source chunks. If the documents
   don't contain the answer, the system says so. It never invents.
3. **Simple by default.** One SQLite file, no queues, no auth, no extra services
   unless a spec proves the need.
4. **Test what matters.** Pure logic (chunking, diffing, retrieval fusion,
   citation parsing) has unit tests. The RAG quality is measured by the
   evaluation harness.
5. **No framework magic for core logic.** Retrieval and prompting are written
   by hand so behaviour is explainable.
6. **Reproducible.** `docker compose up` runs everything. Config via
   environment variables. No secrets in git.
7. **Documented decisions.** Significant choices get a short ADR in docs/adr/.
8. **Scope is fixed.** Out of scope: auth, multi-tenant, OCR, integrations,
   paid APIs, workflows.
```

## A5. Templates (manual SDD)

**`specs/NNN-name/spec.md`**

```markdown
# Spec NNN: <feature name>

## Why
One or two sentences: the user problem.

## User stories
- As a <user>, I want <capability> so that <benefit>.

## Functional requirements
- FR-1: The system MUST ...
- FR-2: The system MUST ...

## Acceptance criteria (Given / When / Then)
- AC-1: Given ..., when ..., then ...

## Edge cases & errors
- What happens if ...?

## Out of scope
- ...

## Open questions
- [NEEDS CLARIFICATION: ...]
```

**`specs/NNN-name/plan.md`**

```markdown
# Plan NNN
## Approach (summary)
## Components & files to create/change
## Data model changes
## API contracts (method, path, request, response, errors)
## Libraries & why
## Risks / alternatives considered
## How each acceptance criterion will be verified
```

**`specs/NNN-name/tasks.md`**

```markdown
# Tasks NNN
- [ ] T1: <small, testable step>   (verifies: AC-1)
- [ ] T2: ...
```

**The prompt to start any feature (works in any AI chat):**

> You are helping me build a RAG app following Spec Driven Development. Read the constitution and spec below. First, list ambiguities or missing edge cases in the spec and ask me questions. Do not write code yet. [paste constitution] [paste spec]

Then: "Now write plan.md using the template", then "Now write tasks.md", then "Implement T1 only. Show the code and the test; wait for my review."

---

# PART B: Set up your computer from scratch

You need: a GitHub account, a code editor, Git, Python tooling, Node.js, Docker, and Ollama. Pick your operating system track.

## B0. Windows only: install WSL2 (a Linux environment inside Windows)

All the instructions below assume a Linux/macOS-style terminal. On Windows, this is the smoothest route.

1. Open **PowerShell as Administrator** and run: `wsl --install`
2. Restart when asked. Ubuntu opens and asks you to create a username and password.
3. From now on, use the **Ubuntu** terminal for everything and store your projects inside Linux (e.g. `~/projects`), not under `C:\`. It is much faster.
4. Run `sudo apt update && sudo apt upgrade -y` once.

## B1. Terminal basics (if new)

- macOS: open **Terminal** (Cmd+Space, type "Terminal").
- Linux/WSL: open your terminal.
- Useful commands: `pwd` (where am I), `ls` (list), `cd folder` (enter), `cd ..` (up), `mkdir name` (create folder).

## B2. Git and GitHub

**Install Git**

- macOS: `xcode-select --install` (or `brew install git` if you use Homebrew)
- Ubuntu/WSL: `sudo apt install -y git curl build-essential`

**Configure your identity** (use the same email as your GitHub account):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

**GitHub account and CLI**

1. Create a free account at https://github.com.
2. Install the GitHub CLI by following https://cli.github.com (macOS: `brew install gh`; Ubuntu: use the official apt instructions on that page).
3. Log in: `gh auth login` → choose GitHub.com → HTTPS → "Login with a web browser" and follow the prompts.
4. Check: `gh auth status`

## B3. Code editor: VS Code

1. Install from https://code.visualstudio.com.
2. **Windows/WSL:** also install the **WSL** extension, then in Ubuntu run `code .` inside a project folder to open it connected to WSL.
3. Install extensions: **Python**, **Ruff**, **ESLint**, **Tailwind CSS IntelliSense**, **Docker**, **GitHub Copilot** (optional; free tier available).

## B4. Python with uv

`uv` is a fast, modern tool that installs Python and manages dependencies and virtual environments for you. You do not need to install Python separately.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# close and reopen the terminal, then:
uv --version
uv python install 3.12
```

## B5. Node.js (for the frontend)

Use a version manager (nvm) so you can switch versions easily.

```bash
# Check https://github.com/nvm-sh/nvm for the latest version number in this URL
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
# close and reopen the terminal, then:
nvm install --lts
node --version && npm --version
```

## B6. Docker

Docker runs your app in containers so it behaves the same everywhere.

- **macOS / Windows:** install **Docker Desktop** from https://www.docker.com/products/docker-desktop. On Windows, enable "Use the WSL 2 based engine" and WSL integration for Ubuntu in the settings. Personal use is free.
- **Linux:** follow https://docs.docker.com/engine/install/ for your distribution, then `sudo usermod -aG docker $USER` and log out/in.

Verify: `docker run hello-world`

## B7. Ollama (run LLMs locally for free)

1. Install from https://ollama.com/download (Linux/WSL: `curl -fsSL https://ollama.com/install.sh | sh`).
2. Pull a small model to start (check https://ollama.com/library for current good options; newer models appear often):
   ```bash
   ollama pull llama3.2:3b
   ollama run llama3.2:3b "Say hello in one sentence"
   ```
3. Hardware guide: 8 GB RAM → 3B models; 16 GB → 7–8B models. No GPU is required but CPU-only generation is slower.
4. Ollama serves an API at `http://localhost:11434`. Your backend will call it.
5. WSL note: if you installed Ollama on Windows rather than inside WSL and WSL can't reach it, install it inside WSL instead; it's the simplest fix.

## B8. Free hosted LLM key (for the public demo later; optional now)

Create a free API key with a provider that has a free tier and an OpenAI-compatible API, e.g. Google AI Studio (Gemini) or Groq. Free-tier limits and model names change, so read their current pricing page. Never commit the key; it goes in a `.env` file (git-ignored, set up in Part C).

## B9. Your AI coding assistant

Pick one (see A3). If using Spec Kit, install it now:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify check      # reports which tools it can find
```

## B10. Verify everything

```bash
git --version
gh auth status
uv --version
python3 --version        # or: uv run python --version
node --version
docker --version
ollama --version
```

All commands should print versions without errors.

---

# PART C: Create the repo and skeleton

## C1. Create the GitHub repo

```bash
mkdir -p ~/projects && cd ~/projects
gh repo create knowledge-assistant --public --clone --add-readme --license mit
cd knowledge-assistant
```

(You can create it private first and flip it public when polished.)

## C2. Backend skeleton

```bash
uv init backend --app --python 3.12
cd backend
uv add fastapi "uvicorn[standard]" sqlmodel alembic pydantic-settings \
       python-multipart sse-starlette httpx \
       pymupdf pymupdf4llm python-docx markdown-it-py beautifulsoup4 \
       fastembed sqlite-vec
uv add --dev pytest pytest-asyncio ruff
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Knowledge Assistant")

@app.get("/health")
def health():
    return {"status": "ok"}
```

Run it: `uv run uvicorn app.main:app --reload` → open http://localhost:8000/health (and http://localhost:8000/docs for auto-generated API docs). Stop with Ctrl+C.

> **Beginner note:** `uv` creates the virtual environment automatically. `uv run <cmd>` runs a command inside it. Dependencies live in `pyproject.toml`.

## C3. Frontend skeleton

```bash
cd ..    # back to repo root
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite
```

Follow the current Tailwind + Vite guide at https://tailwindcss.com/docs (add the Vite plugin in `vite.config.ts` and `@import "tailwindcss";` in your CSS file). Then add shadcn/ui components using their guide: https://ui.shadcn.com/docs/installation/vite (it runs `npx shadcn@latest init`). Run `npm run dev` → http://localhost:5173.

## C4. Repo hygiene

Create `.gitignore` at the repo root:

```
.env
data/
*.sqlite
*.sqlite3
__pycache__/
.venv/
node_modules/
dist/
.DS_Store
```

Create `.env.example` (commit this one; copy to `.env` locally):

```
LLM_PROVIDER=ollama            # ollama | openai_compat
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OPENAI_COMPAT_BASE_URL=
OPENAI_COMPAT_API_KEY=
OPENAI_COMPAT_MODEL=
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
DATA_DIR=./data
```

## C5. Minimal CI

`.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: cd backend && uv sync && uv run ruff check . && uv run pytest
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: lts/* }
      - run: cd frontend && npm ci && npm run build
```

(Action version numbers move forward; update them if GitHub warns.)

## C6. Initialize SDD and make the first commit

```bash
cd ~/projects/knowledge-assistant
specify init . --ai claude      # or --ai copilot, etc. Skip if doing manual SDD
mkdir -p specs docs/adr
```

Write your constitution (A4), then:

```bash
git add -A
git commit -m "chore: project skeleton, constitution"
git push
```

**Checkpoint:** backend `/health` works, frontend shows the Vite page, CI is green on GitHub, constitution committed.

---

# PART D: Roadmap: 8 features

For **each** feature: create branch `feat/NNN-name` → write spec → clarify → plan → tasks → implement task by task → verify against acceptance criteria → merge via pull request.

## Feature 001: Document ingestion (Weekend 1, part 1)

**Spec focus:** Upload PDF, DOCX, MD, TXT; parse to text with page and heading metadata; chunk; store.
**Example acceptance criteria**
- AC-1: Given a valid PDF, when uploaded, then a document record with status `ready` exists and its chunks carry page numbers.
- AC-2: Given the same file twice (same hash), then the second upload is rejected as duplicate.
- AC-3: Given a scanned (image-only) PDF with no text, then the status is `failed` with a clear message ("no extractable text").
- AC-4: Given a file over the size limit or unsupported type, then HTTP 4xx with an explanatory error.
**Plan topics:** SQLite schema, parser interface (one class per format), heading-aware chunker (~500–800 tokens, ~10% overlap), file storage by hash.
**Tests:** unit tests for the chunker (never split mid-sentence if avoidable; overlap correct; page metadata preserved).
**You'll learn:** FastAPI file uploads, SQLModel, text extraction, why chunking matters.

## Feature 002: Hybrid retrieval (Weekend 1, part 2)

**Spec focus:** Given a question, return the most relevant chunks using vector + keyword search merged.
**Example acceptance criteria**
- AC-1: A query using different words than the document (a synonym) still returns the correct chunk.
- AC-2: A query containing an exact identifier (e.g. an error code or part number) returns the chunk containing it at top rank.
- AC-3: Results include document title, page, score, and text.
**Plan topics:** `fastembed` embeddings, `sqlite-vec` table, FTS5 table, Reciprocal Rank Fusion (RRF), optional reranker (defer).
**Tests:** unit-test RRF with hand-made ranked lists; integration test over a tiny fixture corpus.
**You'll learn:** embeddings, vector similarity, BM25, why hybrid beats either alone.

## Feature 003: Grounded answers with citations (Weekend 2, part 1)

**Spec focus:** Generate an answer from retrieved chunks, with citations, refusal when unsupported, and follow-up awareness.
**Example acceptance criteria**
- AC-1: Answers contain citation markers `[n]` mapping to returned sources.
- AC-2: Given a question unrelated to any document, the system replies that it can't find the answer and returns no fabricated citations.
- AC-3: A follow-up ("and what about its maximum value?") is rewritten into a standalone query using chat history.
- AC-4: Cited indices that don't exist in the sources are removed or flagged.
**Plan topics:** `LLMProvider` interface (Ollama + OpenAI-compatible), prompt templates in files, score threshold, streaming via SSE.
**You'll learn:** prompt engineering for grounding, streaming, provider abstraction, the limits of small models.

## Feature 004: Chat UI (Weekend 2, part 2)

**Spec focus:** Conversational interface with streaming, source cards, document list and upload.
**Example acceptance criteria**
- AC-1: Tokens appear progressively while generating.
- AC-2: Clicking a citation shows the excerpt, document name and page.
- AC-3: Upload zone shows progress and processing status; errors are readable.
- AC-4: Conversations persist and can be reopened.
**You'll learn:** React state, consuming SSE, component design, loading and error states.

## Feature 005: Summaries and explanation levels (Weekend 3, part 1)

**Spec focus:** Executive and technical summaries per document; explanation level selector for chat answers (executive, technical, beginner).
**Example acceptance criteria**
- AC-1: A 100-page document can be summarized without exceeding the model context (hierarchical map-reduce).
- AC-2: Summaries are cached and regenerated only on request.
- AC-3: Executive summary is under N words and avoids jargon; technical summary preserves numbers and units.
**You'll learn:** map-reduce summarization, context window management, prompt variants.

## Feature 006: Version comparison (Weekend 3, part 2)

**Spec focus:** Link two documents as versions; show a structured diff and an AI explanation of notable changes.
**Example acceptance criteria**
- AC-1: Added, removed and modified sections are listed by heading.
- AC-2: Line/word-level differences are highlighted in the UI.
- AC-3: The AI explanation only refers to differences present in the deterministic diff.
- AC-4: Identical documents show "no differences".
**Plan topics:** section alignment, `difflib`, diff UI component.
**You'll learn:** combining deterministic code with LLMs, text diffing, UI for diffs.

## Feature 007: Evaluation harness (Weekend 4, part 1)

**Spec focus:** A repeatable script that measures answer quality on a golden set.
**Example acceptance criteria**
- AC-1: `golden_set.jsonl` contains ≥30 questions with expected source document/page, plus ≥5 unanswerable questions.
- AC-2: The script reports retrieval hit rate@k and refusal accuracy.
- AC-3: Results are saved per run so you can compare changes (chunk size, model, prompts).
- AC-4: Results are summarized in `docs/eval-report.md`.
**You'll learn:** how to measure AI systems instead of guessing. This is your strongest portfolio differentiator.

## Feature 008: Polish, stats and deploy (Weekend 4–5)

**Scope:** Knowledge statistics dashboard (document count, chunk count, top documents cited), engineering mode, README with GIFs and architecture diagram, Dockerfiles and `docker-compose.yml`, seeded sample documents, free hosted demo (check current free-tier options such as Hugging Face Spaces with Docker), short demo video.

**Cut line if time is short:** drop the reranker, stats dashboard and beginner level first. Never cut citations, the refusal behaviour, or the evaluation.

---

# PART E: Working loop and practices

## E1. Daily loop

1. Pick the next unchecked task in `tasks.md`.
2. Give the AI the constitution, the spec, the plan and *only that task*.
3. Ask for the **test first**, then the implementation.
4. Read the diff. Ask the AI to explain anything you don't understand (this is where the learning happens).
5. Run tests and the app. Check the relevant acceptance criterion.
6. Commit: `git commit -m "feat(ingestion): heading-aware chunker (spec 001, T3)"`.
7. If you discovered the spec was wrong, update the spec first, then the code.

## E2. Git workflow (solo, but professional)

- `main` is always working. One branch per feature: `feat/001-ingestion`.
- Open a pull request to yourself on GitHub (`gh pr create`), let CI run, then merge. The PR history is portfolio evidence.
- Commit messages follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## E3. Prompting the AI well

- Give context: constitution + the spec you're on. Don't paste the whole repo.
- One task per request. Ask for small diffs.
- Ask for alternatives when making design choices, then write the decision as an ADR.
- Never accept code you can't explain; ask "why this approach?" and "what could go wrong?"
- When stuck, paste the **exact error** and the relevant code, not a description.

## E4. Testing strategy (kept light)

- `pytest` for pure logic: chunker, RRF, diff, citation parsing, prompt building.
- Mock the LLM in tests with a fake provider that returns canned text.
- One integration test per API endpoint using FastAPI's `TestClient`.
- RAG quality is the evaluation harness (Feature 007), not unit tests.

## E5. Architecture Decision Records (ADRs)

For each major choice, add `docs/adr/001-sqlite-vec.md` with: Context, Decision, Consequences, Alternatives. Five to six short ADRs is plenty.

## E6. Troubleshooting

| Symptom | Likely fix |
|---|---|
| `command not found` after installing | Close and reopen the terminal |
| Docker can't connect to daemon | Start Docker Desktop; on Linux, check the `docker` group membership |
| Ollama very slow | Use a smaller model; close other apps; check RAM |
| Backend can't reach Ollama from Docker | Inside containers use `http://host.docker.internal:11434` (add `extra_hosts: ["host.docker.internal:host-gateway"]` on Linux) |
| `sqlite-vec` import or load error | Check its docs for the extension-loading call; some Python builds restrict extension loading |
| First embedding call is slow | The model downloads once; it is cached afterwards |
| CORS error in the browser | Add the frontend origin (`http://localhost:5173`) to FastAPI's CORS middleware |
| AI-generated code uses an outdated API | Paste the library's current docs into the prompt, or check the changelog |

## E7. Definition of done (whole project)

- [ ] `docker compose up` starts everything from a fresh clone
- [ ] All 8 specs have `spec.md`, `plan.md`, `tasks.md`, all acceptance criteria checked
- [ ] CI is green
- [ ] Evaluation report committed with real numbers
- [ ] README: demo GIF, architecture diagram, setup, design decisions, honest limitations
- [ ] Seed documents included (freely licensed)
- [ ] No secrets in git history
- [ ] Live demo link or demo video

## E8. Suggested learning resources (all free)

- FastAPI tutorial: https://fastapi.tiangolo.com/tutorial/
- Ollama docs: https://github.com/ollama/ollama
- sqlite-vec: https://github.com/asg017/sqlite-vec
- fastembed: https://github.com/qdrant/fastembed
- GitHub Spec Kit: https://github.com/github/spec-kit
- React docs: https://react.dev/learn
- uv docs: https://docs.astral.sh/uv/

---

## Next action

Finish Part B (verify checkpoint B10), do Part C, write the constitution, then start **Spec 001**. If you tell me your operating system and RAM, I can tailor Part B and recommend an exact local model.
