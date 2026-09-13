# Canonical source fragment

Original file: `sfera/db.py`
Lines: 197-353
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
CREATE TABLE IF NOT EXISTS transition_tc_stats(
 transition_id INTEGER NOT NULL, tc_class TEXT NOT NULL,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black_wins INTEGER DEFAULT 0,
 PRIMARY KEY(transition_id, tc_class),
 FOREIGN KEY(transition_id) REFERENCES transitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report_snapshots(
 id INTEGER PRIMARY KEY, pos_hash TEXT NOT NULL, fen TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_report_snapshots_hash ON report_snapshots(pos_hash, created_at DESC);

CREATE TABLE IF NOT EXISTS benchmark_cases(
 id INTEGER PRIMARY KEY, suite TEXT NOT NULL, name TEXT NOT NULL, fen TEXT NOT NULL,
 expected_move TEXT DEFAULT '', expected_eval_min INTEGER, expected_eval_max INTEGER,
 tags_json TEXT DEFAULT '[]', UNIQUE(suite, name)
);
CREATE TABLE IF NOT EXISTS benchmark_runs(
 id INTEGER PRIMARY KEY, label TEXT, engine TEXT, created_at REAL NOT NULL,
 score REAL DEFAULT 0, payload_json TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS benchmark_results(
 id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, case_id INTEGER NOT NULL,
 chosen_move TEXT, score_cp INTEGER, passed INTEGER DEFAULT 0,
 latency_ms REAL DEFAULT 0, payload_json TEXT DEFAULT '{}',
 FOREIGN KEY(run_id) REFERENCES benchmark_runs(id) ON DELETE CASCADE,
 FOREIGN KEY(case_id) REFERENCES benchmark_cases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teacher_lessons(
 id INTEGER PRIMARY KEY, lesson_id TEXT UNIQUE, title TEXT, payload_json TEXT NOT NULL,
 imported_at REAL NOT NULL, applied INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS web_sources(
 id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, text_z BLOB,
 fetched_at REAL NOT NULL, trust REAL DEFAULT .2,
 status TEXT DEFAULT 'quarantine', notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS discoveries(
 id INTEGER PRIMARY KEY, discovery_key TEXT UNIQUE, kind TEXT, title TEXT,
 statement TEXT, score REAL DEFAULT .5, evidence_count INTEGER DEFAULT 0,
 status TEXT DEFAULT 'candidate', payload_json TEXT DEFAULT '{}', updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_discoveries_score ON discoveries(score DESC);

CREATE TABLE IF NOT EXISTS brain_journal(
 id INTEGER PRIMARY KEY, ts REAL NOT NULL, event_type TEXT NOT NULL,
 title TEXT NOT NULL, before_json TEXT DEFAULT '{}', after_json TEXT DEFAULT '{}',
 reason TEXT DEFAULT '', evidence_json TEXT DEFAULT '[]', confidence_before REAL,
 confidence_after REAL
);
CREATE INDEX IF NOT EXISTS idx_brain_journal_ts ON brain_journal(ts DESC);
'''

class SferaDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version','3')")
        self.conn.commit()

    def _cols(self, table):
        return {r['name'] for r in self.conn.execute(f'PRAGMA table_info({table})')}

    def _add_col(self, table, spec):
        name = spec.split()[0]
        if name not in self._cols(table):
            self.conn.execute(f'ALTER TABLE {table} ADD COLUMN {spec}')

    def _migrate(self):
        for spec in ('source_id INTEGER',"time_control TEXT DEFAULT ''","eco TEXT DEFAULT ''","opening TEXT DEFAULT ''","start_fen TEXT DEFAULT ''"):
            if spec: self._add_col('games', spec)
        for spec in ('canonical_fen TEXT','memory_level INTEGER DEFAULT 0'):
            self._add_col('positions', spec)
        self._add_col('exemplars','source_id INTEGER')
        self._add_col('concepts','current_version INTEGER DEFAULT 1')
        self._add_col('research_sessions',"strategy TEXT DEFAULT 'adaptive'")
        for spec in ('pos_hash TEXT','priority REAL DEFAULT 0','novelty REAL DEFAULT 0','disagreement REAL DEFAULT 0'):
            self._add_col('research_nodes', spec)
        self.conn.commit()
        self._migrate_position_identity()

    def _migrate_position_identity(self):
        from .identity import position_hash128, canonical_fen_core
        rows=list(self.conn.execute("SELECT * FROM positions WHERE canonical_fen IS NULL OR length(pos_hash)<>32"))
        for r in rows:
            try:
                nh=position_hash128(r['fen']); can=canonical_fen_core(r['fen'])
            except Exception:
                continue
            ex=self.conn.execute('SELECT * FROM positions WHERE pos_hash=? AND id<>?',(nh,r['id'])).fetchone()
            if ex:
                for e in self.conn.execute('SELECT * FROM exemplars WHERE position_id=?',(r['id'],)):
                    self.conn.execute('INSERT OR IGNORE INTO exemplars(position_id,game_id,ply,move_san,quality,source_id) VALUES(?,?,?,?,?,?)',(ex['id'],e['game_id'],e['ply'],e['move_san'],e['quality'],e['source_id']))
                self.conn.execute('UPDATE evidence SET position_id=? WHERE position_id=?',(ex['id'],r['id']))
                self.conn.execute('UPDATE engine_opinions SET position_id=? WHERE position_id=?',(ex['id'],r['id']))
                self.conn.execute('''UPDATE positions SET seen_count=seen_count+?,white_wins=white_wins+?,draws=draws+?,black_wins=black_wins+?,
                    avg_elo=CASE WHEN seen_count+?>0 THEN (avg_elo*seen_count+?*?)/(seen_count+?) ELSE avg_elo END,
                    novelty=MIN(novelty,?),memory_score=MAX(memory_score,?),memory_level=MAX(memory_level,?),last_seen=MAX(last_seen,?) WHERE id=?''',
                    (r['seen_count'],r['white_wins'],r['draws'],r['black_wins'],r['seen_count'],r['avg_elo'],r['seen_count'],r['seen_count'],r['novelty'],r['memory_score'],r['memory_level'] or 0,r['last_seen'] or 0,ex['id']))
                self.conn.execute('DELETE FROM exemplars WHERE position_id=?',(r['id'],))
                self.conn.execute('DELETE FROM positions WHERE id=?',(r['id'],))
            else:
                self.conn.execute('UPDATE positions SET pos_hash=?,canonical_fen=? WHERE id=?',(nh,can,r['id']))
        self.conn.commit()

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params); self.conn.commit(); return cur
    def many(self, sql, seq):
        cur = self.conn.executemany(sql, seq); self.conn.commit(); return cur
    def query(self, sql, params=()): return list(self.conn.execute(sql, params))
    def one(self, sql, params=()): return self.conn.execute(sql, params).fetchone()

    def stats(self):
        tables = ['games','positions','transitions','episodes','concepts','concept_versions','skills','research_sessions','teacher_lessons','web_sources','discoveries','conflicts','engine_cache','brain_journal']
        out = {t: self.one(f"SELECT COUNT(*) n FROM {t}")['n'] for t in tables}
        out['db_mb'] = round(self.path.stat().st_size/1024/1024, 2) if self.path.exists() else 0
        return out

    @staticmethod
    def pack_moves(moves: list[str]) -> bytes: return zlib.compress(' '.join(moves).encode('utf-8'), 9)
    @staticmethod
    def unpack_moves(blob: bytes) -> list[str]: return zlib.decompress(blob).decode('utf-8').split()

    def register_source(self, kind, name, uri='', fingerprint='', trust=.5, license='', notes=''):
        now=time.time()
        if fingerprint:
            row=self.one('SELECT id FROM sources WHERE fingerprint=?',(fingerprint,))
            if row:return row['id']
        cur=self.execute('''INSERT INTO sources(kind,name,uri,fingerprint,trust,license,notes,added_at)
            VALUES(?,?,?,?,?,?,?,?)''',(kind,name,uri,fingerprint or None,trust,license,notes,now))
        return cur.lastrowid

    def add_game(self, headers: dict, moves: list[str], source='', source_id=None) -> int | None:
        canonical = json.dumps(headers, sort_keys=True, ensure_ascii=False)+'|'+ ' '.join(moves)
        ph = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        try:
            cur = self.conn.execute('''INSERT INTO games(pgn_hash,white,black,white_elo,black_elo,result,date,event,source,source_id,time_control,eco,opening,start_fen,moves_z,ply_count,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                ph, headers.get('White',''), headers.get('Black',''), _int(headers.get('WhiteElo')),
                _int(headers.get('BlackElo')), headers.get('Result','*'), headers.get('Date',''), headers.get('Event',''),
                source,source_id,headers.get('TimeControl',''),headers.get('ECO',''),headers.get('Opening',''),headers.get('FEN','') if headers.get('SetUp')=='1' else '',self.pack_moves(moves), len(moves), time.time()))
            self.conn.commit(); return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

    def upsert_position(self, *, pos_hash, fen, structure_sig, material_sig, features, result, elo, novelty, memory_score, memory_level=0, canonical_fen=None):
        now=time.time(); canonical_fen=canonical_fen or ' '.join(fen.split()[:4]); row=self.one('SELECT * FROM positions WHERE pos_hash=?',(pos_hash,))
```
