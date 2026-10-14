# Grava a base CNPJ (2 camadas) e o risco no Supabase pela carga_observatorio (upsert genérico pela coluna chave)
# Uso: TOKEN_CARGA=<token> python3 rfb_supabase.py
import json, os, urllib.request, datetime
URL='https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/rpc/carga_observatorio'; KEY='sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
D=json.load(open('/home/claude/p2/dados/receita.json')); TB=D['TB']; ref=D['ref']; hoje=datetime.date.today().isoformat()
def enviar(t,L,lote=800):
    tot=0
    for i in range(0,len(L),lote):
        body=json.dumps({'token':os.environ['TOKEN_CARGA'],'tabela':t,'linhas':L[i:i+lote]},ensure_ascii=False).encode()
        r=urllib.request.Request(URL,data=body,headers={'apikey':KEY,'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
        tot+=json.load(urllib.request.urlopen(r,timeout=300))
    print(t,tot,flush=True)
E=[dict(chave=b,cnpj_basico=b,cnpj=e[9] or None,razao_social=e[0],nome_fantasia=e[1] or None,situacao=e[2],uf=e[3],municipio=e[4],abertura=e[5],cnae=TB['cn'][e[6]],natureza=TB['nj'][e[7]],capital=e[8],origens=[TB['o'][i] for i in e[10]],referencia=ref,importado_em=hoje) for b,e in D['C'].items()]
P=[dict(chave=p,id=p,nome=x[0],origens=[TB['o'][i] for i in x[1]],correspondencia=x[2],possivel_homonimo=bool(x[3]),papel=x[4],cargos=x[5],referencia=ref,importado_em=hoje) for p,x in D['P'].items()]
V=[dict(chave=v[0]+'|'+v[1],cnpj_basico=v[0],socio=v[1],qualificacao=TB['q'][v[2]],desde=v[3],camada=v[4],correspondencia=v[5],referencia=ref,importado_em=hoje) for v in D['V']]
K=[dict(chave='|'.join([k[0],k[2] or '',k[3] or '',k[4] or ''])[:500],cnpj_basico=k[0],pessoas=k[1],orgao=k[2],municipio=k[3],esfera=k[4],contratos=k[5],valor=k[6],primeiro=k[7],ultimo=k[8],link=k[9],objeto=k[10],referencia=ref,importado_em=hoje) for k in D['K']]
for t,L in (('rfb_empresas',E),('rfb_socios',P),('rfb_vinculos',V),('risco_empresas_envolvidos',K)): enviar(t,L)
