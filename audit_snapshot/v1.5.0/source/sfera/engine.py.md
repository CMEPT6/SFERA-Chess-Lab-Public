# Canonical source fragment

Original file: `sfera/engine.py`
Lines: 1-180
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import subprocess, threading, queue, time, re, os, json, hashlib, heapq, math
from dataclasses import dataclass, asdict
from pathlib import Path
from .chesslite import Board
from .identity import canonical_fen_core, position_hash128

@dataclass
class EngineLine:
    rank:int; depth:int; score_cp:int|None; mate:int|None; pv:list[str]; wdl:list[int]|tuple[int,int,int]|None=None

class UCIEngine:
    """Generic UCI bridge. Works with Stockfish, LCZero and other UCI engines."""
    def __init__(self,path,threads=2,hash_mb=256,options=None,db=None):
        self.path=str(path);self.threads=threads;self.hash_mb=hash_mb;self.options=options or {};self.db=db
        self.p=None;self.q=queue.Queue();self.name=Path(self.path).stem;self.id_name='';self.id_author='';self.fingerprint=self._fingerprint()

    def _fingerprint(self):
        p=Path(self.path)
        try:
            h=hashlib.sha256();
            with open(p,'rb') as f:
                for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
            return h.hexdigest()[:24]
        except Exception:return hashlib.sha256(self.path.encode()).hexdigest()[:24]

    def start(self):
        if self.p:return
        self.p=subprocess.Popen([self.path],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,encoding='utf-8',errors='replace')
        threading.Thread(target=self._reader,daemon=True).start();self._send('uci')
        end=time.time()+12
        while time.time()<end:
            try:l=self.q.get(timeout=.1)
            except queue.Empty:continue
            if l.startswith('id name '):self.id_name=l[8:].strip();self.name=self.id_name
            elif l.startswith('id author '):self.id_author=l[10:].strip()
            elif 'uciok' in l:break
        else:raise TimeoutError('uciok')
        base={'Threads':self.threads,'Hash':self.hash_mb};base.update(self.options)
        for k,v in base.items():self._send(f'setoption name {k} value {v}')
        self._send('setoption name UCI_ShowWDL value true')
        self._send('isready');self._wait('readyok',12)

    def _reader(self):
        for line in self.p.stdout:self.q.put(line.strip())
    def _send(self,s):self.p.stdin.write(s+'\n');self.p.stdin.flush()
    def _wait(self,token,timeout):
        end=time.time()+timeout
        while time.time()<end:
            try:l=self.q.get(timeout=.1)
            except queue.Empty:continue
            if token in l:return l
        raise TimeoutError(token)

    def _cache_key(self,fen,depth,multipv):
        raw=f'{self.fingerprint}|{canonical_fen_core(fen)}|d={depth}|mpv={multipv}'
        return hashlib.blake2b(raw.encode(),digest_size=16).hexdigest()

    def analyze(self,fen,depth=16,multipv=3,timeout=90,use_cache=True):
        key=self._cache_key(fen,depth,multipv)
        if use_cache and self.db:
            row=self.db.one('SELECT * FROM engine_cache WHERE cache_key=?',(key,))
            if row:
                self.db.execute('UPDATE engine_cache SET hit_count=hit_count+1,last_used=? WHERE cache_key=?',(time.time(),key))
                data=json.loads(row['result_json']);return [EngineLine(**x) for x in data]
        self.start();self._send(f'setoption name MultiPV value {multipv}');self._send(f'position fen {fen}');self._send(f'go depth {depth}')
        end=time.time()+timeout;latest={}
        while time.time()<end:
            try:l=self.q.get(timeout=.1)
            except queue.Empty:continue
            if l.startswith('info ') and ' pv ' in l:
                d=_grab(l,r'\bdepth (\d+)');mpv=_grab(l,r'\bmultipv (\d+)') or 1;cp=_grab(l,r'\bscore cp (-?\d+)');mate=_grab(l,r'\bscore mate (-?\d+)')
                mw=re.search(r'\bwdl (\d+) (\d+) (\d+)',l);wdl=[int(mw.group(1)),int(mw.group(2)),int(mw.group(3))] if mw else None
                pv=l.split(' pv ',1)[1].split();latest[int(mpv)]=EngineLine(int(mpv),int(d or 0),cp,mate,pv,wdl)
            elif l.startswith('bestmove'):break
        result=[latest[k] for k in sorted(latest)]
        if self.db and result:
            now=time.time();self.db.execute('''INSERT OR REPLACE INTO engine_cache(cache_key,engine_fingerprint,engine_name,canonical_fen,depth,multipv,result_json,created_at,last_used,hit_count)
              VALUES(?,?,?,?,?,?,?,?,?,COALESCE((SELECT hit_count FROM engine_cache WHERE cache_key=?),0))''',(key,self.fingerprint,self.name,canonical_fen_core(fen),depth,multipv,json.dumps([asdict(x) for x in result],separators=(',',':')),now,now,key))
        return result

    def raw_command(self,command,quiet_window=.25,timeout=5):
        self.start();self._send(command);out=[];end=time.time()+timeout;last=time.time()
        while time.time()<end:
            try:l=self.q.get(timeout=.1);out.append(l);last=time.time()
            except queue.Empty:
                if out and time.time()-last>=quiet_window:break
        return '\n'.join(out)

    def eval_trace(self,fen):
        self.start();self._send(f'position fen {fen}');return self.raw_command('eval',timeout=4)

    def close(self):
        if self.p:
            try:self._send('quit');self.p.wait(timeout=2)
            except Exception:self.p.kill()
            self.p=None


