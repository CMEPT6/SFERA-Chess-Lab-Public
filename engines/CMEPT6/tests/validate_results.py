#!/usr/bin/env python3
"""Read an independently refereed match and verify recorded PGN/JSON consistency."""
import json
from pathlib import Path
import sys
from referee import Position

prefix = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('results/independent_match')
records = [json.loads(line) for line in prefix.with_suffix('.jsonl').read_text().splitlines() if line.strip()]
summary = json.loads(prefix.with_suffix('.summary.json').read_text())
pgn = prefix.with_suffix('.pgn').read_text(encoding='utf-8')
assert records and len(records) == summary['games_requested']
counts = {'win': 0, 'draw': 0, 'loss': 0, 'unfinished': 0}
for rec in records:
    p = Position.start()
    sans = []
    for m in rec['moves_uci']:
        legal = p.legal()
        assert m in legal, (rec['game'], m)
        sans.append(p.san(m, legal))
        p = p.make(m)
    assert sans == rec['moves_san']
    assert rec['plies'] == len(rec['moves_uci'])
    assert rec['result'] in ('1-0', '0-1', '1/2-1/2', '*')
    counts[rec['outcome_for_a']] += 1
    assert '[Round "' + str(rec['game']) + '"]' in pgn
    assert '[Result "' + rec['result'] + '"]' in pgn
assert counts == {'win':summary['wins_a'],'draw':summary['draws'],'loss':summary['losses_a'],'unfinished':summary['unfinished']}, counts
assert summary['games_completed'] == sum(v for k,v in counts.items() if k != 'unfinished')
print(f'PASS: {len(records)} independently verified games, SAN, PGN headers, results and WDL')
