#!/usr/bin/env python3
"""Empresas sancionadas (CEIS e CNEP, Portal da Transparência/CGU) cruzadas com os
contratos de órgãos paulistas publicados no PNCP (Portal Nacional de Contratações Públicas).

Uso:
  python3 sancoes_pncp.py pasta_saida/ [empresas_base.json]
Gera em pasta_saida/: sancoes.json (sanções de interesse), contratos.json (contratos
assinados durante a vigência de uma sanção) e sancoes.sql (carga no Supabase).
empresas_base.json (opcional): [{"nome": "...", "registros": [...]}] — empresas citadas
na base, cruzadas pelo nome com os sancionados.

Regras:
  - só pessoas jurídicas (o CPF de pessoa física nunca é gravado);
  - sanções de interesse: vigentes em 2023 ou depois (data final vazia ou >= 01/01/2023) e
    (órgão sancionador em SP, ou abrangência "Todas as Esferas em todos os Poderes", ou
    declaração de inidoneidade, ou condenação por improbidade - Lei 8.429/92);
  - para cada CNPJ, busca no PNCP os contratos de órgãos com UF = SP (busca textual pelo
    CNPJ, campo fornecedor_ni conferido);
  - contrato "durante a sanção": data de assinatura entre o início e o fim da sanção;
  - "aplicavel": a abrangência alcança o órgão contratante (todas as esferas;
    inidoneidade; improbidade; ou mesmo ente: órgão municipal do mesmo município, órgão
    estadual de SP para sanção estadual de SP, órgão federal para sanção federal).
    Nos demais casos o contrato é listado como "sanção de outro ente" (informativo).
Um contrato listado é um sinal para verificação, não prova de irregularidade: a sanção
pode ter sido suspensa judicialmente, o registro pode ter erro e o contrato pode ser de
outro tipo (empenho, aditivo, ata).
"""
import csv, datetime, io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, zipfile

HOJE = datetime.date.today()
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/124'}

def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()).strip()

def dt(s):
    try:
        d, m, a = s.strip().split('/'); return datetime.date(int(a), int(m), int(d))
    except Exception:
        return None

def get(url, tent=5, bin=False):
    erro = None
    for t in range(tent):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
            return r if bin else json.loads(r)
        except Exception as e:
            erro = e; time.sleep(2 * (t + 1))
    raise erro

def baixar(cad):
    for k in range(10):
        d = (HOJE - datetime.timedelta(days=k)).strftime('%Y%m%d')
        try:
            z = get(f'https://portaldatransparencia.gov.br/download-de-dados/{cad}/{d}', tent=2, bin=True)
            zf = zipfile.ZipFile(io.BytesIO(z))
            nome = zf.namelist()[0]
            return d, list(csv.DictReader(io.TextIOWrapper(zf.open(nome), encoding='latin-1'), delimiter=';'))
        except Exception:
            continue
    raise RuntimeError('não foi possível baixar ' + cad)

RESTRITIVAS = ('Impedimento/proibição de contratar', 'Suspensão', 'Declaração de Inidoneidade')

def restritiva(cat):
    # só sanções que impedem contratar; multa, publicação da decisão e interdição de atividades ficam fora
    return cat.startswith(RESTRITIVAS) and not cat.startswith('Suspensão/Interdição')

def interesse(r):
    if not restritiva(r['CATEGORIA DA SANÇÃO']):
        return False
    fim = dt(r['DATA FINAL SANÇÃO'])
    if fim and fim < datetime.date(2023, 1, 1):
        return False
    ab, fund, cat = r['ABRAGÊNCIA DA SANÇÃO'], r['FUNDAMENTAÇÃO LEGAL'].upper(), r['CATEGORIA DA SANÇÃO'].upper()
    return (r['UF ÓRGÃO SANCIONADOR'] == 'SP' or ab == 'Todas as Esferas em todos os Poderes' or 'INIDONEIDADE' in cat
            or '8429' in fund or '8.429' in fund)

def ampla(s):
    # a abrangência declarada no CEIS/CNEP prevalece; sem informação, vale a natureza da sanção
    if s['abrangencia'] == 'Todas as Esferas em todos os Poderes':
        return True
    if s['abrangencia'] in ('', 'Sem Informação'):
        return 'inidoneidade' in norm(s['categoria']) or '8429' in s['fundamentacao'].replace('.', '')
    return False

