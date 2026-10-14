#!/usr/bin/env python3
"""Consulta nomes novos na consulta pública de 1º grau do TJSP (e-SAJ cpopg)
e gera o SQL para gravar o resultado no Supabase.

Uso:
  python3 consultar_tjsp.py nomes.json > tjsp.sql

nomes.json é uma lista de objetos:
  [{"nome": "Fulano de Tal", "tipo": "pessoa", "registros": ["R201"], "datas": ["2026-09-28"]},
   {"nome": "Empresa Exemplo", "tipo": "empresa", "registros": ["R201"]}]
  - tipo: "pessoa" ou "empresa"
  - registros: IDs da base ligados ao nome
  - datas: data_evento_iso dos registros (usadas para aceitar prisões de possível homônimo)
  - municipios (opcional): municípios do caso; processo de pessoa em foro de outra comarca
    fica como "verificar homonímia" (não vale para "São Paulo", usado nos casos estaduais)

Saída: SQL (stdout) para rodar com execute_sql do conector Supabase, e um
resumo por nome (stderr). O SQL grava tjsp_consultas (upsert) e tjsp_processos
(sem duplicar nome+número) e recalcula tjsp_consultas.relevantes.

Regras (as mesmas da carga inicial de 29/09/2026):
  - pessoa: busca por nome exato; se não houver resultado, busca pelo nome
    parcial e aceita só partes com o mesmo primeiro nome e todos os termos na
    mesma ordem (confiança "verificar homonímia");
  - empresa: busca parcial, parte deve conter o nome consultado;
  - exclui vítima, testemunha, ofendido e perito ("Interessado" é mantido: em ações penais e de improbidade o réu às vezes aparece assim);
  - exclui ações de consumo (ex.: ação civil pública sobre contratos de consumo);
  - "fraude" isolada (ex.: estelionato) não basta: precisa haver ligação com licitação ou administração;
  - só classes/assuntos de interesse público (improbidade, ação civil pública,
    ação popular, crimes contra a administração, organização criminosa,
    lavagem, licitações, eleitoral, prisões e medidas investigativas);
  - processo criminal sem ligação com administração pública só fica se a
    confiança for "alta" ou se a distribuição estiver a até 5 dias de um fato
    da base;
  - confiança "alta": empresa, ou pessoa com 3+ termos significativos achada
    pelo nome exato; demais casos: "verificar homonímia";
  - intervalo de 1,2 s entre requisições; até 8 páginas (200 processos) por nome.
"""
import datetime, html as H, http.cookiejar, json, re, sys, time, unicodedata, urllib.parse, urllib.request

BASE = 'https://esaj.tjsp.jus.br'
REL = re.compile(r'mandado de prisao|prisao temporaria|prisao preventiva|busca e apreensao criminal|medidas investigatorias|'
                 r'interceptacao|quebra de sigilo|improbidade|acao civil publica|acao popular|administracao publica|peculato|corrup|'
                 r'concuss|prevarica|organizacao criminosa|organizacoes criminosas|lavagem|ocultacao de bens|licita|fraude (a|em|na|no|de) licita|'
                 r'crimes? de responsabilidade|eleitoral|dano ao erario|enriquecimento ilicito|principios administrativos|'
                 r'ordem tributaria|trafico|associacao para|abuso de poder|desvio|falsidade ideologica|advocacia administrativa|'
                 r'trafico de influencia|patrimonio publico|responsabilidade fiscal|contratos administrativos')
ADMIN = re.compile(r'improbidade|acao civil publica|acao popular|administra|peculato|corrup|concuss|prevarica|licita|dano ao erario|'
                   r'enriquecimento|principios administrativos|ordem tributaria|lavagem|organizac|eleitoral|responsabilidade|desvio|'
                   r'patrimonio publico|contratos administrativos|advocacia administrativa|falsidade ideologica|trafico de influencia')
PAPEL_EXCLUIDO = re.compile(r'vitima|testemunha|ofendid|perito')
ASSUNTO_EXCLUIDO = re.compile(r'consumo|consumidor')
HONORIFICO = re.compile(r'^(sra?|exm[ao]|dra?|ilm[ao])\.?\s+', re.I)
PARTICULAS = {'da', 'de', 'do', 'das', 'dos', 'e'}

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36')]

