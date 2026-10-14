# Base CNPJ da Receita Federal (dados abertos) em duas camadas, a partir das sementes do painel.
# Saídas: rfb.json (painel), envolvidos.json (empresas para cruzar com contratos). CPF (mesmo mascarado) nunca sai daqui.
import json, pickle, zipfile, io, re, hashlib, unicodedata, sys, collections
R='/home/claude/rfb/'
SAL=open(R+'sal.txt').read().strip()
def lk(z):
    with zipfile.ZipFile(R+'zip/'+z) as zf:
        with zf.open(zf.namelist()[0]) as f:
            return {a:b for a,b in (ln.rstrip('\r\n')[1:-1].split('";"')[:2] for ln in io.TextIOWrapper(f,encoding='latin-1',newline=''))}
MUN=lk('Municipios.zip'); NAT=lk('Naturezas.zip'); QUAL=lk('Qualificacoes.zip'); CNAE=lk('Cnaes.zip')
def nrm(t):
    t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper()
    return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
S=json.load(open(R+'sementes.json')); p1=pickle.load(open(R+'p1.pkl','rb')); p2=pickle.load(open(R+'p2.pkl','rb'))
EMP=pickle.load(open(R+'emp.pkl','rb')); EST=pickle.load(open(R+'est.pkl','rb'))
# nomes de município do painel (com acento) pela forma normalizada
P='/home/claude/p2/'; s=open(P+'index.html',encoding='utf-8').read(); i=s.index('const DATA = ')+13; D,_=json.JSONDecoder().raw_decode(s[i:])
gi=s.index('const GEO = ')+12; GEO,_=json.JSONDecoder().raw_decode(s[gi:])
MP={}
for m in [x['mun'] for x in D['R']]+[n[11] for n in D['NEWS']]+[x['mun'] for x in D['PAR']]+[x.get('mun') for x in D['TCE']['itens']]:
    if m: MP[nrm(m)]=m
SIT={'01':'NULA','02':'ATIVA','03':'SUSPENSA','04':'INAPTA','08':'BAIXADA'}
def comp(b):
    e=EMP.get(b,['']*6); t=EST.get(b)
    cap=e[3].replace(',','.') if len(e)>3 else '0'
    try: cap=float(cap)
    except: cap=0
    if t:
        mn=MUN.get(t[8],''); mnp=MP.get(nrm(mn), mn.title() if t[7]=='SP' else mn.title())
        ab=t[5]; ab=f'{ab[6:8]}/{ab[4:6]}/{ab[:4]}' if len(ab)==8 else ''
        return dict(r=e[0],f=t[2],s=SIT.get(t[3],t[3]),uf=t[7],m=mnp,ab=ab,cn=CNAE.get(t[6],''),nj=NAT.get(e[1],''),cap=cap,c=t[0],fil=t[9])
    return dict(r=e[0],f='',s='',uf='',m='',ab='',cn='',nj=NAT.get(e[1],'') if e[1] else '',cap=cap,c='',fil=[])
def tt(t):
    pe={'De','Da','Do','Das','Dos','E','Em'}
    return ' '.join(w.lower() if i and w in pe else w for i,w in enumerate(str(t).title().split()))
def pid(n,m): return 'p'+hashlib.sha1((SAL+n+'|'+m).encode()).hexdigest()[:11]
ROWS={}
for r in p1['L1A']+p1['L1P']+p2['L2']:
    ROWS[(r[0],r[1],r[2],r[3])]=r
porK=collections.defaultdict(list); porB=collections.defaultdict(list)
for r in ROWS.values():
    porB[r[0]].append(r)
    if r[1]=='2': porK[(r[2],r[3])].append(r)
SB={c[:8]:o for c,o in S['cnpj'].items()}
def tok(n): return len(n.split())
C={}            # empresas que entram: b -> dados
V=[]            # vínculos: [b, sócio (pid ou c+b), qualificação, entrada, camada, confiança]
PES={}          # pid -> [nome, origens, conf, homonimos]
vist=set()
def addV(b,soc,q,de,cam,cf):
    k=(b,soc)
    if k in vist: return
    vist.add(k); V.append([b,soc,QUAL.get(q,q),(de[6:8]+'/'+de[4:6]+'/'+de[:4]) if len(de)==8 else '',cam,cf])
    if b not in C: C[b]=comp(b)
def sp_first(rows):
    return sorted(rows,key=lambda r:(0 if (EST.get(r[0]) or [0]*8)[7]=='SP' else 1, r[0]))
# 1) pessoas citadas no painel -> empresas (validação por município ou nome único no estado)
match=collections.defaultdict(list)
for r in p1['L1P']:
    if r[1]=='2' and r[2] in S['pes']: match[r[2]].append((r[2],r[3]))