def aplicavel(s, c):
    if ampla(s):
        return True
    esf, uf, org, ab = norm(s['esfera_orgao']), s['uf_orgao'], norm(s['orgao']), s['abrangencia']
    if esf == 'municipal':
        return uf == 'SP' and c['esfera'] == 'M' and bool(norm(c['municipio'])) and norm(c['municipio']) in org
    if esf == 'estadual':
        return uf == 'SP' and c['esfera'] == 'E' and ab != 'No órgão sancionador'
    if esf == 'federal':
        return c['esfera'] == 'F' and ab != 'No órgão sancionador'
    return False

def contratos(cnpj):
    out = []
    for pag in range(1, 6):
        d = get('https://pncp.gov.br/api/search/?' + urllib.parse.urlencode(
            dict(q=cnpj, tipos_documento='contrato', ufs='SP', pagina=pag, tam_pagina=100, ordenacao='-data')))
        its = d.get('items') or []
        out += [x for x in its if (x.get('fornecedor_ni') or '') == cnpj]
        if len(its) < 100:
            break
        time.sleep(0.2)
    return out

def q(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, (int, float)): return str(v)
    return "'" + str(v).replace("'", "''") + "'"

def arr(v):
    return "array[" + ",".join(q(x) for x in v) + "]::text[]" if v else "'{}'::text[]"

