# Monta dados/estab.json (matriz e filiais por raiz do CNPJ) a partir de estab_raw.json (varre.py).
# Só raízes com 2+ estabelecimentos. Até 60 por raiz: matriz, filiais com contrato no PNCP, filiais em SP, ativas.
# Uso: python3 estab_painel.py <saida.json>
import json, sys, re
R='/home/claude/rfb/'
RAW=json.load(open(R+'estab/estab_raw.json')); F=json.load(open(R+'rfb_full.json'))
CT=set()
try:
    for b, its in json.load(open(R+'pncp_cache_raiz.json')).items():
        for x in its or []: CT.add(str(x.get('ni') or ''))
except Exception: pass
def tit(t):
    t=str(t or '').strip()
    if not t: return ''
    t=' '.join(w.capitalize() for w in t.lower().split())
    return re.sub(r'\s(Da|De|Do|Das|Dos|E|Em)\s', lambda m: m.group(0).lower(), t)
import unicodedata
def nrm(t): t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
H=open('/home/claude/oisp/index.html',encoding='utf-8').read(); gi=H.index('GEO = ')+6; GEO,_=json.JSONDecoder().raw_decode(H[gi:])
MN={nrm(m): tit(m) for m in GEO['municipios']}
di=H.index('const DATA = ')+13; DD,_=json.JSONDecoder().raw_decode(H[di:])
for x in DD['R']:
    if x.get('mun'): MN[nrm(x['mun'])]=x['mun']
def mun(m, uf): return MN.get(nrm(m), tit(m)) if uf=='SP' else tit(m)
L={}; N={}; tot=0
for b, es in RAW.items():
    if len(es) < 2: continue
    N[b]=len(es)
    pr=lambda x: (x[1]!='1', (b+x[0]) not in CT, x[7]!='SP', x[3]!='02', x[0])
    es=sorted(es, key=pr)[:60]
    L[b]=[[x[0], x[1], tit(x[2])[:50], x[3].lstrip('0') or '0', x[7], mun(x[8], x[7])] for x in sorted(es, key=lambda x: x[0])]
    tot+=len(L[b])
out=dict(ref=F.get('ref',''), L=L, N=N)
json.dump(out, open(sys.argv[1],'w'), ensure_ascii=False, separators=(',',':'))
print(len(L),'raízes com filiais;',tot,'estabelecimentos;',round(len(json.dumps(out,ensure_ascii=False,separators=(',',':')))/1e6,2),'MB')
