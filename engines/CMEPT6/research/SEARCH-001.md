# CMEPT6 RESEARCH REPORT — SEARCH-001

- Agent and specialization: AGENT A, search architect; first-pass C/D audit.
- Base version and commit: CMEPT6 1.1, `9c00ccb3678ffbdd554b57d0b2b30364d6e76cf1`.
- Branch: `research/search`. Independent blind round completed before cross-review.
- Problem: `qsearch` treats an unchecked stalemate as stand-pat evaluation or
  alpha, rather than zero. The public `status` and full-depth terminal tests
  do not cover this horizon error.
- Hypothesis: checking existence of any legal move before stand-pat makes
  non-check terminal scores correct in all alpha/beta windows and at the
  quiet-search remaining-depth limit. Its per-node cost must be measured.
- Sources examined: this repository's `src/main.cpp`, `tests/test_regression.py`,
  `tests/test_release.py`, `tests/slider_fuzz.cpp`, `CMakeLists.txt`, CI workflows,
  README, council charter/rules. No external engine code copied.

## Isolated technical solution

`has_legal_move` generates pseudo-legal moves and stops after the first legal
one, restoring the board before returning. Non-check qsearch tests this before
static evaluation, stand-pat beta cutoff, and `remaining <= 0` return.
The existing MAX_PLY emergency static-evaluation cutoff is unchanged.
The checked-node mate path is unchanged.

`CMEPT6_SEARCH_TESTS` exposes Searcher internals only in the direct test
translation unit. It is absent from production builds. This avoids a new
UCI test command or changing search visibility in production.

Changed files: `src/main.cpp`, `tests/search_terminal.cpp`, `CMakeLists.txt`,
the two root CMEPT6 CI workflows, this report.

## Correctness evidence

Build environment: Windows x64, MSVC 19.12.25835, Windows SDK 10.0.26100.0.
Compiler options: `/O2 /MT /EHsc /std:c++17` for both baseline and candidate.

Before the functional fix, the new test was compiled against baseline search
with only the test-access macro seam added: **42 checks, 21 failures**.
The actual baseline production executable was compiled from an untouched
copy of the base commit's `main.cpp`.

After the fix: **42 checks, 0 failures**. Three stalemate fixtures, both colors,
and a blocked-pawn case cover full window, stand-pat fail-high window,
fail-low window, remaining depths 0 and 10, and the depth-zero search handoff.
Tests also verify board restoration, checked-horizon mate, and a quiet legal
position that must retain static evaluation.

For `7k/5K2/6Q1/8/8/8/8/8 b - - 0 1`, baseline returned **-980** (full window)
or **2000** (fail-low window), while the candidate returned the required **0**.
The blocked-pawn fixture's baseline score was **-996**.

Existing candidate suites passed:

- `run_tests.py`: all 24 perft checks, UCI/depth-4 search, mate in one.
- `test_regression.py`: all UCI, terminal-status and uncertainty tests.
- `test_release.py`: nodes, asynchronous stop, movetime, mate precedence,
  startpos perft 5 = 4,865,609 and endgame perft 5 = 674,624.

Reproduction after checkout:

```text
cmake -S engines/CMEPT6 -B build -DCMAKE_BUILD_TYPE=Release -DCMEPT6_BUILD_INTERNAL_TESTS=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

These CMake/CTest invocations are configured for CI; local test executables
were built directly with MSVC because CMake was not in PATH. Linux and hosted
CI results are not claimed here.

## Performance and strength

The integration agent is measuring the identical baseline/candidate binaries
with a paired fixed-depth benchmark. The direct existence probe adds work to
every non-check qnode. Initial short-depth evidence indicates a substantial
slowdown; detailed measurements will be attached by the integration agent.

Matches: not run. Elo and confidence interval: not measured.
No claim of greater strength, higher NPS, or Stockfish competitiveness.

## Other audit findings — outside this patch

1. Repetition hashing includes every FEN en-passant square, even when no legal
   capture exists. Reproduced on baseline: after `e2e4 g8f6 g1f3 f6g8 f3g1
   g8f6 g1f3 f6g8 f3g1`, `status` reports `ongoing`; the board with Black to
   move has occurred three times and the first e3 EP square is irrelevant.
   This needs a separate correctness patch, including pinned-EP cases.
2. Uncertainty Search currently adapts aspiration width from score jumps and
   PV switches. There is no calibrated multi-candidate uncertainty model or
   demonstrated computation-allocation advantage in this source.
3. Full `std::sort` recomputes move scores in its comparator. Pre-scored move
   ordering is a plausible isolated performance experiment, not a proven win.
4. No trained NNUE or parallel tree search exists in this source. The UCI worker
   thread provides asynchronous stop, not multicore search.

## Decision and next experiment

Recommendation: **continue research; do not merge as a strength improvement**.
Correctness gain is demonstrated, but extra legal-move probing can reduce
available search depth at fixed time. Next isolate an allocation-free early
legal-move probe (without building a full list), preserving these terminal tests,
and repeat fixed-node/depth/time measurements before any Elo experiment.

PR: not opened by this agent. Commit SHA and PR number are supplied in the
integration report after commit/PR creation. No main-branch change performed.

Council fields: MODEL=Codex; ROLE=Search Architect; TASK_ID=SEARCH-001;
FINDINGS/SOLUTION/PATCH/TESTS/BENCHMARK/RISKS as above;
WHAT_I_REJECTED=whole-engine rewrite, untested Elo claim, folding the EP bug
into this patch; CONFIDENCE=high for this reproduced terminal-score defect,
unmeasured for playing-strength impact.
