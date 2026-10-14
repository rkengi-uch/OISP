#!/usr/bin/env python3
"""Consulta nomes no CNIA do CNJ (Cadastro Nacional de Condenações Cíveis por Ato de
Improbidade Administrativa e Inelegibilidade) e gera o SQL para o Supabase
(tabelas cnia_consultas e cnia_condenacoes).

Fonte: https://www.cnj.jus.br/improbidade_adm/consultar_requerido.php (consulta pública
por nome, sem captcha). O cadastro só recebe condenações com trânsito em julgado ou
decisão de órgão colegiado (Lei 8.429/92 e LC 64/90).

Uso:
  python3 consultar_cnia.py nomes.json > cnia.sql
nomes.json: [{"nome": "...", "tipo": "pessoa"|"empresa", "origem": ["registros"], "registros": ["R201"], "municipios": ["Diadema"]}]

Regras:
  - pessoa: só aceita resultado com o nome idêntico (sem acentos e maiúsculas);
    empresa: o nome do CNIA deve conter o nome consultado;
  - confiança "alta": pessoa com 3+ termos significativos (ou empresa), condenação
    no TJSP, TRF3, STJ ou STF e, se houver município do caso, comarca igual a um deles
    (ou comarca não informada); nos demais casos, "verificar homonímia";
  - intervalo de 1 s entre requisições.
"""
import html as H, http.cookiejar, json, re, sys, time, unicodedata, urllib.parse, urllib.request

U = 'https://www.cnj.jus.br/improbidade_adm/'
PARTICULAS = {'da', 'de', 'do', 'das', 'dos', 'e'}
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) Chrome/124'), ('Referer', U + 'consultar_requerido.php')]

def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()).strip()

def termos(s):
    return [t for t in re.findall(r'[a-z0-9]+', norm(s)) if t not in PARTICULAS]

def txt(s):
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()

def abrir(url, data=None):
    erro = None
    for t in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'} if data else {})
            return op.open(req, timeout=60).read().decode('latin-1')
        except Exception as e:
            erro = e; time.sleep(5 * (t + 1))
    raise erro

def sajax(fn, args):
    data = [('rs', fn), ('rst', ''), ('rsrnd', str(int(time.time() * 1000)))] + [('rsargs[]', str(a)) for a in args]
    return abrir(U + 'consultar_requerido.php', urllib.parse.urlencode(data, encoding='latin-1', errors='replace').encode('latin-1'))

def pesquisar(nome, tipo):
    tp = 'J' if tipo == 'empresa' else 'F'
    if not cj:
        abrir(U + 'consultar_requerido.php')
    v = sajax('verificarCamposPesquisa', ['', '', '', '', nome.upper(), tp, ''])
    if 'ok' not in v[:60]:
        return None, [], 'erro: ' + txt(v)[:80]
    linhas, pag, total = [], 0, 0
    while pag < 6:
        r = sajax('pesquisarRequeridoGetTabela', ['', '', '', '', nome.upper(), tp, '', total, 'POSICAO_INICIAL_PAGINACAO_PHP%d' % (pag * 15), 'QUANTIDADE_REGISTROS_PAGINACAO15'])
        r = r.replace("\\'", "'").replace('\\"', '"').replace('\\n', ' ')
        if 'Nenhum Requerido encontrado' in r:
            break
        m = re.search(r'Número de registros:\s*(\d+)', r) or re.search(r'N\S*mero de registros:\s*(\d+)', r)
        total = int(m.group(1)) if m else total
        novos = re.findall(r"visualizar_condenacao\.php\?seq_condenacao=(\d+)'[^>]*>([^<]*)</a>.*?visualizar_processo\.php\?seq_processo=(\d+)'[^>]*>([^<]*)</a>", r, re.S)
        if not novos:
            break
        linhas += [dict(seq_condenacao=a, nome_cnia=txt(b), seq_processo=c, numero=txt(d)) for a, b, c, d in novos]
        if len(linhas) >= total:
            break
        pag += 1; time.sleep(1)
    return total, linhas, 'ok' if linhas else 'sem resultados'

