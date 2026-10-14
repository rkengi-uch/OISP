import urllib.request,urllib.parse,http.cookiejar,re,html,json,time
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)); op.addheaders=[('User-Agent','Mozilla/5.0 Chrome/124'),('X-Requested-With','XMLHttpRequest')]
s=op.open('https://portal.tcm.sp.gov.br/ConsultaProcesso',timeout=60).read().decode('utf-8','ignore')
tok=re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"',s); tok=tok.group(1) if tok else ''
def busca(anos):
    data=[('buscaComFiltro','true'),('TiposProcessosList','BALANÇO'),('Arquivados','true'),('Arquivados','false'),('Resolucao','false'),('page','1'),('pageSize','500')]+[('AnosList',a) for a in anos]
    if tok: data.append(('__RequestVerificationToken',tok))
    return op.open('https://portal.tcm.sp.gov.br/ConsultaProcesso',data=urllib.parse.urlencode(data).encode(),timeout=120).read().decode('utf-8','ignore')
def limpa(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',re.sub(r'<img[^>]*>','',x)))).strip()
r=busca(['2023','2024','2025','2026'])
ids=list(dict.fromkeys(re.findall(r"verDetalhes\('(TC\d+)'\)",r)))
rows=[]
for nid in ids:
    k=r.find(f"verDetalhes('{nid}')"); a=r.rfind('<tr',0,k); b=r.find('</tr>',k)
    tds=[limpa(t) for t in re.findall(r'<td[^>]*>(.*?)</td>',r[a:b],re.S)]
    rows.append({'id':nid,'tds':tds})
print(len(ids)); print(rows[0]['tds']); print(rows[5]['tds'])
def ajax(path,nid):
    d={'nutc':nid}
    if tok: d['__RequestVerificationToken']=tok
    try: return json.loads(op.open('https://portal.tcm.sp.gov.br'+path,data=urllib.parse.urlencode(d).encode(),timeout=60).read().decode('utf-8','ignore'))
    except Exception as e: return {'erro':str(e)}
t=ajax('/ConsultaProcesso/CarregarResultados',ids[5]); print({k:(limpa(v)[:600] if isinstance(v,str) else v) for k,v in t.items()})
t=ajax('/ConsultaProcesso/CarregarAcordao',ids[5]); print({k:(limpa(v)[:600] if isinstance(v,str) else v) for k,v in t.items()})
t=ajax('/ConsultaProcesso/CarregarInteressados',ids[5]); print({k:(limpa(v)[:600] if isinstance(v,str) else v) for k,v in t.items()})
json.dump(rows,open('rows.json','w'),ensure_ascii=False)
import os
out=json.load(open('tcm_balancos.json')) if os.path.exists('tcm_balancos.json') else []
feitos={d['id'] for d in out}
for rw in rows:
    if rw['id'] in feitos: continue
    nid=rw['id']; d={'id':nid}
    d['tc']=rw['tds'][3]; d['orgao']=rw['tds'][5]; d['objeto']=rw['tds'][6]
    for path,keys in [('/ConsultaProcesso/CarregarResultados',['renderResultadosHtml']),('/ConsultaProcesso/CarregarAcordao',['renderAcordaoHtml','renderEmentaHtml']),('/ConsultaProcesso/CarregarInteressados',['renderHtml']),('/ConsultaProcesso/CarregarRecursos',['renderRecursoHtml'])]:
        t=ajax(path,nid)
        for k_ in keys: d[k_]=t.get(k_,'') ; d[k_+'_txt']=limpa(t.get(k_,''))
        time.sleep(0.4)
    out.append(d); json.dump(out,open('tcm_balancos.json','w'),ensure_ascii=False); print(d['tc'],'|',d['orgao'][:40],'|',d['renderResultadosHtml_txt'][:120],'|',d['renderAcordaoHtml_txt'][:80],flush=True)
json.dump(out,open('tcm_balancos.json','w'),ensure_ascii=False)