aceitos={}; NATN={}
for nome,keys in match.items():
    keys=list(set(keys)); sd=S['pes'][nome]; ms={nrm(m) for m in sd['m']}; NATN[nome]=len(keys)
    def info(k):
        rs=porK[k]; ufs=[(EST.get(r[0]) or [0]*9)[7] for r in rs]; mns=[nrm(MUN.get((EST.get(r[0]) or [0]*9)[8],'')) for r in rs]
        return rs,ufs,mns
    sp_keys=[k for k in keys if 'SP' in info(k)[1]]
    for k in keys:
        rs,ufs,mns=info(k)
        if ms and any(m in ms for m in mns): cf='mun'
        elif 'SP' in ufs and len(sp_keys)==1 and len([w for w in nome.split() if w not in ('DE','DA','DO','DAS','DOS','E')])>=4: cf='sp'
        else: continue
        aceitos[k]=(cf,sd)
hom=collections.Counter(k[0] for k in aceitos)
for k,(cf,sd) in aceitos.items():
    p=pid(*k); PES[p]=[sd['n'] if nrm(sd['n'])==k[0] else tt(k[0]),sorted(sd['o']),cf,hom[k[0]]>1 or NATN.get(k[0],0)>=5,'semente',sd.get('pp',[])]
    rs=sp_first(porK[k])[:40]
    for r in rs:
        addV(r[0],p,r[4],r[5],1,cf)
        # camada 2: demais sócios dessas empresas
        for r2 in sp_first([x for x in porB[r[0]] if (x[2],x[3])!=k])[:30]:
            if r2[1]=='2':
                p2_=pid(r2[2],r2[3]); PES.setdefault(p2_,[tt(r2[2]),[],'cnpj',False,'camada2',[]]); addV(r[0],p2_,r2[4],r2[5],2,'cnpj')
            elif r2[1]=='1' and len(r2[3])==14:
                addV(r[0],'c'+r2[3][:8],r2[4],r2[5],2,'cnpj'); C.setdefault(r2[3][:8],comp(r2[3][:8]))
# 2) empresas citadas no painel -> sócios (camada 1) -> outras empresas dos sócios (camada 2)
for b,orig in SB.items():
    C.setdefault(b,comp(b))
    for r in porB.get(b,[]):
        if r[1]=='2':
            k=(r[2],r[3]); p=pid(*k)
            if p not in PES: PES[p]=[tt(r[2]),[],'cnpj',False,'socio',[]]
            elif PES[p][4]=='camada2': PES[p][4]='socio'
            addV(b,p,r[4],r[5],1,'cnpj')
            for r2 in sp_first([x for x in porK[k] if x[0]!=b])[:40]:
                addV(r2[0],p,r2[4],r2[5],2,'cnpj')
        elif r[1]=='1' and len(r[3])==14:
            pj=r[3][:8]; addV(b,'c'+pj,r[4],r[5],1,'cnpj'); C.setdefault(pj,comp(pj))
            for r2 in sp_first(porB.get(pj,[]))[:30]:
                if r2[1]=='2':
                    p2_=pid(r2[2],r2[3]); PES.setdefault(p2_,[tt(r2[2]),[],'cnpj',False,'camada2',[]]); addV(pj,p2_,r2[4],r2[5],2,'cnpj')
# origem das empresas sementes
for b in C: C[b]['o']=sorted(SB.get(b,[]))
# envolvidos e suas empresas (para o cruzamento com contratos públicos)
inv=collections.defaultdict(set)    # b -> pids de envolvidos
for b,soc,q,de,cam,cf in V:
    if not soc.startswith('p'): continue
    pp=PES[soc]
    if pp[4]=='semente' or (pp[4]=='socio'):
        if b in SB and pp[4]=='socio': continue          # a própria empresa sancionada já tem cruzamento próprio
        inv[b].add(soc)
alvo={}
for b,ps in inv.items():
    c=C[b]; cn=[c['c']] if c['c'] else []
    cn+= [x for x in c['fil'] if x not in cn][:9]
    if cn: alvo[b]={'cnpjs':cn,'pids':sorted(ps)}
json.dump(alvo,open(R+'envolvidos.json','w'),ensure_ascii=False)
out={'ref':'09/2026','C':{b:[c['r'],c['f'],c['s'],c['uf'],c['m'],c['ab'],c['cn'],c['nj'],c['cap'],c['c'],c['o']] for b,c in C.items()},
     'P':{p:v[:6] for p,v in PES.items()},'V':V}
json.dump(out,open(R+'rfb_full.json','w'),ensure_ascii=False)
print('empresas',len(C),'pessoas',len(PES),'vínculos',len(V),'camada1',sum(1 for v in V if v[4]==1),'aceitos por nome',len(aceitos),
      'conf',collections.Counter(v[0] for v in aceitos.values()),'homônimos',sum(1 for k in aceitos if hom[k[0]]>1),'empresas de envolvidos',len(alvo))
