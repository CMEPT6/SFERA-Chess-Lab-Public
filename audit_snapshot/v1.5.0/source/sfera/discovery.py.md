# Canonical source fragment

Original file: `sfera/discovery.py`
Lines: 1-107
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import json, math, time, statistics
from .chesslite import Board, pv_to_fan
from .identity import position_hash128

class DiscoveryEngine:
    """Finds candidate knowledge in both static structures and state transitions."""
    def __init__(self,db):self.db=db

    def mine(self,min_occurrences=20,limit=100):
        out=[]
        out.extend(self._mine_structures(min_occurrences,limit))
        out.extend(self._mine_transitions(max(5,min_occurrences//2),limit))
        out.sort(key=lambda x:x['score'],reverse=True)
        return out[:limit]

    def _mine_structures(self,min_occurrences,limit):
        rows=self.db.query('''SELECT structure_sig,SUM(seen_count) occ,SUM(white_wins) ww,SUM(draws) dd,SUM(black_wins) bw,
          AVG(avg_elo) elo,AVG(memory_score) mem,COUNT(*) unique_positions
          FROM positions GROUP BY structure_sig HAVING occ>=? ORDER BY occ DESC LIMIT ?''',(min_occurrences,limit*30))
        out=[]
        for r in rows:
            occ=r['occ'] or 1;decisive=(r['ww']+r['bw'])/occ;imbalance=abs(r['ww']-r['bw'])/occ
            rarity=1/math.log2(max(2,occ));quality=min(1,(r['elo'] or 0)/2600)
            score=min(1,.30*imbalance+.18*decisive+.18*quality+.18*(r['mem'] or 0)+.16*rarity)
            if score<.24:continue
            title=f"Structure {r['structure_sig']}"
            statement=f"Candidate static pattern from {occ} observations / {r['unique_positions']} unique states; W/D/B={r['ww']}/{r['dd']}/{r['bw']}; avg Elo={r['elo'] or 0:.0f}. Requires causal/engine verification."
            payload=dict(r);self._save('structure:'+r['structure_sig'],'structure',title,statement,score,occ,payload);out.append({'title':title,'score':score,'statement':statement})
        return out

    def _mine_transitions(self,min_occurrences,limit):
        rows=self.db.query('''SELECT t.id,t.move_uci,t.move_san,t.seen_count,t.white_wins,t.draws,t.black_wins,t.avg_elo,t.surprise,t.memory_score,
          t.avg_engine_delta_cp,t.engine_delta_samples,p.structure_sig,p.features_json,t.feature_delta_json
          FROM transitions t JOIN positions p ON p.id=t.from_position_id
          WHERE t.seen_count>=? ORDER BY t.memory_score DESC,t.seen_count DESC LIMIT ?''',(min_occurrences,limit*40))
        out=[]
        for r in rows:
            engine_signal=min(1,abs(r['avg_engine_delta_cp'] or 0)/200) if r['engine_delta_samples'] else 0
            repetition=min(1,math.log1p(r['seen_count'])/8);score=min(1,.30*(r['surprise'] or 0)+.24*(r['memory_score'] or 0)+.20*engine_signal+.16*repetition+.10*min(1,(r['avg_elo'] or 0)/2600))
            if score<.28:continue
            move=r['move_san'] or r['move_uci'];title=f"Transition {move} in {r['structure_sig'][:10]}"
            d=json.loads(r['feature_delta_json'] or '{}')
            statement=f"Repeated action pattern: {move}, seen {r['seen_count']} times. Feature delta={d}."
            if r['engine_delta_samples']:statement+=f" Mean engine consequence {r['avg_engine_delta_cp']:+.0f}cp over {r['engine_delta_samples']} samples."
            payload=dict(r);key=f"transition:{r['id']}";self._save(key,'transition',title,statement,score,r['seen_count'],payload);out.append({'title':title,'score':score,'statement':statement})
        return out

    def _save(self,key,kind,title,statement,score,evidence_count,payload):
        self.db.execute('''INSERT INTO discoveries(discovery_key,kind,title,statement,score,evidence_count,status,payload_json,updated_at)
          VALUES(?,?,?,?,?,?,'candidate',?,?) ON CONFLICT(discovery_key) DO UPDATE SET statement=excluded.statement,score=excluded.score,evidence_count=excluded.evidence_count,payload_json=excluded.payload_json,updated_at=excluded.updated_at''',(key,kind,title,statement,score,evidence_count,json.dumps(payload,ensure_ascii=False,default=str),time.time()))

    def promote(self,discovery_id):
        d=self.db.one('SELECT * FROM discoveries WHERE id=?',(discovery_id,))
        if not d:return None
        cid=self.db.upsert_concept('Discovery: '+d['title'],d['statement'],min(.82,.42+.38*d['score']),max(1,d['evidence_count']),tags=['discovery',d['kind']],source='discovery-engine',reason='promoted from hypothesis')
        self.db.execute("UPDATE discoveries SET status='promoted' WHERE id=?",(discovery_id,));return cid

class ScientistCoach:
    def __init__(self,db,engine=None):self.db=db;self.engine=engine
    def report(self,fen,depth=14,multipv=3):
        b=Board(fen);ph=position_hash128(fen);ss=b.structure_signature();exact=self.db.one('SELECT * FROM positions WHERE pos_hash=?',(ph,))
        struct=self.db.one('''SELECT SUM(seen_count) occ,SUM(white_wins) ww,SUM(draws) dd,SUM(black_wins) bw,AVG(avg_elo) elo FROM positions WHERE structure_sig=?''',(ss,))
        lines=['SCIENTIST ↔ COACH REPORT','']
        if self.engine:
            ans=self.engine.analyze(fen,depth=depth,multipv=multipv);lines.append('SCIENTIST / engine:')
            for a in ans:
                ev=f"{a.score_cp/100:+.2f}" if a.score_cp is not None else f"мат {a.mate}"
                lines.append(f"  Кандидат {a.rank}  {ev}")
                lines.append('    '+pv_to_fan(fen,a.pv[:12]).replace('\n','\n    '))
        else:lines.append('SCIENTIST: engine not connected.')
        lines.append('')
        if exact:
            lines.append(f"COACH / exact state: seen {exact['seen_count']}; W/D/B {exact['white_wins']}/{exact['draws']}/{exact['black_wins']}; avg Elo {exact['avg_elo']:.0f}")
            moves=self.db.query('''SELECT move_san,move_uci,seen_count,white_wins,draws,black_wins,avg_engine_delta_cp,engine_delta_samples FROM transitions WHERE from_position_id=? ORDER BY seen_count DESC LIMIT 8''',(exact['id'],))
            if moves:
                lines.append('Human continuations:')
                for m in moves:lines.append(f"  {m['move_san'] or m['move_uci']}: {m['seen_count']}x, W/D/B {m['white_wins']}/{m['draws']}/{m['black_wins']}"+(f", Δengine {m['avg_engine_delta_cp']:+.0f}cp" if m['engine_delta_samples'] else ''))
        else:lines.append('COACH / exact state: not found in Genome.')
        if struct and struct['occ']:lines.append(f"COACH / pawn structure: {struct['occ']} observations; W/D/B {struct['ww']}/{struct['dd']}/{struct['bw']}; avg Elo {struct['elo'] or 0:.0f}")
        lines+=['','Rule: engine evidence estimates objective chess strength; corpus statistics describe human behavior. They are deliberately kept separate.']
        return '\n'.join(lines)

class BehavioralDecoder:
    def __init__(self,engine):self.engine=engine
    def decode(self,fen,depth=14,multipv=5):
        root=self.engine.analyze(fen,depth=depth,multipv=multipv)
        if not root:return 'No engine result'
        vals=[(a.rank,a.score_cp,a.pv) for a in root if a.score_cp is not None]
        lines=['SFERA Engine Behavior Decoder','','Картина кандидатов:']
        for rank,cp,pv in vals:
            badge='⭐' if rank==1 else '△'
            lines.append(f"{badge} Кандидат {rank}   {cp/100:+.2f}")
            lines.append(pv_to_fan(fen,pv[:12]))
            lines.append(f"UCI: {' '.join(pv[:12])}")
            lines.append('')
        if len(vals)>=2:
            gap=vals[0][1]-vals[1][1];lines+= [f"Разрыв между 1-м и 2-м кандидатом: {gap/100:+.2f} пешки."]
            if abs(gap)>=80:lines.append('Сигнал: узкое/форсированное решение — лучший план выражен очень чётко.')
            elif abs(gap)<=15:lines.append('Сигнал: широкое плато — несколько планов почти равны по силе.')
            else:lines.append('Сигнал: есть заметное предпочтение, но альтернативы жизнеспособны.')
        try:
            trace=self.engine.eval_trace(fen)
            if trace and 'unknown command' not in trace.lower():lines+=['','Сырой диагностический вывод движка (опционально):',trace[:5000]]
        except Exception:pass
        lines+=['','Этот блок объясняет наблюдаемое поведение движка и делает вывод более человеческим. Он не утверждает, что копирует скрытые веса нейросети.']
        return '\n'.join(lines)
```
