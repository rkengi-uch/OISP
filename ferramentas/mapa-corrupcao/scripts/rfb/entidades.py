# Índice único de entidades do painel (autocompletar e filtros): uma entrada por pessoa, empresa/entidade,
# município, operação e órgão, com todas as grafias encontradas nas bases.
import json, re, unicodedata, collections, sys
P='/home/claude/p2/'; R='/home/claude/rfb/'
s=open(P+'index.html',encoding='utf-8').read(); i=s.index('const DATA = ')+13; D,_=json.JSONDecoder().raw_decode(s[i:])
L=lambda f: json.load(open(P+'dados/'+f+'.json',encoding='utf-8'))
QSA=L('qsa'); IMP=L('impedimentos'); SAN=L('sancoes'); TCU=L('tcu'); TSE=L('tse')
RFB=json.load(open(R+'rfb_full.json')) if len(sys.argv)<2 else json.load(open(sys.argv[1]))
def nrm(t):
    t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',t).split())
def limpo(n): return re.sub(r'\s*\(.*?\)','',str(n or '')).strip()
SUF=re.compile(r'\b(ltda|eireli|epp|me|s a|sa|s s|ss|cia|companhia|mei|em recuperacao judicial)\b')
def base_emp(n): return ' '.join(SUF.sub(' ',nrm(re.sub(r'^\s*[\d.\-/]+\s+','',n))).split())
def tit(t):
    t=str(t or '').strip()
    if re.search(r'[a-zà-ú]',t): return t
    pe={'de','da','do','das','dos','e','em','para','a','o'}
    w=t.lower().split(); return ' '.join(x if (i and x in pe) else (x.upper() if x in {'ltda','me','epp','eireli','sa','s/a','os','oscip','ong','apae','cia'} else x.capitalize()) for i,x in enumerate(w))
# ---------- empresas e entidades, agrupadas pelo CNPJ básico
E={}
def E_add(cnpj,nome,fonte,mun=''):
    c=re.sub(r'\D','',str(cnpj or ''));
    if len(c)<8 or not nome: return
    b=c[:8]; e=E.setdefault(b,{'c':c if len(c)==14 else '','n':collections.Counter(),'f':set(),'m':set(),'w':0})
    if len(c)==14 and not e['c']: e['c']=c
    e['n'][tit(re.sub(r'^\s*[\d.\-/]{8,}\s+','',str(nome)).strip())]+=1; e['f'].add(fonte); e['w']+=1
    if mun: e['m'].add(mun)
for c,v in QSA['emp'].items(): E_add(c,v[0],'Receita',v[2].title() if v[3]=='SP' else '')
for x in IMP['itens']: E_add(x.get('c'),x.get('n'),'TCE-SP',x.get('m'))
for x in SAN['emp']: E_add(x['cnpj'],x['nome'],'CEIS/CNEP')
for x in SAN['con']: E_add(x['cnpj'],x['forn'],'PNCP',x.get('mun'))
for x in IMP['con']: E_add(x.get('c'),x.get('n'),'PNCP')
for x in TCU: E_add(x.get('cnpj'),x['nome'],'TCU',x.get('mun'))
for x in TSE['forn']: E_add(x.get('c'),x.get('f'),'TSE')
for x in TSE['doa']: E_add(x.get('c'),x.get('e'),'TSE')
for b in D['QSA'].get('base',[]):
    for n in b['como']: E_add(b['c'],n,'Base de registros')
for b,v in RFB['C'].items():
    nm=v[0] or v[1]
    if nm: E_add(v[9] or b,nm,'Receita',v[4] if v[3]=='SP' else '')
    if v[1] and v[1]!=v[0]: E_add(v[9] or b,v[1],'Receita (nome fantasia)')
# nomes sem CNPJ (base de registros, entidades/OS citadas): ligados a um CNPJ quando o nome-base coincide
IDXB=collections.defaultdict(set)
for b,e in E.items():
    for n in e['n']:
        k=base_emp(n)
        if len(k)>=8 and len(k.split())>=2: IDXB[k].add(b)
SEMC={}
def sem_cnpj(nome,fonte,mun=''):
    k=base_emp(nome)
    if len(k)<6: return
    bs=IDXB.get(k)
    if bs and len(bs)==1: E_add(next(iter(bs)),nome,fonte,mun); return
    x=SEMC.setdefault(k,{'n':collections.Counter(),'f':set(),'m':set(),'w':0}); x['n'][tit(nome)]+=1; x['f'].add(fonte); x['w']+=1
    if mun: x['m'].add(mun)
for x in D['R']:
    for n in re.split(r';',x.get('empresa') or ''):
        n=re.sub(r'\(.*?\)','',n).strip(' .')
        if len(n)>4: sem_cnpj(n,'Base de registros',x['mun'])
for x in D['ENT']: sem_cnpj(limpo(x['ent']),'Entidades/OS',x.get('mun'))
for p in (D['TJSP'].get('processos') or [])+(D['TJ2'].get('processos') or []):
    if p.get('tipo')=='empresa': sem_cnpj(p['nome'],'TJSP')
fmt=lambda c:re.sub(r'^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$',r'\1.\2.\3/\4-\5',c)
OUT=[]
for b,e in E.items():
    nomes=[n for n,_ in e['n'].most_common()]
    rv=RFB['C'].get(b); can=re.sub(r'[\s.,;\-–]+$','',tit(rv[0])) if rv and rv[0] else nomes[0]
    ac=[n for n in nomes if base_emp(n)==base_emp(can) and re.search(r'[^\x00-\x7f]',n) and re.search(r'[a-zà-ú]',n)]
    if ac: can=ac[0]
    al=[n for n in nomes if nrm(n)!=nrm(can)]
    # grafias que só diferem no sufixo societário viram uma só
    vis={base_emp(can)}; al2=[]
    for n in al:
        k=nrm(n)
        if k not in {nrm(x) for x in al2}: al2.append(n)
    d=' · '.join(x for x in ['CNPJ '+fmt(e['c']) if e['c'] else 'CNPJ '+b+'…', sorted(e['m'])[0] if e['m'] else '', ', '.join(sorted(e['f'])[:4])] if x)
    OUT.append(['e',can,al2[:8],e['c'] or b,d,e['w']])
