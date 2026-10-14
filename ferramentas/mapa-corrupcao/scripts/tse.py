#!/usr/bin/env python3
"""Dados abertos do TSE (eleições municipais de 2020 e 2024, SP) cruzados com o Observatório.

Arquivos (https://dadosabertos.tse.jus.br, CDN cdn.tse.jus.br/estatistica/sead/odsele/):
  consulta_cand_AAAA.zip, consulta_cand_complementar_2024.zip, motivo_cassacao_AAAA.zip,
  bem_candidato_AAAA.zip (extraia os *_SP.csv) e, da prestação de contas de candidatos de 2024
  (arquivo de 1,3 GB: extraia só os CSVs de SP com remotezip), receitas_candidatos_2024_SP.csv e
  despesas_contratadas_candidatos_2024_SP.csv.

Uso:
  python3 tse.py pasta_tse/ cache_qsa/ saida/
  (cache_qsa/ = cache do qsa.py; os dígitos centrais do CPF mascarado dos sócios são usados só em
  memória, para confirmar a correspondência com doadores e candidatos.)

Saídas (tabelas do Supabase):
  tse_candidaturas.json  eleitos de 2024; candidaturas de 2020 e 2024 indeferidas por
                         inelegibilidade da LC 64/90 (alterada pela Lei da Ficha Limpa, LC 135/2010);
                         e candidaturas com nome e município iguais aos de pessoas do cadastro.
                         Inclui o total de bens declarados (e o da eleição anterior, quando a mesma
                         pessoa concorreu: ligação pelo título de eleitor, que não é gravado).
  tse_doacoes.json       doações de pessoas físicas a eleitos de 2024 em que o doador é sócio de
                         empresa/entidade do Observatório (nome igual E dígitos centrais do CPF iguais).
  tse_fornecedores.json  despesas de campanha de eleitos de 2024 contratadas com empresa do
                         Observatório (CNPJ idêntico).
  relacoes_societarias.json sócios (QSA) que coincidem com pessoas do cadastro ou eleitos de 2024.

Regras: CPF e título de eleitor nunca são gravados; empresas não podem doar desde 2015 (ADI 4650),
por isso o cruzamento de doações passa pelos sócios; coincidência de nome sem CPF é sempre
"verificar homonímia"; doação declarada é legal e não indica irregularidade por si só.
"""
import csv, json, os, re, sys, unicodedata, urllib.request, collections

SUPABASE = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/'
CHAVE = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
csv.field_size_limit(10 ** 8)
ELEICAO = {'2024': '2045202024', '2020': '2030402020'}

def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', re.sub(r'\s*\([^)]*\)', '', s)).strip()

def ler(tabela, select):
    out, ini = [], 0
    while True:
        r = urllib.request.Request(f'{SUPABASE}{tabela}?select={select}', headers={'apikey': CHAVE, 'Range': f'{ini}-{ini+999}'})
        d = json.load(urllib.request.urlopen(r, timeout=120)); out += d
        if len(d) < 1000: return out
        ini += 1000

def rd(p):
    return csv.DictReader(open(p, encoding='latin1'), delimiter=';')

def valor(s):
    try: return float((s or '0').replace('.', '').replace(',', '.')) if ',' in (s or '') else float(s or 0)
    except ValueError: return 0.0

def miolo(cpf):
    # CPF completo (TSE) -> 6 dígitos centrais; CPF mascarado da Receita ("***123456**") -> os 6 visíveis
    d = re.sub(r'\D', '', cpf or '')
    if len(d) == 11: return d[3:9]
    if len(d) == 6 and d != '000000': return d
    return None

def titulo(s):
    return s.title().replace(' Da ', ' da ').replace(' De ', ' de ').replace(' Do ', ' do ').replace(' Das ', ' das ').replace(' Dos ', ' dos ').replace(' E ', ' e ')

def link_cand(ano, sq, ue):
    return f'https://divulgacandcontas.tse.jus.br/divulga/#/candidato/SUDESTE/SP/{ELEICAO[ano]}/{sq}/{ano}/{ue}'