def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()).strip()

def termos(s):
    return [{'jr': 'junior'}.get(t, t) for t in re.findall(r'[a-z0-9]+', norm(s)) if t not in PARTICULAS]

def txt(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()

def fetch(url):
    erro = None
    for t in range(4):
        try:
            r = op.open(url, timeout=60)
            return r.geturl(), r.read().decode('utf-8', 'ignore')
        except Exception as e:
            erro = e
            time.sleep(6 * (t + 1))
    raise erro

def url_busca(nome, completo):
    return BASE + '/cpopg/search.do?' + urllib.parse.urlencode({
        'conversationId': '', 'cbPesquisa': 'NMPARTE', 'dadosConsulta.valorConsulta': nome,
        'chNmCompleto': 'true' if completo else 'false', 'cdForo': '-1'})

def parse_lista(s):
    out, foro = [], ''
    for m in re.finditer(r'<h2 class="unj-subtitle[^"]*foroDosProcessos">(.*?)</h2>|<div id="divProcesso(\w+)"(.*?)</li>', s, re.S):
        if m.group(1):
            foro = txt(m.group(1)); continue
        b = m.group(3)
        a = re.search(r'href="(/cpopg/show\.do\?processo\.codigo=(\w+)&processo\.foro=(\d+))[^"]*"[^>]*>\s*([\d\.\-]+)', b)
        if not a:
            continue
        g = lambda c: (lambda x: txt(x.group(1)) if x else '')(re.search(r'class="' + c + r'"[^>]*>(.*?)</(?:div|label)>', b, re.S))
        out.append(dict(codigo=a.group(2), foro_cod=a.group(3), numero=a.group(4),
                        participacao=g('unj-label tipoDeParticipacao').rstrip(':'), nome_parte=g('unj-base-alt nomeParte'),
                        classe=g('classeProcesso'), assunto=g('assuntoPrincipalProcesso'),
                        distribuicao=g('dataLocalDistribuicaoProcesso'), foro=foro))
    return out

def parse_detalhe(s, url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    g = lambda i: (lambda x: txt(x.group(1)) if x else '')(re.search(r'id="' + i + r'"[^>]*>(.*?)</(?:span|div)>', s, re.S))
    base = dict(codigo=q.get('processo.codigo', [''])[0], foro_cod=q.get('processo.foro', [''])[0], numero=g('numeroProcesso'),
                classe=g('classeProcesso'), assunto=g('assuntoProcesso'), foro=g('foroProcesso'),
                distribuicao=(g('dataHoraDistribuicaoProcesso') + ' - ' + g('varaProcesso')).strip(' -'))
    itens = []
    for m in re.finditer(r'<tr class="fundoClaro"[^>]*>(.*?)</tr>', s, re.S):
        c = re.findall(r'<td[^>]*>(.*?)</td>', m.group(1), re.S)
        if len(c) >= 2:
            d = dict(base); d.update(participacao=txt(c[0]), nome_parte=txt(c[1]).split(' Advogad')[0].strip()); itens.append(d)
    return itens

def buscar(nome, completo):
    url = url_busca(nome, completo)
    u, s = fetch(url)
    if '/show.do' in u:
        return 1, parse_detalhe(s, u), 'ok'
    m = re.search(r'(\d[\d\.]*)\s+Processos? encontrados', s)
    if not m:
        if re.search(r'muitos processos', s, re.I):
            return None, [], 'nome muito comum: o TJSP pede refinamento'
        return 0, [], 'sem resultados'
    total = int(m.group(1).replace('.', ''))
    itens, pag = parse_lista(s), 1
    while len(itens) < total and pag < 8:
        pag += 1; time.sleep(1.2)
        _, s2 = fetch(url + '&paginaConsulta=%d' % pag)
        novos = parse_lista(s2)
        if not novos:
            break
        itens += novos
    return total, itens, ('ok' if len(itens) >= total else 'parcial (%d de %d verificados)' % (len(itens), total))

def casa_parcial(alvo, parte):
    q = termos(alvo)
    for seg in re.split(r'\s+-\s+', parte):
        t = termos(HONORIFICO.sub('', seg.strip()))
        if not t or t[0] != q[0]:
            continue
        i = 0
        for x in t:
            if i < len(q) and x == q[i]:
                i += 1
        if i == len(q):
            return True
    return False

def data_de(s):
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', s or '')
    return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None

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
    q = termos(nome)
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
        conf = 'alta' if (emp or (len(q) >= 3 and not parcial)) else 'verificar homonímia'
        if conf != 'alta' and not ADMIN.search(assunto):
            d = data_de(it['distribuicao'])
            if not (d and any(abs((d - x).days) <= 5 for x in datas)):
                continue
        muns = [norm(m) for m in item.get('municipios') or [] if m and norm(m) != 'sao paulo']
        if conf == 'alta' and not emp and muns and not any(m in norm(it['foro']) for m in muns):
            conf = 'verificar homonímia'   # foro diferente do município do caso
        if it['numero'] in vistos: continue
        vistos.add(it['numero'])
        it.update(confianca=conf, link=f"{BASE}/cpopg/show.do?processo.codigo={it['codigo']}&processo.foro={it['foro_cod']}&processo.numero={it['numero']}")
        procs.append(it)
    return dict(nome=nome, tipo=tipo, registros=item.get('registros') or [], total=total, status=status,
                link_busca=url_busca(nome, completo=not emp)), procs

def q(v):
    if v is None: return 'null'
    return "'" + str(v).replace("'", "''") + "'"

def arr(v):
    return "array[" + ",".join(q(x) for x in v) + "]::text[]" if v else "'{}'::text[]"

if __name__ == '__main__':
    nomes = json.load(open(sys.argv[1], encoding='utf-8'))
    sql = ['begin;']
    for i, item in enumerate(nomes):
        try:
            c, procs = consultar(item)
        except Exception as e:
            c, procs = dict(nome=item['nome'], tipo=item['tipo'], registros=item.get('registros') or [], total=None,
                            status='erro: ' + str(e)[:80], link_busca=url_busca(item['nome'], item['tipo'] != 'empresa')), []
        print(f"{c['nome']}: {c['status']} | {len(procs)} processo(s) listado(s)", file=sys.stderr)
        sql.append(
            "insert into tjsp_consultas (nome,tipo,registros,total_resultados,relevantes,status,link_busca,consultado_em) values "
            f"({q(c['nome'])},{q(c['tipo'])},{arr(c['registros'])},{q(c['total'])}::int,{len(procs)},{q(c['status'])},{q(c['link_busca'])},current_date) "
            "on conflict (nome,tipo) do update set registros=(select array(select distinct unnest(tjsp_consultas.registros || excluded.registros))), "
            "total_resultados=excluded.total_resultados, status=excluded.status, link_busca=excluded.link_busca, consultado_em=current_date;")
        for p in procs:
            sql.append(
                "insert into tjsp_processos (nome_consultado,tipo,registros,numero,codigo,foro_cod,link,classe,assunto,participacao,nome_parte,foro,distribuicao,confianca) values "
                f"({q(c['nome'])},{q(c['tipo'])},{arr(c['registros'])},{q(p['numero'])},{q(p['codigo'])},{q(p['foro_cod'])},{q(p['link'])},"
                f"{q(p['classe'])},{q(p['assunto'])},{q(p['participacao'])},{q(p['nome_parte'])},{q(p['foro'])},{q(p['distribuicao'])},{q(p['confianca'])}) "
                "on conflict (nome_consultado,numero) do nothing;")
        if i < len(nomes) - 1:
            time.sleep(1.2)
    sql.append("update tjsp_consultas c set relevantes=(select count(*) from tjsp_processos p where p.nome_consultado=c.nome) "
               "where c.nome in (" + ",".join(q(n['nome']) for n in nomes) + ");")
    sql.append('commit;')
    print('\n'.join(sql))
