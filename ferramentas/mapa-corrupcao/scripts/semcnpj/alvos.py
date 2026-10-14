# nomes de empresas citadas no painel sem CNPJ conhecido
import json,re,unicodedata
s=open('/home/claude/p2/index.html',encoding='utf-8').read(); i=s.index('const DATA = ')+13; D,_=json.JSONDecoder().raw_decode(s[i:])
def nrm(t): t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
SUF=re.compile(r'\b(LTDA|S A|SA|EIRELI|ME|EPP|S S|SS|CIA|COMPANHIA)\b')
def key(t): return ' '.join(SUF.sub(' ',nrm(re.sub(r'\(.*?\)',' ',t))).split())
conhec=set()
E=json.load(open('/home/claude/p2/dados/entidades.json'))['L']
for x in E:
    if x[0]=='e' and re.sub(r'\D','',str(x[3] or '')): 
        for n in [x[1]]+(x[2] or []): conhec.add(key(n))
A={}
for r in D['R']:
    for pt in str(r.get('empresa') or '').split(';'):
        k=key(pt)
        if len(k.split())>=2 and k not in conhec: A.setdefault(k,{'nome':re.sub(r'\(.*?\)','',pt).strip(' .'),'mun':set(),'ids':set()}); A[k]['mun'].add(r['mun']); A[k]['ids'].add(r['id'])
for e in D.get('ENT',[]):
    if not re.sub(r'\D','',str(e.get('cnpj') or '')):
        k=key(e['ent'])
        if len(k.split())>=2 and k not in conhec: A.setdefault(k,{'nome':re.sub(r'\(.*?\)','',e['ent']).strip(),'mun':set(),'ids':set()}); A[k]['mun'].add(e.get('mun') or '')
out={k:{'nome':v['nome'],'mun':sorted(m for m in v['mun'] if m),'ids':sorted(v['ids'])} for k,v in A.items()}
json.dump(out,open('/home/claude/rfb/semcnpj/alvos.json','w'),ensure_ascii=False,indent=0)
print(len(out)); print(list(out.items())[:15])
