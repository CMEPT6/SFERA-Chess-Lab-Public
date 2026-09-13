# Canonical source fragment

Original file: `sfera/report.py`
Lines: 162-284
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
        return {'available':True,'score':round(diff,1),'entropy':round(entropy,3),'top_move_share':round(100*top,1),
                'branches':branches,'sample':total,
                'note':'Human Difficulty — поведенческий показатель разброса человеческих решений, не оценка объективной сложности позиции.'}

    def _concepts(self,pid,pos):
        linked=[]
        if pid:
            rows=self.db.query('''SELECT DISTINCT c.* FROM concepts c JOIN evidence e ON e.subject_type='concept' AND e.subject_id=c.id
              WHERE e.position_id=? ORDER BY c.confidence DESC LIMIT 30''',(pid,))
            linked=[dict(r) for r in rows]
        discoveries=[]
        if pos and pos['structure_sig']:
            like='%' + str(pos['structure_sig'])[:12] + '%'
            discoveries=[dict(r) for r in self.db.query('SELECT * FROM discoveries WHERE title LIKE ? OR statement LIKE ? ORDER BY score DESC LIMIT 15',(like,like))]
        return {'linked':linked,'discoveries':discoveries,'note':'Связанные Concept показываются только при наличии provenance/evidence. Похожие discoveries остаются гипотезами до проверки.'}

    def _engines(self,fen,depth,multipv):
        if not self.engine:return {'available':False,'note':'Stockfish не подключён. Корпусная часть отчёта построена без движка.','primary':[],'secondary':[]}
        primary=self.engine.analyze(fen,depth=depth,multipv=multipv)
        secondary=self.secondary.analyze(fen,depth=max(8,depth-2),multipv=multipv) if self.secondary else []
        def pack(lines):
            out=[]
            for x in lines:
                out.append({'rank':x.rank,'depth':x.depth,'score_cp':x.score_cp,'mate':x.mate,'wdl':x.wdl,
                            'move':x.pv[0] if x.pv else '','pv_fan':pv_to_fan(fen,x.pv,max_plies=12),'pv_uci':' '.join(x.pv[:12])})
            return out
        p=pack(primary);s=pack(secondary)
        gap=None
        if len(primary)>=2 and primary[0].score_cp is not None and primary[1].score_cp is not None:
            gap=abs(primary[0].score_cp-primary[1].score_cp)
        return {'available':True,'primary_name':self.engine.name,'secondary_name':self.secondary.name if self.secondary else '',
                'primary':p,'secondary':s,'candidate_gap_cp':gap,
                'note':'Движковая оценка отделена от человеческой статистики. WDL показывается только если его реально отдал UCI-движок.'}

    @staticmethod
    def to_markdown(report):
        m=report['meta'];o=report['overview'];lines=[f"# SFERA REPORT",'',f"FEN: `{m['fen']}`",'', '## Overview',o.get('text','')]
        e=report['elo'];lines+=['','## Elo']
        if e.get('rows'):
            for r in e['rows']:lines.append(f"- {r['elo_band']}: {r['seen_count']} партий, score стороны хода {r['side_score']:.1f}%")
        else:lines.append(e.get('note','Нет данных'))
        lines+=['','## Plans']
        for r in report['plans']['rows'][:12]:lines.append(f"- {r['move']} — {r['family']}; {r['seen']}x; score {r['score']:.1f}%")
        lines+=['','## Human Difficulty',str(report['human_difficulty'])]
        lines+=['','## Engines']
        for r in report['engines'].get('primary',[]):lines.append(f"- #{r['rank']} {r['move']} {r['score_cp']}cp — {r['pv_fan'].replace(chr(10),' / ')}")
        return '\n'.join(lines)


class ReportAnalyticsBackfill:
    """Rebuilds v1.5 report segmentation from games already stored in SFERA.

    It clears only derived report statistics, never games/Genome/memory.
    Old games imported before v1.5 normally have no TimeControl stored, so their
    time-control bucket stays Unknown; Elo/year are rebuilt from preserved game metadata.
    """
    def __init__(self, db): self.db=db

    @staticmethod
    def _band(elo):
        if not elo:return 'Unknown'
        if elo<1400:return '<1400'
        if elo<1800:return '1400–1799'
        if elo<2200:return '1800–2199'
        if elo<2500:return '2200–2499'
        return '2500+'

    @staticmethod
    def _year(date):
        try:
            y=int((date or '')[:4]);return y if 1800<=y<=2200 else 0
        except Exception:return 0

    @staticmethod
    def _tc(tc):
        tc=(tc or '').strip()
        if not tc:return 'Unknown'
        try:
            if '+' in tc:
                a,b=tc.split('+',1);est=float(a)+40*float(b)
            elif '/' in tc:return 'Classical/Other'
            else:est=float(tc)
            if est<=180:return 'Bullet'
            if est<=600:return 'Blitz'
            if est<=1800:return 'Rapid'
            return 'Classical'
        except Exception:return 'Unknown'

    def rebuild(self, progress=None):
        for t in ('position_elo_stats','transition_elo_stats','position_year_stats','transition_year_stats','position_tc_stats','transition_tc_stats'):
            self.db.conn.execute(f'DELETE FROM {t}')
        games=self.db.query('SELECT * FROM games ORDER BY id')
        stats={'games':0,'positions':0,'transitions':0,'errors':0,'total':len(games)}
        for i,g in enumerate(games,1):
            elo_vals=[x for x in (g['white_elo'],g['black_elo']) if x]
            elo=sum(elo_vals)/len(elo_vals) if elo_vals else 0
            band=self._band(elo);year=self._year(g['date']);tc=self._tc(g['time_control'])
            try:moves=self.db.unpack_moves(g['moves_z'])
            except Exception:
                stats['errors']+=1;continue
            board=Board(g['start_fen'] or 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
            root=self.db.one('SELECT id FROM positions WHERE pos_hash=?',(position_hash128(board.fen()),))
            prev_id=root['id'] if root else None
            if prev_id:
                self.db.bump_position_analytics(prev_id,g['result'],band,year,tc);stats['positions']+=1
            for san in moves:
                if prev_id is None:break
                try:mv=board.push_san(san)
                except Exception:
                    stats['errors']+=1;break
                nxt=self.db.one('SELECT id FROM positions WHERE pos_hash=?',(position_hash128(board.fen()),))
                if not nxt:break
                pid=nxt['id'];self.db.bump_position_analytics(pid,g['result'],band,year,tc);stats['positions']+=1
                tr=self.db.one('SELECT id FROM transitions WHERE from_position_id=? AND move_uci=? AND to_position_id=?',(prev_id,mv.uci(),pid))
                if tr:
                    self.db.bump_transition_analytics(tr['id'],g['result'],band,year,tc);stats['transitions']+=1
                prev_id=pid
            stats['games']+=1
            if i%250==0:
                self.db.conn.commit()
                if progress:progress(dict(stats))
        self.db.conn.commit();self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('report_analytics_v15','rebuilt')")
        return stats
```
