# Canonical source fragment

Original file: `sfera/report.py`
Lines: 1-161
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import json, math, time
from collections import Counter
from .identity import position_hash128
from .chesslite import Board, pv_to_fan

PIECE_NAMES={'P':'пешка','N':'конь','B':'слон','R':'ладья','Q':'ферзь','K':'король',
             'p':'пешка','n':'конь','b':'слон','r':'ладья','q':'ферзь','k':'король'}
PIECE_SYMBOLS={'P':'♙','N':'♘','B':'♗','R':'♖','Q':'♕','K':'♔','p':'♟','n':'♞','b':'♝','r':'♜','q':'♛','k':'♚'}
ELO_ORDER=['<1400','1400–1799','1800–2199','2200–2499','2500+','Unknown']
TC_ORDER=['Bullet','Blitz','Rapid','Classical','Classical/Other','Unknown']


def _score_pct(w,d,b,side='w'):
    n=w+d+b
    if not n:return 0.0
    pts=(w+.5*d) if side=='w' else (b+.5*d)
    return 100.0*pts/n

def _wdl_text(w,d,b):
    n=w+d+b
    if not n:return 'нет данных'
    return f'{n} партий · W/D/B {w}/{d}/{b} · белые {_score_pct(w,d,b,"w"):.1f}% · чёрные {_score_pct(w,d,b,"b"):.1f}%'


def _move_family(move_san, move_uci, delta):
    san=move_san or ''
    if san.startswith('O-O'):return 'Рокировка / безопасность короля'
    if 'x' in san:return 'Размен / захват'
    if '=' in san:return 'Превращение пешки'
    if san and san[0] in 'NBRQK':return 'Манёвр фигуры'
    if delta:
        if any('pawn' in str(k).lower() or 'island' in str(k).lower() for k in delta):return 'Пешечная перестройка'
    return 'Пешечный ход / пространство'


def _norm_entropy(counts):
    counts=[c for c in counts if c>0]
    if len(counts)<=1:return 0.0
    total=sum(counts); p=[c/total for c in counts]
    h=-sum(x*math.log2(x) for x in p)
    return h/math.log2(len(counts))


