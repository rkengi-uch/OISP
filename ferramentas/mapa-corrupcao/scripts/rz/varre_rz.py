# Índice de estabelecimentos por raiz do CNPJ, para a busca pela raiz na rede (qualquer empresa, mesmo fora do painel).
# Entram as raízes com pelo menos uma filial ativa, suspensa ou inapta e com algum estabelecimento em SP.
# Por raiz: estabelecimentos em SP (ativos, suspensos ou inaptos) + a matriz (qualquer UF ou situação) + totais no país.
# Saída: rz_raw.json {raiz: [total, ativos, baixados, [[ordem+dv, mf, sit, uf, mun_codigo], ...]]}
import json, zipfile, io, sys
Z='/home/claude/rfb/zip/'; OUT='/home/claude/rfb/rz/'
ATV={'02','03','04'}
R1=set()
for i in range(10):
    with zipfile.ZipFile(Z+f'Estabelecimentos{i}.zip') as z:
        for n in z.namelist():
            for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
                if ln[12:16]=='0001': continue
                p=ln.split('";"')
                if len(p)>6 and p[5] in ATV: R1.add(ln[1:9])
    print('passo 1', i, len(R1), flush=True)
D={}
for i in range(10):
    with zipfile.ZipFile(Z+f'Estabelecimentos{i}.zip') as z:
        for n in z.namelist():
            for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
                b=ln[1:9]
                if b not in R1: continue
                p=[x.strip('"\n') for x in ln.split('";"')]
                if len(p)<21: continue
                e=D.get(b)
                if e is None: e=D[b]=[0,0,0,[]]
                e[0]+=1
                if p[5] in ATV: e[1]+=1
                elif p[5]=='08': e[2]+=1
                if (p[19]=='SP' and p[5] in ATV) or p[3]=='1': e[3].append([p[1]+p[2],p[3],p[5].lstrip('0') or '0',p[19],p[20]])
    print('passo 2', i, len(D), flush=True)
D={b:e for b,e in D.items() if any(x[3]=='SP' for x in e[3])}
json.dump(D,open(OUT+'rz_raw.json','w'),separators=(',',':'))
print('fim', len(D), sum(len(e[3]) for e in D.values()), flush=True)