if __name__ == '__main__':
    pasta = sys.argv[1]; os.makedirs(pasta, exist_ok=True)
    base = json.load(open(sys.argv[2], encoding='utf-8')) if len(sys.argv) > 2 else []
    sancoes, ref = [], {}
    for cad in ('ceis', 'cnep'):
        d, rows = baixar(cad); ref[cad] = d
        for r in rows:
            if r['TIPO DE PESSOA'] != 'J':
                continue
            s = dict(cadastro=r['CADASTRO'], codigo=r['CÓDIGO DA SANÇÃO'], cnpj=r['CPF OU CNPJ DO SANCIONADO'],
                     nome=r['RAZÃO SOCIAL - CADASTRO RECEITA'] or r['NOME DO SANCIONADO'], nome_informado=r['NOME INFORMADO PELO ÓRGÃO SANCIONADOR'],
                     categoria=r['CATEGORIA DA SANÇÃO'], inicio=r['DATA INÍCIO SANÇÃO'], fim=r['DATA FINAL SANÇÃO'], publicacao=r['DATA PUBLICAÇÃO'],
                     processo=r['NÚMERO DO PROCESSO'], abrangencia=r['ABRAGÊNCIA DA SANÇÃO'], orgao=r['ÓRGÃO SANCIONADOR'],
                     uf_orgao=r['UF ÓRGÃO SANCIONADOR'], esfera_orgao=r['ESFERA ÓRGÃO SANCIONADOR'], fundamentacao=r['FUNDAMENTAÇÃO LEGAL'][:400],
                     valor_multa=r.get('VALOR DA MULTA', ''), interesse=interesse(r))
            sancoes.append(s)
    print(f'CEIS {ref["ceis"]}, CNEP {ref["cnep"]}: {len(sancoes)} sanções de PJ', file=sys.stderr)
    # empresas da base x sancionados (por nome)
    base_hit = {}
    idx = {}
    for s in sancoes:
        for n in {norm(s['nome']), norm(s['nome_informado'])}:
            if n: idx.setdefault(n, set()).add(s['cnpj'])
    for e in base:
        n = norm(re.sub(r'\([^)]*\)', '', e['nome']))
        n2 = re.sub(r'\b(ltda|eireli|s/?a|me|epp|s\.a\.)\b\.?', '', n).strip(' .-')
        if len(n2) < 6: continue
        for k, cs in idx.items():
            if k == n or (len(n2) >= 10 and k.startswith(n2)):
                for c in cs: base_hit.setdefault(c, set()).add(e['nome'])
    alvo = sorted({s['cnpj'] for s in sancoes if s['interesse']} | set(base_hit))
    print(f'{len(alvo)} CNPJs para consultar no PNCP ({len(base_hit)} ligados a empresas da base)', file=sys.stderr, flush=True)
    por_cnpj = {}
    for s in sancoes:
        por_cnpj.setdefault(s['cnpj'], []).append(s)
    achados, com_contrato = [], set()
    from concurrent.futures import ThreadPoolExecutor
    def tarefa(cnpj):
        try:
            return cnpj, contratos(cnpj), None
        except Exception as e:
            return cnpj, [], e
    feitos = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for cnpj, cs, err in ex.map(tarefa, alvo):
            feitos += 1
            if err:
                print(f'{cnpj}: erro {err}', file=sys.stderr)
            for x in cs:
                ass = (x.get('data_assinatura') or '')[:10]
                try: da = datetime.date.fromisoformat(ass)
                except Exception: continue
                c = dict(esfera=x.get('esfera_id'), municipio=x.get('municipio_nome') or '')
                for s in por_cnpj.get(cnpj, []):
                    if not restritiva(s['categoria']): continue
                    ini, fim = dt(s['inicio']), dt(s['fim'])
                    if ini and da >= ini and (not fim or da <= fim):
                        com_contrato.add(cnpj)
                        achados.append(dict(cnpj=cnpj, codigo_sancao=s['codigo'], cadastro=s['cadastro'], fornecedor=x.get('fornecedor_nome'),
                            orgao=x.get('orgao_nome'), orgao_cnpj=x.get('orgao_cnpj'), unidade=x.get('unidade_nome'), esfera=x.get('esfera_nome'),
                            municipio=x.get('municipio_nome'), codigo_ibge=x.get('codigo_ibge'), numero_controle=x.get('numero_controle_pncp'),
                            tipo=x.get('tipo_contrato_nome'), objeto=(x.get('description') or '')[:500], titulo=x.get('title'),
                            modalidade=x.get('modalidade_licitacao_nome'), amparo='; '.join(x.get('amparo_legal_nome') or []),
                            data_assinatura=ass, vigencia_fim=(x.get('data_fim_vigencia') or '')[:10], valor=x.get('valor_global'),
                            cancelado=bool(x.get('cancelado')), aplicavel=aplicavel(s, c),
                            link='https://pncp.gov.br/app' + (x.get('item_url') or '')))
            if feitos % 200 == 0:
                print(f'{feitos}/{len(alvo)} CNPJs, {len(achados)} contratos durante sanção', file=sys.stderr, flush=True)
    manter = {c for c in alvo if c in com_contrato or c in base_hit} | {s['cnpj'] for s in sancoes if s['uf_orgao'] == 'SP' and s['interesse']}
    sel = [dict(s, empresas_base=sorted(base_hit.get(s['cnpj'], []))) for s in sancoes if s['cnpj'] in manter]
    json.dump(sel, open(os.path.join(pasta, 'sancoes.json'), 'w'), ensure_ascii=False)
    json.dump(achados, open(os.path.join(pasta, 'contratos.json'), 'w'), ensure_ascii=False)
    sql = ['begin;']
    for s in sel:
        sql.append('insert into sancoes_empresas (cadastro,codigo,cnpj,nome,nome_informado,categoria,inicio,fim,publicacao,processo,abrangencia,orgao,uf_orgao,esfera_orgao,fundamentacao,valor_multa,empresas_base,referencia) values (' +
                   ','.join([q(s['cadastro']), q(s['codigo']), q(s['cnpj']), q(s['nome']), q(s['nome_informado']), q(s['categoria']), q(s['inicio']), q(s['fim']), q(s['publicacao']),
                             q(s['processo']), q(s['abrangencia']), q(s['orgao']), q(s['uf_orgao']), q(s['esfera_orgao']), q(s['fundamentacao']), q(s['valor_multa']),
                             arr(s['empresas_base']), q(ref[s['cadastro'].lower()] if s['cadastro'].lower() in ref else '')]) + ') on conflict (cadastro,codigo) do update set fim=excluded.fim, abrangencia=excluded.abrangencia, empresas_base=excluded.empresas_base, referencia=excluded.referencia, atualizado_em=current_date;')
    for a in achados:
        sql.append('insert into sancoes_contratos (cnpj,codigo_sancao,cadastro,fornecedor,orgao,orgao_cnpj,unidade,esfera,municipio,codigo_ibge,numero_controle,tipo,objeto,titulo,modalidade,amparo,data_assinatura,vigencia_fim,valor,cancelado,aplicavel,link) values (' +
                   ','.join(q(a[k]) for k in ['cnpj', 'codigo_sancao', 'cadastro', 'fornecedor', 'orgao', 'orgao_cnpj', 'unidade', 'esfera', 'municipio', 'codigo_ibge', 'numero_controle',
                                              'tipo', 'objeto', 'titulo', 'modalidade', 'amparo', 'data_assinatura', 'vigencia_fim', 'valor', 'cancelado', 'aplicavel', 'link']) +
                   ') on conflict (numero_controle,codigo_sancao) do update set aplicavel=excluded.aplicavel, cancelado=excluded.cancelado, valor=excluded.valor, atualizado_em=current_date;')
    sql.append('commit;')
    open(os.path.join(pasta, 'sancoes.sql'), 'w').write('\n'.join(sql))
    print(f'fim: {len(sel)} sanções gravadas, {len(achados)} contratos durante sanção ({sum(a["aplicavel"] for a in achados)} com abrangência aplicável)', file=sys.stderr)