def _grab(s,pat):
    m=re.search(pat,s);return int(m.group(1)) if m else None


def _wdl_probs(wdl):
    if not wdl:return None
    vals=[max(0.0,float(x)) for x in wdl];tot=sum(vals)
    return [x/tot for x in vals] if tot else None

def _entropy_norm(wdl):
    p=_wdl_probs(wdl)
    if not p:return .5
    h=-sum(x*math.log2(x) for x in p if x>0)
    return h/math.log2(3)

def _js_wdl(a,b):
    p=_wdl_probs(a);q=_wdl_probs(b)
    if not p or not q:return None
    eps=1e-12;m=[(x+y)/2 for x,y in zip(p,q)]
    def kl(x,y):return sum(v*math.log2(max(v,eps)/max(w,eps)) for v,w in zip(x,y) if v>0)
    return .5*kl(p,m)+.5*kl(q,m)

class AdaptiveResearchTree:
    """IDeA-inspired best-first research tree.

    It does not expand every branch equally. Priority rises with novelty,
    close candidate plateaus, engine disagreement and shallow depth.
    """
    def __init__(self,db,engine:UCIEngine,secondary_engine:UCIEngine|None=None):
        self.db=db;self.engine=engine;self.secondary=secondary_engine

    def build(self,fen,title='Adaptive Research',tree_plies=4,branch=4,depth=14,max_nodes=300,progress=None):
        engines=self.engine.name+((' + '+self.secondary.name) if self.secondary else '')
        sid=self.db.execute('INSERT INTO research_sessions(title,root_fen,engine,strategy,created_at) VALUES(?,?,?,?,?)',(title,fen,engines,'best-first',time.time())).lastrowid
        ph=position_hash128(fen)
        root=self.db.execute('''INSERT INTO research_nodes(session_id,parent_id,ply,fen,pos_hash,move_uci,depth,branch_rank,pv,priority)
          VALUES(?,?,?,?,?,?,?,?,?,?)''',(sid,None,0,fen,ph,None,depth,0,'',1.0)).lastrowid
        pq=[(-1.0,root,fen,0)];total=0
        while pq and total<max_nodes:
            negprio,parent,cf,ply=heapq.heappop(pq)
            if ply>=tree_plies:continue
            lines=self.engine.analyze(cf,depth=depth,multipv=branch)
            other=self.secondary.analyze(cf,depth=max(8,depth-2),multipv=branch) if self.secondary else []
            disagreement=self._disagreement(lines,other)
            cps=[x.score_cp for x in lines if x.score_cp is not None]
            plateau=1.0
            if len(cps)>=2:plateau=max(0,min(1,1-abs(cps[0]-cps[1])/150))
            uncertainty=_entropy_norm(lines[0].wdl) if lines else .5
            for ln in lines:
                if total>=max_nodes or not ln.pv:break
                move=ln.pv[0];b=Board(cf)
                try:b.push_uci(move)
                except Exception:continue
                nf=b.fen();nph=position_hash128(nf);known=self.db.one('SELECT novelty,seen_count FROM positions WHERE pos_hash=?',(nph,))
                novelty=float(known['novelty']) if known else 1.0
                priority=.26*novelty+.20*plateau+.22*disagreement+.16*uncertainty+.10/(1+ply)+.06*(1/max(1,ln.rank))
                cp=ln.score_cp if ln.score_cp is not None else (100000 if (ln.mate or 0)>0 else -100000)
                nid=self.db.execute('''INSERT INTO research_nodes(session_id,parent_id,ply,fen,pos_hash,move_uci,eval_cp,mate,depth,branch_rank,pv,priority,novelty,disagreement)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sid,parent,ply+1,nf,nph,move,cp,ln.mate,ln.depth,ln.rank,' '.join(ln.pv),priority,novelty,disagreement)).lastrowid
                heapq.heappush(pq,(-priority,nid,nf,ply+1));total+=1
                if progress:progress(total)
        return sid,total

    @staticmethod
    def _disagreement(a,b):
        if not a or not b:return 0.0
        am=a[0].pv[0] if a[0].pv else '';bm=b[0].pv[0] if b[0].pv else ''
        move_dis=1.0 if am and bm and am!=bm else 0.0
        js=_js_wdl(a[0].wdl,b[0].wdl)
        if js is not None:
            return min(1,.55*move_dis+.45*min(1,js))
        if a[0].score_cp is None or b[0].score_cp is None:return move_dis
        eval_dis=min(1,abs(a[0].score_cp-b[0].score_cp)/200)
        return .6*move_dis+.4*eval_dis

ResearchTree=AdaptiveResearchTree
```
