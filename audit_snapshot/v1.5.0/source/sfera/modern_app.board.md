# Canonical source fragment

Original file: `sfera/modern_app.py`
Lines: 134-259 (`ChessBoardWidget`)
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
class ChessBoardWidget(QWidget):
    """Interactive analysis board: drag/click moves, legal hints and fixed piece assets."""
    moveMade = Signal(str, str, str)   # new_fen, uci, FAN
    fenChanged = Signal(str)
    THEMES = {
        'Дерево': ('#e6c39a', '#a66f43', '#5a402d'),
        'Lichess Brown': ('#f0d9b5', '#b58863', '#6b4e35'),
        'Chess.com Green': ('#eeeed2', '#769656', '#4f6c39'),
        'Классика': ('#f3f4f6', '#8193a6', '#415264'),
    }
    PIECE_STYLES = ('Классика SVG', 'Cburnett')

    def __init__(self, fen=START_FEN, parent=None):
        super().__init__(parent)
        self.fen=fen; self.board=Board(fen); self.theme='Дерево'; self.piece_style='Cburnett'
        self.flipped=False; self.selected=None; self.dragging=False; self.drag_pos=QPointF(); self.last_move=None; self.history=[]
        self.setMouseTracking(True); self.setMinimumSize(430,430); self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self._png={}; self._svg={}
        png_dir=ROOT/'assets'/'pieces_cburnett'; svg_dir=ROOT/'assets'/'pieces'
        for pc in 'KQRBNPkqrbnp':
            fn=('w' if pc.isupper() else 'b')+pc.upper()
            pp=png_dir/(fn+'.png'); sp=svg_dir/(fn+'.svg')
            if pp.exists(): self._png[pc]=QPixmap(str(pp))
            if sp.exists() and QSvgRenderer is not None:self._svg[pc]=QSvgRenderer(str(sp))

    def set_fen(self,fen,keep_history=False):
        try:
            self.board=Board(fen); self.fen=self.board.fen(); self.selected=None; self.last_move=None
            if not keep_history:self.history=[]
            self.update(); self.fenChanged.emit(self.fen); return True
        except Exception:return False
    def set_theme(self,name):
        if name in self.THEMES:self.theme=name;self.update()
    def set_piece_style(self,name):
        if name in self.PIECE_STYLES:self.piece_style=name;self.update()
    def flip(self):self.flipped=not self.flipped;self.update()
    def undo(self):
        if not self.history:return False
        fen=self.history.pop();self.board=Board(fen);self.fen=self.board.fen();self.selected=None;self.last_move=None;self.update();self.fenChanged.emit(self.fen);return True
    def sizeHint(self):return QSize(560,560)

    def _geom(self):
        side=max(80,min(self.width(),self.height())-44);s=side/8.0;ox=(self.width()-side)/2.0;oy=(self.height()-side)/2.0
        return side,s,ox,oy
    def _display_for_square(self,idx):
        f=idx%8; rank=idx//8
        if self.flipped:return 7-f,rank
        return f,7-rank
    def _square_at(self,pos):
        side,s,ox,oy=self._geom();x=pos.x()-ox;y=pos.y()-oy
        if x<0 or y<0 or x>=side or y>=side:return None
        df=int(x//s);dr=int(y//s)
        if self.flipped:f=7-df;rank=dr
        else:f=df;rank=7-dr
        return rank*8+f
    def _legal_targets(self):
        if self.selected is None:return []
        try:return self.board.legal_moves_from(self.selected)
        except Exception:return []
    def _try_move(self,fr,to):
        candidates=[m for m in self.board.legal_moves_from(fr) if m.to==to]
        if not candidates:return False
        chosen=next((m for m in candidates if (m.promo or '').upper()=='Q'),candidates[0])
        old=self.board.fen();uci=chosen.uci();fan=move_to_fan(self.board,uci,figurine=True)
        self.history.append(old);self.board.push(chosen);self.fen=self.board.fen();self.last_move=(fr,to);self.selected=None;self.dragging=False;self.update()
        self.fenChanged.emit(self.fen);self.moveMade.emit(self.fen,uci,fan);return True

    def mousePressEvent(self,event):
        sq=self._square_at(event.position())
        if sq is None:return
        if self.selected is not None and sq!=self.selected:
            if self._try_move(self.selected,sq):return
        pc=self.board.b[sq]
        if pc and ((pc.isupper() and self.board.turn=='w') or (pc.islower() and self.board.turn=='b')):
            self.selected=sq;self.dragging=True;self.drag_pos=event.position();self.update()
        else:
            self.selected=None;self.dragging=False;self.update()
    def mouseMoveEvent(self,event):
        if self.dragging:self.drag_pos=event.position();self.update()
    def mouseReleaseEvent(self,event):
        if not self.dragging:return
        fr=self.selected;to=self._square_at(event.position());self.dragging=False
        if fr is not None and to is not None and to!=fr and self._try_move(fr,to):return
        self.update()

    def _draw_piece(self,p,pc,rect):
        if self.piece_style=='Классика SVG' and pc in self._svg:
            rr=QRectF(rect);pad=rect.width()*.105;rr.adjust(pad,pad,-pad,-pad);self._svg[pc].render(p,rr);return
        pm=self._png.get(pc)
        if pm and not pm.isNull():
            pad=rect.width()*.13;rr=QRectF(rect);rr.adjust(pad,pad,-pad,-pad)
            scaled=pm.scaled(int(rr.width()),int(rr.height()),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            x=rr.x()+(rr.width()-scaled.width())/2;y=rr.y()+(rr.height()-scaled.height())/2;p.drawPixmap(int(x),int(y),scaled)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing,True);p.setRenderHint(QPainter.SmoothPixmapTransform,True)
        side,s,ox,oy=self._geom();light,dark,border=[QColor(x) for x in self.THEMES[self.theme]]
        p.setPen(QPen(border,1.4));p.setBrush(QColor('#faf7f1'));p.drawRoundedRect(QRectF(ox-6,oy-6,side+12,side+12),6,6)
        for dr in range(8):
            for df in range(8):
                p.fillRect(QRectF(ox+df*s,oy+dr*s,s,s),light if (dr+df)%2==0 else dark)
        for sq in (self.last_move or ()):
            df,dr=self._display_for_square(sq);p.fillRect(QRectF(ox+df*s,oy+dr*s,s,s),QColor(246,210,70,90))
        if self.selected is not None:
            df,dr=self._display_for_square(self.selected);p.fillRect(QRectF(ox+df*s,oy+dr*s,s,s),QColor(45,126,210,80))
            legal=self._legal_targets();targets={m.to for m in legal}
            for to in targets:
                tf,tr=self._display_for_square(to);cx=ox+(tf+.5)*s;cy=oy+(tr+.5)*s
                if self.board.b[to]:p.setPen(QPen(QColor(35,110,185,150),max(2,int(s*.07))));p.setBrush(Qt.NoBrush);p.drawEllipse(QPointF(cx,cy),s*.38,s*.38)
                else:p.setPen(Qt.NoPen);p.setBrush(QColor(35,110,185,130));p.drawEllipse(QPointF(cx,cy),s*.105,s*.105)
        p.setFont(QFont('Segoe UI',max(8,int(s*.13))));p.setPen(border)
        files='hgfedcba' if self.flipped else 'abcdefgh';ranks='12345678' if self.flipped else '87654321'
        for f,ch in enumerate(files):p.drawText(QRectF(ox+f*s,oy+side+4,s,17),Qt.AlignCenter,ch)
        for r,ch in enumerate(ranks):p.drawText(QRectF(ox-22,oy+r*s,18,s),Qt.AlignCenter,ch)
        for idx,pc in enumerate(self.board.b):
            if not pc or (self.dragging and idx==self.selected):continue
            df,dr=self._display_for_square(idx);self._draw_piece(p,pc,QRectF(ox+df*s,oy+dr*s,s,s))
        if self.dragging and self.selected is not None:
            pc=self.board.b[self.selected]
            if pc:self._draw_piece(p,pc,QRectF(self.drag_pos.x()-s/2,self.drag_pos.y()-s/2,s,s))
        p.end()
```

## Immediate canonical observations

This exact baseline has drag/click moves, legal target hints, last-move highlight, flip, FEN loading and undo. It **auto-selects queen on promotion**, has **no redo stack**, and this widget fragment contains **no explicit check/checkmate highlight or PGN move-navigation implementation**. These gaps must not be confused with fixes from a different local branch.
