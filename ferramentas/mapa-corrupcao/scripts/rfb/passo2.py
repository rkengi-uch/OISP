import json, zipfile, io, glob, pickle, time
from passo1lib import linhas
p1=pickle.load(open('/home/claude/rfb/p1.pkl','rb')); L1A,L1P=p1['L1A'],p1['L1P']
# chaves de pessoa (nome + CPF mascarado) só em memória
KA={(r[2],r[3]) for r in L1A if r[1]=='2'}
KP={(r[2],r[3]) for r in L1P if r[1]=='2'}
PJ={r[3][:8] for r in L1A+L1P if r[1]=='1' and len(r[3])==14}
CP={r[0] for r in L1P}            # empresas achadas pelo nome -> sócios delas (camada 2)
K=KA|KP; B=CP|PJ
print(len(KA),len(KP),len(PJ),len(CP),flush=True)
L2=[]; t=time.time()
for z in sorted(glob.glob('/home/claude/rfb/zip/Socios*.zip')):
    for r in linhas(z):
        if (r[2],r[3]) in K or r[0] in B: L2.append(r)
    print(z,len(L2),round(time.time()-t),flush=True)
pickle.dump({'L2':L2},open('/home/claude/rfb/p2.pkl','wb'))