class SferaReportBuilder:
    """Position-centric research report.

    It deliberately separates facts already supported by the local corpus from
    engine-derived estimates. Missing historical segmentation is reported as
    missing, never reconstructed from averages.
    """
    def __init__(self, db, engine=None, secondary=None):
        self.db=db; self.engine=engine; self.secondary=secondary

    def build(self, fen, depth=14, multipv=5, save_snapshot=True):
        board=Board(fen); ph=position_hash128(fen)
        pos=self.db.one('SELECT * FROM positions WHERE pos_hash=?',(ph,))
        pid=pos['id'] if pos else None
        out={
            'meta':{'fen':fen,'pos_hash':ph,'generated_at':time.time(),'in_genome':bool(pos)},
            'overview':self._overview(board,pos),
            'elo':self._elo(pid,board.turn),
            'trends':self._trends(pid,board.turn),
            'plans':self._plans(pid,board),
            'piece_routes':self._routes(pid,board),
            'tactics':self._tactics(pid,board),
            'teaching_games':self._teaching(pid),
            'human_difficulty':self._difficulty(pid,board.turn),
            'concepts':self._concepts(pid,pos),
            'engines':self._engines(fen,depth,multipv),
        }
        if save_snapshot:
            self.db.execute('INSERT INTO report_snapshots(pos_hash,fen,payload_json,created_at) VALUES(?,?,?,?)',
                            (ph,fen,json.dumps(out,ensure_ascii=False,default=str),time.time()))
        return out

    def _overview(self,board,pos):
        if not pos:
            return {'text':'Эта точная позиция ещё не встречалась в Chess Genome. Корпусная статистика отсутствует; движковая часть отчёта всё равно доступна.',
                    'seen':0,'turn':board.turn,'structure':'','material':''}
        text=(f"Позиция встречалась {pos['seen_count']} раз. {_wdl_text(pos['white_wins'],pos['draws'],pos['black_wins'])}. "
              f"Средний Elo: {pos['avg_elo']:.0f}. Novelty: {pos['novelty']:.3f}. MemoryScore: {pos['memory_score']:.3f}.")
        tc=self.db.query('SELECT * FROM position_tc_stats WHERE position_id=?',(pos['id'],))
        return {'text':text,'seen':pos['seen_count'],'turn':board.turn,'structure':pos['structure_sig'] or '',
                'material':pos['material_sig'] or '','time_controls':[dict(x) for x in tc]}

    def _elo(self,pid,turn):
        if not pid:return {'available':False,'note':'Позиции нет в Genome.' ,'rows':[]}
        rows=[dict(r) for r in self.db.query('SELECT * FROM position_elo_stats WHERE position_id=?',(pid,))]
        if not rows:
            return {'available':False,'note':'Старая часть базы была импортирована до Elo-сегментации v1.5. Для честного отчёта нужен повторный импорт/переиндексация исходного PGN. Средний Elo нельзя превращать в фиктивные диапазоны.','rows':[]}
        order={k:i for i,k in enumerate(ELO_ORDER)};rows.sort(key=lambda r:order.get(r['elo_band'],99))
        for r in rows:r['side_score']=round(_score_pct(r['white_wins'],r['draws'],r['black_wins'],turn),1)
        return {'available':True,'note':'Score рассчитан для стороны, которой принадлежит ход в текущей позиции.','rows':rows}

    def _trends(self,pid,turn):
        if not pid:return {'available':False,'note':'Позиции нет в Genome.','rows':[]}
        rows=[dict(r) for r in self.db.query('SELECT * FROM position_year_stats WHERE position_id=? ORDER BY year',(pid,))]
        if not rows:
            return {'available':False,'note':'Историческая разбивка появится после импорта PGN в формате v1.5. Старые агрегаты не содержат год для каждой позиции.','rows':[]}
        for r in rows:r['side_score']=round(_score_pct(r['white_wins'],r['draws'],r['black_wins'],turn),1)
        return {'available':True,'rows':rows}

    def _moves(self,pid,limit=30):
        if not pid:return []
        return self.db.query('''SELECT t.*,p.fen next_fen FROM transitions t JOIN positions p ON p.id=t.to_position_id
          WHERE t.from_position_id=? ORDER BY t.seen_count DESC,t.memory_score DESC LIMIT ?''',(pid,limit))

    def _plans(self,pid,board):
        rows=self._moves(pid,20);out=[]
        for r in rows:
            try:delta=json.loads(r['feature_delta_json'] or '{}')
            except Exception:delta={}
            score=_score_pct(r['white_wins'],r['draws'],r['black_wins'],board.turn)
            out.append({'move':r['move_san'] or r['move_uci'],'uci':r['move_uci'],'family':_move_family(r['move_san'],r['move_uci'],delta),
                        'seen':r['seen_count'],'score':round(score,1),'avg_elo':round(r['avg_elo'] or 0),
                        'surprise':round(r['surprise'] or 0,3),'memory_score':round(r['memory_score'] or 0,3),
                        'engine_delta_cp':r['avg_engine_delta_cp'],'delta':delta})
        return {'rows':out,'note':'Это статистические семейства планов по реальным продолжениям. Они не выдаются за полноценное стратегическое объяснение без Concept/engine validation.'}

    def _routes(self,pid,board):
        rows=self._moves(pid,30);out=[]
        for r in rows:
            u=r['move_uci'] or ''
            if len(u)<4:continue
            try:
                fr='abcdefgh'.index(u[0])+(int(u[1])-1)*8;pc=board.b[fr]
            except Exception:pc=None
            side_score=_score_pct(r['white_wins'],r['draws'],r['black_wins'],board.turn)
            out.append({'piece':PIECE_SYMBOLS.get(pc,'')+' '+PIECE_NAMES.get(pc,'фигура'),'route':u[:2]+' → '+u[2:4],
                        'move':r['move_san'] or u,'seen':r['seen_count'],'score':round(side_score,1)})
        return {'rows':out,'note':'v1.5 показывает надёжные маршруты следующего хода из точной позиции. Многопереходный route-miner остаётся отдельной задачей, чтобы не выдумывать траектории из агрегированных данных.'}

    def _tactics(self,pid,board):
        rows=self._moves(pid,50);cand=[]
        for r in rows:
            ed=abs(r['avg_engine_delta_cp'] or 0) if r['engine_delta_samples'] else 0
            score=.45*(r['surprise'] or 0)+.35*min(1,ed/200)+.20*(r['memory_score'] or 0)
            if score<.18:continue
            reason=[]
            if r['surprise'] and r['surprise']>.45:reason.append('необычный переход')
            if ed>=80:reason.append(f'engine Δ≈{r["avg_engine_delta_cp"]:+.0f}cp')
            if 'x' in (r['move_san'] or ''):reason.append('захват')
            cand.append({'move':r['move_san'] or r['move_uci'],'interest':round(score,3),'seen':r['seen_count'],'reason':', '.join(reason) or 'высокий MemoryScore'})
        cand.sort(key=lambda x:x['interest'],reverse=True)
        return {'rows':cand[:15],'note':'Это кандидаты на тактическое исследование, а не автоматически распознанные мотивы. Настоящий motif label требует engine/Concept verification.'}

    def _teaching(self,pid):
        if not pid:return {'rows':[]}
        rows=self.db.query('''SELECT e.ply,e.move_san,e.quality,g.white,g.black,g.white_elo,g.black_elo,g.result,g.date,g.event,g.source
          FROM exemplars e JOIN games g ON g.id=e.game_id WHERE e.position_id=? ORDER BY e.quality DESC,g.created_at DESC LIMIT 12''',(pid,))
        return {'rows':[dict(r) for r in rows], 'note':'Показываются сохранённые репрезентативные партии/эпизоды; это не случайная выборка всей базы.'}

    def _difficulty(self,pid,turn):
        rows=self._moves(pid,100)
        if not rows:return {'available':False,'score':None,'note':'Недостаточно человеческих продолжений для оценки сложности.'}
        counts=[r['seen_count'] for r in rows];total=sum(counts);top=max(counts)/total if total else 1
        entropy=_norm_entropy(counts);branches=len(rows)
        diff=100*min(1,.68*entropy+.32*(1-top))
```
