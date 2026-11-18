#!/usr/bin/env python3
"""Paired, sequential CMEPT6 search benchmark; not a strength/Elo test.

Example: python tests/benchmark.py --baseline baseline.exe --candidate candidate.exe
  --depth 7 --repeats 3 --out results/search-benchmark.json
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import queue
import random
import re
import statistics
import time

from referee import Position
from tournament import UCIEngine, EngineFailure

DEFAULT_SUITE = Path(__file__).with_name('benchmark_positions.json')
INFO = re.compile(r'^info depth (\d+) score (cp|mate) (-?\d+) nodes (\d+) time (\d+) nps (\d+)(?: pv(?: (.*))?)?$')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_suite(path):
    rows = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('position suite must be a nonempty JSON array')
    names = set()
    for row in rows:
        if not isinstance(row.get('name'), str) or not row['name'] or row['name'] in names:
            raise ValueError('position names must be unique and nonempty')
        if '\n' in row['fen'] or '\r' in row['fen']:
            raise ValueError('FEN cannot contain UCI command separators')
        pos = Position.from_fen(row['fen'])
        if pos.check(not pos.white):
            raise ValueError('the side not to move cannot be in check')
        names.add(row['name'])
    return rows


def parse_result(lines, fen, elapsed):
    best = lines[-1].split() if lines else []
    if len(best) < 2 or best[0] != 'bestmove':
        raise EngineFailure('search did not terminate with bestmove')
    legal = Position.from_fen(fen).legal()
    if best[1] not in legal and not (best[1] == '0000' and not legal):
        raise EngineFailure('illegal bestmove: ' + best[1])
    infos = [INFO.fullmatch(line) for line in lines]
    infos = [match for match in infos if match]
    if not infos and legal:
        raise EngineFailure('nonterminal search returned no completed-depth telemetry')
    last = infos[-1] if infos else None
    return {
        'bestmove': best[1], 'wall_ms': elapsed * 1000,
        'completed_depth': int(last[1]) if last else None,
        'score_type': last[2] if last else None,
        'score': int(last[3]) if last else None,
        # Nodes/time/nps belong to the last COMPLETED iteration. With go nodes
        # they exclude the unfinished iteration: never label these total nodes.
        'last_completed_nodes': int(last[4]) if last else None,
        'last_completed_engine_ms': int(last[5]) if last else None,
        'last_completed_nps': int(last[6]) if last else None,
        'pv': last[7] if last else None,
        'uci_output': lines,
    }


class BenchEngine(UCIEngine):
    def measure(self, fen, budget):
        self.new_game()  # cold TT and game state for EVERY sample
        self.send('position fen ' + fen)
        self.ready()
        started = time.perf_counter()
        self.send(budget)
        lines = []
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EngineFailure('benchmark search timeout')
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise EngineFailure('benchmark search timeout') from exc
            if line is None:
                raise EngineFailure('engine exited during benchmark')
            lines.append(line)
            if len(lines) > 10000:
                raise EngineFailure('excessive engine output')
            if 'Invalid FEN' in line or 'Illegal UCI move' in line:
                raise EngineFailure(line)
            if line.startswith('bestmove '):
                return parse_result(lines, fen, time.perf_counter() - started)


def summarize(samples):
    pairs = {}
    for sample in samples:
        pairs.setdefault((sample['repeat'], sample['position']), {})[sample['engine']] = sample
    if not pairs or any(set(pair) != {'baseline', 'candidate'} for pair in pairs.values()):
        raise ValueError('cannot summarize missing or incomplete paired observations')
    ratios = []
    changed = 0
    for pair in pairs.values():
        a, b = pair['baseline'], pair['candidate']
        if a['wall_ms'] <= 0 or b['wall_ms'] <= 0:
            raise ValueError('wall times must be positive')
        ratios.append(b['wall_ms'] / a['wall_ms'])
        changed += a['bestmove'] != b['bestmove']
    return {
        'paired_samples': len(pairs),
        'candidate_over_baseline_wall_ratio_geomean': math.exp(statistics.mean(map(math.log, ratios))),
        'candidate_over_baseline_wall_ratio_median': statistics.median(ratios),
        'different_bestmoves': changed,
        'samples_under_50ms': sum(s['wall_ms'] < 50 for s in samples),
        'elo': None,
        'interpretation': 'Timing/telemetry only. No strength conclusion, confidence interval or SPRT. Lower wall ratio is faster at this budget; depth and node budgets answer different questions.',
    }


def run(args):
    if args.repeats < 1 or args.hash < 1 or args.hash > 1024 or args.timeout <= 0:
        raise ValueError('invalid repeats, hash or timeout')
    if (args.depth is not None and not 1 <= args.depth <= 64) or (args.nodes is not None and args.nodes < 10000):
        raise ValueError('depth must be 1..64; node budget must be >= 10000')
    suite = load_suite(args.positions)
    out = Path(args.out)
    if out.exists():
        raise ValueError('output exists: choose a new run filename')
    budget = f'go depth {args.depth}' if args.depth is not None else f'go nodes {args.nodes}'
    report = {
        'schema': 1, 'status': 'running', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'base_revision': args.base_revision, 'candidate_revision': args.candidate_revision,
        'platform': {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine(),
                     'processor': platform.processor(), 'logical_cpus': os.cpu_count(), 'python': platform.python_version()},
        'engines': {k: {'filename': Path(v).name, 'sha256': digest(v)} for k,v in [('baseline',args.baseline),('candidate',args.candidate)]},
        'config': {'budget': budget, 'repeats': args.repeats, 'hash_mb': args.hash,
                   'uncertainty_search': False, 'search_threads': 1, 'seed': args.seed,
                   'processes': 'two resident engines, searches sequential, paired order randomized',
                   'warmup': 'one depth-2 search per process; cold TT on every measured sample',
                   'position_suite_sha256': digest(args.positions)},
        'positions': suite, 'samples': [],
    }
    engines = {}
    try:
        for name, path in [('baseline', args.baseline), ('candidate', args.candidate)]:
            engines[name] = BenchEngine(path, name, {'Hash': args.hash, 'UncertaintySearch': 'false'}, args.timeout)
            engines[name].measure(suite[0]['fen'], 'go depth 2')
        rng = random.Random(args.seed)
        for repeat in range(args.repeats):
            positions = list(suite)
            rng.shuffle(positions)
            for row in positions:
                order = ['baseline', 'candidate']; rng.shuffle(order)
                for name in order:
                    sample = engines[name].measure(row['fen'], budget)
                    if args.depth and sample['score_type'] != 'mate' and sample['completed_depth'] != args.depth:
                        raise EngineFailure('requested fixed depth was not completed')
                    sample.update(engine=name, position=row['name'], repeat=repeat, order=order.index(name))
                    report['samples'].append(sample)
        report['summary'] = summarize(report['samples'])
        report['status'] = 'complete'
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)
        raise
    finally:
        for engine in engines.values():
            engine.close()
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['summary'], indent=2))


def cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True)
    p.add_argument('--candidate', required=True)
    p.add_argument('--base-revision', default='NOT PROVIDED')
    p.add_argument('--candidate-revision', default='NOT PROVIDED')
    budget = p.add_mutually_exclusive_group(required=True)
    budget.add_argument('--depth', type=int)
    budget.add_argument('--nodes', type=int)
    p.add_argument('--positions', default=str(DEFAULT_SUITE))
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--hash', type=int, default=32)
    p.add_argument('--timeout', type=float, default=60)
    p.add_argument('--seed', type=int, default=20261116)
    p.add_argument('--out', required=True)
    return p.parse_args()


if __name__ == '__main__':
    run(cli())
