# Todos os estabelecimentos (matriz e filiais) das empresas do painel, pela raiz do CNPJ, nos arquivos abertos da Receita.
# Uso: python3 varre.py   -> estab_raw.json {raiz: [[ordem+dv, matriz(1)/filial(2), nome fantasia, situação, data situação, início, cnae, uf, município]]}
import json, zipfile, io
R='/home/claude/rfb/'; Z=R+'zip/'
F=json.load(open(R+'rfb_full.json'))
B=set(F['C'])|{c[:8] for c in json.load(open(R+'cnpjs_painel.json'))}
print(len(B),'raízes',flush=True)
MU={}
with zipfile.ZipFile(Z+'Municipios.zip') as z:
    for n in z.namelist():
        for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
            p=[x.strip('"\n') for x in ln.split('";"')]
            if len(p)>=2: MU[p[0]]=p[1]
OUT={}
for i in range(10):
    with zipfile.ZipFile(Z+f'Estabelecimentos{i}.zip') as z:
        for n in z.namelist():
            for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
                b=ln[1:9]
                if b not in B: continue
                p=[x.strip('"\n') for x in ln.split('";"')]
                if len(p)<21: continue
                OUT.setdefault(b,[]).append([p[1]+p[2],p[3],p[4],p[5],p[6],p[10],p[11],p[19],MU.get(p[20],p[20])])
    print('est',i,len(OUT),sum(len(v) for v in OUT.values()),flush=True)
json.dump(OUT,open(R+'estab/estab_raw.json','w'),ensure_ascii=False,separators=(',',':'))
print('fim',flush=True)
