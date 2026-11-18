# CMEPT6 RESEARCH REPORT — TESTING-001

- Agent: integration / testing and performance measurements.
- Baseline: CMEPT6 1.1, `9c00ccb3678ffbdd554b57d0b2b30364d6e76cf1`.
- Branch: `research/testing`. Measurement date: 2026-11-16; report finalized 2026-11-18.
- Problem: previous results did not preserve paired timing observations,
  executable checksums, order, cold-TT policy and complete UCI telemetry together.
- Hypothesis: a sequential paired runner with randomized order and explicit
  failure states can make search experiments reproducible and reviewable.
- Sources: local CMEPT6 source, independent referee and tournament transport.
- Changed files: `tests/benchmark.py`, `tests/benchmark_positions.json`,
  `tests/test_benchmark.py`, CI test steps, this report and raw JSON results.

## Implementation and validation

Both processes use Hash 32 MB, UncertaintySearch=false and the engine's single
search thread. Searches run sequentially. Each measured search starts with
ucinewgame (clears the TT); each process has one depth-2 warm-up. Position and
engine order are randomized using seed 20261116. The JSON records executable
SHA256, suite SHA256, host information, budgets, order and raw UCI output.
No secrets or authentication state are captured.

The runner validates legal bestmove independently, checks completed depth,
rejects crashes/timeouts/missing telemetry, refuses existing output paths,
and writes failed-run evidence without a successful summary. Seven unit tests
passed, including crash/timeout and incomplete-pair rejection. Real-engine
runs at depths 7 and 9 completed (18 paired observations per run).

The recorded nodes/time/NPS come from the LAST COMPLETED iteration. They are
not total work when a go-nodes limit interrupts a subsequent iteration.
Wall time includes UCI process transport overhead, not process startup.
These samples are descriptive and are not independent strength observations.

## Search candidate results

Candidate: the search branch's has_legal_move-before-stand-pat stalemate fix.
Both binaries built MSVC 19.12 x64, /O2 /MT /EHsc /std:c++17.
Exact binary hashes are preserved in each JSON; candidate revision field
explicitly says working tree because measurements preceded its commit.

| Budget | Pairs | Geometric mean candidate/base wall time | Different bestmoves | Samples <50 ms |
|---|---:|---:|---:|---:|
| depth 7 | 18 | 1.52046 | 0 | 17/36 |
| depth 9 | 18 | 1.38750 | 0 | 6/36 |

Depth 9 therefore showed about 38.8% longer elapsed time for this candidate
on this six-position suite. No confidence interval is claimed. Short samples,
host scheduling, and this small suite limit generalization. See
`results/qsearch-depth7.json` and `results/qsearch-depth9.json` for all samples,
individual engine NPS, nodes, times and search scores.

Matches: not run. Elo/CI/SPRT: not measured. Recommendation: accept the
benchmark infrastructure after review; continue research on the search fix,
retaining its failing regression but avoiding a strength-release claim.

## Next gates

1. Reduce stalemate-detection overhead while keeping all terminal regressions.
2. Repeat paired fixed-depth and fixed-node runs, then a predeclared fixed-time
   match using fastchess, paired openings and equal resources.
3. Specify statistical hypotheses before matches; preserve incomplete games
   and engine failures rather than dropping them from the denominator.
4. Add pinned-en-passant repetition regressions separately.
5. Compare full window / fixed aspiration / adaptive aspiration separately.

No changes were merged into main. No playing-strength gain is established.
PR and published commit IDs are recorded by the integration agent.
