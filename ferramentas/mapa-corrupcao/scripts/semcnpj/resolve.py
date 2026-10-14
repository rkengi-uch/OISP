# decide o CNPJ de cada nome citado (só quando a correspondência é única e segura) e monta dados/empcnpj.json
import json,re,unicodedata,zipfile,io,datetime
R='/home/claude/rfb/'; Z=R+'zip/'
A=json.load(open(R+'semcnpj/alvos.json')); C=json.load(open(R+'semcnpj/cand.json'))
def tab(n):
    with zipfile.ZipFile(Z+n) as z:
        return {p[0]:p[1] for p in (ln.strip().strip('"').split('";"') for ln in io.TextIOWrapper(z.open(z.namelist()[0]),encoding='latin-1')) if len(p)>=2}
MUN=tab('Municipios.zip'); NAT=tab('Naturezas.zip'); CNAE=tab('Cnaes.zip'); QUAL=tab('Qualificacoes.zip')
def nrm(t): t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split())
def semdoc(t): return re.sub(r'\s+',' ',re.sub(r'\b\d{11}\b|\b\d{2}\.\d{3}\.\d{3}\b|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b','',str(t or ''))).strip()
def tit(t): t=semdoc(t); t=' '.join(w.capitalize() for w in str(t or '').lower().split()); return re.sub(r'\s(Da|De|Do|Das|Dos|E|Em)\s',lambda m:m.group(0).lower(),t)
SIT={'01':'NULA','02':'ATIVA','03':'SUSPENSA','04':'INAPTA','08':'BAIXADA'}
dt=lambda d: d[6:8]+'/'+d[4:6]+'/'+d[:4] if len(d)==8 else ''
VAR={'TERRAPLANAGEM':'TERRAPLENAGEM'}  # variações de grafia comuns
SUF=re.compile(r'\b(LTDA|S A|SA|EIRELI|ME|EPP|S S|SS|CIA|COMPANHIA|EM RECUPERACAO JUDICIAL)\b')
def key(t): return ' '.join(VAR.get(w,w) for w in SUF.sub(' ',nrm(re.sub(r'\(.*?\)',' ',t))).split())
falta={e['b'] for e in C['est'] if e['b'] not in C['raz']}
for i in range(10):
    if not falta: break
    with zipfile.ZipFile(Z+f'Empresas{i}.zip') as z:
        for ln in io.TextIOWrapper(z.open(z.namelist()[0]),encoding='latin-1'):
            b=ln[1:9]
            if b in falta: p_=ln.strip().strip('"').split('";"'); C['raz'][b]=[key(p_[1]),p_[1],p_[2]]; falta.discard(b)
por={}  # alvo -> {basico: [est]}
for e in C['est']:
    for k in {e['kr'],e['kf']}-{''}:
        por.setdefault(k,{}).setdefault(e['b'],[]).append(e)
OUT={}; bas_ok={}
for k,a in A.items():
    G=por.get(k,{})
    # candidatos: empresas (CNPJ básico) com estabelecimento em SP
    cand={b:[e for e in es if e['uf']=='SP'] for b,es in G.items()}; cand={b:es for b,es in cand.items() if es}
    # empresário individual / MEI fica de fora: a razão social traz nome e CPF da pessoa (CPF nunca é guardado nem exibido)
    cand={b:es for b,es in cand.items() if (C['raz'].get(b) or ['','',''])[2] not in ('2135','2305')}
    munA={nrm(m) for m in a['mun']}
    escolha=None; crit=''
    if len(cand)==1: escolha=next(iter(cand)); crit='único CNPJ em SP com esta razão social ou nome fantasia na Receita'
    elif len(cand)>1:
        mesmo=[b for b,es in cand.items() if any(nrm(MUN.get(e['mun'],''))in munA for e in es)]
        if len(mesmo)==1: escolha=mesmo[0]; crit='único CNPJ com este nome no mesmo município do registro'
    lst=[]
    for b,es in sorted(cand.items()):
        m=next((e for e in es if e['mat']=='1'),es[0]); r=C['raz'].get(b)
        lst.append(dict(c=m['c'],r=tit(r[1]) if r else tit(m['fan']),f=tit(m['fan']),s=SIT.get(m['sit'],m['sit']),m=tit(MUN.get(m['mun'],'')),uf=m['uf']))
    OUT[k]=dict(nome=a['nome'],ids=a['ids'],n=len(cand),cand=lst[:12])
    if escolha:
        # ligação automática só com razão social igual e nome específico (3+ palavras) ou mesmo município; senão, "possível correspondência"
        porRaz=any(e['kr']==k for e in G.get(escolha,[])) or key((C['raz'].get(escolha) or ['',''])[1])==key(a['nome']); mesmoMun=any(nrm(MUN.get(e['mun'],''))in munA for e in G.get(escolha,[]))
        status='confirmado' if porRaz and (len(k.split())>=3 or mesmoMun) else 'possivel'
        if status=='confirmado' and not any(e['kr']==k for e in G.get(escolha,[])): crit='razão social igual (variação de grafia) e nome fantasia do estabelecimento igual ao citado; único em SP'
        if status=='possivel': crit=('mesmo nome, mas nome curto ou de grupo empresarial com vários CNPJs' if porRaz else 'só o nome fantasia de um estabelecimento coincide')+': verificar antes de ligar'
        es=G[escolha]; m=next((e for e in es if e['mat']=='1'),es[0]); r=C['raz'].get(escolha)
        OUT[k].update(cnpj=m['c'],todos=sorted({e['c'] for e in es}),status=status,crit=crit,razao=tit(r[1]) if r else tit(m['fan']),fant=tit(m['fan']),sit=SIT.get(m['sit'],m['sit']),mun=tit(MUN.get(m['mun'],'')),uf=m['uf'],ab=dt(m['ini']),cnae=CNAE.get(m['cnae'],''),nj=NAT.get(r[2],'') if r else '')
        if status=='confirmado': bas_ok[escolha]=k
# sócios (sem CPF) das empresas identificadas
for i in range(10):
    with zipfile.ZipFile(Z+f'Socios{i}.zip') as z:
        for ln in io.TextIOWrapper(z.open(z.namelist()[0]),encoding='latin-1'):
            p=[x.strip('"\n') for x in ln.split('";"')]
            if p[0] in bas_ok:
                OUT[bas_ok[p[0]]].setdefault('soc',[]).append(dict(n=tit(p[2]),q=QUAL.get(p[4],'sócio'),de=dt(p[5]),pj=p[1]=='1'))
json.dump(dict(ref=datetime.date.today().strftime('%d/%m/%Y'),L=OUT),open('/home/claude/p2/dados/empcnpj.json','w'),ensure_ascii=False,separators=(',',':'))
for k,v in OUT.items(): print(v['nome'],'|',v['n'],'cand |',v.get('status',''),v.get('cnpj','—'),v.get('razao',''),v.get('sit',''),v.get('mun',''),'|',v.get('crit',''),'| sócios',len(v.get('soc',[])))
