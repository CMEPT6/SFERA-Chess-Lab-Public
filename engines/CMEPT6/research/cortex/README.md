# CORTEX-001 — candidate policy before search
Status: proposed, offline scorer implemented; no live model, engine-strength, or Elo results.
Baseline: 9c00ccb3678ffbdd554b57d0b2b30364d6e76cf1.
This work is isolated from open PRs #3–#6.

## Research question
Can LLM-generated candidate rankings supply useful supervision for a small, locally trained chess policy head? This is an offline teacher screen, not an attempt to run a language model at every search node. Neural move ordering is already known; our hypothesis is about incremental information from diverse teachers and their disagreements.
References: https://dubesor.de/chess/chess-leaderboard (LLM play, distinct rating pool); https://github.com/SaintNong/neural-moves (neural move-ordering research); https://github.com/google-deepmind/searchless_chess (chess policy/value learning).

## First experiment (pre-register before collecting)
1. Collect 200 development positions and 100 hidden test positions from independently licensed games or engine self-play. Group by source game, deduplicate position identities and symmetry-related copies, avoid opening-book memorization, and prevent train/test leakage. Keep test answers outside agent-visible files.
2. Generate legal move lists with an independent chess library or validated referee. Exclude terminal positions and positions with history-dependent draws that cannot be reconstructed from FEN alone. Label position categories in advance (tactical, quiet, defensive, endgame); use the same positions for all teachers.
3. Freeze referee version, hardware, search settings and budget. Use a strong engine at higher fixed node budget, MultiPV and repeat/deeper checks for close choices; use Syzygy when applicable. Preserve near-tied acceptable moves using a predeclared WDL tolerance (e.g. expected score difference <= 0.01 on the same calibrated scale); record uncertain labels and report separately. Do not equate finite search labels with chess truth.
4. Compare random legal ordering, simple capture/check heuristics, shallow engine ordering, individual LLM teachers, and their aggregate ranking. Every model sees identical inputs (FEN and legal UCI list), with model/version, prompt, temperature, response token budget, latency and cost logged. No hints from the reference. Use separate no-tools track and tool-allowed track if needed.
5. Compute top-1/top-3, mean reciprocal rank (MRR), invalid/missing rates, time and cost; report paired bootstrap intervals grouped by game and separate category results. Include all positions in denominators. The scorer supports ranking metrics and uniform-random expectations only; provenance, referee generation, cost and bootstrap are future work.
6. Only if teacher candidates add measurable held-out value beyond inexpensive baselines, distill into an independent small policy network (random initialization; own weights, documented data and license provenance). Compare single-teacher vs multi-teacher with identical data and training budgets. No live LLM in the candidate UCI engine by default.
7. Test actual move ordering at fixed nodes and fixed wall time, with policy OFF/ON and matched controls. Verify legal search, then run paired-opening matches against baseline via independent arbiter and predeclared statistical acceptance criteria. Top-3 or NPS is not Elo. Check current competition rules separately before submitting.

## Common teacher prompt
Given the FEN and supplied legal UCI moves, rank exactly three distinct legal candidates (or all if fewer than three). Return JSON only: {"id":"<position_id>","moves":["e2e4","d2d4","g1f3"]}. No engine/tools unless the track allows them. Do not infer the reference answer from other agents.

## Offline runner
Node.js, no dependencies. From this directory:
    node score.mjs --self-test
    node score.mjs positions.json answers.json

positions.json is an array: [{"id":"p01","fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1","legal":["...all independently verified legal UCI moves..."],"best":["...referee-approved moves..."]}].
answers.json is an array: [{"id":"p01","moves":["e2e4","d2d4","g1f3"]}].
The strings with ellipses above are documentation placeholders, not runnable data.
The scorer checks move syntax and set consistency, not FEN legality: it relies on the externally generated legal list. Missing/invalid answers count as zero. Extra or duplicate IDs reject the input. Report random baselines as expectations, not measured matches. Synthetic self-test is not a chess benchmark.
Keep hidden labels private; do not upload API keys or proprietary data. Do not reuse benchmark positions as training examples.

## Next steps
Generate a licensed development set and a held-out set, validate legal moves independently, then collect teacher answers within an explicitly approved budget. No paid APIs or autonomous agents have been activated.
