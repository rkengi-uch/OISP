#!/usr/bin/env python3
"""Quadro societário (QSA, dados abertos do CNPJ da Receita Federal) das empresas e entidades que
aparecem no Observatório: sancionadas no CEIS/CNEP, listas do TCU e impedimentos do TCE-SP.

O arquivo completo da Receita (arquivos.receitafederal.gov.br) não é acessível daqui; a consulta é
feita por CNPJ em duas réplicas dos dados abertos da Receita, alternadas para dividir a carga:
BrasilAPI (https://brasilapi.com.br/api/cnpj/v1/<cnpj>) e Minha Receita (https://minhareceita.org/<cnpj>).
Use cabeçalho User-Agent de navegador (sem ele a BrasilAPI responde 403).

Uso:
  python3 qsa.py cache/ saida/ [impedimentos.json] [empresas_base_cnpj.json]
  - empresas_base_cnpj.json: [{"cnpj", "citada_como": [nomes no campo empresa da base], "registros": [IDs]}],
    empresas citadas na base com CNPJ confirmado em fonte pública (a API de despesas municipais do TCE-SP,
    transparencia.tce.sp.gov.br/api/json/despesas/<municipio>/<ano>/<mes>, traz nome e CNPJ dos fornecedores
    pagos pelas prefeituras; confira sempre a razão social e os sócios na BrasilAPI).
  - cache/: respostas brutas por CNPJ (ficam SÓ no contêiner; contêm CPF mascarado dos sócios e
    nunca são enviadas ao Supabase nem ao painel). Reexecuções reaproveitam o cache.
  - saida/qsa_empresas.json e saida/qsa_socios.json: carga das tabelas qsa_empresas e qsa_socios.

Regras: nunca gravar CPF (nem mascarado); sócio pessoa jurídica guarda o CNPJ; o QSA é um retrato
da data de atualização da Receita (pode estar desatualizado; sócios que saíram não aparecem).
"""
import json, os, re, sys, time, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor

SUPABASE = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/'
CHAVE = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/124', 'Accept': 'application/json'}

def ler(tabela, select):
    out, ini = [], 0
    while True:
        r = urllib.request.Request(f'{SUPABASE}{tabela}?select={select}', headers={'apikey': CHAVE, 'Range': f'{ini}-{ini+999}'})
        d = json.load(urllib.request.urlopen(r, timeout=120)); out += d
        if len(d) < 1000: return out
        ini += 1000

def consulta(cnpj, cache):
    arq = os.path.join(cache, cnpj + '.json')
    if os.path.exists(arq):
        return json.load(open(arq))
    fontes = [f'https://brasilapi.com.br/api/cnpj/v1/{cnpj}', f'https://minhareceita.org/{cnpj}']
    if int(cnpj[-1]) % 2: fontes.reverse()   # divide a carga entre as duas réplicas
    for t in range(4):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(fontes[t % 2], headers=UA), timeout=60))
            json.dump(d, open(arq, 'w'), ensure_ascii=False); return d
        except urllib.error.HTTPError as e:
            if e.code == 404:
                json.dump({'_erro': 404}, open(arq, 'w')); return {'_erro': 404}
            time.sleep(3 * (t + 1))
        except Exception:
            time.sleep(3 * (t + 1))
    return None

def tipo_socio(s):
    i = s.get('identificador_de_socio')
    return {1: 'PJ', 2: 'PF', 3: 'Estrangeiro'}.get(i, 'PF')

def main(cache, saida, imp_json=None, base_json=None):
    os.makedirs(cache, exist_ok=True); os.makedirs(saida, exist_ok=True)
    origem = {}
    for x in ler('sancoes_empresas', 'cnpj'):
        origem.setdefault(x['cnpj'], set()).add('CEIS/CNEP')
    for x in ler('tcu_listas', 'cnpj,lista'):
        if x['cnpj']: origem.setdefault(x['cnpj'], set()).add('TCU')
    imp = json.load(open(imp_json)) if imp_json else ler('tce_impedimentos', 'cnpj,lista')
    for x in imp:
        if x.get('cnpj'): origem.setdefault(x['cnpj'], set()).add('TCE-SP ' + ('impedida de contratar' if x['lista'] == 'contrato' else 'impedida de receber repasses'))
    base = {x['cnpj']: x for x in (json.load(open(base_json)) if base_json else [])}
    if not base_json:
        base = {x['cnpj']: x for x in ler('qsa_empresas', 'cnpj,citada_como,registros') if x.get('citada_como')}
    for c in base: origem.setdefault(c, set()).add('Citada na base')
    alvo = sorted(c for c in origem if re.fullmatch(r'\d{14}', c or ''))
    print(len(alvo), 'CNPJs', file=sys.stderr, flush=True)
    emp, soc, falhas = [], [], 0
    hoje = datetime.date.today().isoformat()
    with ThreadPoolExecutor(6) as ex:
        for n, (cnpj, d) in enumerate(zip(alvo, ex.map(lambda c: consulta(c, cache), alvo)), 1):
            if n % 500 == 0: print(n, 'consultados', file=sys.stderr, flush=True)
            if not d or d.get('_erro'):
                falhas += 1; continue
            emp.append(dict(cnpj=cnpj, razao_social=d.get('razao_social'), nome_fantasia=d.get('nome_fantasia') or None,
                            situacao=d.get('descricao_situacao_cadastral'), data_situacao=d.get('data_situacao_cadastral'),
                            abertura=d.get('data_inicio_atividade'), municipio=d.get('municipio'), uf=d.get('uf'),
                            cnae=d.get('cnae_fiscal_descricao'), natureza=d.get('natureza_juridica'), porte=d.get('porte'),
                            capital_social=d.get('capital_social'), origens=sorted(origem[cnpj]), consultado_em=hoje,
                            citada_como=(base.get(cnpj) or {}).get('citada_como'), registros=(base.get(cnpj) or {}).get('registros')))
            for s in d.get('qsa') or []:
                t = tipo_socio(s)
                soc.append(dict(cnpj=cnpj, nome_socio=(s.get('nome_socio') or '').strip(), tipo=t,
                                cnpj_socio=re.sub(r'\D', '', s.get('cnpj_cpf_do_socio') or '') if t == 'PJ' else None,
                                qualificacao=s.get('qualificacao_socio'), data_entrada=s.get('data_entrada_sociedade'),
                                faixa_etaria=s.get('faixa_etaria'), representante=(s.get('nome_representante_legal') or '').strip() or None,
                                consultado_em=hoje))
    json.dump(emp, open(os.path.join(saida, 'qsa_empresas.json'), 'w'), ensure_ascii=False)
    json.dump(soc, open(os.path.join(saida, 'qsa_socios.json'), 'w'), ensure_ascii=False)
    print(f'{len(emp)} empresas com cadastro, {falhas} sem resposta; {len(soc)} sócios', file=sys.stderr)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None, sys.argv[4] if len(sys.argv) > 4 else None)
