# Contratos (PNCP) com órgãos de SP buscados pela RAIZ do CNPJ (8 dígitos, formatada "NN.NNN.NNN"):
# traz matriz e todas as filiais. Lotes de 40 raízes com OR; lote com mais de 2.000 resultados é dividido.
# Uso: python3 pncp_raiz.py <cnpjs_painel.json>   (grava/continua pncp_cache_raiz.json: {raiz: [contratos]})
import json, time, urllib.request, urllib.parse, sys
from concurrent.futures import ThreadPoolExecutor
R='/home/claude/rfb/'; cache=R+'pncp_cache_raiz.json'
raizes=sorted({c[:8] for c in json.load(open(sys.argv[1])) if len(c)>=8})
try: CA=json.load(open(cache))
except Exception: CA={}
fmt=lambda b: f'{b[:2]}.{b[2:5]}.{b[5:8]}'
def get(url,tent=6):
    for t in range(tent):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'OISP/1.0'}),timeout=40) as r: return json.loads(r.read())
        except Exception: time.sleep(1.5*(t+1))
    raise RuntimeError('falhou')
def busca(bs,pag):
    q=' OR '.join('"%s"'%fmt(b) for b in bs)
    return get('https://pncp.gov.br/api/search/?'+urllib.parse.urlencode(dict(q=q,tipos_documento='contrato',ufs='SP',pagina=pag,tam_pagina=100,ordenacao='-data')))
def item(x):
    return dict(ni=x.get('fornecedor_ni'),o=x.get('orgao_nome'),m=x.get('municipio_nome'),e=x.get('esfera_id'),u=x.get('unidade_nome'),d=(x.get('data_assinatura') or '')[:10],v=x.get('valor_global'),
                obj=(x.get('description') or '')[:300],l='https://pncp.gov.br/app'+(x.get('item_url') or ''),c=x.get('cancelado'))
def lote(bs):
    d=busca(bs,1); tot=d.get('total') or 0
    if tot>2000 and len(bs)>1:
        h=len(bs)//2; a=lote(bs[:h]); a.update(lote(bs[h:])); return a
    out={b:[] for b in bs}; its=d.get('items') or []; pag=1
    while True:
        for x in its:
            b=(x.get('fornecedor_ni') or '')[:8]
            if b in out: out[b].append(item(x))
        if len(its)<100 or pag>=25: break
        pag+=1; its=busca(bs,pag).get('items') or []
    return out
fila=[b for b in raizes if b not in CA]
print(len(raizes),'raízes;',len(fila),'a consultar',flush=True)
LT=int(sys.argv[2]) if len(sys.argv)>2 else 40
lotes=[fila[i:i+LT] for i in range(0,len(fila),LT)]
def tarefa(bs):
    try: return lote(bs)
    except Exception: return None
feitos=0
with ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(tarefa,lotes):
        feitos+=1
        if r: CA.update(r)
        if feitos%10==0:
            json.dump(CA,open(cache,'w')); print(feitos,len(lotes),len(CA),sum(1 for v in CA.values() if v),flush=True)
json.dump(CA,open(cache,'w'))
print('fim',len(CA),'com contrato',sum(1 for v in CA.values() if v),flush=True)
