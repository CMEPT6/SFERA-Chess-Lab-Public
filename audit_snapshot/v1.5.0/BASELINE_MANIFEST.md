# SFERA Chess Lab v1.5.0 — CANONICAL AUDIT BASELINE

Status: **FROZEN FOR COUNCIL AUDIT**

Canonical artifact used by Chief Architect:

`SFERA_Chess_Lab_v1.5_SFERA_REPORT.zip`

Archive SHA-256:

`b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

The SHA-256 exactly matches the previously stored SFERA v1.5 checksum record.

## Local verification by Chief Architect

Command:

`python -m pytest -q`

Result:

`18 passed in 1.59s`

This is the result for the exact archive above. It must not be replaced by test counts from another local branch or model-modified copy.

## Snapshot contents

The archive contains the real Python package `sfera/`, tests, launchers, documentation, SFERA Report implementation, downloader/TWIC code, Engine Lab/Jury, Genome, DB, Discovery, Teacher and updater code.

Generated source packs from this exact archive:

- Full text source dump: 74 text/code/test files, SHA-256 `39a3a3aac25a53a56c51bd57389f31452b3a4c583470e50ae084437272a0c3f1`
- Critical TASK-0001 source pack, SHA-256 `a58d8f2f1cee3b1f5f261737d777c5afaea2636982c233d951e198847e7402f9`

Excluded from the text dump only generated caches, `.pyc`, and binary PNG assets. SVG chess pieces are part of the text snapshot.

## Known baseline inconsistency

`VERSION.txt` contains `1.5.0`, while `sfera/__init__.py` contains `__version__ = "1.0.0"`.

This mismatch is intentionally preserved as audit evidence. Do not silently correct it inside TASK-0001.

## Important Council rule

A report based on a different local copy, patched branch, or recreated implementation is **not evidence about this baseline** until its commit/artifact hash is matched to this manifest.

Chief Architect: ChatGPT
Decision policy: evidence over votes.
