#!/usr/bin/env python3
"""Cadastro único de pessoas (tabela `pessoas`): reúne numa linha cada nome que aparece em
qualquer camada do Observatório, com o nome de exibição, apelidos, outras grafias encontradas,
camadas, municípios, cargos, IDs da base e o alerta de possível homônimo.

Uso:  python3 pessoas.py saida.json
Depois, grave com a carga em massa (tabela "pessoas"; ver SKILL.md, "Carga em massa").

Regras:
  - chave = nome sem acentos, minúsculo, sem parênteses e sem pontuação; nomes com a mesma
    chave são tratados como o mesmo registro do cadastro (o que NÃO prova que sejam a mesma
    pessoa: veja `possivel_homonimo`);
  - apelido = texto entre parênteses no nome da base (ex.: "Marcelo de Lima Fernandes
    (Marcelo Lima)"), quando tem 2+ palavras; vira chave alternativa para busca e ficha;
  - variantes = outras grafias da mesma chave e nomes encontrados no TJSP/CNIA pela busca
    parcial (estes ficam só como "a conferir", nunca unem cadastros);
  - possivel_homonimo = o mesmo nome aparece em 2+ municípios diferentes nas camadas de
    agentes (base, TCE-SP, pareceres, TCU); a ficha avisa para conferir;
  - os campos manuais `mesma_pessoa_que` e `observacao` nunca são sobrescritos.
"""
import json, re, sys, unicodedata, urllib.request

SUPABASE = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/'
CHAVE = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
MUN_IGUAL = {'embu': 'embu das artes', 'moji mirim': 'mogi mirim', 'moji guacu': 'mogi guacu', 'santa barbara d oeste': 'santa barbara d oeste'}
GENERICO = re.compile(r'nao identificad|nao nominad|vereadores|auditores|servidores|secretarios|empresarios|investigados|policiais|agentes')

def norm(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()

def limpo(s):
    return re.sub(r'\s+', ' ', re.sub(r'\s*\([^)]*\)|["“”]', '', s or '')).strip()

def chave(s):
    return re.sub(r'[^a-z0-9]+', ' ', norm(limpo(s))).strip()

def ler(tabela, select='*'):
    out, ini = [], 0
    while True:
        r = urllib.request.Request(f'{SUPABASE}{tabela}?select={select}', headers={'apikey': CHAVE, 'Authorization': 'Bearer ' + CHAVE, 'Range': f'{ini}-{ini+999}'})
        d = json.load(urllib.request.urlopen(r, timeout=120)); out += d
        if len(d) < 1000: return out
        ini += 1000

def qualidade(nome):
    # prefere grafia com minúsculas e acentos
    return (any(c.islower() for c in nome), sum(1 for c in nome if ord(c) > 127), len(nome))

def nomes_par(s):
    return [x.strip() for x in re.split(r'\s+e\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])|;|,', limpo(s)) if len(x.strip().split()) >= 2]

def main(saida):
    P = {}
    def add(nome, camada, mun=None, cargo=None, reg=None, apelido=None, variante_conferir=None, agente=True):
        n = limpo(nome); k = chave(n)
        if len(k.split()) < 2 or GENERICO.search(k): return
        p = P.setdefault(k, dict(chave=k, grafias=set(), apelidos=set(), conferir=set(), camadas=set(), municipios=set(), mun_agente=set(), cargos=set(), registros=set()))
        p['grafias'].add(n); p['camadas'].add(camada)
        if mun: p['municipios'].add(mun)
        if mun and agente and mun != 'Intermunicipal': p['mun_agente'].add(MUN_IGUAL.get(chave(mun), chave(mun)))
        if cargo: p['cargos'].add(cargo)
        if reg: p['registros'].add(reg)
        if apelido and len(apelido.split()) >= 2 and chave(apelido) != k: p['apelidos'].add(apelido.strip())
        if variante_conferir and chave(variante_conferir) != k: p['conferir'].add(limpo(variante_conferir))
    for x in ler('registros', 'id,nome,municipio,cargo'):
        ap = re.findall(r'\(([^)]+)\)', x['nome'] or '')
        ap = [a for a in ap if not re.search(r'\d|ex-|cassad|afastad|preso|condenad', a, re.I)]
        add(x['nome'], 'Base', x['municipio'] if x['municipio'] != 'Governo do Estado de SP' else None, x['cargo'], x['id'], ap[0] if ap else None)
    for x in ler('tjsp_processos', 'nome_consultado,nome_parte,confianca'):
        add(x['nome_consultado'], 'TJSP 1º grau', variante_conferir=x['nome_parte'], agente=False)
    for x in ler('tjsp2_processos', 'nome_consultado,nome_parte'):
        add(x['nome_consultado'], 'TJSP 2º grau', variante_conferir=x['nome_parte'], agente=False)
    for x in ler('cnia_condenacoes', 'nome_consultado,nome_cnia'):
        add(x['nome_consultado'], 'CNIA', agente=False)
    for x in ler('contas_irregulares_tce', 'responsavel,municipio,papel,nivel'):
        add(x['responsavel'], 'TCE-SP contas', x['municipio'] if x['nivel'] != 'Estadual' else None, x['papel'])
    for x in ler('pareceres_tce', 'prefeitos,municipio,resultado'):
        if x['resultado'] != 'desfavorável': continue
        for n in nomes_par(x['prefeitos']): add(n, 'TCE-SP parecer', x['municipio'], 'Prefeito')
    for x in ler('contas_tcmsp', 'responsavel'):
        for n in (x['responsavel'] or '').split(';'):
            add(n, 'TCMSP', 'São Paulo', agente=False)
    for x in ler('tcu_listas', 'nome,municipio_painel,tipo'):
        if x['tipo'] == 'pessoa': add(x['nome'], 'TCU', x['municipio_painel'])
    linhas = []
    for k, p in P.items():
        nome = sorted(p['grafias'], key=qualidade, reverse=True)[0]
        if nome.isupper(): nome = ' '.join(w if w in ('DA', 'DE', 'DO', 'DAS', 'DOS', 'E') and False else w.capitalize() for w in nome.split()).replace(' Da ', ' da ').replace(' De ', ' de ').replace(' Do ', ' do ').replace(' Das ', ' das ').replace(' Dos ', ' dos ').replace(' E ', ' e ')
        var = sorted((p['grafias'] - {nome}) | {f'{v} (a conferir)' for v in p['conferir']})[:8]
        linhas.append(dict(chave=k, nome=nome, apelidos=sorted(p['apelidos']), chaves_alias=sorted({chave(a) for a in p['apelidos']}),
                           variantes=var, camadas=sorted(p['camadas']), municipios=sorted(p['municipios']), cargos=sorted(p['cargos'])[:6],
                           registros=sorted(p['registros']), possivel_homonimo=len(p['mun_agente']) >= 2))
    json.dump(linhas, open(saida, 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(linhas), 'pessoas;', sum(1 for l in linhas if l['possivel_homonimo']), 'com possível homônimo;',
          sum(1 for l in linhas if l['apelidos']), 'com apelido;', sum(1 for l in linhas if len(l['camadas']) >= 2), 'em 2+ camadas', file=sys.stderr)

if __name__ == '__main__':
    main(sys.argv[1])
