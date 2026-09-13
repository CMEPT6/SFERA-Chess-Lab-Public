# Canonical source fragment

Original file: `sfera/genome.py`
Lines: 1-148
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import math, json, time
from pathlib import Path
from .db import SferaDB
from .chesslite import Board, START_FEN
from .identity import position_hash128, canonical_fen_core, source_fingerprint
from .pgnstream import iter_pgn
from .memory import MemoryValueEngine


def _int(x):
    try:return int(x)
    except:return 0


def _elo_band(elo):
    try: e=float(elo or 0)
    except Exception: return 'Unknown'
    if e<=0:return 'Unknown'
    if e<1400:return '<1400'
    if e<1800:return '1400–1799'
    if e<2200:return '1800–2199'
    if e<2500:return '2200–2499'
    return '2500+'

def _game_year(headers):
    d=(headers.get('Date') or headers.get('UTCDate') or '').strip()
    try:
        y=int(d[:4]); return y if 1800<=y<=2200 else 0
    except Exception:return 0

def _time_class(headers):
    tc=(headers.get('TimeControl') or '').strip()
    if not tc or tc in ('-','?'):return 'Unknown'
    try:
        if '+' in tc:
            a,b=tc.split('+',1); est=float(a)+40*float(b)
        elif '/' in tc:
            return 'Classical/Other'
        else: est=float(tc)
        if est<=180:return 'Bullet'
        if est<=600:return 'Blitz'
        if est<=1800:return 'Rapid'
        return 'Classical'
    except Exception:return 'Unknown'

def _delta(a:dict,b:dict)->dict:
    keys=sorted(set(a)|set(b)); out={}
    for k in keys:
        av=a.get(k); bv=b.get(k)
        if isinstance(av,(int,float)) and isinstance(bv,(int,float)):
            d=bv-av
            if d:out[k]=d
        elif av!=bv:
            out[k]=[av,bv]
    return out