def detalhe(seq):
    s = abrir(U + 'visualizar_condenacao.php?seq_condenacao=' + seq)
    i = s.find('Data do Cadastramento')
    t = s[i:]
    flat = txt(re.sub(r'<script.*?</script>', '', t, flags=re.S))
    def entre(a, b):
        m = re.search(re.escape(a) + r'\s*(.*?)\s*(?:' + b + ')', flat)
        return m.group(1).strip() if m else ''
    d = dict(data_cadastro=entre('Data do Cadastramento:', 'DADOS'), esfera=entre('Esfera:', 'Tribunal|Justiça|Superior|Supremo'),
             tribunal=entre('Tribunal de Justiça Estadual:', r'\d+º Grau|Comarca') or entre('Tribunal Regional Federal:', r'\d+º Grau|Seção|Subseção') or
             entre('Tribunal:', r'\d+º Grau|Comarca'),
             grau=(re.search(r'(\d+º Grau[^:]*):\s*([^:]*?)(?:Comarca|Seção|Varas|Gabinete|DADOS)', flat) or [None, '', ''])[2].strip() if re.search(r'\d+º Grau', flat) else '',
             comarca=entre('Comarca:', 'Varas|DADOS'), vara=entre('Varas e Juizados Estaduais:', 'DADOS') or entre('Varas Federais:', 'DADOS'),
             numero=entre('Número do Processo:', 'Esfera'))
    if not d['tribunal']:
        m = re.search(r'(Superior Tribunal de Justiça|Supremo Tribunal Federal|Tribunal Regional Federal da \d+ª Região|Tribunal de Justiça [^:]*?)(?:\s+\d+º Grau|\s+Comarca|\s+DADOS|$)', flat)
        d['tribunal'] = m.group(1) if m else ''
    m = re.search(r'<td>([^<]*?)\s*</td>\s*<td>(Ativo|Inativo|[^<]{0,20})</td>', t)
    d['situacao_pessoa'] = txt(m.group(2)) if m else ''
    tj = re.search(r'name="tipo_pena"\s+checked=checked\s+value="(\w)"', t)
    d['tipo_julgamento'] = {'J': 'Trânsito em julgado', 'C': 'Órgão colegiado'}.get(tj.group(1) if tj else '', '')
    m = re.search(r"labelDataJulgColeg'>.*?</td>\s*<td[^>]*>\s*<span\s*>([^<]*)</span>", t, re.S)
    d['data_decisao'] = txt(m.group(1)) if m else ''
    penas = {}
    for tr in re.finditer(r'<tr([^>]*)>(.*?)</tr>', t, re.S):
        attrs, body = tr.group(1), tr.group(2)
        if 'display: none' in attrs or 'display:none' in attrs:
            continue
        cells = re.findall(r'<td[^>]*>(.*?)</td>', body, re.S)
        if len(cells) < 2:
            continue
        rot, val = txt(cells[0]), txt(cells[1])
        if rot and val.startswith('SIM'):
            penas[rot] = val
    def tem(p):
        return any(re.search(p, norm(k)) for k in penas)
    def valor(p):
        for k, v in penas.items():
            if re.search(p, norm(k)):
                m = re.search(r'R\$\s*([\d\.,]+)', v); return m.group(1) if m else 'sim'
        return ''
    d.update(ressarcimento=valor('ressarcimento'), multa=valor('multa'), perda_bens=valor('perda de bens'),
             perda_cargo=tem('perda de emprego|perda do cargo|funcao publica'), suspensao_direitos=tem('suspensao dos direitos'),
             inelegibilidade=tem('inelegibilidade'), proibicao_contratar=tem('proibicao de contratar'),
             pena_privativa=tem('privativa'),
             penas='; '.join(re.sub(r'\?$', '', k) + (': ' + v[3:].strip() if len(v) > 3 else '') for k, v in penas.items()))
    return d

def eh_sp(tribunal):
    n = norm(tribunal)
    return 'sao paulo' in n or '3' in n and 'regional federal' in n or 'superior tribunal' in n or 'supremo' in n

