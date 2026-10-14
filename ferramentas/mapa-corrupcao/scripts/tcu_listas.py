#!/usr/bin/env python3
"""Listas públicas do Tribunal de Contas da União (TCU), filtradas para responsáveis com UF = SP.

Listas (https://sites.tcu.gov.br/dados-abertos/inidoneos-irregulares):
  ci  contas julgadas irregulares            https://certidoes.apps.tcu.gov.br/lista-responsaveis
  el  possível implicação eleitoral          https://certidoes.apps.tcu.gov.br/lista-implicacao-eleitoral
  in  inabilitados para função pública       https://certidoes.apps.tcu.gov.br/lista-inabilitados
  id  licitantes inidôneos                   https://certidoes.apps.tcu.gov.br/lista-inidoneos

Uso:
  python3 tcu_listas.py baixar pasta/                 # baixa os CSVs (navegador Chromium via Playwright)
  python3 tcu_listas.py processar pasta/ saida.json   # filtra SP, liga municípios e nomes da base

O site do TCU tem proteção contra robôs (desafio em JavaScript e bloqueio por excesso de
requisições, página "Acesso Bloqueado"). Por isso o download usa o navegador, uma lista por vez,
com pausa de 90 s entre elas. Se aparecer "Acesso Bloqueado", espere 30 minutos antes de tentar
de novo; não insista. Alternativa: o usuário baixa os CSVs pelo botão "Baixar arquivo" de cada
página e anexa à conversa.

Regras: o CPF publicado pelo TCU nunca é gravado (só o CNPJ de pessoa jurídica). O município
é o do cadastro do responsável no TCU, não necessariamente o do fato.
"""
import csv, io, json, os, re, sys, time, unicodedata, urllib.request

LISTAS = {'ci': 'lista-responsaveis', 'el': 'lista-implicacao-eleitoral', 'in': 'lista-inabilitados', 'id': 'lista-inidoneos'}
SUPABASE = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/'
CHAVE = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'

def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()).strip()

def chave(s):
    return re.sub(r'[^a-z0-9]+', ' ', norm(s)).strip()

def limpo(s):
    return re.sub(r'\s+', ' ', re.sub(r'\s*\([^)]*\)', '', s or '')).strip()

def baixar(pasta):
    import asyncio
    from playwright.async_api import async_playwright
    os.makedirs(pasta, exist_ok=True)
    async def run():
        async with async_playwright() as p:
            px = os.environ.get('HTTPS_PROXY')
            b = await p.chromium.launch(proxy={'server': px} if px else None)
            ctx = await b.new_context(accept_downloads=True); pg = await ctx.new_page()
            for i, (k, slug) in enumerate(LISTAS.items()):
                if os.path.exists(os.path.join(pasta, k + '.csv')):
                    print(k, 'já baixada', file=sys.stderr); continue
                if i: await asyncio.sleep(90)
                try:
                    await pg.goto('https://certidoes.apps.tcu.gov.br/' + slug, timeout=120000)
                    if 'Bloqueado' in (await pg.title()):
                        print(k, 'ACESSO BLOQUEADO pelo TCU; tente de novo em 30 minutos', file=sys.stderr); break
                    btn = pg.get_by_text('Baixar arquivo').first
                    await btn.wait_for(timeout=240000); await pg.wait_for_timeout(2000)
                    async with pg.expect_download(timeout=240000) as di:
                        await btn.click()
                    d = await di.value; await d.save_as(os.path.join(pasta, k + '.csv'))
                    print(k, 'ok', file=sys.stderr)
                except Exception as e:
                    print(k, 'erro', str(e)[:200], '| página:', (await pg.title()), file=sys.stderr)
                    try: await pg.screenshot(path=os.path.join(pasta, k + '_erro.png'))
                    except Exception: pass
            await b.close()
    asyncio.run(run())

def ler(tabela, select):
    out, ini = [], 0
    while True:
        r = urllib.request.Request(f'{SUPABASE}{tabela}?select={select}', headers={'apikey': CHAVE, 'Authorization': 'Bearer ' + CHAVE, 'Range': f'{ini}-{ini+999}'})
        d = json.load(urllib.request.urlopen(r, timeout=120)); out += d
        if len(d) < 1000: return out
        ini += 1000

def ler_csv(caminho):
    t = open(caminho, 'rb').read()
    try: t = t.decode('utf-8')
    except UnicodeDecodeError: t = t.decode('latin-1')
    linhas = t.splitlines()
    if linhas and linhas[0].lower().startswith('sep='):
        linhas = linhas[1:]
    sep = '|' if '|' in linhas[0] else ';'
    return list(csv.DictReader(io.StringIO('\n'.join(linhas)), delimiter=sep))

def campo(r, *nomes):
    for n in nomes:
        for k in r:
            if k and norm(k) == norm(n):
                return (r[k] or '').strip()
    return ''

def processar(pasta, saida):
    # municípios do painel (nome com acento e gi) e nomes da base
    muns = {}
    for tab in ('registros', 'contas_irregulares_tce', 'pareceres_tce', 'noticias'):
        for x in ler(tab, 'municipio,gi'):
            if x.get('municipio') and x.get('gi') is not None:
                muns.setdefault(chave(x['municipio']), (x['municipio'], x['gi']))
    base = {}
    for x in ler('registros', 'id,nome,municipio'):
        base.setdefault(chave(limpo(x['nome'])), []).append(x['id'])
    out, meta = [], {}
    for k in LISTAS:
        f = os.path.join(pasta, k + '.csv')
        if not os.path.exists(f):
            print(k, 'arquivo ausente', file=sys.stderr); continue
        R = ler_csv(f); sp = [r for r in R if campo(r, 'UF') == 'SP']
        meta[k] = {'total': len(R), 'sp': len(sp)}
        for r in sp:
            nome = re.sub(r"^['\"\s]+|['\"\s]+$", '', campo(r, 'Nome'))
            doc = re.sub(r'\D', '', campo(r, 'CPF/CNPJ', 'CPF', 'CNPJ'))
            tipo = 'empresa' if len(doc) == 14 else 'pessoa'
            mr = campo(r, 'Município', 'Municipio')
            m = muns.get(chave(mr))
            out.append(dict(lista=k, nome=nome, tipo=tipo, cnpj=doc if tipo == 'empresa' else None, uf='SP', municipio=mr,
                            municipio_painel=m[0] if m else (('São Paulo') if norm(mr) == 'sao paulo' else None), gi=m[1] if m else None,
                            processo=campo(r, 'Processo'), link_processo=campo(r, 'Link do processo'),
                            acordaos=campo(r, 'Acórdão', 'Acórdãos') if not campo(r, 'Acórdãos').startswith('http') else '',
                            data_acordao=campo(r, 'Data do acórdão'),
                            link_acordaos=campo(r, 'Link dos acórdãos') or (campo(r, 'Acórdãos') if campo(r, 'Acórdãos').startswith('http') else ''),
                            transito=campo(r, 'Trânsito em julgado'), data_final=campo(r, 'Data final da sanção', 'Data final'),
                            base=sorted(set(base.get(chave(nome), [])))))
    vis, fin = set(), []
    for o in out:
        kk = (o['lista'], o['nome'], o['processo'])
        if kk in vis: continue
        vis.add(kk); fin.append(o)
    json.dump({'meta': meta, 'linhas': fin}, open(saida, 'w'), ensure_ascii=False)
    print(json.dumps(meta), len(fin), 'linhas', file=sys.stderr)

if __name__ == '__main__':
    if sys.argv[1] == 'baixar':
        baixar(sys.argv[2])
    else:
        processar(sys.argv[2], sys.argv[3])
