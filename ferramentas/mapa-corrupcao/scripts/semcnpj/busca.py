# procura, nos arquivos abertos do CNPJ, razão social ou nome fantasia iguais aos nomes citados (sem sufixo societário)
import json,re,unicodedata,zipfile,io,csv,sys
A=json.load(open('/home/claude/rfb/semcnpj/alvos.json'))
def nrm(t): t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
SUF=re.compile(r'\b(LTDA|S A|SA|EIRELI|ME|EPP|S S|SS|CIA|COMPANHIA|EM RECUPERACAO JUDICIAL)\b')
def key(t): return ' '.join(SUF.sub(' ',nrm(t)).split())
K=set(A); Z='/home/claude/rfb/zip/'
raz={}  # basico -> (key, razao, natureza)
for i in range(10):
    with zipfile.ZipFile(Z+f'Empresas{i}.zip') as z:
        for n in z.namelist():
            for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
                p=ln.split('";"'); 
                if len(p)<2: continue
                r=p[1]; k=key(r)
                if k in K: raz[p[0].strip('"')]=(k,r,p[2])
    print('emp',i,len(raz),flush=True)
est=[]  # estabelecimentos dos candidatos por razão + por fantasia (SP)
for i in range(10):
    with zipfile.ZipFile(Z+f'Estabelecimentos{i}.zip') as z:
        for n in z.namelist():
            for ln in io.TextIOWrapper(z.open(n),encoding='latin-1'):
                p=[x.strip('"\n') for x in ln.split('";"')]
                if len(p)<21: continue
                b=p[0]; fk=key(p[4]) if p[4] else ''
                if b in raz or (fk in K and p[19]=='SP'):
                    est.append(dict(b=b,c=p[0]+p[1]+p[2],mat=p[3],fan=p[4],sit=p[5],ini=p[10],cnae=p[11],uf=p[19],mun=p[20],kr=raz.get(b,('',))[0],kf=fk if fk in K else ''))
    print('est',i,len(est),flush=True)
json.dump(dict(raz={b:list(v) for b,v in raz.items()},est=est),open('/home/claude/rfb/semcnpj/cand.json','w'),ensure_ascii=False)
print('fim')
