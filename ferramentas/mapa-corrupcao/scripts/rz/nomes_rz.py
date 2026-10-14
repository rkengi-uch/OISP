# Razão social das raízes do índice nacional (arquivos Empresas da Receita) -> rz_nomes.json
import json, zipfile, io
Z='/home/claude/rfb/zip/'; R='/home/claude/rfb/rz/'
B=set(json.load(open(R+'rz_raw.json'))); N={}
for i in range(10):
    with zipfile.ZipFile(Z+f'Empresas{i}.zip') as z:
        for n in z.namelist():
            for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
                b=ln[1:9]
                if b in B: N[b]=ln.split('";"')[1]
    print(i,len(N),flush=True)
json.dump(N,open(R+'rz_nomes.json','w'),ensure_ascii=False,separators=(',',':')); print('fim',flush=True)
