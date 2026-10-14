# sementes da consulta à base CNPJ: CNPJs e nomes de pessoas citados no painel
import json, re, sys, unicodedata
P='/home/claude/p2/'
s=open(P+(sys.argv[1] if len(sys.argv)>1 else 'index.html'),encoding='utf-8').read(); i=s.index('const DATA = ')+13; D,_=json.JSONDecoder().raw_decode(s[i:])
L=lambda f: json.load(open(P+'dados/'+f+'.json',encoding='utf-8'))
QSA=L('qsa'); IMP=L('impedimentos'); SAN=L('sancoes'); TCU=L('tcu'); TSE=L('tse')
def nrm(t):
    t=unicodedata.normalize('NFD',str(t or '')).encode('ascii','ignore').decode().upper()
    return re.sub(r'[^A-Z0-9 ]+',' ',t).split() and ' '.join(re.sub(r'[^A-Z0-9 ]+',' ',t).split()) or ''
def limpo(n): return re.sub(r'\s*\(.*?\)','',str(n or '')).strip()
cnpjs={}
def addc(c,orig):
    c=re.sub(r'\D','',str(c or ''))
    if len(c)==14: cnpjs.setdefault(c,set()).add(orig)
for c in QSA['emp']: addc(c,'QSA')
for x in IMP['itens']: addc(x.get('c'),'TCE-SP impedimento')
for x in SAN['emp']: addc(x.get('cnpj'),'CEIS/CNEP')
for x in SAN['con']: addc(x.get('cnpj'),'CEIS/CNEP')
for x in TCU: addc(x.get('cnpj'),'TCU')
for b in D['QSA'].get('base',[]): addc(b['c'],'Citada na base')
for e in D.get('ENT',[]): addc(e.get('cnpj'),'Entidade ou empresa citada em operação')
for x in TSE['forn']: addc(x.get('c'),'TSE fornecedor')
for x in TSE['doa']: addc(x.get('c'),'TSE doação')
pes={}
def addp(n,mun,orig,papel=''):
    n=limpo(n); k=nrm(n)
    if len(k.split())<2 or re.search(r'NAO IDENTIFICAD|NOMINAD|VEREADORES|SERVIDORES|AUDITORES|EMPRESARIOS|^\d',k): return
    p=pes.setdefault(k,{'n':n,'m':set(),'o':set(),'pp':set()})
    if mun: p['m'].add(nrm(mun))
    p['o'].add(orig)
    if papel: p['pp'].add(papel)
for x in D['R']:
    if re.search(r'\b(LTDA|S/?A|EIRELI|ME|EPP)\b',x['nome'].upper()): continue
    addp(x['nome'],x['mun'],'Base de registros',x.get('cargo',''))
for x in D['TCE']['itens']: addp(x['resp'],x.get('mun'),'TCE-SP contas irregulares',x.get('papel',''))
def nomesPar(t): return [a.strip() for a in re.split(r'\s+e\s+|;|/|,',str(t or '')) if a.strip()]
for x in D['PAR']:
    for n in nomesPar(x['pref']): addp(n,x['mun'],'TCE-SP parecer desfavorável','Prefeito')
for x in D['TCM']:
    for n in nomesPar(x.get('responsavel','')): addp(n,'São Paulo','TCMSP',x.get('orgao',''))
for x in (D['TJSP'].get('processos') or []):
    if x.get('tipo')=='pessoa': addp(x['nome'],None,'TJSP')
for x in (D['TJ2'].get('processos') or []):
    if x.get('tipo')=='pessoa': addp(x['nome'],None,'TJSP 2º grau')
for x in (D['CNIA'].get('itens') or []):
    if x.get('tipo')=='pessoa': addp(x['nome'],x.get('comarca'),'CNIA')
for x in TCU:
    if x.get('tipo')!='empresa': addp(x['nome'],x.get('mun'),'TCU',)
for x in TSE['fl']: addp(x['n'],x.get('m'),'TSE Ficha Limpa',x.get('c',''))
for x in D['PES']:
    for m in x.get('m',[]): addp(x['n'],m,'Cadastro de pessoas')
out={'cnpj':{c:sorted(o) for c,o in cnpjs.items()},'pes':{k:{'n':v['n'],'m':sorted(v['m']),'o':sorted(v['o']),'pp':sorted(v['pp'])[:4]} for k,v in pes.items()}}
json.dump(out,open('/home/claude/rfb/sementes.json','w'),ensure_ascii=False)
print(len(out['cnpj']),'CNPJs;',len(out['pes']),'pessoas')
