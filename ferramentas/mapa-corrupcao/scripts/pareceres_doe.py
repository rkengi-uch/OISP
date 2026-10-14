#!/usr/bin/env python3
"""Extrai os pareceres prévios sobre contas anuais de prefeituras do Diário Oficial do TCE-SP.

Uso:
  python3 pareceres_doe.py baixar AAAA-MM-DD AAAA-MM-DD  pasta/   # baixa as edições do período
  python3 pareceres_doe.py extrair pasta/ saida.json              # lê os PDFs e extrai os pareceres

Fonte: https://doe.tce.sp.gov.br/ (o calendário consulta /json/file/AAAA/M/D, que devolve o
caminho do PDF; dias com edição extra devolvem uma lista com dois arquivos).

Cada parecer extraído traz: data de publicação, edição (URL do PDF e página), processo TC,
processo de referência (reexame), município, exercício, prefeito(s), relator, colegiado
(Primeira Câmara, Segunda Câmara ou Plenário), data da sessão, tipo (parecer ou reexame),
resultado (desfavorável ou favorável), ementa e trecho da decisão.
Parecer prévio é ato distinto do julgamento de contas: é opinião técnica do TCE-SP que a
Câmara Municipal pode derrubar por 2/3 dos vereadores.
"""
import datetime, glob, json, os, re, subprocess, sys, time, unicodedata, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) Chrome/124'}
BASE = 'https://doe.tce.sp.gov.br'
MESES = {m: i + 1 for i, m in enumerate(['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
                                         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'])}

def baixar(ini, fim, pasta):
    os.makedirs(pasta, exist_ok=True)
    d = datetime.date.fromisoformat(ini); f = datetime.date.fromisoformat(fim)
    while d <= f:
        try:
            j = json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/json/file/{d.year}/{d.month}/{d.day}', headers=UA), timeout=30).read())
            arq = j.get('file'); arqs = arq if isinstance(arq, list) else ([arq] if arq else [])
            for k, p in enumerate(arqs):
                dest = os.path.join(pasta, f"{d.isoformat()}{'' if k == 0 else '-extra'}.pdf")
                if not os.path.exists(dest):
                    open(dest, 'wb').write(urllib.request.urlopen(urllib.request.Request(BASE + p, headers=UA), timeout=120).read())
                    open(dest + '.url', 'w').write(BASE + p)
                    time.sleep(0.5)
        except Exception as e:
            print('erro', d, e, file=sys.stderr)
        d += datetime.timedelta(days=1); time.sleep(0.3)

def norm(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()

def limpa(s):
    return re.sub(r'\s+', ' ', s or '').strip(' .;:-–')

FIM_SECAO = re.compile(r'\n(SENTENÇAS|DESPACHOS|ACÓRDÃOS|DECISÕES|EDITAIS|ATOS|COMUNICADOS|PAUTAS?|NOTIFICAÇÕES|CERTIDÕES|SECRETARIA-DIRETORIA GERAL|RESOLUÇÕES|PORTARIAS|INTIMAÇÕES|CITAÇÕES|EXTRATOS?)\b[^\n]{0,60}\n')
TC = re.compile(r'(?m)^\s*(?:PROCESSO:?\s*)?TC-\s?0*(\d{1,6})[.\/](\d{3})[.\/](\d{2})(?:-\d)?')

def data_sessao(t):
    m = re.search(r'sess[aã]o (?:realizada )?(?:de |em )?(\d{1,2})(?:º)? de (\w+) de (\d{4})', t, re.I)
    if m and norm(m.group(2)) in {norm(k): v for k, v in MESES.items()}:
        mes = {norm(k): v for k, v in MESES.items()}[norm(m.group(2))]
        return f'{int(m.group(1)):02d}/{mes:02d}/{m.group(3)}'
    return ''

def resultado(t):
    n = norm(t)
    trecho = n
    k = max(n.rfind('acorda '), n.rfind('o egregio plenario'), n.rfind('vistos, relatados'))
    if k > 0: trecho = n[k:]
    if 'reexame' in n and 'provimento' in trecho:
        if re.search(r'neg(ou|ar)(-lhe)? provimento|nao provid|negado provimento', trecho): return 'desfavorável' if 'desfavoravel' in n else 'favorável'
        m = re.search(r'parecer (previo )?(des)?favoravel', trecho[trecho.find('provimento'):])
        if m: return 'desfavorável' if m.group(2) else 'favorável'
    ms = [m for m in re.finditer(r'(emitir|emitiu|emite|emissao d[eo]|mantido o|manter o|mantendo o)\s+(o\s+)?parecer\s+(previo\s+)?(des)?favoravel', trecho)
          if not re.search(r'vot(ou|ado|aram)|vencid', trecho[max(0, m.start() - 60):m.start()])]
    if ms: return 'desfavorável' if ms[-1].group(4) else 'favorável'
    ms = list(re.finditer(r'parecer (previo )?(des)?favoravel', n))
    return ('desfavorável' if ms[-1].group(2) else 'favorável') if ms else ''

def campos(bloco):
    g = lambda rx: (lambda m: limpa(m.group(1)) if m else '')(re.search(rx, bloco, re.I | re.S))
    mun = re.split(r'\s+e\s+(?=[A-Z])', g(r'Prefeitura Municipal(?: de|:)\s*([^.;,(]+)'))[0]
    ex = g(r'Exerc[ií]cio(?: de|:)?\s*(\d{4})') or g(r'exerc[ií]cio de (\d{4})')
    pref = g(r'(?m)^Prefeit\w*(?:\([a-z]{1,3}\))?:\s*(.+?)(?:\.\n|\n[A-ZÁÉÍÓÚ][a-záéíóú]+(?:\([a-z]{1,3}\))?(?: de \w+)?:)') or g(r'Respons[aá]ve(?:l|is)(?:\(is\))?:\s*(.+?)\s*(?:[–-]\s*|\()(?:Ex-)?Prefeit')
    ref = g(r'\(ref\.?\s*TC-\s*0*([\d.\-/]+)')
    ementa = ''
    mi = re.search(r'EMENTA\s*:|\n(?:PEDIDO DE )?REEXAME\.|\nCONTAS (?:ANUAIS|MUNICIPAIS)\.', bloco)
    if mi:
        linhas = []
        for ln in bloco[mi.start():].lstrip('\n').split('\n')[:30]:
            if linhas and re.search(r'[a-záéíóúâêôãõç]{3,}', ln): break
            linhas.append(ln)
        ementa = limpa(re.sub(r'^EMENTA\s*:\s*', '', ' '.join(linhas)))
    col = 'Plenário' if re.search(r'Plen[aá]rio', bloco) else ('Primeira Câmara' if re.search(r'Primeira C[aâ]mara', bloco) else ('Segunda Câmara' if re.search(r'Segunda C[aâ]mara', bloco) else ''))
    m = re.search(r'(?:emitir|emitiu|provimento|parecer desfavor)[^\n]{0,40}', bloco, re.I)
    k = max(bloco.rfind('ACORDA'), bloco.rfind('O Egrégio Plenário'))
    decisao = limpa(bloco[k:k + 700]) if k >= 0 else ''
    return dict(municipio=mun, exercicio=int(ex) if ex.isdigit() else None, prefeitos=pref, processo_ref=ref,
                ementa=ementa, colegiado=col, data_sessao=data_sessao(bloco), decisao=decisao,
                tipo='reexame' if re.search(r'reexame', bloco[:1500], re.I) else 'parecer')


def texto_colunas(pdf):
    """Texto em ordem de leitura respeitando as colunas do DOE (4 colunas por página).
    Usa as caixas de texto do pdftotext (-bbox-layout); blocos que atravessam colunas
    (cabeçalhos) entram primeiro. Páginas separadas por \f."""
    import html as H
    xml = subprocess.run(['pdftotext', '-bbox-layout', pdf, '-'], capture_output=True, text=True).stdout
    paginas = []
    for pg in re.finditer(r'<page width="([\d.]+)" height="[\d.]+">(.*?)</page>', xml, re.S):
        W = float(pg.group(1)); brutos = []
        for b in re.finditer(r'<block xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="[\d.]+">(.*?)</block>', pg.group(2), re.S):
            x0, y0, x1 = float(b.group(1)), float(b.group(2)), float(b.group(3))
            linhas = [' '.join(H.unescape(w) for w in re.findall(r'<word[^>]*>(.*?)</word>', ln.group(1)))
                      for ln in re.finditer(r'<line[^>]*>(.*?)</line>', b.group(4), re.S)]
            brutos.append((x0, y0, x1, '\n'.join(linhas)))
        # colunas da página: inícios de bloco estreitos que se repetem (o DOE alterna 2, 3 e 4 colunas)
        estreitos = sorted(x0 for x0, y0, x1, t in brutos if (x1 - x0) < W * 0.55)
        inicios = []
        for x in estreitos:
            if not inicios or x - inicios[-1][-1] > 25: inicios.append([x])
            else: inicios[-1].append(x)
        cols = [min(c) for c in inicios if len(c) >= 2] or [0]
        larg = (W - 60) / max(1, len(cols))
        blocos = []
        for x0, y0, x1, t in brutos:
            if (x1 - x0) > larg * 1.5 and len(cols) > 1:
                col = -1
            else:
                col = max([i for i, c in enumerate(cols) if c <= x0 + 8] or [0])
            blocos.append((col, y0, t))
        cab = sorted([b for b in blocos if b[0] < 0], key=lambda b: b[1])
        corpo = sorted([b for b in blocos if b[0] >= 0], key=lambda b: (b[0], b[1]))
        paginas.append('\n'.join(b[2] for b in cab + corpo))
    txt = '\f'.join(paginas)
    return re.sub(r'(\w)-\n(?=[a-záéíóúâêôãõç])', r'\1', txt)   # junta palavras hifenizadas na quebra de linha


def resultado_final(bloco, c, ntxt):
    """Resultado do parecer, na ordem de confiabilidade:
    1) ementa (fica junto do cabeçalho, sem mistura de colunas);
    2) frase da decisão que cita a Prefeitura e o exercício (procurada no texto inteiro);
    3) leitura do bloco."""
    em = c.get('ementa') or ''
    nem = norm(em)
    if c.get('tipo') == 'reexame' or 'reexame' in nem:
        if re.search(r'nao provimento|negado provimento|nao provid|improvimento|desprovimento|nao conhecimento', nem):
            return 'desfavorável'
        if re.search(r'\bprovimento\b', nem) and 'parcial' not in nem:
            return 'favorável'
    ms = re.findall(r'\b(des)?favoravel\b', nem)
    if ms and c.get('tipo') != 'reexame':
        return 'desfavorável' if ms[-1] else 'favorável'
    mun = norm(c.get('municipio') or ''); ex = str(c.get('exercicio') or '')
    if mun and ex:
        rx = r'(emitir|emitido|emissao d[eo]|emitiu|mantido o|manter o|mantendo o)\s+(o\s+)?parecer\s+(previo\s+)?(des)?favoravel[^.]{0,160}?prefeitura municipal de ' + re.escape(mun) + r'\b[^.]{0,80}?' + ex
        ms = [m for m in re.finditer(rx, ntxt) if not re.search(r'vot(ou|ado|aram)|vencid', ntxt[max(0, m.start() - 60):m.start()])]
        if ms: return 'desfavorável' if ms[-1].group(4) else 'favorável'
    return resultado(bloco)

def extrair(pasta):
    saida = []
    for pdf in sorted(glob.glob(os.path.join(pasta, '*.pdf'))):
        txt = subprocess.run(['pdftotext', pdf, '-'], capture_output=True, text=True).stdout
        txt = re.sub(r'(\w)-\n(?=[a-záéíóúâêôãõç])', r'\1', txt)
        ntxt = norm(re.sub(r'\s+', ' ', txt))
        nome = os.path.basename(pdf)[:-4].replace('-extra', '')
        url = open(pdf + '.url').read().strip() if os.path.exists(pdf + '.url') else (f"{BASE}/pdf/{nome[:4]}/{nome[5:7]}/doe-tce-{nome}.pdf" if not pdf.endswith('-extra.pdf') else '')
        mpub = re.search(r'Publicação:\s*(\d{2}/\d{2}/\d{4})', txt)
        pub = mpub.group(1) if mpub else ''
        if not pub:   # edições antigas (até início de 2023): a data da edição é a data de publicação
            mf = re.search(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(pdf)); pub = f'{mf.group(3)}/{mf.group(2)}/{mf.group(1)}' if mf else ''
        for sec in re.finditer(r'\nPARECERES\n', txt):
            ini = sec.end(); mfim = FIM_SECAO.search(txt, ini); fim = mfim.start() if mfim else len(txt)
            secao = txt[ini:fim]
            relator = ''
            # blocos: cada processo TC que abre um parecer
            pos = [m.start() for m in TC.finditer(secao)]
            heads = [(m.start(), limpa(m.group(1).replace('\n', ' '))) for m in re.finditer(r'PARECERES? DO CONSELHEIRO\s+((?:SUBSTITUTO\s*-?\s*(?:AUDITOR\s+)?)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+(?:\n[A-ZÁÉÍÓÚÂÊÔÃÕÇ ]+)?)\n', secao)]
            for j, p in enumerate(pos):
                b = secao[p:(pos[j + 1] if j + 1 < len(pos) else len(secao))]
                if not re.search(r'Prefeitura Municipal|Prefeit[oa]', b[:900]):
                    continue
                if not re.search(r'parecer', b, re.I): continue
                if not re.search(r'contas anuais|contas municipais|contas da prefeitura|contas do prefeito', norm(b[:1800])): continue
                mtc = TC.search(b); proc = f"{int(mtc.group(1))}/{mtc.group(2)}/{mtc.group(3)}"
                rel = [h for h in heads if h[0] <= p]; relator = rel[-1][1].title() if rel else relator
                c = campos(b)
                pagina = txt[:ini + p].count('\f') + 1
                # texto integral do bloco (para leitura no painel sem depender do PDF)
                texto = re.sub(r'[ \t]+', ' ', b)
                texto = re.sub(r'\n(?=[a-záéíóúâêôãõç0-9,;(])', ' ', texto)      # junta quebras de linha no meio da frase
                texto = re.sub(r'\n{2,}', '\n', texto).strip()[:12000]
                c['texto'] = texto
                c['texto'] = re.sub(r'\s+', ' ', b).strip()[:9000]   # íntegra do bloco, para leitura no painel
                c.update(processo=proc, relator=relator, resultado=resultado_final(b, c, ntxt), data_publicacao=pub,
                         edicao=url, pagina=pagina, arquivo=os.path.basename(pdf))
                if c['municipio']:
                    saida.append(c)
    # um processo pode aparecer no sumário e no corpo: fica o registro mais completo
    unico = {}
    for x in saida:
        k = x['processo']   # republicações do mesmo processo: fica a primeira publicação
        d = x['data_publicacao'].split('/')[::-1]
        if k not in unico or d < unico[k]['data_publicacao'].split('/')[::-1]: unico[k] = x
    return list(unico.values())

if __name__ == '__main__':
    if sys.argv[1] == 'baixar':
        baixar(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        r = extrair(sys.argv[2])
        json.dump(r, open(sys.argv[3], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(len(r), 'pareceres;', sum(1 for x in r if x['resultado'] == 'desfavorável'), 'desfavoráveis', file=sys.stderr)
