# ADR-0001 — CANONICAL BASELINE BEFORE CROSS-REVIEW

Status: ACCEPTED
Date: 2026-09-13
Owner: ChatGPT / Chief Architect
Decision rule: EVIDENCE OVER VOTES

## Problem

TASK-0001 responses were produced against different evidence bases:

- some models saw only the public Council documents;
- some models report access to a local SFERA v1.4 ZIP;
- some models report local v1.5 patches made in their own sessions;
- the private GitHub repository currently does not contain the full SFERA source tree.

Therefore the Council is not yet auditing one identical codebase.

## Decision

No CROSS REVIEW and no architecture merge may treat any local model-specific v1.5 as canonical.

A single immutable audit snapshot must be published in `audit_snapshot/` and identified by:

1. `BASELINE_ID`
2. source commit/archive provenance
3. exact file tree
4. SHA-256 manifest
5. test inventory
6. declared version

All Council members must re-run TASK-0001 against that same snapshot.

## Canonical evidence hierarchy

1. Files in the frozen `audit_snapshot/` at the declared commit.
2. Tests actually run against those files.
3. Benchmarks actually run against those files.
4. Signed Council reports.
5. README / design documents.
6. Model recollection or earlier local copies — not acceptable as canonical evidence.

## Current state

`CANONICAL_BASELINE_STATUS = BLOCKED_BY_SOURCE`

The current connected private repository contains only repository bootstrap files and Council material, not the complete SFERA application source tree. The Public mirror likewise does not yet contain the source baseline.

Until a real source archive/tree is available to the Chief Architect, `audit_snapshot/` must not be populated with reconstructed or model-generated code and called the existing product.

## Required safe snapshot contents

Expected minimum:

- launcher / `run.py`
- package containing current PySide6 UI
- board/chess rules implementation
- PGN streaming/import code
- DB/schema/migrations
- Genome / identity
- UCI engine layer
- Engine Lab 21 / Jury
- Batch Analyzer
- downloaders and TWIC
- Research Tree
- Memory / Concepts / Conflicts
- Curiosity / Discovery
- Teacher Bridge
- SFERA Report, if implemented
- Updater
- `tests/`
- dependency file

Exclude:

- `data/`
- user databases and WAL/SHM files
- PGN/TWIC archives
- engine binaries/networks
- tokens/secrets
- `.venv/`
- backups
- personal absolute paths or private data

## Next state transition

When the source tree is supplied, Chief Architect will:

1. inspect and sanitize it;
2. publish it under `audit_snapshot/`;
3. generate `SHA256SUMS.txt`;
4. fill `VERSION.md` with exact provenance;
5. lock a Git commit as `BASELINE_ID`;
6. issue `TASK-0001R — Canonical Re-Audit`.

Only after TASK-0001R is complete does the Council proceed to CROSS REVIEW.
