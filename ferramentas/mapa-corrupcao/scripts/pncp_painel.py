# Monta dados/pncp.json: contratos (PNCP) de TODAS as empresas e entidades da base do painel com
# órgãos municipais e estaduais de SP, agrupados por empresa (CNPJ básico) e órgão contratante.
# Contrato com valor acima de R$ 1 bilhão fica fora da soma (provável erro de registro) e é contado à parte.
# Busca pela RAIZ do CNPJ (matriz e filiais); cada contrato guarda o CNPJ do estabelecimento (k[4]).
# Uso: python3 pncp_painel.py <cnpjs_painel.json> <index.html> <saida.json>
import json, sys, re, unicodedata, datetime
R = '/home/claude/rfb/'
LISTA, IDX, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CA = json.load(open(R + 'pncp_cache_raiz.json'))  # {raiz: contratos da matriz e de todas as filiais}
# raiz que o PNCP não respondeu na busca em lote: usa a consulta anterior por CNPJ (só o estabelecimento consultado)
try:
    for c, its in json.load(open(R + 'pncp_cache.json')).items():
        if c[:8] not in CA and its is not None: CA.setdefault('~' + c[:8], []).extend(dict(x, ni=x.get('ni') or c) for x in its)
    for k in [k for k in CA if k[0] == '~']: CA[k[1:]] = CA.pop(k)
except Exception: pass
ALVO = json.load(open(LISTA))
s = open(IDX, encoding='utf-8').read(); i = s.index('const DATA = ') + 13; D, _ = json.JSONDecoder().raw_decode(s[i:])
def nrm(t):
    t = unicodedata.normalize('NFD', str(t or '')).encode('ascii', 'ignore').decode().upper(); return ' '.join(re.sub(r'[^A-Z0-9 ]+', ' ', t).split())
MP = {}
for m in [x['mun'] for x in D['R']] + [n[11] for n in D['NEWS']] + [x['mun'] for x in D['PAR']] + [x.get('mun') for x in D['TCE']['itens']]:
    if m: MP[nrm(m)] = m
def tit(t):
    t = str(t or '')
    if re.search(r'[a-zà-ú]', t): return t
    t = ' '.join(w.capitalize() for w in t.lower().split())
    return re.sub(r'\s(Da|De|Do|Das|Dos|E|Em)\s', lambda m: m.group(0).lower(), t)
# nomes: índice de entidades do painel e cadastro da Receita
NOME = {}
try:
    for x in json.load(open('/home/claude/p2/dados/entidades.json'))['L']:
        c = re.sub(r'\D', '', str(x[3] or ''))
        if len(c) == 14 and x[1]: NOME.setdefault(c, x[1])
except Exception: pass
EMPC = {}
try:
    for k, v in json.load(open('/home/claude/p2/dados/empcnpj.json'))['L'].items():
        if v.get('status') == 'confirmado':
            for c in v.get('todos', [v['cnpj']]): NOME.setdefault(c, v['razao']); EMPC[c[:8]] = v
except Exception: pass
F = json.load(open(R + 'rfb_full.json'))
NJ = {b: (x[7] or '') for b, x in F['C'].items()}
for b, x in F['C'].items():
    if x[9] and x[0]: NOME.setdefault(x[9], tit(x[0]))
PUB = re.compile(r'Empresa P[uú]blica|Economia Mista|An[oô]nima Aberta|Autarquia|Funda[cç][aã]o P[uú]blica|[OÓ]rg[aã]o P[uú]blico|Cons[oó]rcio P[uú]blico|Poder Executivo|Poder Legislativo|Munic[ií]pio|Estado ou do Distrito', re.I)
PUBN = re.compile(r'^(PREFEITURA|MUNICIPIO|CAMARA MUNICIPAL|FUNDO MUNICIPAL|SECRETARIA|GOVERNO DO ESTADO|ESTADO DE|BANCO DO BRASIL|CAIXA ECONOMICA|COMPANHIA DE SANEAMENTO)', re.I)
ESF = {'M': 'Municipal', 'E': 'Estadual'}
G = {}; excl = 0; FEITAS = set()
RZ = {}
for c in ALVO: RZ.setdefault(c[:8], c if c[8:12] == '0001' else RZ.get(c[:8], c))
for b, c in RZ.items():
    if PUB.search(NJ.get(b, '')) or PUBN.search(nrm(NOME.get(c, ''))): excl += 1; continue
    if b in CA: FEITAS.add(b)
    for x in CA.get(b) or []:
        ni = str(x.get('ni') or '')
        if ni[:8] != b or x.get('e') not in ESF or x.get('c'): continue
        esf = ESF[x['e']]
        mun = 'Governo do Estado de SP' if esf == 'Estadual' else MP.get(nrm(x['m']), tit(x['m'] or ''))
        k = (x['o'] or '', mun, esf)
        e = G.setdefault(b, {'c': c, 'g': {}, 'est': set()})
        e['est'].add(ni)
        g = e['g'].setdefault(k, {'n': 0, 'v': 0.0, 'd': [], 'l': '', 'obj': '', 'x': 0, 'k': []})
        vv = float(x['v'] or 0)
        if vv > 1e9: g['x'] += 1; vv = 0  # valor acima de R$ 1 bilhão num só contrato: provável erro de registro no PNCP
        g['n'] += 1; g['v'] += vv; g['d'].append(x['d'] or '')
        if (x['d'] or '') >= max(g['d']): g['l'] = x['l']; g['obj'] = (x['obj'] or '')[:200]
        g['k'].append([x['d'] or '', round(float(x['v'] or 0), 2), (x['obj'] or '')[:110], (x['l'] or '').replace('https://pncp.gov.br/app/contratos/', ''), ni])
        if ni[8:12] == '0001' and e['c'][8:12] != '0001': e['c'] = ni
