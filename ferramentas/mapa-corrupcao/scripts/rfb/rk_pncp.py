# Contratos (PNCP) de empresas de envolvidos com órgãos municipais e estaduais de SP
import json, time, urllib.request, urllib.parse, sys, collections, ssl
from concurrent.futures import ThreadPoolExecutor
R='/home/claude/rfb/'
A=json.load(open(R+'envolvidos.json')); F=json.load(open(R+'rfb_full.json')); C=F['C']
alvo=[(b,c) for b,v in A.items() if C[b][2] in ('ATIVA','INAPTA','SUSPENSA') for c in v['cnpjs']]
cache=R+'pncp_cache.json'
try: CA=json.load(open(cache))
except Exception: CA={}
def get(url,tent=6):
    for t in range(tent):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OISP/1.0'}),timeout=40) as r: return json.loads(r.read())
        except Exception as e:
            time.sleep(1.5*(t+1))
    raise RuntimeError('falhou '+url)
def busca(cs,pag):
    q=' OR '.join('"%s"'%c for c in cs)
    return get('https://pncp.gov.br/api/search/?'+urllib.parse.urlencode(dict(q=q,tipos_documento='contrato',ufs='SP',pagina=pag,tam_pagina=100,ordenacao='-data')))
def item(x):
    return dict(o=x.get('orgao_nome'),m=x.get('municipio_nome'),e=x.get('esfera_id'),u=x.get('unidade_nome'),d=(x.get('data_assinatura') or '')[:10],v=x.get('valor_global'),
                obj=(x.get('description') or '')[:300],l='https://pncp.gov.br/app'+(x.get('item_url') or ''),c=x.get('cancelado'))
def lote(cs):
    """consulta um lote de CNPJs (OR); se houver resultados demais, divide o lote"""
    d=busca(cs,1); tot=d.get('total') or 0; S=set(cs); out={c:[] for c in cs}
    if tot>2000 and len(cs)>1:
        h=len(cs)//2; a=lote(cs[:h]); a.update(lote(cs[h:])); return a
    its=d.get('items') or []; pag=1
    while True:
        for x in its:
            ni=x.get('fornecedor_ni') or ''
            if ni in S: out[ni].append(item(x))
        if len(its)<100 or pag>=25: break
        pag+=1; its=busca(cs,pag).get('items') or []
    return out
fila=[c for b,c in alvo if c not in CA]
fila=list(dict.fromkeys(fila))
print(len(alvo),'CNPJs;',len(fila),'a consultar',flush=True)
LOTE=40
lotes=[fila[i:i+LOTE] for i in range(0,len(fila),LOTE)]
def tarefa(cs):
    try: return lote(cs)
    except Exception as e: return None
feitos=0
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(tarefa,lotes):
        feitos+=1
        if r: CA.update(r)
        if feitos%10==0:
            json.dump(CA,open(cache,'w')); print(feitos,len(lotes),len(CA),sum(1 for v in CA.values() if v),flush=True)
json.dump(CA,open(cache,'w'))
print('fim',len(CA),'com contrato',sum(1 for v in CA.values() if v),flush=True)
