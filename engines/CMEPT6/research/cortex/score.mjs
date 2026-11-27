// CMEPT6 CORTEX-001: offline ranking evaluation, no network access.
import { readFileSync } from 'node:fs';
function score(positions, answers) {
  const move = /^[a-h][1-8][a-h][1-8][qrbn]?$/;
  if (!Array.isArray(positions) || !positions.length || !Array.isArray(answers)) throw Error("Expected non-empty positions and answers arrays");
  const ids = new Set(), response = new Map();
  for (const p of positions) {
    if (typeof p.id !== "string" || !p.id || ids.has(p.id) || typeof p.fen !== "string" || !p.fen ||
        !Array.isArray(p.legal) || !p.legal.length || !p.legal.every(m=>typeof m==="string" && move.test(m)) ||
        new Set(p.legal).size !== p.legal.length || !Array.isArray(p.best) || !p.best.length ||
        new Set(p.best).size !== p.best.length || !p.best.every(m=>p.legal.includes(m))) throw Error("Invalid position: "+p.id);
    ids.add(p.id);
  }
  for (const a of answers) {
    if (!ids.has(a.id) || response.has(a.id)) throw Error("Unknown or duplicate answer id: "+a.id);
    response.set(a.id,a.moves);
  }
  let valid=0, missing=0, invalid=0, top1=0, top3=0, rr=0, random1=0, random3=0;
  const rows=[];
  for (const p of positions) {
    const n=p.legal.length, b=p.best.length, k=Math.min(3,n);
    random1+=b/n;
    let miss=1;
    for(let j=0;j<k;j++) miss*=Math.max(0,n-b-j)/(n-j);
    random3+=1-miss;
    let status="valid", rank=0;
    if (!response.has(p.id)) {missing++; status="missing";}
    else {
      const ms=response.get(p.id);
      if (!Array.isArray(ms) || ms.length!==k || new Set(ms).size!==k || !ms.every(m=>p.legal.includes(m))) {invalid++;status="invalid";}
      else {
        valid++;
        rank=ms.findIndex(m=>p.best.includes(m))+1;
        if(rank===1) top1++;
        if(rank>0) {top3++;rr+=1/rank;}
      }
    }
    rows.push({id:p.id,status,rank});
  }
  const count=positions.length;
  return {positions:count,valid,missing,invalid,top1:top1/count,top3:top3/count,mrr:rr/count,random_top1:random1/count,random_top3:random3/count,rows};
}
function selfTest() {
  const p=[{id:"p1",fen:"fixture",legal:["e2e4","d2d4","g1f3","c2c4"],best:["e2e4"]},
  {id:"p2",fen:"fixture",legal:["e7e8q","e7e8r"],best:["e7e8q"]},
  {id:"p3",fen:"fixture",legal:["a1a2"],best:["a1a2"]},
  {id:"p4",fen:"fixture",legal:["a1a2","a1b1","a1b2"],best:["a1a2"]}];
  const a=[{id:"p1",moves:["d2d4","e2e4","g1f3"]},{id:"p2",moves:["e7e8q","e7e8r"]},{id:"p4",moves:["a1a2","a1a2","a1b2"]}];
  const r=score(p,a);
  const check=(x,msg)=>{if(!x)throw Error(msg)};
  check(r.valid===2 && r.missing===1 && r.invalid===1,"status counts");
  check(r.top1===.25 && r.top3===.5 && r.mrr===.375,"ranking metrics");
  check(Math.abs(r.random_top3-.9375)<1e-12,"uniform random baseline");
  for(const bad of [[...a,a[0]],[{id:"unknown",moves:[]}]]){
    let caught=false;try{score(p,bad)}catch{caught=true}check(caught,"reject malformed response ids");
  }
  let caught=false;try{score([{...p[0],best:["h7h8q"]}],[])}catch{caught=true}check(caught,"reject inconsistent reference");
  return "6 assertions passed (synthetic fixtures only)";
}
if (process.argv[2]==='--self-test') console.log(selfTest());
else {
  if (process.argv.length!==4) throw Error('Usage: node score.mjs positions.json answers.json');
  const load=p=>JSON.parse(readFileSync(p,'utf8'));
  console.log(JSON.stringify(score(load(process.argv[2]),load(process.argv[3])),null,2));
}
