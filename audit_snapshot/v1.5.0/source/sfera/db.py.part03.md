# Canonical source fragment

Original file: `sfera/db.py`
Lines: 354-442
Archive SHA-256: `b354d664e739928369b89ff334dce87a0b2e0c111355477998c2cb0d0f723892`

```python
        w,d,b=(1,0,0) if result=='1-0' else ((0,0,1) if result=='0-1' else ((0,1,0) if result=='1/2-1/2' else (0,0,0)))
        if row:
            n=row['seen_count']+1; avg=((row['avg_elo'] or 0)*row['seen_count']+elo)/max(1,n)
            nv=min(float(row['novelty']),novelty,1/(n**0.5)); ms=max(float(row['memory_score']),memory_score); ml=max(int(row['memory_level'] or 0),memory_level)
            self.conn.execute('''UPDATE positions SET seen_count=?,white_wins=white_wins+?,draws=draws+?,black_wins=black_wins+?,avg_elo=?,novelty=?,memory_score=?,memory_level=?,canonical_fen=COALESCE(canonical_fen,?),last_seen=? WHERE id=?''',(n,w,d,b,avg,nv,ms,ml,canonical_fen,now,row['id']))
            return row['id'], False
        cur=self.conn.execute('''INSERT INTO positions(pos_hash,fen,canonical_fen,structure_sig,material_sig,features_json,seen_count,white_wins,draws,black_wins,avg_elo,novelty,memory_score,memory_level,first_seen,last_seen)
          VALUES(?,?,?,?,?,?,1,?,?,?,?,?,?,?,?,?)''',(pos_hash,fen,canonical_fen,structure_sig,material_sig,json.dumps(features,ensure_ascii=False,separators=(',',':')),w,d,b,elo,novelty,memory_score,memory_level,now,now))
        return cur.lastrowid, True

    def upsert_transition(self, *, from_id, to_id, move_uci, move_san, result, elo, feature_delta, memory_score=0, surprise=0):
        now=time.time(); row=self.one('SELECT * FROM transitions WHERE from_position_id=? AND move_uci=? AND to_position_id=?',(from_id,move_uci,to_id))
        w,d,b=(1,0,0) if result=='1-0' else ((0,0,1) if result=='0-1' else ((0,1,0) if result=='1/2-1/2' else (0,0,0)))
        if row:
            n=row['seen_count']+1; avg=((row['avg_elo'] or 0)*row['seen_count']+elo)/max(1,n)
            self.conn.execute('''UPDATE transitions SET seen_count=?,white_wins=white_wins+?,draws=draws+?,black_wins=black_wins+?,avg_elo=?,surprise=MAX(surprise,?),memory_score=MAX(memory_score,?),last_seen=? WHERE id=?''',(n,w,d,b,avg,surprise,memory_score,now,row['id']))
            return row['id'],False
        cur=self.conn.execute('''INSERT INTO transitions(from_position_id,to_position_id,move_uci,move_san,seen_count,white_wins,draws,black_wins,avg_elo,feature_delta_json,surprise,memory_score,first_seen,last_seen)
            VALUES(?,?,?,?,1,?,?,?,?,?,?,?,?,?)''',(from_id,to_id,move_uci,move_san,w,d,b,elo,json.dumps(feature_delta,ensure_ascii=False,separators=(',',':')),surprise,memory_score,now,now))
        return cur.lastrowid,True

    def add_exemplar(self, position_id, game_id, ply, move_san, quality, max_per_position=5, source_id=None):
        cnt=self.one('SELECT COUNT(*) n FROM exemplars WHERE position_id=?',(position_id,))['n']
        if cnt < max_per_position:
            self.conn.execute('INSERT OR IGNORE INTO exemplars(position_id,game_id,ply,move_san,quality,source_id) VALUES(?,?,?,?,?,?)',(position_id,game_id,ply,move_san,quality,source_id))

    def add_evidence(self, subject_type, subject_id, *, source_id=None, game_id=None, position_id=None, engine_fingerprint='', polarity=1, weight=.5, claim='', payload=None):
        return self.execute('''INSERT INTO evidence(subject_type,subject_id,source_id,game_id,position_id,engine_fingerprint,polarity,weight,claim,payload_json,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(subject_type,subject_id,source_id,game_id,position_id,engine_fingerprint,polarity,weight,claim,json.dumps(payload or {},ensure_ascii=False),time.time())).lastrowid

    def journal(self,event_type,title,before=None,after=None,reason='',evidence=None,confidence_before=None,confidence_after=None):
        return self.execute('''INSERT INTO brain_journal(ts,event_type,title,before_json,after_json,reason,evidence_json,confidence_before,confidence_after)
          VALUES(?,?,?,?,?,?,?,?,?)''',(time.time(),event_type,title,json.dumps(before or {},ensure_ascii=False),json.dumps(after or {},ensure_ascii=False),reason,json.dumps(evidence or [],ensure_ascii=False),confidence_before,confidence_after)).lastrowid

    def add_episode(self, kind, task, observation, action, outcome, lesson, confidence=.5, value=.5, tags=None):
        self.execute('''INSERT INTO episodes(ts,kind,task,observation,action,outcome,lesson,confidence,value,tags_json)
          VALUES(?,?,?,?,?,?,?,?,?,?)''',(time.time(),kind,task,observation,action,outcome,lesson,confidence,value,json.dumps(tags or [],ensure_ascii=False)))

    def upsert_concept(self, title, statement, confidence=.5, evidence=1, contradictions=0, tags=None, source='sfera', reason='update'):
        now=time.time(); row=self.one('SELECT * FROM concepts WHERE title=?',(title,))
        if row:
            ev=row['evidence_count']+evidence; con=row['contradiction_count']+contradictions
            denom=max(1,row['evidence_count']+max(0,evidence))
            conf=max(.01,min(.999,(row['confidence']*row['evidence_count']+confidence*max(0,evidence))/denom - contradictions*.03))
            changed=(statement.strip()!=row['statement'].strip()) or abs(conf-row['confidence'])>.02 or contradictions>0
            version=int(row['current_version'] or 1)+(1 if changed else 0)
            self.execute('UPDATE concepts SET statement=?,confidence=?,evidence_count=?,contradiction_count=?,current_version=?,tags_json=?,source=?,updated_at=? WHERE id=?',(statement,conf,ev,con,version,json.dumps(tags or [],ensure_ascii=False),source,now,row['id']))
            if changed:
                self.execute('''INSERT OR IGNORE INTO concept_versions(concept_id,version,statement,confidence,evidence_count,contradiction_count,reason,source,created_at)
                  VALUES(?,?,?,?,?,?,?,?,?)''',(row['id'],version,statement,conf,ev,con,reason,source,now))
                self.journal('concept_revision',title,{'statement':row['statement'],'confidence':row['confidence']},{'statement':statement,'confidence':conf},reason,confidence_before=row['confidence'],confidence_after=conf)
            return row['id']
        cur=self.execute('''INSERT INTO concepts(title,statement,confidence,evidence_count,contradiction_count,status,current_version,tags_json,source,updated_at)
          VALUES(?,?,?,?,?,'active',1,?,?,?)''',(title,statement,confidence,evidence,contradictions,json.dumps(tags or [],ensure_ascii=False),source,now))
        cid=cur.lastrowid
        self.execute('''INSERT INTO concept_versions(concept_id,version,statement,confidence,evidence_count,contradiction_count,reason,source,created_at)
          VALUES(?,?,?,?,?,?,?,?,?)''',(cid,1,statement,confidence,evidence,contradictions,'created',source,now))
        self.journal('concept_created',title,{}, {'statement':statement,'confidence':confidence},'created',confidence_after=confidence)
        return cid

    @staticmethod
    def _wdl_counts(result):
        return (1,0,0) if result=='1-0' else ((0,0,1) if result=='0-1' else ((0,1,0) if result=='1/2-1/2' else (0,0,0)))

    def bump_position_analytics(self, position_id, result, elo_band='Unknown', year=0, tc_class='Unknown'):
        w,d,b=self._wdl_counts(result)
        self.conn.execute("""INSERT INTO position_elo_stats(position_id,elo_band,seen_count,white_wins,draws,black_wins)
          VALUES(?,?,1,?,?,?) ON CONFLICT(position_id,elo_band) DO UPDATE SET seen_count=seen_count+1,white_wins=white_wins+excluded.white_wins,draws=draws+excluded.draws,black_wins=black_wins+excluded.black_wins""",(position_id,elo_band,w,d,b))
        if year:
            self.conn.execute("""INSERT INTO position_year_stats(position_id,year,seen_count,white_wins,draws,black_wins)
              VALUES(?,?,1,?,?,?) ON CONFLICT(position_id,year) DO UPDATE SET seen_count=seen_count+1,white_wins=white_wins+excluded.white_wins,draws=draws+excluded.draws,black_wins=black_wins+excluded.black_wins""",(position_id,int(year),w,d,b))
        self.conn.execute("""INSERT INTO position_tc_stats(position_id,tc_class,seen_count,white_wins,draws,black_wins)
          VALUES(?,?,1,?,?,?) ON CONFLICT(position_id,tc_class) DO UPDATE SET seen_count=seen_count+1,white_wins=white_wins+excluded.white_wins,draws=draws+excluded.draws,black_wins=black_wins+excluded.black_wins""",(position_id,tc_class or 'Unknown',w,d,b))

    def bump_transition_analytics(self, transition_id, result, elo_band='Unknown', year=0, tc_class='Unknown'):
        w,d,b=self._wdl_counts(result)
        self.conn.execute("""INSERT INTO transition_elo_stats(transition_id,elo_band,seen_count,white_wins,draws,black_wins)
          VALUES(?,?,1,?,?,?) ON CONFLICT(transition_id,elo_band) DO UPDATE SET seen_count=seen_count+1,white_wins=white_wins+excluded.white_wins,draws=draws+excluded.draws,black_wins=black_wins+excluded.black_wins""",(transition_id,elo_band,w,d,b))
        if year:
            self.conn.execute("""INSERT INTO transition_year_stats(transition_id,year,seen_count,white_wins,draws,black_wins)
              VALUES(?,?,1,?,?,?) ON CONFLICT(transition_id,year) DO UPDATE SET seen_count=seen_count+1,white_wins=white_wins+excluded.white_wins,draws=draws+excluded.draws,black_wins=black_wins+excluded.black_wins""",(transition_id,int(year),w,d,b))
        self.conn.execute("""INSERT INTO transition_tc_stats(transition_id,tc_class,seen_count,white_wins,draws,black_wins)
          VALUES(?,?,1,?,?,?) ON CONFLICT(transition_id,tc_class) DO UPDATE SET seen_count=seen_count+1,white_wins=white_wins+excluded.white_wins,draws=draws+excluded.draws,black_wins=black_wins+excluded.black_wins""",(transition_id,tc_class or 'Unknown',w,d,b))

    def close(self): self.conn.commit(); self.conn.close()

def _int(x):
    try:return int(x)
    except:return 0
```
