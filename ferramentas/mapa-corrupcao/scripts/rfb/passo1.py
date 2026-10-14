import json, zipfile, io, glob, pickle, time
S=json.load(open('/home/claude/rfb/sementes.json'))
seedB={c[:8] for c in S['cnpj']}; nomes=set(S['pes'])
L1A=[]; L1P=[]; t=time.time()
def linhas(z):
    with zipfile.ZipFile(z) as zf:
        n=zf.namelist()[0]
        with zf.open(n) as f:
            for ln in io.TextIOWrapper(f,encoding='latin-1',newline=''):
                yield ln.rstrip('\r\n')[1:-1].split('";"')
for z in sorted(glob.glob('/home/claude/rfb/zip/Socios*.zip')):
    for r in linhas(z):
        b=r[0]
        if b in seedB: L1A.append(r)
        elif r[2] in nomes: L1P.append(r)
    print(z, len(L1A), len(L1P), round(time.time()-t), flush=True)
pickle.dump({'L1A':L1A,'L1P':L1P},open('/home/claude/rfb/p1.pkl','wb'))
