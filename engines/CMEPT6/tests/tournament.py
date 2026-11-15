#!/usr/bin/env python3
"""Independent standard-chess UCI match harness. No pip packages required.

Example:
  python tests/tournament.py --a ./build/cmept6-engine --b ./build/cmept6-engine \
      --games 20 --depth 4 --max-plies 180 --out results/duel_v1_1

Game results are determined by tests/referee.py, NOT by the engine's 'status'.
Moves and checkmate are checked independently. 'Unfinished' games are recorded
as * (never counted as draws). Elo summaries are exploratory, not SPRT.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
from referee import Position

ROOT = Path(__file__).resolve().parents[1]
def read_openings(file: str):
    entries = []
    for no, text in enumerate(Path(file).read_text(encoding='utf-8').splitlines(), 1):
        if not text.strip() or text.lstrip().startswith('#'): continue
        if '|' not in text: raise ValueError(f'{file}:{no}: expected Name|e2e4 ...')
        title, moves = text.split('|', 1)
        pos = Position.start()
        for m in moves.split():
            if m not in pos.legal(): raise ValueError(f'{file}:{no}: illegal opening move {m}')
            pos = pos.make(m)
        if not moves.strip(): raise ValueError(f'{file}:{no}: empty opening')
        entries.append((title.strip(), moves.strip()))
    if not entries: raise ValueError('no openings in file')
    return entries

UCI_MOVE = re.compile(r'^[a-h][1-8][a-h][1-8][qrbn]?$')

class EngineFailure(Exception): pass

class UCIEngine:
    def __init__(self, path: str, name: str, options: dict, timeout: float):
        self.name, self.timeout = name, timeout
        exe = str(Path(path).resolve())
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.lines = queue.Queue()
        self.thread = threading.Thread(target=self._read_lines, daemon=True)
        self.thread.start()
        self.send('uci')
        self.wait('uciok', min(timeout, 12))
        for key, value in options.items():
            self.send(f'setoption name {key} value {value}')
        self.ready()

    def _read_lines(self):
        try:
            for line in self.p.stdout: self.lines.put(line.strip())
        finally:
            self.lines.put(None)

    def send(self, command):
        if self.p.poll() is not None: raise EngineFailure(f'{self.name} exited: {self.p.returncode}')
        try:
            self.p.stdin.write(command + '\n'); self.p.stdin.flush()
        except OSError as exc:
            raise EngineFailure(f'{self.name}: write failed') from exc

    def wait(self, prefix, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        recent = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise EngineFailure(f'{self.name}: timeout waiting for {prefix}; {recent[-4:]}')
            try: line = self.lines.get(timeout=remaining)
            except queue.Empty: raise EngineFailure(f'{self.name}: timeout waiting for {prefix}')
            if line is None: raise EngineFailure(f'{self.name}: exited before {prefix}; {recent[-4:]}')
            recent.append(line)
            if 'Illegal UCI move' in line or 'Invalid FEN' in line:
                raise EngineFailure(f'{self.name}: engine rejected valid position: {line}')
            if line.startswith(prefix): return line

    def ready(self):
        self.send('isready')
        self.wait('readyok', 12)

    def new_game(self):
        self.send('ucinewgame')
        self.ready()

    def bestmove(self, moves: list[str], depth: int, move_ms: int) -> str:
        self.send('position startpos' + (' moves ' + ' '.join(moves) if moves else ''))
        self.ready()
        self.send(f'go movetime {move_ms}' if move_ms else f'go depth {depth}')
        line = self.wait('bestmove ', self.timeout)
        move = line.split()[1]
        if not UCI_MOVE.fullmatch(move):
            raise EngineFailure(f'{self.name}: malformed or absent bestmove: {move}')
        return move

    def close(self):
        if self.p.poll() is None:
            try: self.send('quit'); self.p.wait(timeout=3)
            except Exception:
                self.p.kill(); self.p.wait(timeout=3)
        self.p.stdin.close()
        self.p.stdout.close()
        self.thread.join(timeout=1)


def format_pgn(moves_san, white_name, black_name, result, reason, round_n, opening, depth, move_ms):
    date = datetime.now(timezone.utc).strftime('%Y.%m.%d')
    tags = {
        'Event': 'CMEPT6 independent UCI experiment', 'Site': 'local', 'Date': date,
        'Round': str(round_n), 'White': white_name, 'Black': black_name,
        'Result': result, 'Opening': opening, 'Termination': reason,
        'TimeControl': f'{move_ms}ms per move' if move_ms else f'depth {depth}',
    }
    headers = '\n'.join('[' + k + ' "' + v.replace('"', "'") + '"]' for k, v in tags.items())
    words = []
    for i, san in enumerate(moves_san):
        if i % 2 == 0: words.append(f'{1+i//2}.')
        words.append(san)
    words.append(result)
    return headers + '\n\n' + ' '.join(words) + '\n\n'


def experiment(config):
    if config.games < 2 or config.games % 2:
        raise ValueError('--games must be a positive even number (paired openings)')
    if config.depth < 1 or config.max_plies < 10 or config.movetime < 0:
        raise ValueError('invalid depth, time or max-plies')
    opening_book = read_openings(config.openings_file)
    if config.games > 2 * len(opening_book):
        print(f'NOTE: {config.games} games reuse {len(opening_book)} paired openings. '
              'For rating studies use a larger opening suite.', flush=True)
    dest = Path(config.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    engines = []
    scores = Counter()
    records = []
    try:
        for name, path, uncertainty in ((config.name_a, config.a, config.a_uncertainty),
                                        (config.name_b, config.b, config.b_uncertainty)):
            client = UCIEngine(path, name, {'Hash': config.hash,
                'UncertaintySearch': 'true' if uncertainty else 'false'}, config.timeout)
            engines.append(client)
        a, b = engines
        with dest.with_suffix('.pgn').open('w', encoding='utf-8') as pgn, \
                dest.with_suffix('.jsonl').open('w', encoding='utf-8') as log:
            for i in range(config.games):
                white_is_a = i % 2 == 0
                white, black = (a,b) if white_is_a else (b,a)
                opening_name, opening_uci = opening_book[(i//2) % len(opening_book)]
                moves = []
                pos = Position.start()
                san_moves = []
                reps = Counter({pos.key(): 1})
                error = None
                result_reason = None
                result = '*'
                a.new_game(); b.new_game()
                for opening_move in opening_uci.split():
                    legal = pos.legal()
                    assert opening_move in legal
                    san_moves.append(pos.san(opening_move, legal))
                    pos = pos.make(opening_move)
                    moves.append(opening_move)
                    reps[pos.key()] += 1
                for ply in range(len(moves), config.max_plies):
                    result_reason = pos.result(reps)
                    if result_reason is not None:
                        result, reason = result_reason; break
                    current = white if pos.white else black
                    try:
                        move = current.bestmove(moves, config.depth, config.movetime)
                        legal = pos.legal()
                        if move not in legal:
                            raise EngineFailure(f'{current.name}: illegal move {move} at ply {ply}; allowed={legal}')
                    except EngineFailure as exc:
                        error = str(exc)
                        result = '0-1' if pos.white else '1-0'
                        reason = f'engine error / forfeit: {current.name}'
                        break
                    san_moves.append(pos.san(move, legal))
                    pos = pos.make(move)
                    moves.append(move)
                    reps[pos.key()] += 1
                else:
                    terminal = pos.result(reps)
                    if terminal is not None:
                        result, reason = terminal
                    else:
                        result, reason = '*', 'unfinished: ply cutoff (NOT scored as draw)'
                outcome = ('unfinished' if result == '*' else 'draw' if result == '1/2-1/2'
                           else 'win' if (result == '1-0') == white_is_a else 'loss')
                scores[outcome] += 1
                rec = {'game': i + 1, 'opening': opening_name,
                       'a_white': white_is_a, 'result': result, 'outcome_for_a': outcome,
                       'reason': reason, 'error': error, 'plies': len(moves),
                       'moves_uci': moves, 'moves_san': san_moves,
                       'depth': config.depth if not config.movetime else None,
                       'movetime_ms': config.movetime or None}
                log.write(json.dumps(rec, ensure_ascii=False) + '\n'); log.flush()
                pgn.write(format_pgn(san_moves, white.name, black.name, result, reason,
                                     i + 1, opening_name, config.depth, config.movetime)); pgn.flush()
                records.append(rec)
                print(f'Game {i+1}/{config.games} {opening_name}: {result} A:{outcome} ({reason})', flush=True)
    finally:
        for eng in engines: eng.close()
    completed = scores['win'] + scores['loss'] + scores['draw']
    points = scores['win'] + scores['draw'] * .5
    score = points / completed if completed else None
    # A descriptive, smoothed Elo estimate (NOT a confidence interval or an SPRT pass).
    smoothed = (points + 0.5) / (completed + 1) if completed else None
    elo = 400 * math.log10(smoothed / (1 - smoothed)) if completed else None
    summary = {
        'engine_a': str(Path(config.a).resolve()), 'engine_b': str(Path(config.b).resolve()),
        'games_requested': config.games, 'games_completed': completed,
        'distinct_paired_openings': min(config.games // 2, len(opening_book)),
        'wins_a': scores['win'], 'draws': scores['draw'], 'losses_a': scores['loss'],
        'unfinished': scores['unfinished'], 'score_a': score,
        'exploratory_elo_a_minus_b': round(elo, 2) if elo is not None else None,
        'warning': 'NOT an established Elo rating. No confidence bounds/SPRT; small or depth-limited samples are not evidence of strength.',
        'referee': 'separate Python standard-chess rules, no CMEPT6 status command',
    }
    dest.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--a', required=True, help='Engine A executable')
    p.add_argument('--b', required=True, help='Engine B executable')
    p.add_argument('--games', type=int, default=20, help='Even number, paired colour openings')
    p.add_argument('--name-a', default='Engine A', help='PGN name of engine A')
    p.add_argument('--name-b', default='Engine B', help='PGN name of engine B')
    p.add_argument('--openings-file', default=str(ROOT / 'tests' / 'openings_uci.txt'),
                   help='Opening list Name|UCI moves, two games per line')
    p.add_argument('--depth', type=int, default=4, help='Fixed depth if no movetime')
    p.add_argument('--movetime', type=int, default=0, help='Fixed ms per move instead of fixed depth')
    p.add_argument('--max-plies', type=int, default=180)
    p.add_argument('--timeout', type=float, default=35)
    p.add_argument('--hash', type=int, default=32)
    p.add_argument('--a-uncertainty', action='store_true')
    p.add_argument('--b-uncertainty', action='store_true')
    p.add_argument('--out', default='results/independent_match')
    return p.parse_args()

if __name__ == '__main__':
    experiment(cli())
