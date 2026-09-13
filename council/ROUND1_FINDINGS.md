# SFERA Council — Round 1 Findings

Chief Architect: ChatGPT

Round 1 produced useful ideas, but participants did not all inspect the same source state. Cross-review is therefore frozen until one canonical baseline is used.

Canonical artifact: `SFERA_Chess_Lab_v1.5_SFERA_REPORT.zip`

SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

Chief Architect verification on that exact archive: `18 passed in 1.59s`.

## Baseline conflicts found

- A submitted audit reported 22 tests, while the canonical archive runs 18 tests.
- A submitted audit described SFERA Report as absent. The canonical archive contains `sfera/report.py`, `SFERA_REPORT_RU.md`, and `tests/test_report_v15.py`.
- The canonical Research Tree does create a new session and an in-memory priority queue on every `build()` call, so resume-after-restart remains a real gap.
- The canonical Discovery `promote()` path can promote a candidate without an enforced control-group, counterexample and out-of-sample validation gate, so Discovery validation remains a real gap.

## Provisional priorities supported by canonical code

1. Discovery Validation Pipeline.
2. Research Tree Resume.
3. Storage Benchmark before storage rewrite.
4. Richer Batch Analyzer semantics beyond cp-loss.

## Freeze

Do not declare a new SFERA version from Council work until all auditors can inspect the same canonical source snapshot and TASK-0001 is rerun against it.

Policy: **Evidence over votes. Same code before cross-review.**
