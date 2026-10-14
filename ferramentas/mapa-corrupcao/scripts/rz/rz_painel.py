# Divide rz_raw.json em dados/rz/NN.json (pelos 2 primeiros dígitos da raiz) e grava dados/rz/mun.json (código Receita -> nome).
# Uso: python3 rz_painel.py <pasta dados/rz>
import json, sys, os, re, zipfile, io, unicodedata
R='/home/claude/rfb/'; OUT=sys.argv[1]; os.makedirs(OUT, exist_ok=True)
D=json.load(open(R+'rz/rz_raw.json'))
def nrm(t): t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
def tit(t):
    t=' '.join(w.capitalize() for w in str(t or '').lower().split()); return re.sub(r'\s(Da|De|Do|Das|Dos|E|Em)\s', lambda m: m.group(0).lower(), t)
H=open('/home/claude/oisp/index.html',encoding='utf-8').read(); gi=H.index('GEO = ')+6; GEO,_=json.JSONDecoder().raw_decode(H[gi:])
MN={nrm(m): tit(m) for m in GEO['municipios']}
di=H.index('const DATA = ')+13; DD,_=json.JSONDecoder().raw_decode(H[di:])
for x in DD['R']:
    if x.get('mun'): MN[nrm(x['mun'])]=x['mun']
usados={x[4] for e in D.values() for x in e[3]}
MU={}
with zipfile.ZipFile(R+'zip/Municipios.zip') as z:
    for n in z.namelist():
        for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
            p=[x.strip('"\n') for x in ln.split('";"')]
            if len(p)>=2 and p[0] in usados: MU[p[0]]=MN.get(nrm(p[1]), tit(p[1]))
json.dump(MU,open(OUT+'/mun.json','w'),ensure_ascii=False,separators=(',',':'))
NM=json.load(open(R+'rz/rz_nomes.json'))
def nome(b):
    t=re.sub(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{11}\b','',NM.get(b,'')).strip(' -')  # nunca CPF no nome
    return tit(t)
S={}
for b,e in D.items(): S.setdefault(b[:2],{})[b]=[e[0],e[1],e[2],[[x[0],x[1],x[2],x[3],x[4]] if x[3]!='SP' else [x[0],x[1],x[2],'SP',x[4]] for x in sorted(e[3])],nome(b)]
tam=0
for k,v in S.items():
    s=json.dumps(v,separators=(',',':')); tam+=len(s); open(f'{OUT}/{k}.json','w').write(s)
print(len(D),'raízes;',len(S),'arquivos;',round(tam/1e6,1),'MB; maior',max(len(json.dumps(v)) for v in S.values())//1000,'KB')
