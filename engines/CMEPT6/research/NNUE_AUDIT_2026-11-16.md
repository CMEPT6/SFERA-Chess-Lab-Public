# CMEPT6 RESEARCH REPORT — NNUE feature contract

- Agent and specialization: B / NNUE RESEARCHER; independent blind round.
- Base: CMEPT6 1.1, `9c00ccb3678ffbdd554b57d0b2b30364d6e76cf1`.
- Branch: `research/nnue`.
- Status: PROTOTYPE, not a trained evaluation function.
- Problem: the production engine has no NNUE inference, feature contract,
  accumulator state, weight format, training pipeline or evaluation dataset.
- Hypothesis: a compact, king-conditioned sparse feature transformer can be
  updated exactly across ordinary and special moves. This first gate tests
  correctness, not playing strength.
- Changed files: this report, `research/nnue_features.py`,
  `research/test_nnue_features.py`. No production C++ changes.
- PR: not opened by this agent; root integration agent owns publication.
- Recommendation: continue research; accept only as an isolated test contract.

## Baseline audit

`src/main.cpp::evaluate` scans the 0x88 mailbox and reconstructs pawn-file
counts and bishop counts at every call. It combines fixed material values,
piece center/rank bonuses, doubled/isolated pawn penalties, bishop-pair bonus
and a binary king-phase term. It returns side-to-move evaluation plus a tempo
bonus. There are no trained parameters. Do not confuse incrementally maintained
piece bitboards with a neural accumulator.

`add_piece` / `remove_piece`, `Board::king`, `Undo`, and `make_move` /
`unmake_move` provide integration points. A search stack should own accumulator
states; embedding 512 extra bytes in Board would also enlarge board copies.
Captures, en passant, castling, promotions and king-context changes all need
dirty-piece events. Null moves change perspective ordering, not board features.
State restoration and TT evaluation semantics must be agreed with agent A.

## Primary sources checked 2026-11-16

- [Stockfish NNUE documentation](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html)
  describes sparse inputs, two perspectives, incremental accumulators and
  quantization. These are useful general techniques, not a novelty claim.
