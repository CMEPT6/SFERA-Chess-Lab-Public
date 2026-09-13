# Canonical source fragment

Original file: `sfera/pgnstream.py`
Lines: 1-60
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
from __future__ import annotations
import re, io, gzip, bz2, lzma, subprocess, shutil
from pathlib import Path

HEADER_RE=re.compile(r'^\[([A-Za-z0-9_]+)\s+"(.*)"\]\s*$')

def clean_movetext(text:str)->list[str]:
    text=re.sub(r';[^\n]*',' ',text)
    text=re.sub(r'\{.*?\}',' ',text,flags=re.S)
    prev=None
    while prev!=text:
        prev=text; text=re.sub(r'\([^()]*\)',' ',text)
    text=re.sub(r'\$\d+',' ',text)
    toks=[]
    for t in text.replace('\n',' ').split():
        t=re.sub(r'^\d+\.(\.\.)?','',t)
        if not t or t in ('1-0','0-1','1/2-1/2','*'): continue
        if re.match(r'^\d+\.+$',t): continue
        toks.append(t)
    return toks

def _open_text(path):
    path=Path(path); low=path.name.lower()
    if low.endswith('.gz'): return gzip.open(path,'rt',encoding='utf-8',errors='replace')
    if low.endswith('.bz2'): return bz2.open(path,'rt',encoding='utf-8',errors='replace')
    if low.endswith('.xz'): return lzma.open(path,'rt',encoding='utf-8',errors='replace')
    if low.endswith('.zst'):
        try:
            from compression import zstd
            return io.TextIOWrapper(zstd.open(path,'rb'),encoding='utf-8',errors='replace')
        except Exception:
            exe=shutil.which('zstd') or shutil.which('zstd.exe')
            if not exe: raise RuntimeError('For .zst install zstd.exe in PATH or use Python with compression.zstd support.')
            proc=subprocess.Popen([exe,'-dc',str(path)],stdout=subprocess.PIPE)
            stream=io.TextIOWrapper(proc.stdout,encoding='utf-8',errors='replace')
            stream._sfera_proc=proc if hasattr(stream,'__dict__') else None
            return stream
    return open(path,'r',encoding='utf-8',errors='replace')

def iter_pgn(path:str|Path):
    headers={}; move_lines=[]
    def emit():
        if headers or move_lines:
            return dict(headers), clean_movetext('\n'.join(move_lines))
    with _open_text(path) as f:
        for line in f:
            s=line.strip()
            m=HEADER_RE.match(s)
            if m:
                if move_lines:
                    item=emit()
                    if item: yield item
                    headers={}; move_lines=[]
                headers[m.group(1)]=m.group(2)
            else:
                if s or move_lines: move_lines.append(line)
        item=emit()
        if item: yield item
```
