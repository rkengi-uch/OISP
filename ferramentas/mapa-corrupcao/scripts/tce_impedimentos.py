#!/usr/bin/env python3
"""Impedimentos publicados pelo TCE-SP (www4.tce.sp.gov.br/apenados), cruzados com os contratos de
órgãos paulistas no PNCP.

O site do TCE-SP bloqueia acesso automatizado: peça ao usuário os dois CSVs do botão de
exportação de cada lista ("Impedimentos de contratar/licitar" e "Impedimento de receber repasse")
e salve-os como contrato.csv e repasse.csv numa pasta.

Uso:
  python3 tce_impedimentos.py pasta/ saida/
Gera em saida/: impedimentos.json (tabela tce_impedimentos) e contratos.json (tabela
tce_impedimentos_contratos).

Regras:
  - CPF e RG nunca são gravados (só o CNPJ e o nome publicado);
  - o arquivo do TCE-SP vem com acentos corrompidos (UTF-8 lido como Latin-1): o script corrige;
  - município: pelo código do órgão que aplicou a pena no TCE-SP (prefeitura < 1000; órgão municipal
    = código da prefeitura × 10^7 + sufixo; o resto é estadual, "Governo do Estado de SP");
  - contrato "durante o impedimento": assinatura entre o início e o término (sem término = vigente);
  - "aplicavel" segue o alcance da pena na lei citada:
      inidoneidade (8.666 art. 87 IV; 14.133 art. 156 IV; 13.019 art. 73 III; DL 2.300) → qualquer órgão;
      impedimento do ente (14.133 art. 156 III; 10.520 art. 7º; 12.462 art. 47; 13.019 art. 73 II)
        → órgãos do mesmo ente (mesmo município, ou Estado de SP);
      suspensão do órgão (8.666 art. 87 III; 13.303 art. 83 III) → mesmo município e mesmo tipo de
        órgão (prefeitura/câmara); demais casos ficam como informativos;
  - lista de repasses: entidades do terceiro setor impedidas de receber novos repasses do órgão
    concessor (não entram no cruzamento com o PNCP, que não traz convênios).
Contrato listado é sinal para verificação, não prova de irregularidade (a pena pode ter sido
suspensa judicialmente ou reabilitada; o registro pode ser aditivo ou empenho).
"""
import csv, datetime, json, os, re, sys, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sancoes_pncp import contratos as pncp_contratos

try:
    import ftfy
    fix = ftfy.fix_text
except ImportError:
    def fix(s):
        try: return s.encode('cp1252').decode('utf8')
        except Exception: return s

SUPABASE = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/'
CHAVE = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
SIGLAS = {'SJRP': 'SAO JOSE DO RIO PRETO', 'S.J.RIO PRETO': 'SAO JOSE DO RIO PRETO', 'S.J.CAMPOS': 'SAO JOSE DOS CAMPOS', 'S.B.CAMPO': 'SAO BERNARDO DO CAMPO'}

def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    for x, y in SIGLAS.items(): s = s.replace(x, y)
    return re.sub(r'[^A-Z0-9]+', ' ', s).replace('Z', 'S').strip()

def dt(s):
    try:
        d, m, a = s.strip().split('/'); return datetime.date(int(a), int(m), int(d))
    except Exception:
        return None

def iso(s):
    d = dt(s); return d.isoformat() if d else None

def ler_municipios():
    r = urllib.request.Request(SUPABASE + 'municipios?select=gi,nome,nome_norm', headers={'apikey': CHAVE, 'Range': '0-999'})
    M = json.load(urllib.request.urlopen(r, timeout=60))
    return sorted(((norm(m['nome']), m['nome'], m['gi']) for m in M), key=lambda x: -len(x[0]))

