# Canonical source fragment

Original file: `sfera/db.py`
Lines: 1-196
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import sqlite3, json, time, zlib, hashlib
from pathlib import Path

SCHEMA = r'''
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA temp_store=MEMORY;

CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS sources(
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, uri TEXT,
 fingerprint TEXT UNIQUE, trust REAL DEFAULT .5, license TEXT DEFAULT '',
 notes TEXT DEFAULT '', added_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sources_kind ON sources(kind);

CREATE TABLE IF NOT EXISTS games(
 id INTEGER PRIMARY KEY, pgn_hash TEXT UNIQUE, white TEXT, black TEXT,
 white_elo INTEGER, black_elo INTEGER, result TEXT, date TEXT, event TEXT,
 source TEXT, source_id INTEGER, time_control TEXT DEFAULT '', eco TEXT DEFAULT '', opening TEXT DEFAULT '', start_fen TEXT DEFAULT '',
 moves_z BLOB NOT NULL, ply_count INTEGER DEFAULT 0, created_at REAL NOT NULL,
 FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS positions(
 id INTEGER PRIMARY KEY, pos_hash TEXT UNIQUE NOT NULL, fen TEXT NOT NULL,
 canonical_fen TEXT, structure_sig TEXT, material_sig TEXT, features_json TEXT,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0,
 black_wins INTEGER DEFAULT 0, avg_elo REAL DEFAULT 0, novelty REAL DEFAULT 1,
 memory_score REAL DEFAULT 0, memory_level INTEGER DEFAULT 0,
 engine_eval_cp INTEGER, first_seen REAL, last_seen REAL
);
CREATE INDEX IF NOT EXISTS idx_positions_structure ON positions(structure_sig);
CREATE INDEX IF NOT EXISTS idx_positions_memory ON positions(memory_score DESC);
CREATE INDEX IF NOT EXISTS idx_positions_seen ON positions(seen_count DESC);

CREATE TABLE IF NOT EXISTS transitions(
 id INTEGER PRIMARY KEY,
 from_position_id INTEGER NOT NULL, to_position_id INTEGER NOT NULL,
 move_uci TEXT NOT NULL, move_san TEXT DEFAULT '',
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0,
 black_wins INTEGER DEFAULT 0, avg_elo REAL DEFAULT 0,
 feature_delta_json TEXT DEFAULT '{}',
 avg_engine_delta_cp REAL, engine_delta_samples INTEGER DEFAULT 0,
 surprise REAL DEFAULT 0, memory_score REAL DEFAULT 0,
 first_seen REAL, last_seen REAL,
 UNIQUE(from_position_id, move_uci, to_position_id),
 FOREIGN KEY(from_position_id) REFERENCES positions(id) ON DELETE CASCADE,
 FOREIGN KEY(to_position_id) REFERENCES positions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_transitions_from ON transitions(from_position_id, seen_count DESC);
CREATE INDEX IF NOT EXISTS idx_transitions_to ON transitions(to_position_id);
CREATE INDEX IF NOT EXISTS idx_transitions_memory ON transitions(memory_score DESC);

CREATE TABLE IF NOT EXISTS exemplars(
 position_id INTEGER, game_id INTEGER, ply INTEGER, move_san TEXT,
 quality REAL DEFAULT 0, source_id INTEGER,
 PRIMARY KEY(position_id, game_id, ply),
 FOREIGN KEY(position_id) REFERENCES positions(id) ON DELETE CASCADE,
 FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE,
 FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS episodes(
 id INTEGER PRIMARY KEY, ts REAL NOT NULL, kind TEXT, task TEXT, observation TEXT,
 action TEXT, outcome TEXT, lesson TEXT, confidence REAL DEFAULT .5,
 value REAL DEFAULT .5, tags_json TEXT DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_episodes_value ON episodes(value DESC);

CREATE TABLE IF NOT EXISTS concepts(
 id INTEGER PRIMARY KEY, title TEXT UNIQUE, statement TEXT NOT NULL,
 confidence REAL DEFAULT .5, evidence_count INTEGER DEFAULT 1,
 contradiction_count INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
 current_version INTEGER DEFAULT 1, tags_json TEXT DEFAULT '[]',
 source TEXT DEFAULT 'sfera', updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_concepts_conf ON concepts(confidence DESC);

CREATE TABLE IF NOT EXISTS concept_versions(
 id INTEGER PRIMARY KEY, concept_id INTEGER NOT NULL, version INTEGER NOT NULL,
 statement TEXT NOT NULL, confidence REAL NOT NULL, evidence_count INTEGER NOT NULL,
 contradiction_count INTEGER NOT NULL, reason TEXT DEFAULT '', source TEXT DEFAULT 'sfera',
 created_at REAL NOT NULL,
 UNIQUE(concept_id, version),
 FOREIGN KEY(concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence(
 id INTEGER PRIMARY KEY, subject_type TEXT NOT NULL, subject_id INTEGER NOT NULL,
 source_id INTEGER, game_id INTEGER, position_id INTEGER,
 engine_fingerprint TEXT, polarity INTEGER DEFAULT 1, weight REAL DEFAULT .5,
 claim TEXT DEFAULT '', payload_json TEXT DEFAULT '{}', created_at REAL NOT NULL,
 FOREIGN KEY(source_id) REFERENCES sources(id),
 FOREIGN KEY(game_id) REFERENCES games(id),
 FOREIGN KEY(position_id) REFERENCES positions(id)
);
CREATE INDEX IF NOT EXISTS idx_evidence_subject ON evidence(subject_type, subject_id);

CREATE TABLE IF NOT EXISTS conflicts(
 id INTEGER PRIMARY KEY, subject_type TEXT NOT NULL, subject_a_id INTEGER NOT NULL,
 subject_b_id INTEGER, description TEXT NOT NULL, score REAL DEFAULT .5,
 status TEXT DEFAULT 'open', payload_json TEXT DEFAULT '{}', created_at REAL NOT NULL,
 resolved_at REAL
);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status, score DESC);

CREATE TABLE IF NOT EXISTS skills(
 id INTEGER PRIMARY KEY, name TEXT UNIQUE, steps_json TEXT NOT NULL,
 success_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0,
 confidence REAL DEFAULT .5, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS curiosity(
 id INTEGER PRIMARY KEY, topic TEXT UNIQUE, score REAL DEFAULT .5,
 reason TEXT, evidence_gap INTEGER DEFAULT 0, contradictions INTEGER DEFAULT 0,
 updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_curiosity_score ON curiosity(score DESC);

CREATE TABLE IF NOT EXISTS research_sessions(
 id INTEGER PRIMARY KEY, title TEXT, root_fen TEXT, engine TEXT,
 strategy TEXT DEFAULT 'adaptive', created_at REAL NOT NULL, notes TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS research_nodes(
 id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, parent_id INTEGER,
 ply INTEGER, fen TEXT NOT NULL, pos_hash TEXT,
 move_uci TEXT, eval_cp INTEGER, mate INTEGER, depth INTEGER,
 branch_rank INTEGER, pv TEXT, priority REAL DEFAULT 0,
 novelty REAL DEFAULT 0, disagreement REAL DEFAULT 0,
 FOREIGN KEY(session_id) REFERENCES research_sessions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_research_session ON research_nodes(session_id, ply);

CREATE TABLE IF NOT EXISTS engine_cache(
 cache_key TEXT PRIMARY KEY, engine_fingerprint TEXT NOT NULL, engine_name TEXT,
 canonical_fen TEXT NOT NULL, depth INTEGER, multipv INTEGER,
 result_json TEXT NOT NULL, created_at REAL NOT NULL, last_used REAL NOT NULL,
 hit_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_engine_cache_fen ON engine_cache(engine_fingerprint, canonical_fen);

CREATE TABLE IF NOT EXISTS engine_opinions(
 id INTEGER PRIMARY KEY, position_id INTEGER NOT NULL, engine_fingerprint TEXT NOT NULL,
 engine_name TEXT, depth INTEGER, rank INTEGER, score_cp INTEGER, mate INTEGER,
 move_uci TEXT, pv TEXT, created_at REAL NOT NULL,
 UNIQUE(position_id, engine_fingerprint, depth, rank),
 FOREIGN KEY(position_id) REFERENCES positions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_engine_opinions_pos ON engine_opinions(position_id);

CREATE TABLE IF NOT EXISTS import_checkpoints(
 source_fingerprint TEXT PRIMARY KEY, source_path TEXT NOT NULL,
 game_index INTEGER DEFAULT 0, imported_games INTEGER DEFAULT 0,
 status TEXT DEFAULT 'running', stats_json TEXT DEFAULT '{}', updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS position_elo_stats(
 position_id INTEGER NOT NULL, elo_band TEXT NOT NULL,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black_wins INTEGER DEFAULT 0,
 PRIMARY KEY(position_id, elo_band),
 FOREIGN KEY(position_id) REFERENCES positions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_position_elo_band ON position_elo_stats(elo_band, seen_count DESC);

CREATE TABLE IF NOT EXISTS transition_elo_stats(
 transition_id INTEGER NOT NULL, elo_band TEXT NOT NULL,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black_wins INTEGER DEFAULT 0,
 PRIMARY KEY(transition_id, elo_band),
 FOREIGN KEY(transition_id) REFERENCES transitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS position_year_stats(
 position_id INTEGER NOT NULL, year INTEGER NOT NULL,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black_wins INTEGER DEFAULT 0,
 PRIMARY KEY(position_id, year),
 FOREIGN KEY(position_id) REFERENCES positions(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_position_year ON position_year_stats(year, seen_count DESC);

CREATE TABLE IF NOT EXISTS transition_year_stats(
 transition_id INTEGER NOT NULL, year INTEGER NOT NULL,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black_wins INTEGER DEFAULT 0,
 PRIMARY KEY(transition_id, year),
 FOREIGN KEY(transition_id) REFERENCES transitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS position_tc_stats(
 position_id INTEGER NOT NULL, tc_class TEXT NOT NULL,
 seen_count INTEGER DEFAULT 0, white_wins INTEGER DEFAULT 0, draws INTEGER DEFAULT 0, black_wins INTEGER DEFAULT 0,
 PRIMARY KEY(position_id, tc_class),
 FOREIGN KEY(position_id) REFERENCES positions(id) ON DELETE CASCADE
);

```