def main(pasta, cache, saida):
    os.makedirs(saida, exist_ok=True)
    P = lambda f: os.path.join(pasta, f)
    MUN = {norm(m['nome']): (m['nome'], m['gi']) for m in ler('municipios', 'gi,nome')}
    MUN.update({'embu': MUN.get('embu das artes'), 'moji mirim': MUN.get('mogi mirim'), 'moji guacu': MUN.get('mogi guacu')})
    def mun(nm):
        return MUN.get(norm(nm)) or (titulo(nm), None)

    # --- candidaturas
    cand = {}
    for ano in ('2020', '2024'):
        comp = {r['SQ_CANDIDATO']: r for r in rd(P('consulta_cand_complementar_2024_SP.csv'))} if ano == '2024' else {}
        mot = collections.defaultdict(list)
        for r in rd(P(f'motivo_cassacao_{ano}_SP.csv')):
            mot[r['SQ_CANDIDATO']].append(r['DS_MOTIVO'].strip())
        for r in rd(P(f'consulta_cand_{ano}_SP.csv')):
            if r['TP_ABRANGENCIA'] != 'MUNICIPAL': continue
            c = comp.get(r['SQ_CANDIDATO'], {})
            sit = c.get('DS_SITUACAO_CANDIDATO_TOT') or ''
            if sit in ('', '#NULO'): sit = c.get('DS_SITUACAO_JULGAMENTO') or r['DS_SITUACAO_CANDIDATURA']
            ms = mot.get(r['SQ_CANDIDATO'], [])
            ficha = any(m.startswith(('Inelegibilidade infraconstitucional', 'Ficha limpa')) for m in ms)
            indef = sit.startswith('INDEFERIDO') or r['DS_SITUACAO_CANDIDATURA'] == 'INAPTO'
            nome_m, gi = mun(r['NM_UE'])
            cand[(ano, r['SQ_CANDIDATO'])] = dict(
                ano=int(ano), sq=r['SQ_CANDIDATO'], eleicao=r['DS_ELEICAO'], municipio=nome_m, gi=gi, ue=r['SG_UE'], cargo=titulo(r['DS_CARGO']),
                nome=titulo(r['NM_CANDIDATO']), nome_urna=r['NM_URNA_CANDIDATO'], partido=r['SG_PARTIDO'], numero=r['NR_CANDIDATO'],
                situacao=sit.capitalize() if sit else None, resultado=r['DS_SIT_TOT_TURNO'] if r['DS_SIT_TOT_TURNO'] != '#NULO' else None,
                eleito=r['DS_SIT_TOT_TURNO'].startswith('ELEITO'), motivos=sorted(set(ms)), ficha_limpa=ficha and indef,
                processo=(c.get('NR_PROCESSO') or None) if ano == '2024' else None, link=link_cand(ano, r['SQ_CANDIDATO'], r['SG_UE']),
                _tit=r['NR_TITULO_ELEITORAL_CANDIDATO'], _cpf=miolo(r['NR_CPF_CANDIDATO']), _k=norm(r['NM_CANDIDATO']))
    # bens
    for ano in ('2020', '2024'):
        for r in rd(P(f'bem_candidato_{ano}_SP.csv')):
            c = cand.get((ano, r['SQ_CANDIDATO']))
            if c:
                c['bens_total'] = round(c.get('bens_total', 0) + valor(r['VR_BEM_CANDIDATO']), 2); c['bens_n'] = c.get('bens_n', 0) + 1
    por_tit = {}
    for (ano, sq), c in cand.items():
        if ano == '2020' and c['_tit']: por_tit[c['_tit']] = c
    for (ano, sq), c in cand.items():
        if ano == '2024':
            a = por_tit.get(c['_tit'])
            if a:
                c['anterior'] = dict(ano=2020, cargo=a['cargo'], municipio=a['municipio'], resultado=a['resultado'], bens_total=a.get('bens_total'), sq=a['sq'])
                c['_cpf'] = c['_cpf'] or a['_cpf']
    # pessoas do cadastro (nome + município)
    pes = ler('pessoas', 'chave,nome,municipios,chaves_alias,registros')
    pk = collections.defaultdict(list)
    for p in pes:
        for k in [p['chave']] + (p['chaves_alias'] or []):
            pk[k].append(p)
    for c in cand.values():
        hits = [p for p in pk.get(c['_k'], []) if norm(c['municipio']) in {norm(m) for m in (p['municipios'] or [])}]
        if hits:
            c['pessoa'] = hits[0]['chave']; c['registros'] = sorted({r for p in hits for r in (p['registros'] or [])})

    # --- QSA (cache do qsa.py)
    socios = collections.defaultdict(list)   # nome normalizado -> [(miolo, cnpj, qualif, razao)]
    empresas = {}
    for f in os.listdir(cache):
        d = json.load(open(os.path.join(cache, f)))
        if not d or d.get('_erro'): continue
        empresas[d['cnpj']] = d
        for s in d.get('qsa') or []:
            if s.get('identificador_de_socio') == 2:
                socios[norm(s.get('nome_socio'))].append((miolo(s.get('cnpj_cpf_do_socio')), d['cnpj'], s.get('qualificacao_socio'), s.get('data_entrada_sociedade')))
    origem = collections.defaultdict(set)
    for x in ler('sancoes_empresas', 'cnpj'): origem[x['cnpj']].add('CEIS/CNEP')
    for x in ler('tcu_listas', 'cnpj'):
        if x['cnpj']: origem[x['cnpj']].add('TCU')
    for x in ler('tce_impedimentos', 'cnpj,lista'):
        if x['cnpj']: origem[x['cnpj']].add('TCE-SP impedida de contratar' if x['lista'] == 'contrato' else 'TCE-SP impedida de receber repasses')
    for x in ler('qsa_empresas', 'cnpj,origens'):
        for o in (x['origens'] or []): origem[x['cnpj']].add(o)
    def emp(cnpj):
        e = empresas.get(cnpj, {})
        return dict(cnpj=cnpj, empresa=e.get('razao_social'), situacao_empresa=e.get('descricao_situacao_cadastral'),
                    municipio_empresa=titulo(e.get('municipio') or '') or None, uf_empresa=e.get('uf'), origens=sorted(origem.get(cnpj, [])))

    eleitos = {k: c for k, c in cand.items() if k[0] == '2024' and c['eleito']}
    # --- doações a eleitos de 2024
    doa = collections.defaultdict(lambda: dict(valor=0.0, n=0, datas=set()))
    for r in rd(P('receitas_candidatos_2024_SP.csv')):
        c = eleitos.get(('2024', r['SQ_CANDIDATO']))
        if not c: continue
        cpf = re.sub(r'\D', '', r['NR_CPF_CNPJ_DOADOR'])
        if len(cpf) != 11: continue
        nm = norm(r['NM_DOADOR_RFB'] if r['NM_DOADOR_RFB'] not in ('', '#NULO') else r['NM_DOADOR'])
        for mi, cnpj, q, ent in socios.get(nm, []):
            if mi and mi == cpf[3:9]:
                k = (c['sq'], nm, cnpj)
                x = doa[k]; x['valor'] += valor(r['VR_RECEITA']); x['n'] += 1; x['datas'].add(r['DT_RECEITA'])
                x.update(cand=c, doador=titulo(r['NM_DOADOR_RFB'] if r['NM_DOADOR_RFB'] not in ('', '#NULO') else r['NM_DOADOR']), qualificacao=q,
                         proprio=(c['_k'] == nm), origem=r['DS_ORIGEM_RECEITA'])
    doacoes = []
    for (sq, nm, cnpj), x in doa.items():
        c = x['cand']
        doacoes.append(dict(sq_candidato=sq, candidato=c['nome'], nome_urna=c['nome_urna'], cargo=c['cargo'], partido=c['partido'], municipio=c['municipio'], gi=c['gi'],
                            doador=x['doador'], qualificacao_socio=x['qualificacao'], valor=round(x['valor'], 2), n_doacoes=x['n'],
                            datas=sorted(x['datas'], key=lambda d: d.split('/')[::-1]), autodoacao=x['proprio'], origem_receita=x['origem'],
                            confianca='nome e CPF parcial coincidem', link=c['link'], **emp(cnpj)))
    # --- fornecedores de campanha de eleitos de 2024
    forn = collections.defaultdict(lambda: dict(valor=0.0, n=0, desc=set()))
    for r in rd(P('despesas_contratadas_candidatos_2024_SP.csv')):
        c = eleitos.get(('2024', r['SQ_CANDIDATO']))
        cnpj = re.sub(r'\D', '', r['NR_CPF_CNPJ_FORNECEDOR'])
        if not c or len(cnpj) != 14 or cnpj not in origem: continue
        x = forn[(c['sq'], cnpj)]; x['valor'] += valor(r['VR_DESPESA_CONTRATADA']); x['n'] += 1
        x['desc'].add((r['DS_ORIGEM_DESPESA'] or '').strip()); x['cand'] = c; x['nome'] = r['NM_FORNECEDOR_RFB'] if r['NM_FORNECEDOR_RFB'] not in ('', '#NULO') else r['NM_FORNECEDOR']
    fornecedores = [dict(sq_candidato=sq, candidato=x['cand']['nome'], nome_urna=x['cand']['nome_urna'], cargo=x['cand']['cargo'], partido=x['cand']['partido'],
                         municipio=x['cand']['municipio'], gi=x['cand']['gi'], fornecedor=x['nome'], valor=round(x['valor'], 2), n_despesas=x['n'],
                         tipos_despesa=sorted(d for d in x['desc'] if d), link=x['cand']['link'], **emp(cnpj))
                    for (sq, cnpj), x in forn.items()]
    # --- relações societárias: sócio = pessoa do cadastro ou eleito de 2024
    rel = []
    pes_k = {}
    for p in pes:
        for k in [p['chave']] + (p['chaves_alias'] or []): pes_k.setdefault(k, p)
    cand_por_k = collections.defaultdict(list)
    for c in eleitos.values(): cand_por_k[c['_k']].append(c)
    for nm, lst in socios.items():
        p = pes_k.get(nm); cs = cand_por_k.get(nm, [])
        if not p and not cs: continue
        for mi, cnpj, q, ent in lst:
            e = emp(cnpj); me = norm(e['municipio_empresa'] or '')
            cs_ok = [c for c in cs if mi and c['_cpf'] and c['_cpf'] == mi]
            if cs_ok: conf = 'nome e CPF parcial coincidem (TSE)'
            elif (p and me in {norm(m) for m in (p['municipios'] or [])}) or any(norm(c['municipio']) == me for c in cs): conf = 'nome e município coincidem: verificar homonímia'
            else: conf = 'só o nome coincide: verificar homonímia'
            alvo = cs_ok or [c for c in cs if norm(c['municipio']) == me] or cs
            rel.append(dict(nome_socio=titulo(nm), qualificacao=q, data_entrada=ent, pessoa=p['chave'] if p else None, pessoa_nome=p['nome'] if p else None,
                            registros=sorted(p['registros'] or []) if p else [], municipios_pessoa=sorted(p['municipios'] or []) if p else [],
                            eleito_2024=[dict(nome=c['nome'], urna=c['nome_urna'], cargo=c['cargo'], municipio=c['municipio'], partido=c['partido'], sq=c['sq']) for c in alvo][:3],
                            confianca=conf, **e))
    # candidaturas a gravar
    manter = [c for c in cand.values() if (c['ano'] == 2024 and c['eleito']) or c['ficha_limpa'] or c.get('pessoa')
              or c['sq'] in {d['sq_candidato'] for d in doacoes} | {f['sq_candidato'] for f in fornecedores}]
    out = [{k: v for k, v in c.items() if not k.startswith('_')} for c in manter]
    json.dump(out, open(os.path.join(saida, 'tse_candidaturas.json'), 'w'), ensure_ascii=False)
    json.dump(doacoes, open(os.path.join(saida, 'tse_doacoes.json'), 'w'), ensure_ascii=False)
    json.dump(fornecedores, open(os.path.join(saida, 'tse_fornecedores.json'), 'w'), ensure_ascii=False)
    json.dump(rel, open(os.path.join(saida, 'relacoes_societarias.json'), 'w'), ensure_ascii=False)
    fl = [c for c in out if c['ficha_limpa']]
    print(f"candidaturas gravadas: {len(out)} (eleitos 2024: {sum(1 for c in out if c['ano']==2024 and c['eleito'])}; "
          f"Ficha Limpa: {len(fl)} [2020 {sum(1 for c in fl if c['ano']==2020)}, 2024 {sum(1 for c in fl if c['ano']==2024)}]; "
          f"ligadas ao cadastro: {sum(1 for c in out if c.get('pessoa'))})", file=sys.stderr)
    print(f'doações de sócios a eleitos: {len(doacoes)} ({sum(d["valor"] for d in doacoes):,.2f}); fornecedores de campanha: {len(fornecedores)}; '
          f'relações societárias: {len(rel)} (CPF parcial {sum(1 for r in rel if r["confianca"].startswith("nome e CPF"))})', file=sys.stderr)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
