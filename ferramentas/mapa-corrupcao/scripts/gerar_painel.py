#!/usr/bin/env python3
"""Gera o painel do Mapa da Corrupção a partir do Supabase.

Uso: python3 gerar_painel.py <index.html do painel publicado> [saida.html] [--comparar] [--recortes recortes_novos.json]

Lê todas as tabelas pela API REST (chave publicável, só leitura), monta o
objeto DATA no formato que o painel espera e o substitui no HTML. Layout,
scripts e a tela de validação do painel ficam intactos.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import json, sys, urllib.request

SUPABASE_URL = 'https://pobqpofsieryoxzmaefb.supabase.co'
CHAVE = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'   # publicável: só leitura (RLS)

import unicodedata, re, time, urllib.error
def norm(t):
    return re.sub(r'\\s+', ' ', unicodedata.normalize('NFD', t or '').encode('ascii', 'ignore').decode().lower()).strip()

def ler(tabela, ordem):
    linhas, ini, passo = [], 0, 1000
    while True:
        req = urllib.request.Request(f'{SUPABASE_URL}/rest/v1/{tabela}?select=*&order={ordem}',
            headers={'apikey': CHAVE, 'Authorization': 'Bearer ' + CHAVE,
                     'Range-Unit': 'items', 'Range': f'{ini}-{ini+passo-1}'})
        # erro passageiro do Supabase (HTTP 5xx, conexão caída, tempo esgotado): até 6 tentativas com espera crescente
        for tent in range(6):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    lote = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code < 500 or tent == 5: raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
                if tent == 5: raise
            print(f'aviso: {tabela} (linhas {ini}+) falhou, nova tentativa {tent + 2}/6', file=sys.stderr)
            time.sleep(3 * 2 ** tent)
        linhas += lote
        if len(lote) < passo: return linhas
        ini += passo

def montar_data():
    D = {}
    R = []
    for x in ler('registros', 'id.asc'):
        o = {'id': x['id'], 'mun': x['municipio'], 'nome': x['nome'] or '', 'cargo': x['cargo'] or '',
             'desc': x['descricao'] or '', 'cond': x['condenacao'] or '', 'afast': x['afastamento'] or '',
             'tip': x['tipificacao'] or '', 'crimes': x['crimes_apurados'] or '', 'op': x['operacao'] or '',
             'orgao': x['orgao_investigativo'] or '', 'ano': x['ano'], 'data': x['data_evento'] or '',
             'medida': x['medida'] or '', 'situacao': x['situacao'] or '', 'empresa': x['empresa'] or '',
             'link': x['link'] or '', 'link2': x['link2'] or '', 'fonte': x['fonte'] or '',
             'cred': x['credibilidade'] or '', 'qtd': x['qtd'] if x['qtd'] is not None else 1, 'gi': x['gi'],
             'esfera': x['esfera'] or '', 'fase': x['fase'] or x['operacao'] or '', 'co': x['setor_co'] or '',
             'co_vinc': x['vinculo_co'] or '', 'nivel': x['nivel'] or '', 'orgest': x['orgao_estadual'] or ''}
        if x['status_validacao'] == 'Pendente' or x['data_coleta'] or x['validado_em']:
            o['val'] = x['status_validacao']
        if x['data_coleta']: o['coleta'] = x['data_coleta']
        if x['validado_em']: o['validado'] = x['validado_em']
        if x['historico'] is not None: o['hist'] = x['historico']
        R.append(o)
    D['R'] = R
    CIT = []
    for x in ler('citados_sem_agente', 'ordem.asc,id.asc'):
        o = {'mun': x['municipio'], 'op': x['operacao'] or '', 'ano': x['ano'], 'orgao': x['orgao'] or '',
             'obs': x['obs'] or '', 'link': x['link'] or '', 'gi': x['gi'], 'co': x['setor_co'] or '',
             'nivel': x['nivel'] or '', 'orgest': x['orgao_estadual'] or ''}
        if x['status_validacao'] == 'Pendente' or x['validado_em']: o['val'] = x['status_validacao']
        if x['validado_em']: o['validado'] = x['validado_em']
        CIT.append(o)
    D['CIT'] = CIT
    D['CO'] = [[x['gi'], x['municipio'], x['setores'] or [], x['origem'], x['vinculo'], x['operacao'],
                # manchete de notícia vai como citação da imprensa, nunca como afirmação do Observatório
                ('Manchete da imprensa: “' + (x['descricao'] or '').strip(' “”"') + '”') if str(x['origem'] or '').startswith('Notícia') and not str(x['descricao'] or '').startswith('Manchete') else x['descricao'],
                x['link'], x['ano'], x['cargos'],
                x['medidas'], x['orgao'], x['nivel']]
               for x in ler('crime_organizado', 'ordem.asc,id.asc')]
    OPL = {}
    for f in ler('operacao_fontes', 'operacao.asc,ordem.asc,id.asc'):
        OPL.setdefault(f['operacao'], []).append({'tipo': f['tipo'], 'fonte': f['fonte'], 'titulo': f['titulo'], 'url': f['url']})
    D['OPLINKS'] = OPL
    D['OPQ'] = {o['nome']: o['consulta'] for o in ler('operacoes', 'nome.asc') if o['consulta']}
    D['LOG'] = [{'data': l['data'], 'id': l['registro_id'], 'acao': l['acao'], 'campo': l['campo'],
                 'antes': l['antes'], 'depois': l['depois'], 'link': l['link']} for l in ler('log_atualizacoes', 'id.asc') if l.get('acao') != 'execucao_diaria']  # marca de controle da rotina não aparece no painel
    # só notícias com link ativo (ou ainda não verificado); inativos e indeterminados ficam fora do painel
    D['NEWS'] = [n['item'] for n in ler('noticias', 'ordem.asc,id.asc') if n.get('link_status') in (None, 'ativo') and not n.get('fora_do_escopo')]
    try:
        D['TJSP'] = {
            'consultas': [{'nome': c['nome'], 'tipo': c['tipo'], 'registros': c['registros'] or [], 'total': c['total_resultados'],
                           'relevantes': c['relevantes'], 'status': c['status'], 'busca': c['link_busca'], 'em': c['consultado_em']}
                          for c in ler('tjsp_consultas', 'nome.asc')],
            'processos': [{'nome': x['nome_consultado'], 'tipo': x['tipo'], 'registros': x['registros'] or [], 'numero': x['numero'],
                           'link': x['link'], 'classe': x['classe'], 'assunto': x['assunto'], 'papel': x['participacao'],
                           'parte': x['nome_parte'], 'foro': x['foro'], 'dist': x['distribuicao'], 'conf': x['confianca'],
                           'em': x['consultado_em']}
                          for x in ler('tjsp_processos', 'nome_consultado.asc,numero.asc,id.asc')]}
    except Exception:
        pass  # tabelas do TJSP indisponíveis
    try:
        import unicodedata as _u
        _n = lambda t: ' '.join(_u.normalize('NFD', t or '').encode('ascii', 'ignore').decode().upper().split())
        por_nome = {}
        for x in R:
            por_nome.setdefault(_n(x['nome']), []).append(x['id'])
        com_tj = {_n(p['nome']) for p in (D.get('TJSP') or {}).get('processos', [])}
        imp = [i for i in ler('tce_importacoes', 'id.desc') if i['status'] == 'importado'][:1]
        D['TCE'] = {
            'meta': ({'atualizacao': imp[0]['lista_atualizacao'], 'periodo': imp[0]['lista_periodo'], 'fonte': imp[0]['fonte_xlsx'],
                      'importado_em': imp[0]['executado_em'][:10], 'linhas': imp[0]['linhas'], 'pessoas': imp[0]['pessoas'],
                      'pagina': 'https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares'} if imp else {}),
            'itens': [{'resp': c['responsavel'], 'papel': c['papel'], 'grupo': c['grupo'], 'materia': c['materia'], 'proc': c['processo_tc'],
                       'origem': c['origem'], 'mun': c['municipio'], 'gi': c['gi'], 'nivel': c['nivel'], 'exerc': c['exercicio'],
                       'tj': c['transito_julgado'], 'ano_tj': int(c['transito_iso'][:4]) if c['transito_iso'] else None,
                       'base': por_nome.get(_n(c['responsavel']), []), 'tjsp': _n(c['responsavel']) in com_tj}
                      for c in ler('contas_irregulares_tce', 'responsavel.asc,id.asc')]}
    except Exception as e:
        print('aviso: contas irregulares do TCE não carregadas:', e, file=sys.stderr)
    try:
        imp = ler('tce_importacoes', 'executado_em.desc')
        itens = ler('contas_irregulares_tce', 'responsavel.asc,id.asc')
        consultados = {norm(c['nome']) for c in D.get('TJSP', {}).get('consultas', [])}
        por_nome = {}
        for r in D['R']:
            por_nome.setdefault(norm(r['nome']), []).append(r)
        T = []
        for x in itens:
            base = sorted({r['id'] for r in por_nome.get(norm(x['responsavel']), [])
                           if x['nivel'] == 'Estadual' or r['mun'] == x['municipio']})
            T.append({'resp': x['responsavel'], 'papel': x['papel'], 'grupo': x['grupo'], 'materia': x['materia'],
                      'proc': x['processo_tc'], 'origem': x['origem'], 'mun': x['municipio'], 'gi': x['gi'],
                      'nivel': x['nivel'], 'exerc': x['exercicio'], 'tj': x['transito_julgado'],
                      'ano_tj': int(x['transito_iso'][:4]) if x['transito_iso'] else None,
                      'base': base, 'tjsp': norm(x['responsavel']) in consultados})
        m = imp[0] if imp else {}
        D['TCE'] = {'meta': {'atualizacao': m.get('lista_atualizacao'), 'periodo': m.get('lista_periodo') or next((i['lista_periodo'] for i in imp if i.get('lista_periodo')), None) or next((x['lista_periodo'] for x in itens if x.get('lista_periodo')), None), 'fonte': m.get('fonte_xlsx'),
                             'importado_em': (m.get('executado_em') or '')[:10], 'linhas': len(T),
                             'pessoas': len({norm(t['resp']) for t in T}),
                             'pagina': 'https://www.tce.sp.gov.br/relacao-de-responsaveis-por-contas-julgadas-irregulares'},
                    'itens': T}
    except Exception as e:
        print('aviso: contas do TCE não lidas:', e, file=sys.stderr)
    try:
        D['PAR'] = [{'proc': x['processo'], 'ref': x['processo_ref'] or '', 'mun': x['municipio'], 'gi': x['gi'], 'exerc': x['exercicio'],
                     'pref': x['prefeitos'] or '', 'rel': x['relator'] or '', 'col': x['colegiado'] or '', 'sessao': x['data_sessao'] or '',
                     'pub': x['data_publicacao'], 'tipo': x['tipo'], 'sit': x['situacao'] or '', 'rev': x['reexame_rev'] or '',
                     'ementa': x['ementa'] or '', 'doe': x['link_doe'] or x['edicao_url'] or '', 'pdf': x['edicao_url'] or '', 'pag': x['pagina'], 'txt': x.get('texto') or ''}
                    for x in ler('pareceres_tce', 'id.asc') if x['resultado'] == 'desfavorável']
        _vistos = set(); _par = []
        for x in sorted(D['PAR'], key=lambda x: x['pub'].split('/')[::-1]):   # republicação: fica a primeira
            if x['proc'] not in _vistos: _vistos.add(x['proc']); _par.append(x)
        D['PAR'] = _par
    except Exception:
        pass  # tabela de pareceres indisponível
    try:
        D['BOL'] = [b['conteudo'] for b in ler('boletins', 'referencia.desc')]
    except Exception:
        pass  # tabela de boletins indisponível
    try:
        D['TCM'] = [{k: x.get(k) for k in ('tc','sigla','orgao','exercicio','objeto','natureza','decisao','situacao','data_julgamento','data_do','sessao','relator','ementa','acordao_url','processo_url','responsavel','responsavel_fonte')}
                    for x in ler('contas_tcmsp', 'exercicio.desc,sigla.asc,tc.asc')]
    except Exception:
        pass  # tabela do TCMSP indisponível
    try:   # TJSP 2º grau (cposg)
        D['TJ2'] = {'consultas': len(ler('tjsp2_consultas', 'nome.asc')),
                    'processos': [{'nome': x['nome_consultado'], 'tipo': x['tipo'], 'registros': x['registros'] or [], 'numero': x['numero'],
                                   'link': x['link'], 'area': x['area'] or '', 'classe': x['classe'] or '', 'assunto': x['assunto'] or '',
                                   'papel': x['participacao'] or '', 'parte': x['nome_parte'] or '', 'orgao': x['orgao_julgador'] or '',
                                   'receb': x['recebido_em'] or '', 'orig': bool(x['originaria']), 'conf': x['confianca']}
                                  for x in ler('tjsp2_processos', 'nome_consultado.asc,numero.asc,id.asc')]}
    except Exception as e:
        print('aviso: TJSP 2º grau não carregado:', e, file=sys.stderr)
    try:   # CNIA (CNJ)
        D['CNIA'] = {'consultas': len(ler('cnia_consultas', 'nome.asc')),
                     'itens': [{'nome': x['nome_consultado'], 'tipo': x['tipo'], 'origem': x['origem'] or [], 'registros': x['registros'] or [],
                                'ncnia': x['nome_cnia'], 'numero': x['numero_processo'], 'tribunal': x['tribunal'] or '', 'grau': x['grau'] or '',
                                'comarca': x['comarca'] or '', 'vara': x['vara'] or '', 'julg': x['tipo_julgamento'] or '', 'data': x['data_decisao'] or '',
                                'ress': x['ressarcimento'] or '', 'cargo': x['perda_cargo'], 'susp': x['suspensao_direitos'], 'ineleg': x['inelegibilidade'],
                                'proib': x['proibicao_contratar'], 'penas': x['penas'] or '', 'link': x['link_condenacao'], 'conf': x['confianca']}
                               for x in ler('cnia_condenacoes', 'nome_consultado.asc,id.asc')]}
    except Exception as e:
        print('aviso: CNIA não carregado:', e, file=sys.stderr)
    try:   # empresas sancionadas (CEIS/CNEP) x contratos no PNCP; vale só a carga mais recente
        emp = ler('sancoes_empresas', 'nome.asc,cadastro.asc,codigo.asc')
        con = ler('sancoes_contratos', 'data_assinatura.desc,id.asc')
        ult_e = max((x['atualizado_em'] for x in emp), default=None)
        ult_c = max((x['atualizado_em'] for x in con), default=None)
        con_todos = [x for x in con if x['atualizado_em'] == ult_c]
        try:
            from alcance import s51_sancao     # alcance pela Súmula 51 do TCE-SP (opção do painel)
        except ImportError:
            s51_sancao = lambda s, c, padrao: bool(padrao)
        por_cod = {x['codigo']: x for x in emp if x['atualizado_em'] == ult_e}
        for x in con_todos:
            sx = por_cod.get(x['codigo_sancao']); x['a51'] = s51_sancao(sx, x, x['aplicavel']) if sx else bool(x['aplicavel'])
        con = [x for x in con_todos if x['aplicavel'] or x['a51']]   # o painel mostra o que é aplicável por um dos dois critérios
        usados = {x['cnpj'] for x in con}
        emp = [x for x in emp if x['atualizado_em'] == ult_e and (x['cnpj'] in usados or x['empresas_base'])]
        ref = max((x['referencia'] or '' for x in emp), default='')
        D['SANC'] = {'ref': (ref[6:8] + '/' + ref[4:6] + '/' + ref[:4]) if len(ref) == 8 else '',
                     'outros': len(con_todos) - len(con), 'napl': sum(1 for x in con if x['aplicavel']), 'n51': sum(1 for x in con if x['a51']), 'n_sancoes': len([1 for x in ler('sancoes_empresas', 'cadastro.asc,codigo.asc') if x['atualizado_em'] == ult_e]),
                     'emp': [{'cad': x['cadastro'], 'cod': x['codigo'], 'cnpj': x['cnpj'], 'nome': x['nome'], 'cat': x['categoria'], 'ini': x['inicio'],
                              'fim': x['fim'], 'ab': x['abrangencia'], 'org': x['orgao'], 'uf': x['uf_orgao'], 'esf': x['esfera_orgao'],
                              'fund': (x['fundamentacao'] or '')[:160], 'proc': x['processo'], 'base': x['empresas_base'] or []} for x in emp],
                     'con': [{'cnpj': x['cnpj'], 'cod': x['codigo_sancao'], 'forn': x['fornecedor'], 'orgao': x['orgao'], 'mun': x['municipio'] or '',
                              'esf': x['esfera'] or '', 'num': x['numero_controle'], 'tipo': x['tipo'] or '', 'obj': (x['objeto'] or '')[:220],
                              'mod': x['modalidade'] or '', 'ass': x['data_assinatura'], 'fimv': x['vigencia_fim'] or '',
                              'valor': float(x['valor']) if x['valor'] is not None else None, 'canc': x['cancelado'], 'apl': x['aplicavel'],
                              'a51': x['a51'], 'link': x['link']} for x in con]}
    except Exception as e:
        print('aviso: sanções/PNCP não carregados:', e, file=sys.stderr)
    try:   # listas do TCU (responsáveis com cadastro em SP); por lista, vale a importação mais recente
        tu = ler('tcu_listas', 'lista.asc,nome.asc,id.asc')
        ult = {}
        for x in tu: ult[x['lista']] = max(ult.get(x['lista'], ''), x['importado_em'] or '')
        tu = [x for x in tu if (x['importado_em'] or '') == ult.get(x['lista'])]
        imp = max(ult.values(), default='')
        D['TCU'] = {'meta': {'importado': '/'.join(imp.split('-')[::-1]) if imp else '',
                             'listas': {k: len([1 for x in tu if x['lista'] == k]) for k in ult}},
                    'itens': [{'l': x['lista'], 'nome': x['nome'], 'tipo': x['tipo'], 'cnpj': x['cnpj'] or '', 'mun': x['municipio_painel'] or '',
                               'munr': (x['municipio'] or '').title(), 'gi': x['gi'], 'proc': x['processo'] or '', 'lproc': x['link_processo'] or '',
                               'ac': x['acordaos'] or '', 'lac': '' if (x['link_acordaos'] or '').endswith(re.sub(r'\D', '', x['processo'] or '') + '.PROC') else (x['link_acordaos'] or ''), 'dac': x['data_acordao'] or '', 'tj': x['transito'] or '',
                               'fim': x['data_final'] or '', 'base': x['base'] or []} for x in tu]}
    except Exception as e:
        print('aviso: listas do TCU não carregadas:', e, file=sys.stderr)
    try:   # agenda "O que acompanhar"
        D['AGENDA'] = [{'d': x['data'], 'p': x['precisao'], 'mun': x['municipio'] or '', 'gi': x['gi'], 't': x['titulo'], 'desc': x['descricao'] or '',
                        'esf': x['esfera'] or '', 'fonte': x['fonte'] or '', 'link': x['link'] or '', 'st': x['status'], 'reg': x['registros'] or []}
                       for x in ler('agenda', 'data.asc,id.asc')]
    except Exception as e:
        print('aviso: agenda não carregada:', e, file=sys.stderr)
    try:   # cadastro único de pessoas: só quem tem apelidos, outras grafias ou possível homônimo
        D['PES'] = [{'n': x['nome'], 'k': sorted(set([x['chave']] + (x['chaves_alias'] or []))), 'ap': x['apelidos'] or [], 'va': x['variantes'] or [],
                     'm': x['municipios'] or [], 'h': bool(x['possivel_homonimo'])}
                    for x in ler('pessoas', 'id.asc') if (x['apelidos'] or x['chaves_alias'] or x['possivel_homonimo'])]
    except Exception as e:
        print('aviso: cadastro de pessoas não carregado:', e, file=sys.stderr)
    br = lambda d: '/'.join(str(d)[:10].split('-')[::-1]) if d else ''
    try:   # impedimentos publicados pelo TCE-SP (+ contratos no PNCP durante o impedimento)
        it = ler('tce_impedimentos', 'lista.asc,apenada.asc,chave.asc'); ref = max((x['referencia'] for x in it if x.get('referencia')), default=None)
        it = [x for x in it if x.get('referencia') == ref]
        try:
            from alcance import s51_impedimento
        except ImportError:
            s51_impedimento = lambda c, nv, padrao: bool(padrao)
        nivel = {(x['orgao'], x['inicio']): x['nivel'] for x in it}
        ct = [x for x in ler('tce_impedimentos_contratos', 'data_assinatura.desc,chave.asc') if x.get('referencia') == ref and not x.get('cancelado')]
        for x in ct:
            nv = nivel.get((x['orgao_apenador'], x['inicio'])) or ('Estadual' if x['municipio_apenador'] == 'Governo do Estado de SP' else 'Municipal')
            x['a51'] = s51_impedimento(x, nv, x['aplicavel'])
        ct = [x for x in ct if x['aplicavel'] or x['a51']]
        D['IMP'] = {'ref': br(ref), 'n': {'c': sum(1 for x in it if x['lista'] == 'contrato'), 'r': sum(1 for x in it if x['lista'] == 'repasse')},
                    'napl': sum(1 for x in ct if x['aplicavel']), 'n51': sum(1 for x in ct if x['a51']),
                    'itens': [{'l': x['lista'][0], 'n': x['apenada'], 'c': x['cnpj'] or '', 'pf': x['pessoa'] == 'PF', 'o': x['orgao'], 'm': x['municipio'], 'gi': x['gi'],
                               'nv': x['nivel'], 'i': br(x['inicio']), 't': br(x['termino']), 'tr': br(x['transito']), 'tp': x['tipo'], 'al': x['alcance'],
                               'mo': x['motivo'] or '', 'p': x['processo'] or ''} for x in it],
                    'con': [{'c': x['cnpj'], 'n': x['apenada'], 'oa': x['orgao_apenador'], 'ma': x['municipio_apenador'], 'i': br(x['inicio']), 't': br(x['termino']),
                             'tp': x['tipo'], 'al': x['alcance'], 'f': x['fornecedor'] or '', 'o': x['orgao'] or '', 'm': x['municipio'] or '', 'e': x['esfera'] or '',
                             'num': x['numero_controle'] or '', 'obj': x['objeto'] or '', 'ass': x['data_assinatura'] or '', 'v': float(x['valor']) if x['valor'] is not None else None,
                             'apl': bool(x['aplicavel']), 'a51': bool(x['a51']), 'link': x['link']} for x in ct]}
    except Exception as e:
        print('aviso: impedimentos do TCE-SP não carregados:', e, file=sys.stderr)
    try:   # quadro societário (QSA) e vínculos com pessoas do painel / eleitos
        qe = ler('qsa_empresas', 'cnpj.asc'); qs = ler('qsa_socios', 'cnpj.asc,nome_socio.asc,chave.asc')
        rel = [x for x in ler('relacoes_societarias', 'nome_socio.asc,chave.asc') if (x.get('mesma_pessoa') or '') != 'nao']
        soc = {}
        for x in qs: soc.setdefault(x['cnpj'], []).append([x['nome_socio'], x['qualificacao'] or '', x['data_entrada'] or '', x['tipo']])
        D['QSA'] = {'ref': br(max((x['consultado_em'] for x in qe if x.get('consultado_em')), default='')), 'n_emp': len(qe), 'n_soc': len(qs),
                    'emp': {x['cnpj']: [x['razao_social'], x['situacao'] or '', x['municipio'] or '', x['uf'] or '', x['abertura'] or '', x['cnae'] or ''] for x in qe}, 'soc': soc,
                    'rel': [{'s': x['nome_socio'], 'q': x['qualificacao'] or '', 'de': x['data_entrada'] or '', 'pk': x['pessoa'], 'pn': x['pessoa_nome'], 'reg': x['registros'] or [],
                             'mp': x['municipios_pessoa'] or [], 'el': x['eleito_2024'] or [], 'cf': x['confianca'], 'c': x['cnpj'], 'e': x['empresa'] or '',
                             'se': x['situacao_empresa'] or '', 'me': x['municipio_empresa'] or '', 'ue': x['uf_empresa'] or '', 'or': x['origens'] or [],
                             'conf': x.get('mesma_pessoa') == 'sim'} for x in rel],
                    'base': [{'c': x['cnpj'], 'e': x['razao_social'], 'como': x['citada_como'], 'reg': x['registros'] or [], 'mun': x['municipio'] or '', 'uf': x['uf'] or '',
                              'sit': x['situacao'] or '', 'or': x['origens'] or []} for x in qe if x.get('citada_como')]}
    except Exception as e:
        print('aviso: quadro societário não carregado:', e, file=sys.stderr)
    try:   # TSE: candidaturas barradas, candidaturas de pessoas do painel, doações e fornecedores
        tc = ler('tse_candidaturas', 'ano.desc,municipio.asc,chave.asc')
        cv = lambda x: {'a': x['ano'], 'n': x['nome'], 'u': x['nome_urna'], 'c': x['cargo'], 'm': x['municipio'], 'gi': x['gi'], 'p': x['partido'], 's': x['situacao'] or '',
                        'r': x['resultado'] or '', 'mo': x['motivos'] or [], 'pr': x['processo'] or '', 'lk': x['link'], 'pk': x['pessoa'], 'reg': x['registros'] or [],
                        'b': float(x['bens_total']) if x['bens_total'] is not None else None, 'bn': x['bens_n'] or 0,
                        'ant': x['anterior'] and {'a': x['anterior']['ano'], 'c': x['anterior']['cargo'], 'r': x['anterior'].get('resultado'), 'b': x['anterior'].get('bens_total')}}
        dd = ler('tse_doacoes', 'valor.desc,chave.asc'); ff = ler('tse_fornecedores', 'valor.desc,chave.asc')
        D['TSE'] = {'meta': {'imp': br(max((x['importado_em'] for x in tc if x.get('importado_em')), default='')),
                             'fl20': sum(1 for x in tc if x['ficha_limpa'] and x['ano'] == 2020), 'fl24': sum(1 for x in tc if x['ficha_limpa'] and x['ano'] == 2024)},
                    'fl': [cv(x) for x in tc if x['ficha_limpa']], 'cand': [cv(x) for x in tc if x.get('pessoa')],
                    'doa': [{'sq': x['sq_candidato'], 'cand': x['candidato'], 'urna': x['nome_urna'], 'cargo': x['cargo'], 'partido': x['partido'], 'm': x['municipio'], 'gi': x['gi'],
                             'd': x['doador'], 'q': x['qualificacao_socio'] or '', 'v': float(x['valor'] or 0), 'nd': x['n_doacoes'], 'datas': x['datas'] or [], 'auto': x['autodoacao'],
                             'lk': x['link'], 'c': x['cnpj'], 'e': x['empresa'] or '', 'me': x['municipio_empresa'] or '', 'or': x['origens'] or []} for x in dd],
                    'forn': [{'sq': x['sq_candidato'], 'cand': x['candidato'], 'urna': x['nome_urna'], 'cargo': x['cargo'], 'partido': x['partido'], 'm': x['municipio'], 'gi': x['gi'],
                              'f': x['fornecedor'], 'v': float(x['valor'] or 0), 'nd': x['n_despesas'], 'tipos': x['tipos_despesa'] or [], 'lk': x['link'], 'c': x['cnpj'],
                              'e': x['empresa'] or '', 'or': x['origens'] or []} for x in ff]}
    except Exception as e:
        print('aviso: dados do TSE não carregados:', e, file=sys.stderr)
    try:   # metodologia e qualidade
        D['META'] = meta_qualidade(D)
    except Exception as e:
        print('aviso: metadados de qualidade não calculados:', e, file=sys.stderr)
    refs = {r['chave']: r['valor'] for r in ler('referencias', 'chave.asc')}
    data_base = refs.pop('DATA_BASE', None)
    # ENT_REL: campos complementares das entidades (cnpj, op, papel, url, fonte, rel[] = relações com órgãos e decisões),
    # casados pelo CNPJ ou pelo nome; o que não casa entra como entidade nova
    rel = []
    for k in sorted(k for k in list(refs) if k.startswith('ENT_REL')): rel += refs.pop(k) or []   # ENT_REL e ENT_REL_<lote>
    ent = refs.get('ENT') or []
    dig = lambda c: ''.join(ch for ch in str(c or '') if ch.isdigit())
    for x in rel:
        alvo = next((e for e in ent if (x.get('cnpj') and dig(e.get('cnpj')) == dig(x.get('cnpj'))) or (x.get('ent') and e.get('ent') == x.get('ent'))), None)
        if alvo is not None: alvo.update({k: v for k, v in x.items() if v not in (None, '', [])})
        elif x.get('ent') and x.get('mun'): ent.append(dict(x))
    D.update(refs)
    return D, data_base

def _maxd(xs):
    xs = [x for x in xs if x]
    return max(xs) if xs else None

def _br(d):
    return '/'.join(str(d)[:10].split('-')[::-1]) if d else ''

def meta_qualidade(D):
    M = {}
    regs = ler('registros', 'id.asc')
    val = sum(1 for x in regs if x['status_validacao'] == 'Validado')
    col = [x['data_coleta'] for x in regs if x['data_coleta']]
    M['base'] = {'total': len(regs), 'validados': val, 'pendentes': sum(1 for x in regs if x['status_validacao'] == 'Pendente'),
                 'ult': max(col, key=lambda s: s.split('/')[::-1]) if col else ''}
    nt = ler('noticias', 'id.asc')
    st = {}
    for n in nt:
        k = 'fora do escopo' if n.get('fora_do_escopo') else (n.get('link_status') or 'não verificado')
        st[k] = st.get(k, 0) + 1
    M['noticias'] = {'status': st, 'verif': _br(_maxd([n.get('link_verificado_em') for n in nt]))}
    for tab, k in (('tjsp_consultas', 'tj1'), ('tjsp2_consultas', 'tj2'), ('cnia_consultas', 'cnia')):
        try:
            c = ler(tab, 'nome.asc'); M[k] = {'nomes': len(c), 'ult': _br(_maxd([x.get('consultado_em') for x in c])),
                                              'erros': sum(1 for x in c if str(x.get('status') or '').startswith('erro'))}
        except Exception: pass
    try:
        imp = ler('tce_importacoes', 'id.desc'); M['tce'] = {'ult': _br((imp[0].get('executado_em') or '')[:10]) if imp else '', 'lista': (imp[0].get('lista_atualizacao') if imp else '')}
    except Exception: pass
    try:
        pr = ler('pareceres_tce', 'id.asc')
        M['par'] = {'lidos': len(pr), 'ult': max((x['data_publicacao'] for x in pr if x.get('data_publicacao')), key=lambda s: s.split('/')[::-1], default='')}
    except Exception: pass
    try:
        ti = ler('tcu_importacoes', 'id.desc'); M['tcu'] = {'ult': _br((ti[0].get('executado_em') or '')[:10]) if ti else ''}
    except Exception: pass
    s = D.get('SANC') or {}; M['sanc'] = {'ref': s.get('ref', '')}
    try:
        ag = ler('agenda', 'id.asc'); M['agenda'] = {'eventos': len(ag), 'ult': _br(_maxd([x.get('atualizado_em') for x in ag]))}
    except Exception: pass
    try:
        ps = ler('pessoas', 'id.asc'); M['pessoas'] = {'total': len(ps), 'homonimos': sum(1 for x in ps if x.get('possivel_homonimo')),
                                                       'com_apelido': sum(1 for x in ps if x.get('apelidos')),
                                                       'ult': _br(_maxd([x.get('atualizado_em') for x in ps]))}
    except Exception: pass
    try:
        tm = ler('contas_tcmsp', 'tc.asc'); M['tcm'] = {'ult': _br(_maxd([(x.get('importado_em') or '')[:10] for x in tm]))}
    except Exception: pass
    return M

def separar_camadas(D):
    """Tira do HTML as camadas pesadas e secundárias; o painel as carrega depois da primeira exibição."""
    L = {}
    if D.get('TCU'):
        L['tcu'] = D['TCU']['itens']; D['TCU'] = dict(D['TCU'], itens=[], lazy='dados/tcu.json')
    if D.get('SANC'):
        L['sancoes'] = {'emp': D['SANC']['emp'], 'con': D['SANC']['con']}; D['SANC'] = dict(D['SANC'], emp=[], con=[], lazy='dados/sancoes.json')
    if D.get('IMP'):
        L['impedimentos'] = {'itens': D['IMP'].pop('itens'), 'con': D['IMP'].pop('con')}; D['IMP']['lazy'] = 'dados/impedimentos.json'
    if D.get('QSA'):
        L['qsa'] = {'emp': D['QSA'].pop('emp'), 'soc': D['QSA'].pop('soc')}; D['QSA']['lazy'] = 'dados/qsa.json'
    if D.get('TSE'):
        L['tse'] = {k: D['TSE'].pop(k) for k in ('fl', 'cand', 'doa', 'forn')}; D['TSE']['lazy'] = 'dados/tse.json'
    if D.get('PAR'):
        L['pareceres_txt'] = {x['proc']: x['txt'] for x in D['PAR'] if x.get('txt')}
        for x in D['PAR']:
            if x.get('txt'): x['txt'] = 1
        D['PAR_TXT'] = 'dados/pareceres_txt.json'
    return L

def substituir(html, D, data_base=None):
    import re
    from collections import Counter
    i = html.find('const DATA = ') + len('const DATA = ')
    _, fim = json.JSONDecoder().raw_decode(html[i:])
    html = html[:i] + json.dumps(D, ensure_ascii=False) + html[i + fim:]
    # cabeçalho: data-base e registros a validar
    pend = sum(1 for x in D['R'] if x.get('val') == 'Pendente')
    if data_base:
        cab = 'DATA-BASE ' + data_base + (f' · {pend} REGISTROS A VALIDAR' if pend else '')
        html = re.sub(r'DATA-BASE \d{2}/\d{2}/\d{4}( · \d+ REGISTROS A VALIDAR)?', cab, html, count=1)
    # legenda de credibilidade: contagem por combinação
    cc = Counter(x.get('cred') for x in D['R'])
    for cod in ('A1', 'B2', 'C2', 'C3'):
        html = re.sub(r'(cred-\w">' + cod + r'</span></td><td>)\d+( registros?)',
                      lambda m: m.group(1) + str(cc[cod]) + m.group(2), html, count=1)
    return html

if __name__ == '__main__':
    entrada = sys.argv[1]; saida = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else entrada
    html = open(entrada, encoding='utf-8').read()
    # proteção: se algo foi colado antes do documento (ex.: invólucro de outra página), descarta e avisa
    _k = html.find('<!DOCTYPE html>')
    if _k > 0:
        print('aviso: conteúdo antes de <!DOCTYPE html> removido (', _k, 'caracteres)', file=sys.stderr)
        html = html[_k:]
    D, data_base = montar_data()
    # Recortes de manchetes: ficam no próprio painel (imagens), não no Supabase.
    # Mantém os do painel atual e acrescenta os novos (--recortes arquivo.json), mais recentes primeiro.
    _i = html.find('const DATA = ') + len('const DATA = ')
    atuais = json.JSONDecoder().raw_decode(html[_i:])[0].get('SHOTS') or D.get('SHOTS') or []
    novos = []
    if '--recortes' in sys.argv:
        novos = json.load(open(sys.argv[sys.argv.index('--recortes') + 1], encoding='utf-8'))
    urls_news = {n[4] for n in D['NEWS']}
    vistos, shots = set(), []
    for s_ in novos + atuais:
        if s_['u'] in vistos: continue
        if s_['u'] not in urls_news:
            print('recorte ignorado (notícia não está em noticias):', s_['u'], file=sys.stderr); continue
        vistos.add(s_['u']); shots.append(s_)
    D['SHOTS'] = shots[:12]
    if '--comparar' in sys.argv:
        i = html.find('const DATA = ') + len('const DATA = ')
        A, _ = json.JSONDecoder().raw_decode(html[i:])
        for k in sorted(set(A) | set(D)):
            ok = json.dumps(A.get(k), sort_keys=True, ensure_ascii=False) == json.dumps(D.get(k), sort_keys=True, ensure_ascii=False)
            print(f'{k:10s}', 'igual' if ok else 'DIFERENTE')
        sys.exit(0)
    import os
    camadas = separar_camadas(D)
    pasta = os.path.join(os.path.dirname(os.path.abspath(saida)), 'dados'); os.makedirs(pasta, exist_ok=True)
    for nome, conteudo in camadas.items():
        json.dump(conteudo, open(os.path.join(pasta, nome + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('camadas separadas em', pasta, ':', ', '.join(f'{k}.json' for k in camadas), '(publique-as junto com o painel, no parâmetro files)')
    open(saida, 'w', encoding='utf-8').write(substituir(html, D, data_base))
    print('painel gerado:', saida, '| registros:', len(D['R']), '| pendentes:',
          sum(1 for x in D['R'] if x.get('val') == 'Pendente'), '| data-base:', data_base)
