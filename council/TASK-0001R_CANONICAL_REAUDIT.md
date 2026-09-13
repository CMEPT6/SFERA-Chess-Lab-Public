# TASK-0001R — CANONICAL FOUNDATION RE-AUDIT

## Purpose

Rerun Foundation Audit against **one exact SFERA v1.5.0 baseline** after Round 1 revealed that different participants had inspected different local copies.

This is still a **BLIND ROUND**. Do not read other participants' answers until your own TASK-0001R report is complete.

## Canonical baseline

Artifact:
`SFERA_Chess_Lab_v1.5_SFERA_REPORT.zip`

SHA-256:
`b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

Chief Architect verification on that exact archive:

`python -m pytest -q` → `18 passed in 1.59s`

Baseline manifest:
https://raw.githubusercontent.com/CMEPT6/SFERA-Chess-Lab-Public/main/audit_snapshot/v1.5.0/BASELINE_MANIFEST.md

Start page with canonical source links:
https://github.com/CMEPT6/SFERA-Chess-Lab-Public/blob/main/START_HERE_AI.md

## Rules

1. Audit **only** evidence visible in the canonical snapshot.
2. Do not reuse a conclusion from an older ZIP or a locally patched copy unless you verify it again against this baseline.
3. If a module is not yet present in the public snapshot, mark it `NOT VERIFIED`.
4. If a statement refers to a file, cite the exact file path and preferably function/class or relevant line range.
5. If you did not execute a test, write `TEST NOT RUN`.
6. Do not infer benchmark results from architecture alone.
7. Keep HUMAN DATA, ENGINE DATA and DISCOVERY HYPOTHESES distinct.

## Required signature

```text
SFERA_COUNCIL_SIGNATURE
MODEL: <exact model/product name>
PROVIDER: <provider>
ROLE: <role from ROLE_MATRIX.md>
TASK_ID: TASK-0001R
SESSION_TAG: <unique tag>
ACCESS_MODE: GITHUB_DIRECT / WEB_URL / USER_PASTED_FILES / PARTIAL
BASELINE_SHA256: b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892
CODE_SEEN: FULL / PARTIAL / NONE
TESTS_ACTUALLY_RUN: <number or 0>
SIGNATURE: <MODEL>-<SESSION_TAG>
```

## Audit matrix

Return:

`MODULE | STATUS | EVIDENCE | BUG/RISK | PRIORITY`

Allowed statuses:

`WORKING / PARTIAL / BROKEN / PLACEHOLDER / NOT IMPLEMENTED / NOT VERIFIED`

Audit at minimum:

1. Windows launcher / PySide6 UI
2. Interactive Board
3. PGN importer
4. Lichess/Chess.com Downloader
5. TWIC Manager
6. Position Genome / identity
7. DB schema + migrations
8. Stockfish / Lc0 UCI bridge
9. Engine Lab 21 / Engine Jury
10. Batch Analyzer 1–8
11. Research Tree persistence/resume
12. Memory / Concepts / Conflicts
13. Curiosity / Discovery
14. Teacher Bridge
15. SFERA Report
16. Updater / rollback / data safety

## Three required verification questions

### A. Discovery gate

Does the canonical code enforce:

`PATTERN → HYPOTHESIS → CONTROL GROUP → ENGINE TEST → COUNTEREXAMPLES → OUT-OF-SAMPLE VALIDATION → CONCEPT`

or can a candidate be promoted directly?

### B. Research Tree resume

Can an existing research session restore its frontier/priority queue after restart and continue growing the same tree, or does `build()` create a new session?

### C. SFERA Report

Is SFERA Report actually present in the canonical baseline? If yes, list which report sections are implemented and what the tests prove.

## Required final sections

- EXECUTIVE SUMMARY
- AUDIT TABLE
- TOP-3 CRITICAL RISKS
- TOP-3 HIGHEST-VALUE IMPROVEMENTS
- EVIDENCE CONFLICTS WITH YOUR PREVIOUS TASK-0001 (if you submitted one)
- TESTS ACTUALLY RUN
- TESTS STILL REQUIRED
- BENCHMARKS ACTUALLY RUN
- BENCHMARKS STILL REQUIRED
- WHAT I DISAGREE WITH
- RECOMMENDATION TO CHIEF ARCHITECT
- CONFIDENCE 0.00–1.00

Finish with:

`SIGNED: <MODEL> | <SESSION_TAG> | TASK-0001R`

## Freeze

No Council merge and no new SFERA version number until TASK-0001R has enough same-baseline evidence to resolve Round-1 contradictions.

**Evidence over votes. Same baseline before cross-review.**
