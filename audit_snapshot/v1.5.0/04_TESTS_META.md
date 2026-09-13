# SFERA v1.5 Canonical Pack — 04_TESTS_META

Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`


## FILE: `VERSION.txt`

```text
1.5.0

```

## FILE: `requirements.txt`

```text
PySide6-Essentials>=6.8,<7

```

## FILE: `tests/test_genome.py`

```python
import unittest, tempfile
from pathlib import Path
from sfera.db import SferaDB
from sfera.genome import GenomeImporter

S='''[Event "t"]\n[White "A"]\n[Black "B"]\n[WhiteElo "2200"]\n[BlackElo "2300"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0\n'''
class T(unittest.TestCase):
    def test_import(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.pgn'; p.write_text(S,encoding='utf-8'); db=SferaDB(Path(d)/'x.db'); r=GenomeImporter(db).import_pgn(p)
            self.assertEqual(r['games'],1); self.assertGreaterEqual(r['positions'],6); self.assertEqual(db.stats()['games'],1); db.close()
if __name__=='__main__':unittest.main()

```

## FILE: `tests/test_engine_lab21.py`

```python
import tempfile, unittest
from pathlib import Path
from sfera.engine_lab21 import EngineLab21Manager, DEFAULT_ENGINES

class Lab21(unittest.TestCase):
    def test_registry_has_exactly_21_slots(self):
        self.assertEqual(len(DEFAULT_ENGINES),21)
        with tempfile.TemporaryDirectory() as d:
            m=EngineLab21Manager(Path(d))
            self.assertEqual(len(m.registry),21)
            self.assertEqual(m.registry[0]['slot'],1)
            self.assertEqual(m.registry[-1]['slot'],21)

if __name__=='__main__':unittest.main()

```

## FILE: `tests/test_report_v15.py`

```python
from pathlib import Path
from sfera.db import SferaDB
from sfera.genome import GenomeImporter
from sfera.report import SferaReportBuilder
from sfera.chesslite import START_FEN

PGN='''[Event "A"]
[Date "2025.01.01"]
[White "A"]
[Black "B"]
[WhiteElo "1300"]
[BlackElo "1300"]
[TimeControl "600+0"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0

[Event "B"]
[Date "2026.02.01"]
[White "C"]
[Black "D"]
[WhiteElo "2100"]
[BlackElo "2100"]
[TimeControl "180+2"]
[Result "1/2-1/2"]

1. e4 c5 2. Nf3 d6 1/2-1/2

[Event "C"]
[Date "2026.03.01"]
[White "E"]
[Black "F"]
[WhiteElo "2600"]
[BlackElo "2600"]
[TimeControl "5400+30"]
[Result "0-1"]

1. d4 Nf6 2. c4 e6 0-1
'''

def test_report_segments_and_plans(tmp_path):
    db=SferaDB(tmp_path/'sfera.sqlite3')
    p=tmp_path/'x.pgn';p.write_text(PGN,encoding='utf-8')
    st=GenomeImporter(db).import_pgn(p)
    assert st['games']==3
    rep=SferaReportBuilder(db).build(START_FEN,save_snapshot=True)
    assert rep['meta']['in_genome'] is True
    elo={r['elo_band']:r['seen_count'] for r in rep['elo']['rows']}
    assert elo['<1400']==1
    assert elo['1800–2199']==1
    assert elo['2500+']==1
    years={r['year']:r['seen_count'] for r in rep['trends']['rows']}
    assert years[2025]==1 and years[2026]==2
    moves={r['move']:r['seen'] for r in rep['plans']['rows']}
    assert moves['e4']==2 and moves['d4']==1
    assert rep['human_difficulty']['available'] is True
    assert db.one('SELECT COUNT(*) n FROM report_snapshots')['n']==1
    db.close()

def test_report_backfill_is_idempotent(tmp_path):
    from sfera.report import ReportAnalyticsBackfill
    db=SferaDB(tmp_path/'sfera.sqlite3')
    p=tmp_path/'x.pgn';p.write_text(PGN,encoding='utf-8')
    GenomeImporter(db).import_pgn(p)
    ReportAnalyticsBackfill(db).rebuild()
    ReportAnalyticsBackfill(db).rebuild()
    rep=SferaReportBuilder(db).build(START_FEN,save_snapshot=False)
    assert sum(r['seen_count'] for r in rep['elo']['rows'])==3
    db.close()

```

## FILE: `tests/test_foundation.py`

```python
import unittest,tempfile
from pathlib import Path
from sfera.identity import position_hash128,canonical_fen_core
from sfera.db import SferaDB
from sfera.genome import GenomeImporter

PGN='''[Event "x"]\n[White "A"]\n[Black "B"]\n[WhiteElo "2200"]\n[BlackElo "2200"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'''

class Foundation(unittest.TestCase):
    def test_canonical_hash_ignores_clocks(self):
        a='8/8/8/8/8/8/8/K6k w - - 0 1'
        b='8/8/8/8/8/8/8/K6k w - - 92 77'
        self.assertEqual(position_hash128(a),position_hash128(b))
        self.assertEqual(len(position_hash128(a)),32)
    def test_transition_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.pgn';p.write_text(PGN,encoding='utf-8');db=SferaDB(Path(d)/'x.db')
            r=GenomeImporter(db).import_pgn(p)
            self.assertEqual(r['games'],1)
            self.assertGreaterEqual(db.one('SELECT COUNT(*) n FROM transitions')['n'],4)
            cp=db.one('SELECT * FROM import_checkpoints')
            self.assertEqual(cp['status'],'complete')
            db.close()
    def test_concept_versions(self):
        with tempfile.TemporaryDirectory() as d:
            db=SferaDB(Path(d)/'x.db')
            cid=db.upsert_concept('X','first',.5,1)
            db.upsert_concept('X','second',.8,2,reason='new evidence')
            c=db.one('SELECT * FROM concepts WHERE id=?',(cid,))
            self.assertGreaterEqual(c['current_version'],2)
            self.assertGreaterEqual(db.one('SELECT COUNT(*) n FROM concept_versions WHERE concept_id=?',(cid,))['n'],2)
            self.assertGreaterEqual(db.one('SELECT COUNT(*) n FROM brain_journal')['n'],2)
            db.close()
if __name__=='__main__':unittest.main()

```