# por que a empresa está na base do painel (vai para o nó da rede quando ela entra pela expansão de um órgão)
OM = {'TCE-SP impedimento': 'impedida pelo TCE-SP', 'TCU': 'listada pelo TCU', 'CEIS/CNEP': 'sancionada no CEIS/CNEP', 'TSE doação': 'ligada a doação de campanha (TSE)',
      'TSE fornecedor': 'fornecedora de campanha (TSE)', 'Citada na base': 'citada na base de registros', 'Entidade ou empresa citada em operação': 'citada em operação'}
ORI = {'Base de registros': 'agente político ou servidor da base', 'TCE-SP contas irregulares': 'responsável por contas irregulares (TCE-SP)', 'TCE-SP parecer desfavorável': 'prefeito com parecer desfavorável (TCE-SP)',
       'TCMSP': 'responsável no TCMSP', 'TJSP': 'parte em processo no TJSP', 'TJSP 2º grau': 'parte em processo no TJSP (2º grau)', 'CNIA': 'condenado por improbidade (CNIA)', 'TCU': 'listado pelo TCU',
       'TSE Ficha Limpa': 'candidatura barrada (Ficha Limpa)', 'Cadastro de pessoas': 'pessoa do painel'}
CFT = {'sp': 'nome igual e único entre sócios de empresas paulistas: verificar homonímia', 'mun': 'nome igual e empresa no mesmo município da pessoa: verificar homonímia', 'cnpj': 'vínculo registrado no CNPJ'}
FON = {}
try:
    for x in json.load(open('/home/claude/p2/dados/entidades.json'))['L']:
        c = re.sub(r'\D', '', str(x[3] or ''))
        if len(c) == 14:
            src = [t.strip() for t in str(x[4]).split('·')[-1].split(',')]
            FON.setdefault(c[:8], set()).update(t for t in src if t and not t.startswith('Receita') and t not in ('PNCP',) and 'homonímia' not in t)
except Exception: pass
FONM = {'TCE-SP': 'listada pelo TCE-SP (impedimentos)', 'TCU': 'listada pelo TCU', 'CEIS/CNEP': 'sancionada no CEIS/CNEP', 'TSE': 'ligada a campanha eleitoral de 2024 (TSE)', 'TSE (doador)': 'doadora de campanha (TSE)',
        'Entidades/OS': 'entidade ou OS do painel', 'Base de registros': 'citada na base de registros', 'TJSP': 'parte em processo no TJSP', 'TJSP 2º grau': 'parte em processo no TJSP (2º grau)', 'CNIA': 'citada no CNIA'}
SOCV = {}
for v in F['V']:
    if v[4] == 1: SOCV.setdefault(v[0], []).append(v)
def razao(b):
    r = [OM[o] for o in (F['C'].get(b, [None] * 11)[10] or []) if o in OM]
    for t in sorted(FON.get(b, ())):
        if t == 'TCE-SP' and 'impedida pelo TCE-SP' in r: continue
        if t.startswith('TSE') and any('(TSE)' in x for x in r): continue
        r.append(FONM.get(t, t))
    for v in SOCV.get(b, []):
        x = F['P'].get(v[1])
        if x and x[4] == 'semente' and x[1]:
            r.append(f"{v[2] or 'sócio'}: {tit(x[0])} ({'; '.join(ORI.get(o, o) for o in x[1])}) · {CFT.get(v[5], 'verificar homonímia')}")
            if len(r) >= 4: break
    if b in EMPC: r.append('citada em registro de agente da base (CNPJ identificado pelo nome na Receita)')
    r = list(dict.fromkeys(r))
    return '; '.join(r[:4])  # vazio: sem motivo explícito; a empresa não entra na rede pela expansão de um órgão
O, OI, M, MI = [], {}, [], {}
def ix(L, I, v):
    if v not in I: I[v] = len(L); L.append(v)
    return I[v]
B = {}; nct = 0; ngr = 0
for b, e in G.items():
    gs = []
    for (o, m, esf), g in e['g'].items():
        ds = sorted(d for d in g['d'] if d)
        gs.append([ix(O, OI, tit(o)), ix(M, MI, m), 1 if esf == 'Estadual' else 0, g['n'], round(g['v'], 2), ds[0] if ds else '', ds[-1] if ds else '', g['l'], g['obj'], g['x'], sorted(g['k'], reverse=True)[:12] if g['n'] > 1 else ([g['k'][0]] if g['k'][0][4][8:12] != '0001' else [])])  # até 12 contratos mais recentes, cada um com link
        nct += g['n']; ngr += 1
    gs.sort(key=lambda r: (-r[4], -r[3]))
    B[b] = [NOME.get(e['c']) or e['c'], e['c'], gs, razao(b), sorted(e['est'])]
Z = sorted(FEITAS - set(B))  # consultadas no PNCP e sem contrato com órgão paulista
out = dict(ref=datetime.date.today().strftime('%d/%m/%Y'), n=dict(consultadas=len(ALVO), com_contrato=len(B), contratos=nct, grupos=ngr, excluidas_publicas=excl), O=O, M=M, B=B, Z=Z)
json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(out['n'], round(len(json.dumps(out, ensure_ascii=False, separators=(',', ':'))) / 1e6, 2), 'MB')
