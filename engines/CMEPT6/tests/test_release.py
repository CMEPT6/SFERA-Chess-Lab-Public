#!/usr/bin/env python3
"""CMEPT6 v1.1: release smoke tests for executable protocol and stop safety.
Usage: python3 tests/test_release.py path/to/cmept6-engine
"""
import pathlib
import re
import subprocess
import sys
import threading
import time

exe = str(pathlib.Path(sys.argv[1]).resolve()) if len(sys.argv)>1 else str(pathlib.Path(__file__).resolve().parents[1]/'build'/'cmept6-engine')

def run_search(initial_commands, go, max_seconds=12, stop_after=None):
    p=subprocess.Popen([exe],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, text=True,bufsize=1)
    timer=threading.Timer(max_seconds,lambda:p.kill() if p.poll() is None else None)
    timer.start()
    try:
        p.stdin.write(initial_commands+'\n'+go+'\n');p.stdin.flush()
        if stop_after is not None:
            time.sleep(stop_after)
            p.stdin.write('stop\n');p.stdin.flush()
        out=[]
        while True:
            line=p.stdout.readline()
            if not line:
                raise RuntimeError(f'Engine closed output without bestmove: {out[-5:]}')
            out.append(line.strip())
            if line.startswith('bestmove '): break
        p.stdin.write('quit\n'); p.stdin.flush();p.wait(timeout=3)
        assert p.returncode==0,p.returncode
        return out
    finally:
        timer.cancel()
        if p.poll() is None: p.kill()

out=run_search('uci\nisready\nposition startpos','go nodes 12000')
assert 'uciok' in out and 'readyok' in out
assert any(x.startswith('bestmove ') for x in out)
assert 'option name Clear Hash type button' in out
print('PASS UCI options, go nodes 12000')

out=run_search('position startpos','go depth 64',stop_after=0.06)
assert re.fullmatch('bestmove ([a-h][1-8]){2}[qrbn]?',out[-1]),out[-1]
print('PASS asynchronous stop')

out=run_search('position startpos','go movetime 60')
assert out[-1].startswith('bestmove ')
print('PASS movetime 60')

out=run_search('position fen 7k/6Q1/5K2/8/8/8/8/8 b - - 100 90','go depth 3')
assert out[-1]=='bestmove 0000',out[-1]
print('PASS checkmate precedes 50-move claim')

out=subprocess.run([exe],input='position startpos\nperft 5\nquit\n',text=True,capture_output=True,timeout=45,check=True).stdout
assert 'perft 5 4865609' in out,out
print('PASS startpos perft depth 5: 4,865,609 nodes')

out=subprocess.run([exe],input='position fen 8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1\nperft 5\nquit\n',text=True,capture_output=True,timeout=45,check=True).stdout
assert 'perft 5 674624' in out,out
print('PASS position 3 perft depth 5: 674,624 nodes')
print('ALL v1.1 RELEASE TESTS PASSED')