def por_nome(o, MUN):
    for n, nome, gi in MUN:
        if re.search(r'(^| )' + re.escape(n) + r'( |$)', o):
            return nome, gi
    import difflib   # grafias divergentes (ex.: "Florinea" sem acento trocado, "Luiz Antonio")
    m = re.search(r'(?:PREFEITURA|CAMARA) MUNICIPAL (?:DA|DE|DO|DAS|DOS) (.+)$', o)
    if m:
        c = difflib.get_close_matches(m.group(1), [n for n, _, _ in MUN], n=1, cutoff=0.85)
        if c: return next((nome, gi) for n, nome, gi in MUN if n == c[0])
    return None, None

class Localizador:
    """O código do órgão no TCE-SP indica o ente: prefeituras têm código < 1000; órgãos municipais
    (câmara, autarquias, fundações, empresas) têm código = código da prefeitura × 10^7 + sufixo;
    órgãos estaduais ficam entre esses dois intervalos."""
    def __init__(self, MUN, orgaos):
        self.MUN, self.pref = MUN, {}
        for o in orgaos:
            cod, _, nome = o.partition('-')
            if cod.isdigit() and int(cod) < 1000:
                mun = por_nome(norm(nome), MUN)
                if mun[0]: self.pref[int(cod)] = mun
    def __call__(self, orgao):
        cod, _, nome = orgao.partition('-'); o = norm(nome)
        if not cod.isdigit():
            return por_nome(o, self.MUN) + ('Municipal',) if por_nome(o, self.MUN)[0] else ('Governo do Estado de SP', None, 'Estadual')
        c = int(cod)
        if 'CONSORCIO' in o or 'INTERMUNICIPAL' in o or 'BACIAS' in o:
            return 'Intermunicipal', None, 'Intermunicipal'
        if c < 1000:
            mun = self.pref.get(c) or por_nome(o, self.MUN)
            return (mun[0], mun[1], 'Municipal') if mun[0] else ('Governo do Estado de SP', None, 'Estadual')
        if c >= 10 ** 7 and c // 10 ** 7 in self.pref:
            return self.pref[c // 10 ** 7] + ('Municipal',)
        if c >= 10 ** 7:
            mun = por_nome(o, self.MUN)
            if mun[0]: return mun + ('Municipal',)
        return 'Governo do Estado de SP', None, 'Estadual'

def alcance(tipo):
    t = norm(tipo)
    if 'INIDONEIDADE' in t: return 'todos'
    if re.search(r'14 133|10 520|12 462|13 019', t): return 'ente'
    if re.search(r'8 666|13 303', t): return 'orgao'
    return 'orgao'

def tipo_orgao(s):
    s = norm(s)
    if 'CAMARA' in s: return 'camara'
    if 'PREFEITURA' in s or s.startswith('MUNICIPIO') or 'FUNDO MUNICIPAL' in s: return 'prefeitura'
    return 'outro'

def aplicavel(imp, c):
    a = alcance(imp['tipo'])
    if a == 'todos': return True
    esf = (c.get('esfera_id') or '')
    mun_c = norm(c.get('municipio_nome') or '')
    if imp['nivel'] == 'Estadual':
        return a == 'ente' and esf == 'E'
    if imp['nivel'] != 'Municipal' or esf != 'M' or mun_c != norm(imp['municipio']):
        return False
    if a == 'ente': return True
    return tipo_orgao(imp['orgao']) != 'outro' and tipo_orgao(imp['orgao']) == tipo_orgao(c.get('orgao_nome') or '')

def main(pasta, saida):
    os.makedirs(saida, exist_ok=True)
    MUN = ler_municipios(); hoje = datetime.date.today().isoformat()
    linhas = {k: [{c: fix(v or '').strip() for c, v in r.items()} for r in csv.DictReader(open(os.path.join(pasta, k + '.csv'), encoding='utf-8-sig'))]
              for k in ('contrato', 'repasse')}
    municipio = Localizador(MUN, [r['apenador'] for r in linhas['contrato']] + [r['concessor'] for r in linhas['repasse']])
    out = []
    for r in linhas['contrato']:
        mun, gi, niv = municipio(r['apenador'])
        out.append(dict(lista='contrato', apenada=r['apenada'], cnpj=re.sub(r'\D', '', r['cnpj']) or None, pessoa='PJ' if r['cnpj'] else 'PF',
                        orgao=re.sub(r'^\d+-', '', r['apenador']), codigo_orgao=r['apenador'].split('-')[0], municipio=mun, gi=gi, nivel=niv,
                        inicio=iso(r['inicio']), termino=iso(r['termino']), tipo=r['tipoApenacao'], alcance=alcance(r['tipoApenacao']),
                        motivo=r['observacao'][:600], processo=r['processo'] or None, referencia=hoje))
    for r in linhas['repasse']:
        mun, gi, niv = municipio(r['concessor'])
        out.append(dict(lista='repasse', apenada=r['apenada'], cnpj=re.sub(r'\D', '', r['cnpj']) or None, pessoa='PJ' if r['cnpj'] else 'PF',
                        orgao=re.sub(r'^\d+-', '', r['concessor']), codigo_orgao=r['concessor'].split('-')[0], municipio=mun, gi=gi, nivel=niv,
                        inicio=iso(r['sentencaPublicada']), termino=None, transito=iso(r['transitadoEmJulgado']), tipo='Impedimento de receber repasses',
                        alcance='orgao', motivo=r['infoCompl'][:600], processo=r['processo'] or None, referencia=hoje))
    json.dump(out, open(os.path.join(saida, 'impedimentos.json'), 'w'), ensure_ascii=False)
    print(len(out), 'impedimentos;', sum(1 for x in out if x['lista'] == 'contrato'), 'contratar/licitar,',
          sum(1 for x in out if x['lista'] == 'repasse'), 'repasses', file=sys.stderr, flush=True)
    por = {}
    for x in out:
        if x['lista'] == 'contrato' and x['cnpj']: por.setdefault(x['cnpj'], []).append(x)
    def tarefa(cnpj):
        try: return cnpj, pncp_contratos(cnpj), None
        except Exception as e: return cnpj, [], e
    achados, feitos = [], 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for cnpj, cs, err in ex.map(tarefa, sorted(por)):
            feitos += 1
            if err: print(cnpj, 'erro', err, file=sys.stderr)
            for c in cs:
                ass = (c.get('data_assinatura') or '')[:10]
                try: da = datetime.date.fromisoformat(ass)
                except Exception: continue
                for imp in por[cnpj]:
                    ini = datetime.date.fromisoformat(imp['inicio']) if imp['inicio'] else None
                    fim = datetime.date.fromisoformat(imp['termino']) if imp['termino'] else None
                    if ini and da >= ini and (not fim or da <= fim):
                        achados.append(dict(cnpj=cnpj, apenada=imp['apenada'], orgao_apenador=imp['orgao'], municipio_apenador=imp['municipio'],
                            inicio=imp['inicio'], termino=imp['termino'], tipo=imp['tipo'], alcance=imp['alcance'],
                            fornecedor=c.get('fornecedor_nome'), orgao=c.get('orgao_nome'), esfera=c.get('esfera_nome'), municipio=c.get('municipio_nome'),
                            numero_controle=c.get('numero_controle_pncp'), objeto=(c.get('description') or '')[:500], data_assinatura=ass,
                            valor=c.get('valor_global'), cancelado=bool(c.get('cancelado')), aplicavel=aplicavel(imp, c),
                            link='https://pncp.gov.br/app' + (c.get('item_url') or '')))
            if feitos % 200 == 0:
                print(f'{feitos}/{len(por)} CNPJs, {len(achados)} contratos durante impedimento', file=sys.stderr, flush=True)
    json.dump(achados, open(os.path.join(saida, 'contratos.json'), 'w'), ensure_ascii=False)
    print(len(achados), 'contratos durante impedimento;', sum(1 for a in achados if a['aplicavel']), 'com alcance aplicável', file=sys.stderr)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
