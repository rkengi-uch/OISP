import pickle, glob, time, sys
from passo1lib import linhas
p1=pickle.load(open('/home/claude/rfb/p1.pkl','rb')); p2=pickle.load(open('/home/claude/rfb/p2.pkl','rb'))
B=set()
for r in p1['L1A']+p1['L1P']+p2['L2']:
    B.add(r[0])
    if r[1]=='1' and len(r[3])==14: B.add(r[3][:8])
print(len(B),'empresas',flush=True)
EMP={}; t=time.time()
if 'emp' in sys.argv:
    for z in sorted(glob.glob('/home/claude/rfb/zip/Empresas*.zip')):
        for r in linhas(z):
            if r[0] in B: EMP[r[0]]=r[1:7]
        print(z,len(EMP),round(time.time()-t),flush=True)
    pickle.dump(EMP,open('/home/claude/rfb/emp.pkl','wb'))
if 'est' in sys.argv:
    EST={}
    for z in sorted(glob.glob('/home/claude/rfb/zip/Estabelecimentos*.zip')):
        for r in linhas(z):
            if r[0] in B:
                if r[3]=='1' or r[0] not in EST:
                    # cnpj completo, matriz, fantasia, situação, data situação, início, cnae, uf, município(código)
                    fil=EST[r[0]][9] if r[0] in EST else []
                    EST[r[0]]=[r[0]+r[1]+r[2],r[3],r[4],r[5],r[6],r[10],r[11],r[19],r[20],fil]
                if r[19]=='SP' and r[5]=='02' and len(EST[r[0]][9])<30: EST[r[0]][9].append(r[0]+r[1]+r[2])
        print(z,len(EST),round(time.time()-t),flush=True)
    pickle.dump(EST,open('/home/claude/rfb/est.pkl','wb'))
