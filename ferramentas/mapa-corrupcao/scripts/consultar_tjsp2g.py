#!/usr/bin/env python3
"""Consulta nomes na consulta pública de 2º grau do TJSP (e-SAJ cposg) e gera o SQL
para gravar o resultado no Supabase (tabelas tjsp2_consultas e tjsp2_processos).

Por que existe: prefeito no exercício do mandato responde por crime diretamente no
Tribunal de Justiça (foro por prerrogativa, CF art. 29, X). Essas ações penais
originárias, os recursos (apelações em improbidade e criminais), habeas corpus e
agravos não aparecem na consulta de 1º grau (cpopg).

Uso:
  python3 consultar_tjsp2g.py nomes.json > tjsp2.sql
nomes.json: o mesmo formato de consultar_tjsp.py
  [{"nome": "...", "tipo": "pessoa"|"empresa", "registros": ["R201"], "datas": ["2026-09-28"], "municipios": ["Diadema"]}]

Regras: as mesmas do 1º grau (nome exato; sem resultado, nome parcial com mesmo
primeiro nome e todos os termos em ordem; exclui vítima/testemunha; só classes e
assuntos de interesse público; processo criminal sem ligação com a administração
só fica com confiança alta ou data próxima de fato da base). "originaria" = ação
penal, inquérito, notícia-crime, procedimento investigatório ou medida cautelar
que começou no próprio Tribunal (típico de prefeito no cargo).
"""
import json, re, sys, time, urllib.parse
sys.path.insert(0, __import__('os').path.dirname(__file__))
from consultar_tjsp import (fetch, txt, norm, termos, casa_parcial, data_de, REL, ADMIN, PAPEL_EXCLUIDO, ASSUNTO_EXCLUIDO, q, arr)
import datetime

BASE = 'https://esaj.tjsp.jus.br'
ORIG = re.compile(r'^(acao penal|inquerito|noticia.crime|procedimento investigatorio|pedido de|medidas? (cautelar|investigat)|'
                  r'interpelacao|representacao criminal|queixa|peticao criminal|busca e apreensao|quebra de sigilo|prisao)')

def url_busca(nome, completo):
    return BASE + '/cposg/search.do?' + urllib.parse.urlencode({
        'conversationId': '', 'paginaConsulta': '0', 'cbPesquisa': 'NMPARTE', 'dePesquisa': nome,
        'chNmCompleto': 'true' if completo else 'false', 'localPesquisa.cdLocal': '-1'})

def parse_lista(s):
    out, area = [], ''
    for m in re.finditer(r'<h2 class="unj-subtitle[^"]*">(.*?)</h2>|<div id="divProcesso(\w+)"(.*?)</li>', s, re.S):
        if m.group(1) is not None:
            area = txt(m.group(1)); continue
        b = m.group(3)
        a = re.search(r'href="/cposg/show\.do\?processo\.codigo=(\w+)[^"]*"[^>]*>\s*([\d\.\-]+)', b)
        if not a:
            continue
        g = lambda c: (lambda x: txt(x.group(1)) if x else '')(re.search(r'class="' + c + r'"[^>]*>(.*?)</(?:div|label)>', b, re.S))
        dist = g('dataLocalDistribuicao')
        out.append(dict(codigo=a.group(1), numero=a.group(2), area=area,
                        participacao=g('unj-label tipoDeParticipacao').rstrip(':'), nome_parte=g('unj-base-alt nomeParticipante'),
                        classe=g('classeProcesso'), assunto=g('assuntoProcesso'),
                        recebido=dist.split(' - ')[0].strip(), orgao=' - '.join(dist.split(' - ')[1:]).strip()))
    return out

def parse_detalhe(s, url):
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    g = lambda i: (lambda x: txt(x.group(1)) if x else '')(re.search(r'id="' + i + r'"[^>]*>(.*?)</(?:span|div)>', s, re.S))
    base = dict(codigo=qs.get('processo.codigo', [''])[0], numero=g('numeroProcesso'), area=g('secaoProcesso'),
                classe=g('classeProcesso'), assunto=g('assuntoProcesso'), orgao=g('orgaoJulgadorProcesso'), recebido='')
    itens = []
    tab = re.search(r'<table id="tablePartesPrincipais"(.*?)</table>', s, re.S)
    for m in re.finditer(r'<tr class="fundoClaro"[^>]*>(.*?)</tr>', tab.group(1) if tab else s, re.S):
        c = re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.S)
        if len(c) >= 2:
            d = dict(base); d.update(participacao=txt(c[0]).rstrip(':'), nome_parte=txt(c[1]).split(' Advogad')[0].strip()); itens.append(d)
    return itens

