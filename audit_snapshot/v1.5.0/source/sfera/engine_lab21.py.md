# Canonical source fragment

Original file: `sfera/engine_lab21.py`
Lines: 1-210
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations

import json
import math
import os
import queue
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from statistics import pstdev

DEFAULT_ENGINES = [
    ('Reckless', '0.9.0'), ('Stockfish', '19'), ('Lc0', '0.32.1'), ('Torch', 'v4'),
    ('Pawnocchio', '2.0.1'), ('PlentyChess', ''), ('Stormphrax', ''), ('Viridithas', ''),
    ('Hobbes', ''), ('Raphael', ''), ('Berserk', ''), ('Caissa', ''), ('Clover', ''),
    ('Tarnished', ''), ('QuanticaDePhoenix', ''), ('PZChessBot', ''), ('Dragon', '3.3'),
    ('Icarus', ''), ('Renegade', ''), ('Ethereal', ''), ('Horsie', ''),
]

ALIASES = {
    'Lc0': ['lc0', 'leela'], 'Stockfish': ['stockfish'], 'Reckless': ['reckless'],
    'Pawnocchio': ['pawnocchio'], 'PlentyChess': ['plenty'], 'Stormphrax': ['stormphrax'],
    'Viridithas': ['viridithas'], 'Hobbes': ['hobbes'], 'Raphael': ['raphael'],
    'Berserk': ['berserk'], 'Caissa': ['caissa'], 'Clover': ['clover'], 'Tarnished': ['tarnished'],
    'QuanticaDePhoenix': ['quantica', 'phoenix'], 'PZChessBot': ['pzchess', 'pz'],
    'Dragon': ['dragon'], 'Icarus': ['icarus'], 'Renegade': ['renegade'],
    'Ethereal': ['ethereal'], 'Horsie': ['horsie'], 'Torch': ['torch'],
}


def _creationflags():
    return getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0


def _read_until(proc, q, predicates, timeout):
    end = time.time() + timeout; lines = []
    while time.time() < end:
        try: line = q.get(timeout=.1)
        except queue.Empty: continue
        lines.append(line)
        if any(p(line) for p in predicates): return lines
    raise TimeoutError('UCI timeout')


def _uci_session(path: str, fen: str | None = None, movetime_ms: int = 0, depth: int = 0):
    p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding='utf-8', errors='replace', bufsize=1, creationflags=_creationflags())
    q = queue.Queue()
    threading.Thread(target=lambda: [q.put(x.strip()) for x in p.stdout], daemon=True).start()
    def send(s): p.stdin.write(s + '\n'); p.stdin.flush()
    try:
        send('uci'); lines = _read_until(p, q, [lambda x: x == 'uciok'], 8)
        name = Path(path).stem
        for line in lines:
            if line.startswith('id name '): name = line[8:].strip()
        send('setoption name UCI_ShowWDL value true')
        send('isready'); _read_until(p, q, [lambda x: x == 'readyok'], 5)
        if fen: send('position fen ' + fen)
        else: send('position startpos')
        send(f'go movetime {int(movetime_ms)}' if movetime_ms else f'go depth {int(depth or 5)}')
        deadline = max(8, movetime_ms / 1000 + 6)
        out = _read_until(p, q, [lambda x: x.startswith('bestmove')], deadline)
        bestmove=''; score_cp=None; mate=None; pv=[]; d=0; wdl=None
        for line in out:
            if line.startswith('info '):
                md=re.search(r'\bdepth (\d+)', line); mc=re.search(r'\bscore cp (-?\d+)', line); mm=re.search(r'\bscore mate (-?\d+)', line)
                mw=re.search(r'\bwdl (\d+) (\d+) (\d+)', line)
                if md: d=max(d,int(md.group(1)))
                if mc: score_cp=int(mc.group(1))
                if mm: mate=int(mm.group(1))
                if mw: wdl=tuple(int(mw.group(i)) for i in (1,2,3))
                if ' pv ' in line: pv=line.split(' pv ',1)[1].split()
            elif line.startswith('bestmove'):
                parts=line.split(); bestmove=parts[1] if len(parts)>1 else ''
        return {'ok':bool(bestmove),'name':name,'path':path,'bestmove':bestmove,'score_cp':score_cp,'mate':mate,'depth':d,'pv':pv[:16],'wdl':wdl}
    finally:
        try: send('quit'); p.wait(timeout=1)
        except Exception:
            try: p.kill()
            except Exception: pass


def _entropy(probs):
    return -sum(p*math.log2(p) for p in probs if p>0)


def _js_divergence(p, q):
    eps=1e-9; p=[max(eps,x) for x in p];q=[max(eps,x) for x in q]
    sp=sum(p);sq=sum(q);p=[x/sp for x in p];q=[x/sq for x in q];m=[(a+b)/2 for a,b in zip(p,q)]
    def kl(a,b):return sum(x*math.log2(x/y) for x,y in zip(a,b))
    return .5*kl(p,m)+.5*kl(q,m)