def consultar(item):
    nome, tipo = item['nome'], item['tipo']
    emp = tipo == 'empresa'
    total, linhas, status = pesquisar(nome, tipo)
    q = termos(nome)
    muns = [norm(m) for m in item.get('municipios') or [] if m and 'governo do estado' not in norm(m)]
    out = []
    for l in linhas:
        if emp:
            if norm(nome) not in norm(l['nome_cnia']): continue
        elif norm(l['nome_cnia']) != norm(nome):
            continue
        time.sleep(1)
        d = detalhe(l['seq_condenacao'])
        conf = 'alta' if ((emp or len(q) >= 3) and eh_sp(d['tribunal'] + ' ' + d['grau'])) else 'verificar homonímia'
        if conf == 'alta' and not emp and muns and d['comarca'] and not any(m == norm(d['comarca']) or m in norm(d['comarca']) for m in muns):
            if not (norm(d['comarca']) == 'sao paulo' and 'sao paulo' in muns):
                conf = 'verificar homonímia'
        d.update(l, confianca=conf, link_condenacao=U + 'visualizar_condenacao.php?seq_condenacao=' + l['seq_condenacao'],
                 link_processo=U + 'visualizar_processo.php?seq_processo=' + l['seq_processo'])
        out.append(d)
    return dict(nome=nome, tipo=tipo, total=total, status=status), out

def q(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    return "'" + str(v).replace("'", "''") + "'"

def arr(v):
    return "array[" + ",".join(q(x) for x in v) + "]::text[]" if v else "'{}'::text[]"

if __name__ == '__main__':
    nomes = json.load(open(sys.argv[1], encoding='utf-8'))
    if len(sys.argv) > 3:   # fatia: ini fim (para rodar em paralelo)
        nomes = nomes[int(sys.argv[2]):int(sys.argv[3])]
    sql = []
    print('begin;', flush=True)
    for i, item in enumerate(nomes):
        try:
            c, conds = consultar(item)
        except Exception as e:
            c, conds = dict(nome=item['nome'], tipo=item['tipo'], total=None, status='erro: ' + str(e)[:80]), []
        print(f"{c['nome']}: {c['status']} | {len(conds)} condenação(ões) com o mesmo nome", file=sys.stderr, flush=True)
        o, r, m = item.get('origem') or [], item.get('registros') or [], item.get('municipios') or []
        sql.append("insert into cnia_consultas (nome,tipo,origem,registros,municipios,total,relevantes,status,consultado_em) values "
                   f"({q(c['nome'])},{q(c['tipo'])},{arr(o)},{arr(r)},{arr(m)},{q(c['total'])}::int,{len(conds)},{q(c['status'])},current_date) "
                   "on conflict (nome,tipo) do update set origem=excluded.origem, registros=excluded.registros, municipios=excluded.municipios, "
                   "total=excluded.total, relevantes=excluded.relevantes, status=excluded.status, consultado_em=current_date;")
        for d in conds:
            cols = ['nome_consultado', 'tipo', 'origem', 'registros', 'nome_cnia', 'seq_condenacao', 'seq_processo', 'numero_processo', 'esfera', 'tribunal', 'grau',
                    'comarca', 'vara', 'tipo_julgamento', 'data_decisao', 'data_cadastro', 'situacao_pessoa', 'ressarcimento', 'multa', 'perda_bens', 'perda_cargo',
                    'suspensao_direitos', 'inelegibilidade', 'proibicao_contratar', 'pena_privativa', 'penas', 'link_condenacao', 'link_processo', 'confianca']
            vals = [q(c['nome']), q(c['tipo']), arr(o), arr(r), q(d['nome_cnia']), q(d['seq_condenacao']), q(d['seq_processo']), q(d['numero'] or d.get('numero')),
                    q(d['esfera']), q(d['tribunal']), q(d['grau']), q(d['comarca']), q(d['vara']), q(d['tipo_julgamento']), q(d['data_decisao']), q(d['data_cadastro']),
                    q(d['situacao_pessoa']), q(d['ressarcimento']), q(d['multa']), q(d['perda_bens']), q(d['perda_cargo']), q(d['suspensao_direitos']),
                    q(d['inelegibilidade']), q(d['proibicao_contratar']), q(d['pena_privativa']), q(d['penas']), q(d['link_condenacao']), q(d['link_processo']), q(d['confianca'])]
            sql.append(f"insert into cnia_condenacoes ({','.join(cols)}) values ({','.join(vals)}) on conflict (nome_consultado,seq_condenacao) do update set "
                       "confianca=excluded.confianca, penas=excluded.penas, consultado_em=current_date;")
        print('\n'.join(sql), flush=True); sql = []
        if i < len(nomes) - 1:
            time.sleep(1)
    print('commit;', flush=True)