def buscar(nome, completo):
    url = url_busca(nome, completo)
    u, s = fetch(url)
    if '/show.do' in u:
        return 1, parse_detalhe(s, u), 'ok'
    m = re.search(r'(\d[\d\.]*)\s+Processos? encontrados', s)
    if not m:
        if re.search(r'muitos processos|refin', s, re.I):
            return None, [], 'nome muito comum: o TJSP pede refinamento'
        return 0, [], 'sem resultados'
    total = int(m.group(1).replace('.', ''))
    itens, pag = parse_lista(s), 0
    while len(itens) < total and pag < 8:
        pag += 1; time.sleep(1.2)
        _, s2 = fetch(url.replace('paginaConsulta=0', 'paginaConsulta=%d' % pag))
        novos = [x for x in parse_lista(s2) if x['codigo'] not in {i['codigo'] for i in itens}]
        if not novos:
            break
        itens += novos
    return total, itens, ('ok' if len(itens) >= total else 'parcial (%d de %d verificados)' % (len(itens), total))

def consultar(item):
    nome, tipo = item['nome'], item['tipo']
    emp = tipo == 'empresa'
    parcial = emp
    total, itens, status = buscar(nome, completo=not emp)
    if not emp and total == 0:
        time.sleep(1.2)
        total, itens, status = buscar(nome, completo=False)
        parcial = True
        if status != 'sem resultados':
            status += ' (busca por nome parcial)'
    datas = [datetime.date.fromisoformat(d) for d in item.get('datas') or [] if d]
    qn = termos(nome)
    procs, vistos = [], set()
    for it in itens:
        parte = it['nome_parte']
        if emp:
            if norm(nome) not in norm(parte): continue
        elif parcial:
            if not casa_parcial(nome, parte): continue
        elif norm(parte) != norm(nome):
            continue
        if PAPEL_EXCLUIDO.search(norm(it['participacao'])): continue
        assunto = norm(it['classe'] + ' ' + it['assunto'])
        if not REL.search(assunto) or ASSUNTO_EXCLUIDO.search(assunto): continue
        conf = 'alta' if (emp or (len(qn) >= 3 and not parcial)) else 'verificar homonímia'
        if conf != 'alta' and not ADMIN.search(assunto):
            d = data_de(it['recebido'])
            if not (d and any(abs((d - x).days) <= 30 for x in datas)):
                continue
        if it['codigo'] in vistos: continue
        vistos.add(it['codigo'])
        it.update(confianca=conf, originaria=bool(ORIG.search(norm(it['classe']))),
                  link=f"{BASE}/cposg/show.do?processo.codigo={it['codigo']}")
        procs.append(it)
    return dict(nome=nome, tipo=tipo, registros=item.get('registros') or [], total=total, status=status,
                link_busca=url_busca(nome, completo=not emp)), procs

if __name__ == '__main__':
    nomes = json.load(open(sys.argv[1], encoding='utf-8'))
    sql = ['begin;']
    for i, item in enumerate(nomes):
        try:
            c, procs = consultar(item)
        except Exception as e:
            c, procs = dict(nome=item['nome'], tipo=item['tipo'], registros=item.get('registros') or [], total=None,
                            status='erro: ' + str(e)[:80], link_busca=url_busca(item['nome'], item['tipo'] != 'empresa')), []
        print(f"{c['nome']}: {c['status']} | {len(procs)} processo(s) de 2º grau listado(s)", file=sys.stderr, flush=True)
        sql.append(
            "insert into tjsp2_consultas (nome,tipo,registros,total_resultados,relevantes,status,link_busca,consultado_em) values "
            f"({q(c['nome'])},{q(c['tipo'])},{arr(c['registros'])},{q(c['total'])}::int,{len(procs)},{q(c['status'])},{q(c['link_busca'])},current_date) "
            "on conflict (nome,tipo) do update set registros=(select array(select distinct unnest(tjsp2_consultas.registros || excluded.registros))), "
            "total_resultados=excluded.total_resultados, relevantes=excluded.relevantes, status=excluded.status, link_busca=excluded.link_busca, consultado_em=current_date;")
        for p in procs:
            sql.append(
                "insert into tjsp2_processos (nome_consultado,tipo,registros,numero,codigo,link,area,classe,assunto,participacao,nome_parte,orgao_julgador,recebido_em,originaria,confianca) values "
                f"({q(c['nome'])},{q(c['tipo'])},{arr(c['registros'])},{q(p['numero'])},{q(p['codigo'])},{q(p['link'])},{q(p['area'])},"
                f"{q(p['classe'])},{q(p['assunto'])},{q(p['participacao'])},{q(p['nome_parte'])},{q(p['orgao'])},{q(p['recebido'])},{'true' if p['originaria'] else 'false'},{q(p['confianca'])}) "
                "on conflict (nome_consultado,numero,codigo) do nothing;")
        if i < len(nomes) - 1:
            time.sleep(1.2)
    sql.append('commit;')
    print('\n'.join(sql))