class EngineLab21Manager:
    def __init__(self, root: str | Path):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.root / 'engines.json'
        self.registry = self._load()

    def _load(self):
        if self.registry_path.exists():
            try:
                data=json.loads(self.registry_path.read_text(encoding='utf-8'))
                if isinstance(data,list): return data
                if isinstance(data,dict) and isinstance(data.get('engines'),list): return data['engines']
            except Exception: pass
        rows=[]
        for i,(name,version) in enumerate(DEFAULT_ENGINES,1):
            rows.append({'slot':i,'name':name,'requestedVersion':version,'path':'','uciName':'','status':'NOT FOUND','uciVerified':False,'functionalTest':False})
        self._save(rows); return rows

    def _save(self, rows=None):
        if rows is not None:self.registry=rows
        self.registry_path.write_text(json.dumps({'format':'SFERA_ENGINE_LAB_21','version':1,'engines':self.registry},ensure_ascii=False,indent=2),encoding='utf-8')

    def import_external_registry(self, path: str | Path):
        path=Path(path)
        if path.is_dir(): path=path/'engines.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        src=data.get('engines',data) if isinstance(data,dict) else data
        by_name={str(e.get('name','')).lower():e for e in src if isinstance(e,dict)}
        for row in self.registry:
            ext=by_name.get(row['name'].lower())
            if ext:
                exe=ext.get('executable') or ext.get('path') or ''
                if exe:row['path']=exe
                row['status']=ext.get('status',row['status'])
        self._save();return self.registry

    def scan(self, folder: str | Path):
        folder=Path(folder)
        exes=list(folder.rglob('*.exe')) if folder.exists() else []
        for row in self.registry:
            aliases=ALIASES.get(row['name'],[row['name'].lower()]); candidates=[]
            for exe in exes:
                s=exe.stem.lower().replace('-','').replace('_','')
                if any(a.lower().replace('-','').replace('_','') in s for a in aliases):candidates.append(exe)
            if candidates:
                exe=min(candidates,key=lambda p:(len(p.parts),len(p.name)))
                row['path']=str(exe);row['status']='FOUND'
        self._save();return self.registry

    def register(self, slot: int, path: str):
        row=self.registry[slot-1];row['path']=path;row['status']='FOUND';row['uciVerified']=False;row['functionalTest']=False;self._save();return row

    def test_slot(self, slot: int):
        row=self.registry[slot-1]
        path=row.get('path','')
        if not path or not Path(path).exists():
            row.update(status='NOT FOUND',uciVerified=False,functionalTest=False);self._save();return row
        try:
            r=_uci_session(path,depth=5);row['uciName']=r['name'];row['uciVerified']=True;row['functionalTest']=bool(r['bestmove']);row['status']='OK' if r['bestmove'] else 'ERROR';row['lastTest']=time.time()
        except Exception as e:
            row['status']='ERROR';row['uciVerified']=False;row['functionalTest']=False;row['error']=f'{type(e).__name__}: {e}'
        self._save();return row

    def test_all(self, progress=None):
        out=[]
        for i in range(1,len(self.registry)+1):
            out.append(self.test_slot(i))
            if progress:progress(i,len(self.registry),out[-1])
        return out

    def working(self):
        return [r for r in self.registry if r.get('path') and Path(r['path']).exists() and r.get('functionalTest')]

    def jury(self, fen: str, seconds: int = 10, slots: list[int] | None = None, max_workers: int = 4):
        rows=self.working()
        if slots: rows=[r for r in rows if r['slot'] in slots]
        results=[]
        with ThreadPoolExecutor(max_workers=max(1,min(max_workers,len(rows) or 1))) as ex:
            fut={ex.submit(_uci_session,r['path'],fen,int(seconds*1000),0):r for r in rows}
            for f in as_completed(fut):
                row=fut[f]
                try:
                    ans=f.result();ans['slot']=row['slot'];ans['registry_name']=row['name'];results.append(ans)
                except Exception as e:
                    results.append({'slot':row['slot'],'registry_name':row['name'],'path':row['path'],'ok':False,'error':f'{type(e).__name__}: {e}'})
        ok=[r for r in results if r.get('ok')]
        move_counts={}
        for r in ok:move_counts[r['bestmove']]=move_counts.get(r['bestmove'],0)+1
        move_disagreement=0.0
        if ok:
            move_disagreement=1-max(move_counts.values())/len(ok)
        cps=[r['score_cp'] for r in ok if r.get('score_cp') is not None]
        eval_spread=pstdev(cps) if len(cps)>=2 else 0.0
        wdls=[]
        for r in ok:
            if r.get('wdl'): wdls.append(r['wdl'])
        js=0.0
        pairs=0
        for i in range(len(wdls)):
            for j in range(i+1,len(wdls)):
                js+=_js_divergence(wdls[i],wdls[j]);pairs+=1
        if pairs:js/=pairs
        disagreement=min(100.0,65*move_disagreement+25*min(1,eval_spread/200)+10*min(1,js))
        consensus=max(move_counts,key=move_counts.get) if move_counts else ''
        return {
            'engines_total':len(rows),'engines_ok':len(ok),'consensus_move':consensus,
            'move_votes':move_counts,'eval_spread_cp':round(eval_spread,1),'wdl_js_divergence':round(js,4),
            'disagreement_score':round(disagreement,1),'results':sorted(results,key=lambda x:x.get('slot',999))
        }
```