- [Stockfish trainer repository](https://github.com/official-stockfish/nnue-pytorch)
  is GPL-3.0. No trainer implementation or network was imported.
- [Triumviratus official repository](https://github.com/Tors3/Triumviratus)
  describes Consilium Plebis as using per-perspective material-selected experts,
  int8 king-relative weights and a pawn/king subnetwork. Its reported strength
  measurements belong to that project and are not CMEPT6 measurements.
  No weights or code were copied. Its GPL-3.0 implementation is not a source
  of MIT code for this experiment.

The prototype below is independently written from a stated feature formula.
It is not claimed to be mathematically novel or superior to those architectures.

## Proposed compact network: C6-K16-128 (design, not trained)

Use two perspectives, one for each king. Square numbering is a1=0 through
h8=63. For black perspective flip ranks (`square XOR 56`) and invert piece
color roles. If the oriented own king is on files e–h, mirror files for ALL
pieces (`square XOR 7`). Bucket the canonical own king into four canonical
files times four rank pairs: `bucket = (king_rank // 2) * 4 + king_file`.
The context is **(bucket, mirror flag)**, not bucket alone.

For each of 12 relative piece types, including both kings:

`feature = (bucket * 12 + relative_piece_type) * 64 + canonical_piece_square`.

There are 12,288 input rows, at most 32 active rows in standard legal chess,
and a shared 128-channel feature transformer. Each perspective has an int16
accumulator. Concatenate side-to-move perspective first, then opposite
perspective; clipped activations feed `256 -> 32 -> 1`. Start with one head;
only after a useful baseline, test four material-selected heads. Material
head selection does not change the feature transformer. This avoids making
every material capture invalidate both accumulators.

### Proposed interface boundary

```text
FeatureContext context(Board, Color)
FeatureId encode(FeatureContext, Color, Piece, Square64)
refresh(Board, Color, Network, Accumulator)
update(parent_accumulator, dirty_removed[], dirty_added[], old_context,
       new_context, Board, Network, child_accumulator)
evaluate(acc_white, acc_black, side_to_move, phase, Network) -> int score_cp
```

Changes in own king bucket or mirroring refresh that perspective. Other moves
subtract removed rows and add new rows. Captures remove a victim row;
en passant uses the actual victim square, promotion changes type, castling
changes both king and rook rows. A king move within the same context still
updates its piece row. Undo restores parent state; null moves reorder outputs.

The Python contract uses board feature-set differences instead of dirty-piece
events, deliberately as a clear oracle. It is NOT the intended hot-path code.
Weights are synthetic deterministic integers solely to detect update mistakes.
No synthetic output is treated as a chess score.

## Executed tests

Command from repository root:

`python engines/CMEPT6/research/test_nnue_features.py`

Python 3.14, Windows: **4 tests passed**, one observed run 0.451 s. The test
duration is not an inference benchmark and includes Python/reference move code.

- Horizontal mirroring and rank-flip/color-swap preserve feature IDs.
- Castling both ways, en passant, king capture of a pawn, and all four
  capture-promotions: incremental accumulators equal full recomputation,
  then undo restores the original integers for both perspectives.
- King d1→e1: bucket stays equal but mirror changes; refresh is mandatory.
- 256 seeded legal-walk iterations, two perspectives: exact update/rebuild
  parity, feature bounds, feature count and int16 bounds.

The independent existing Python referee generates the legal walk. This tests
the new encoder/accumulator contract, not C++ board mutations or SIMD.

## Quantization and serialization gates before engine integration

1. A versioned file header must include feature schema ID, architecture sizes,
   orientation convention, clipping/rounding/scales, payload length, checksum,
   training manifest digest and dataset provenance. Reject incompatible sizes
   and truncation; never reinterpret an unknown network as the current layout.
2. Establish a scalar integer oracle before SIMD. Proposed initial FT int8
   rows and biases clamped to [-127,127] give accumulator bound
   `32*127+127=4191`, safely within int16. Revisit this proof if biases, legal
   piece count or features change. Do not silently wrap arithmetic.
3. With clipped [0,127] input and int8 hidden weights, 256-term dot products
   have absolute product-sum bound `256*127*127=4,129,024`; bounded int32
   biases must preserve int32 safety. Define signed rounding exactly.
4. For each held-out position compare Python float, Python quantized,
   C++ scalar and AVX2. Integer paths must match bit-for-bit. Float-vs-quantized
   error is measured with mean/p99/max and phase strata, not assumed zero.
5. Run make/unmake parity on at least 100,000 legal transitions including
   forced special moves; check ordinary/null/undo/castling/promotion paths.
6. AVX-512 is optional only after CPU capability dispatch and parity tests;
   keep scalar fallback and measure complete search, not only dot products.

## Data and leakage control

Start with a 100,000-position pipeline smoke test, then a separate 1-million
position pilot if validation passes. These are proposed budgets, not generated
datasets. Use reproducible self-play from owned CMEPT6 code and fixed openings.
For every record store game ID, opening family/seed, position/FEN, ply, result,
teacher/version/hash if used, node/time budget, side-to-move label convention,
sampling/filtering version and source/license provenance.

Do not train only on baseline evaluation labels: that mainly learns a noisy
copy of the current evaluator. Compare outcome supervision against a clearly
specified outcome/teacher blend as an ablation. Keep mate labels distinct from
clipped centipawns. Record resignations/adjudications; exclude unfinished games
from terminal-result labels. Do not label a search cutoff as a known result.

Split by game and opening family before sampling positions. Deduplicate
canonical position keys and ensure none appear across train/validation/test;
resolve shared transposition groups before assignment. Retain side, castling
and legally relevant en passant when defining a position key. Freeze test set
and opening holdout manifest before tuning. Never randomly split adjacent plies
from one game across sets. Audit class/phase balance and augmentation leakage.
Keep raw data and manifests separate from this public source mirror.

## Estimated costs (arithmetic, not measured throughput)

For 128 channels, int8 FT rows occupy `12,288*128 = 1,572,864 bytes` (1.5 MiB)
plus biases. Four `256->32->1` heads need about 33 KiB of int8 weights plus
int32 biases. Two int16 accumulators take 512 bytes per ply, or 50 KiB for
100 plies. A quiet non-king move needs two row operations per perspective:
512 integer additions/subtractions total. A two-perspective full refresh
at 32 pieces needs at most 8,192 scalar additions. One head uses 8,224 MACs
excluding activation/scaling; four heads do NOT all run per position.

Float32 training parameters for this small network take roughly 6.2 MiB;
weights+gradients+two Adam states roughly 25 MiB, before activations, framework,
batch indices, optimizer overhead and loaders. This is not a GPU-memory
guarantee. Sparse batches and bounded loaders are required.

Generation wall time is `N * measured_seconds_per_label / workers`; training
time is `epochs * N / measured_examples_per_second`. Measure both on a
10,000-record pilot before committing a long run. No GPU benchmark, NPS,
training duration, accuracy, Elo or confidence interval was measured here.

## Decision and next task

NPS/benchmark: NOT MEASURED. Matches: NOT RUN. Elo/CI: NOT AVAILABLE.
Risks: context-refresh omissions; training/evaluation sign mismatch; quantized
overflow; data leakage; increased eval cost overwhelming accuracy gains;
runtime and memory cost of extra experts; legal-position oracle limitations.

Rejected for this cycle: importing external weights/trainer code, introducing
eight experts immediately, claiming a trained NNUE, running unbudgeted training,
or replacing the working evaluator before scalar parity and strength tests.

Next task: implement the exact feature contract and dirty-piece accumulator
oracle in an isolated C++ module; pass cross-language parity and measured eval
benchmarks. Then train the small pilot and test against the frozen 1.1 baseline
at identical resources with a predeclared paired-match statistical protocol.
No release or production integration is recommended from this prototype alone.
