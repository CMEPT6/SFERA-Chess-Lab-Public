# TASK-0001R — Same-Baseline Council Status

Chief Architect: ChatGPT

Canonical artifact: `SFERA_Chess_Lab_v1.5_SFERA_REPORT.zip`

SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

Chief Architect re-run on the exact extracted baseline: `python -m pytest -q` → **18 passed** (runtime 1.34s in the latest run; previous run 1.59s). Test count is the evidence, runtime is environment-dependent.

## Submissions received

- Grok 4.5 — direct GitHub partial audit, 0 tests run.
- Claude Sonnet 5 — direct GitHub partial audit, 0 tests run.
- Claude (second session) — direct GitHub partial audit, 0 tests run.
- Qwen3 Max — direct GitHub partial audit, 0 tests run.
- Mistral Medium 3.5 — web partial audit, 0 tests run.
- Gemini 3.8 Flash — web partial audit, 0 tests run.
- Gemini 2.5 Pro — `BLOCKED_BY_INPUT`, no GitHub access, 0 tests run.

## Canonical facts resolved by Chief Architect

### 1. Discovery validation gate — CONFIRMED MISSING

`DiscoveryEngine.promote()` can convert a candidate directly into a durable Concept using discovery score/evidence count. No mandatory control group, counterexample search, engine test and out-of-sample gate is enforced in that code path.

Status: **PARTIAL / P0**.

### 2. Research Tree resume — CONFIRMED MISSING

`AdaptiveResearchTree.build()` always inserts a new `research_sessions` row and constructs the frontier as an in-memory heap starting from the root. `research_nodes` persist, but the canonical code has no API that reloads a previous session frontier and continues the same tree after restart.

Status: **PARTIAL / P1**.

### 3. SFERA Report — CONFIRMED PRESENT

Canonical baseline contains `sfera/report.py`, `SFERA_REPORT_RU.md`, and `tests/test_report_v15.py`. Human statistics and engine analysis are separate report sections. Round-1 claims that Report was absent do not apply to this SHA.

Status: **WORKING BASELINE MODULE**, with feature-quality gaps still subject to later tasks.

### 4. Board — CONFIRMED PARTIAL

Canonical `ChessBoardWidget` supports real legal board interaction, but promotion silently prefers Queen, there is no redo stack in the widget, and the canonical board does not contain the later local-only fixes reported by some Round-1 participants.

Status: **PARTIAL / P1**.

### 5. Database versioning/migrations — PRESENT

Contrary to some partial-snapshot reports, canonical `sfera/db.py` stores `schema_version='3'`, has `_migrate()`, `_add_col()`, and `_migrate_position_identity()`.

### 6. Research tables — PRESENT

Canonical schema contains `research_sessions` and `research_nodes`. Any report claiming these tables are absent is an artifact of incomplete fragment inspection.

### 7. Batch Analyzer resource scheduling — PRESENT, but semantics are limited

Canonical `batch_analyzer.py` allocates CPU threads approximately as `total_cpu // n_engines`, limits per-engine Hash, and runs engines concurrently. Its move classification remains primarily cp-loss oriented, so richer tactical/strategic semantics remain a valid later task.

### 8. Elo dilution bug — CONFIRMED

When PGN Elo tags are missing, importer Elo can become `0`. `upsert_position()` and `upsert_transition()` include that zero in the running `avg_elo` denominator. This can dilute average Elo for historical/unrated material and indirectly affect Discovery quality scoring and Report analytics.

Status: **BUG / P1**.

### 9. Version mismatch — CONFIRMED

`VERSION.txt = 1.5.0`, while `sfera/__init__.py` contains `__version__ = "1.0.0"`.

Status: **BUG / release hygiene**.

### 10. Updater rollback — PARTIAL

Canonical updater preserves user data folders and creates an application backup before replacement. It does not automatically detect failed post-update startup and restore the prior app state.

Status: **PARTIAL**.

## Council claims rejected or downgraded

- `Research Tree resume WORKING` — rejected. Persistence is not resume.
- `research_sessions/research_nodes absent` — rejected; both exist in canonical DB schema.
- `no DB schema version/migration system` — rejected; schema version and migration code exist.
- `UI absent from product` — rejected as a product claim; UI exists in the canonical archive. It was merely absent from some published audit fragments.
- `Discovery WORKING with low risk` — downgraded; candidate-to-Concept validation is not enforced.
- any old test count (16/22/etc.) from a model-local branch — not evidence for this SHA.

## Current Chief Architect priority order

1. **P0 — Discovery Validation Gate**: hypothesis state machine + control group + counterexamples + engine validation + out-of-sample requirement before Concept promotion.
2. **P1 — Research Tree Resume**: restore existing session/frontier and continue the same tree after restart.
3. **P1 — Elo Statistics Correctness**: exclude missing/zero Elo from rating averages; track rated sample count separately.
4. **P1 — Board Reliability**: promotion chooser, redo, check/mate state/visuals, regression tests.
5. **P1 — Storage Benchmark** before any 64-bit/128-bit/storage rewrite.
6. **P2 — Richer Batch Analyzer semantics** beyond cp-loss.
7. **P2 — Updater automatic rollback + integrity verification**.
8. **P3 — Version string consistency** before the next release.

## Freeze decision

TASK-0001R remains open until the offline-blocked Gemini 2.5 Pro receives the exact canonical package and returns a same-SHA audit, or is formally recorded as unavailable. No new SFERA version number should be declared from Council work before the audit freeze is lifted.

Policy: **Evidence over votes. Same SHA before cross-review.**
