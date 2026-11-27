# Feature workflow

How to build one feature from the roadmap in [development-plan.md](../development-plan.md) (Part D), using Spec Kit with Claude Code. Repeat it for every feature.

**Before you start:** `main` is clean and pushed, and the `/speckit-*` commands show up when you type `/speckit` in Claude Code. If they don't, restart Claude Code.

## 1. Start with a fresh context

Type `/clear` in Claude Code, or open a new chat.

- Do this at the start of every feature.
- You can also do it between phases inside a feature, and especially before implementing. Each Spec Kit command reads its inputs from files on disk (constitution, `spec.md`, `plan.md`, `tasks.md`), so clearing loses nothing and keeps the context small.

## 2. Specify

Run `/speckit-specify` followed by the feature's **Specify input** paragraph from Part D of the development plan.

- Spec Kit creates a branch (e.g. `001-walking-skeleton`) and `specs/NNN-name/spec.md`.
- Review `spec.md`. It should describe **what** and **why** only, with no technology choices.
- Compare it with the feature's example ACs in the roadmap. Edit by hand if needed.

## 3. Clarify

Run `/speckit-clarify` and answer its questions. The answers are written back into `spec.md`.

- Make sure every acceptance criterion is testable, with concrete numbers (limits, `k`, word counts).
- No `[NEEDS CLARIFICATION]` markers should remain.

## 4. Plan

Run `/speckit-plan`. This is where the **how** goes: architecture, data model, API contracts, libraries.

- Check the plan against the constitution ([.specify/memory/constitution.md](../.specify/memory/constitution.md)), especially simplicity, reproducibility, contracts and test-first.
- Record significant choices as short ADRs in [docs/adr/](adr/).

## 5. Tasks

Run `/speckit-tasks`, then `/speckit-analyze` to catch gaps between the spec, the plan and the tasks.

- Read `tasks.md` and **approve it** before implementing. The workflow gate requires this.
- Each task should take 15–60 minutes, start with a failing test, and name the AC it verifies.

## 6. Implement one task at a time

Run `/speckit-implement`, but ask for **one task only** (e.g. "implement T1 only").

For each task:

1. Read the failing test first, then the code. Ask about anything you don't understand.
2. Run the checks:
   ```bash
   cd backend && uv run pytest && uv run ruff check .
   cd frontend && npm run build
   ```
3. Commit, e.g. `feat(skeleton): add LLMProvider interface (spec 001, T2)`.

If reality differs from the spec, update the spec first, then the code. Use `/clear` whenever the context gets long.

## 7. Verify and merge

1. Tick off every acceptance criterion in `spec.md`.
2. Run the app for real. For example, for Feature 001, clone the repo into a temporary folder and run `docker compose up` there.
3. Open a pull request and merge it once CI is green:
   ```bash
   git push -u origin HEAD
   gh pr create --fill
   # wait for CI to pass, then:
   gh pr merge --merge --delete-branch   # keeps per-task commits
   ```

## 8. Start the next feature

```bash
git checkout main && git pull
```

Then type `/clear` and repeat from step 2 with the next feature in the roadmap.
