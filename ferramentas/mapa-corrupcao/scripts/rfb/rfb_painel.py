# Monta dados/receita.json (painel) a partir de rfb_full.json, envolvidos.json e do cache de contratos do PNCP
import json, collections, unicodedata, re
R='/home/claude/rfb/'; P='/home/claude/p2/'
F=json.load(open(R+'rfb_full.json')); A=json.load(open(R+'envolvidos.json'))
try: CA=json.load(open(R+'pncp_cache.json'))
except Exception: CA={}
s=open(P+'index.html',encoding='utf-8').read(); i=s.index('const DATA = ')+13; D,_=json.JSONDecoder().raw_decode(s[i:])
def nrm(t):
    t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
MP={}
for m in [x['mun'] for x in D['R']]+[n[11] for n in D['NEWS']]+[x['mun'] for x in D['PAR']]+[x.get('mun') for x in D['TCE']['itens']]:
    if m: MP[nrm(m)]=m
ESF={'M':'Municipal','E':'Estadual'}
K=[]
import re as _re
PUB=_re.compile(r'Empresa P[uú]blica|Economia Mista|An[oô]nima Aberta|Autarquia|Funda[cç][aã]o P[uú]blica|[OÓ]rg[aã]o P[uú]blico|Cons[oó]rcio P[uú]blico|Poder Executivo|Poder Legislativo|Munic[ií]pio|Estado ou do Distrito',_re.I)
def forte(p):
    x=F['P'].get(p)
    return bool(x) and (x[2]=='cnpj' or (x[2]=='mun' and not x[3]))
excl=collections.Counter()
for b,v in list(A.items()):
    nj=F['C'][b][7] if b in F['C'] else ''
    if PUB.search(nj or ''): excl['natureza pública ou S.A. aberta']+=1; continue
    ps=[p for p in v['pids'] if forte(p)]
    if not ps: excl['só correspondência fraca pelo nome']+=1; continue
    v=dict(v,pids=ps)
    G={}
    for c in v['cnpjs']:
        for x in CA.get(c) or []:
            if x['e'] not in ESF or x.get('c'): continue
            mun=MP.get(nrm(x['m']),(x['m'] or '').title()); esf=ESF[x['e']]
            if esf=='Estadual': mun='Governo do Estado de SP'
            k=(x['o'] or '',mun,esf); g=G.setdefault(k,{'n':0,'v':0.0,'d':[],'l':'','obj':''})
            g['n']+=1; g['v']+=float(x['v'] or 0); g['d'].append(x['d'])
            if x['d']>=max(g['d']): g['l']=x['l']; g['obj']=x['obj']
    for (o,m,e),g in G.items():
        ds=sorted(d for d in g['d'] if d)
        f=lambda d: d[8:10]+'/'+d[5:7]+'/'+d[:4] if d else ''
        K.append([b,v['pids'],o,m,e,g['n'],round(g['v'],2),f(ds[0]) if ds else '',f(ds[-1]) if ds else '',g['l'],g['obj'][:200]])
usados=set(v[0] for v in F['V'])|set(v[1][1:] for v in F['V'] if v[1][0]=='c')|set(k[0] for k in K)
C={b:x[:10]+[x[10]] for b,x in F['C'].items() if b in usados}
V=F['V']
n=dict(emp=len(C),pes=len(F['P']),v1=sum(1 for v in V if v[4]==1),v2=sum(1 for v in V if v[4]==2),ac=sum(1 for x in F['P'].values() if x[4]=='semente'),
       risco_emp=len(set(k[0] for k in K)),risco_ctr=sum(k[5] for k in K),consultados=len(CA),excluidas=dict(excl))
# compactação: textos repetidos viram índices (o painel expande ao carregar)
TB={'q':[],'cn':[],'nj':[],'o':[]}; IX={k:{} for k in TB}
def ix(t,v):
    if v not in IX[t]: IX[t][v]=len(TB[t]); TB[t].append(v)
    return IX[t][v]
C={b:[x[0],x[1] if x[1]!=x[0] else '',x[2],x[3],x[4],x[5],ix('cn',x[6]),ix('nj',x[7]),x[8],x[9],[ix('o',o) for o in x[10]]] for b,x in C.items()}
V=[[v[0],v[1],ix('q',v[2]),v[3],v[4],v[5]] for v in V]
Pc={p:[x[0],[ix('o',o) for o in x[1]],x[2],1 if x[3] else 0,x[4],x[5]] for p,x in F['P'].items()}
out=dict(ref=F['ref'],n=n,TB=TB,C=C,P=Pc,V=V,K=K)
json.dump(out,open(P+'dados/receita.json','w'),ensure_ascii=False,separators=(',',':'))
print(n, round(len(json.dumps(out,ensure_ascii=False,separators=(',',':')))/1e6,2),'MB')