class GenomeImporter:
    """Streaming corpus ingester.

    Design goals:
    - canonical 128-bit position identity
    - state->action->state transitions, not only snapshots
    - provenance/source registration
    - restart checkpoints at game granularity
    - cheap novelty/value filter before expensive engine work
    """
    def __init__(self,db:SferaDB): self.db=db; self.mve=MemoryValueEngine()

    def _source(self,path):
        p=Path(path); st=p.stat(); sample=b''
        try:
            with open(p,'rb') as f: sample=f.read(65536)
        except Exception: pass
        fp=source_fingerprint(str(p.resolve()),sample,st.st_size,st.st_mtime_ns)
        sid=self.db.register_source('pgn',p.name,str(p.resolve()),fp,trust=.55,notes='Imported chess corpus')
        return fp,sid

    def import_pgn(self,path,max_games=0,min_elo=0,progress=None,resume=True,checkpoint_every=500):
        stats={'games':0,'duplicates':0,'positions':0,'new_positions':0,'transitions':0,'new_transitions':0,
               'parse_errors':0,'skipped_low_elo':0,'skipped_variant':0,'resumed_from':0}
        source=str(Path(path).name); fp,sid=self._source(path)
        cp=self.db.one('SELECT * FROM import_checkpoints WHERE source_fingerprint=?',(fp,)) if resume else None
        start_index=int(cp['game_index']) if cp else 0; stats['resumed_from']=start_index
        if cp and cp['status']=='complete' and not max_games:
            return {**stats,'status':'already_complete'}
        imported_since_start=0
        for idx,(h,moves) in enumerate(iter_pgn(path),1):
            if idx<=start_index: continue
            variant=(h.get('Variant') or 'Standard').strip().lower()
            if variant not in ('standard','normal','chess'):
                stats['skipped_variant']+=1; self._checkpoint(fp,path,idx,stats,'running'); continue
            we=_int(h.get('WhiteElo')); be=_int(h.get('BlackElo')); elo=(we+be)/2 if we and be else max(we,be,0)
            if min_elo and elo<min_elo:
                stats['skipped_low_elo']+=1; self._checkpoint(fp,path,idx,stats,'running'); continue
            gid=self.db.add_game(h,moves,source,sid)
            if gid is None:
                stats['duplicates']+=1; self._checkpoint(fp,path,idx,stats,'running'); continue
            stats['games']+=1; imported_since_start+=1
            board=Board(h.get('FEN',START_FEN) if h.get('SetUp')=='1' else START_FEN)
            result=h.get('Result','*'); elo_band=_elo_band(elo); game_year=_game_year(h); tc_class=_time_class(h)
            root_fen=board.fen(); root_feat=board.features(); root_can=canonical_fen_core(root_fen); root_hash=position_hash128(root_fen)
            root_ss=board.structure_signature(); root_ms=board.material_signature(); root_rep=self._structure_reps(root_ss)
            root_nv=1/math.sqrt(1+root_rep); q=min(1,elo/2800) if elo else .35
            root_val=self.mve.score(novelty=root_nv,quality=q,repetition=root_rep)
            prev_id,_=self.db.upsert_position(pos_hash=root_hash,fen=root_fen,canonical_fen=root_can,structure_sig=root_ss,material_sig=root_ms,features=root_feat,result=result,elo=elo,novelty=root_nv,memory_score=root_val,memory_level=self.mve.level(root_val))
            self.db.bump_position_analytics(prev_id,result,elo_band,game_year,tc_class)
            prev_feat=root_feat
            for ply,san in enumerate(moves,1):
                try:
                    mv=board.push_san(san)
                except Exception:
                    stats['parse_errors']+=1; break
                fen=board.fen(); can=canonical_fen_core(fen); ph=position_hash128(fen); ss=board.structure_signature(); ms=board.material_signature(); feat=board.features()
                reps=self._structure_reps(ss); novelty=1/math.sqrt(1+reps); quality=q
                val=self.mve.score(novelty=novelty,quality=quality,repetition=reps)
                level=self.mve.level(val)
                pid,isnew=self.db.upsert_position(pos_hash=ph,fen=fen,canonical_fen=can,structure_sig=ss,material_sig=ms,features=feat,result=result,elo=elo,novelty=novelty,memory_score=val,memory_level=level)
                stats['positions']+=1; stats['new_positions']+=int(isnew)
                self.db.bump_position_analytics(pid,result,elo_band,game_year,tc_class)
                d=_delta(prev_feat,feat); change_mass=sum(abs(v) if isinstance(v,(int,float)) else .25 for v in d.values())
                surprise=min(1,.55*novelty+.08*change_mass)
                tval=self.mve.score(novelty=novelty,quality=quality,surprise=surprise,repetition=reps)
                tid,tnew=self.db.upsert_transition(from_id=prev_id,to_id=pid,move_uci=mv.uci(),move_san=san,result=result,elo=elo,feature_delta=d,memory_score=tval,surprise=surprise)
                stats['transitions']+=1; stats['new_transitions']+=int(tnew)
                self.db.bump_transition_analytics(tid,result,elo_band,game_year,tc_class)
                if level>=2:
                    self.db.add_exemplar(pid,gid,ply,san,quality,source_id=sid)
                prev_id,prev_feat=pid,feat
            if idx%100==0:self.db.conn.commit()
            if progress and idx%50==0:progress(dict(stats))
            if idx%checkpoint_every==0:self._checkpoint(fp,path,idx,stats,'running')
            if max_games and imported_since_start>=max_games:
                self._checkpoint(fp,path,idx,stats,'paused'); self.db.conn.commit(); return stats
        self._checkpoint(fp,path,idx if 'idx' in locals() else start_index,stats,'complete')
        self.db.conn.commit(); return stats

    def _structure_reps(self,ss):
        r=self.db.one('SELECT COALESCE(SUM(seen_count),0) n FROM positions WHERE structure_sig=?',(ss,)); return int(r['n']) if r else 0

    def _checkpoint(self,fp,path,idx,stats,status):
        self.db.conn.execute('''INSERT INTO import_checkpoints(source_fingerprint,source_path,game_index,imported_games,status,stats_json,updated_at)
          VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_fingerprint) DO UPDATE SET game_index=excluded.game_index,imported_games=excluded.imported_games,status=excluded.status,stats_json=excluded.stats_json,updated_at=excluded.updated_at''',
          (fp,str(path),idx,stats.get('games',0),status,json.dumps(stats,ensure_ascii=False),time.time()))
        self.db.conn.commit()
```