for k,x in SEMC.items():
    nomes=[n for n,_ in x['n'].most_common()]
    OUT.append(['e',nomes[0],nomes[1:6],'',' · '.join(z for z in [sorted(x['m'])[0] if x['m'] else '', ', '.join(sorted(x['f']))] if z),x['w']])
# ---------- pessoas (nome + apelidos; cadastro da Receita separa homônimos)
PP={}
def P_add(nome,fonte,mun='',papel='',alias=None):
    n=limpo(nome); k=nrm(n)
    if len(k.split())<2 or re.search(r'nao identificad|nominad|vereadores|servidores|auditores|empresarios',k): return
    p=PP.setdefault(k,{'n':collections.Counter(),'a':set(),'f':set(),'m':set(),'pp':set(),'w':0})
    p['n'][n]+=1; p['f'].add(fonte); p['w']+=1
    if mun: p['m'].add(mun)
    if papel: p['pp'].add(papel)
    if alias: p['a'].add(alias)
for x in D['R']:
    ap=(re.search(r'\(([^)]+)\)',x['nome']) or [None,None])[1]
    if re.search(r'\b(LTDA|S/?A|EIRELI)\b',x['nome'].upper()): continue
    P_add(x['nome'],'Base de registros',x['mun'],x.get('cargo'),ap)
for x in D['TCE']['itens']: P_add(x['resp'],'TCE-SP',x.get('mun'),x.get('papel'))
for x in D['PAR']:
    for n in re.split(r'\s+e\s+|;|/|,',x['pref'] or ''):
        if n.strip(): P_add(n,'TCE-SP parecer',x['mun'],'Prefeito')
for x in D['TCM']:
    for n in re.split(r';|/|,',x.get('responsavel') or ''):
        if n.strip(): P_add(n,'TCMSP','São Paulo')
for x in (D['TJSP'].get('processos') or []):
    if x.get('tipo')=='pessoa': P_add(x['nome'],'TJSP')
for x in (D['TJ2'].get('processos') or []):
    if x.get('tipo')=='pessoa': P_add(x['nome'],'TJSP 2º grau')
for x in (D['CNIA'].get('itens') or []):
    if x.get('tipo')=='pessoa': P_add(x['nome'],'CNIA',x.get('comarca','').title())
for x in TCU:
    if x.get('tipo')!='empresa': P_add(x['nome'],'TCU',x.get('mun'))
for x in TSE['fl']+TSE['cand']: P_add(x['n'],'TSE',x.get('m'),x.get('c'),x.get('u') if x.get('u') and len(str(x.get('u')).split())>=2 else None)
for x in TSE['doa']: P_add(x['d'],'TSE (doador)',x.get('m'))
for c,ss in QSA['soc'].items():
    for so in ss:
        if so[3]=='PF': P_add(so[0],'Receita (sócio)','',so[1])
for p,v in RFB['P'].items(): P_add(v[0],'Receita (sócio)')
for p in D['PES']:
    k=nrm(p['n'])
    for a in p.get('ap',[])+p.get('va',[]):
        if k in PP: PP[k]['a'].add(a)
# quantos cadastros diferentes (homônimos) na Receita por nome
HOM=collections.Counter(nrm(v[0]) for v in RFB['P'].values())
for k,p in PP.items():
    nomes=[n for n,_ in p['n'].most_common()]
    can=next((n for n in nomes if re.search(r'[a-zà-ú]',n)),nomes[0]); can=tit(can)
    al=sorted({a for a in p['a']}|{n for n in nomes if nrm(n)!=nrm(can)} - {can})[:6]
    h=HOM.get(k,0)
    d=' · '.join(z for z in [', '.join(sorted(p['pp'])[:2]), ', '.join(sorted(p['m'])[:2]), ', '.join(sorted(p['f'])[:3]), f'{h} cadastros com este nome na Receita: verificar homonímia' if h>1 else ''] if z)
    OUT.append(['p',can,al,k,d,p['w']])
# ---------- municípios, operações e órgãos
muns=set(x['mun'] for x in D['R'])|set(n[11] for n in D['NEWS'])|set(x['mun'] for x in D['PAR'])|set(x.get('mun') for x in D['TCE']['itens'])|set(x.get('m') for x in IMP['itens'])
for m in sorted(x for x in muns if x and x!='Intermunicipal'): OUT.append(['m',m,[],'','município' if m!='Governo do Estado de SP' else 'esfera estadual',3])
ops=collections.Counter([x['op'] for x in D['R'] if x.get('op')]+list(D.get('OPLINKS',{}).keys())+[c['op'] for c in D['CIT'] if c.get('op')])
for o,w in ops.items():
    if o and len(o)>2: OUT.append(['o',o,[],'','operação',w])
org=collections.Counter([x['orgao'] for x in SAN['con']]+[x.get('o') for x in IMP['itens'] if x.get('o')])
for o,w in org.items():
    if o: OUT.append(['g',tit(o),[],'','órgão público',min(w,20)])
json.dump({'ref':D['META'].get('data_base',''),'L':OUT},open(P+'dados/entidades.json','w'),ensure_ascii=False,separators=(',',':'))
print(collections.Counter(r[0] for r in OUT), round(len(json.dumps(OUT,ensure_ascii=False))/1e6,2),'MB')
