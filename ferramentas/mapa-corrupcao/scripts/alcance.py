"""Alcance das sanções segundo a Súmula nº 51 do TCE-SP.

"A declaração de inidoneidade para licitar ou contratar (artigo 87, IV da Lei nº 8.666/93) tem seus
efeitos jurídicos estendidos a todos os órgãos da Administração Pública, ao passo que, nos casos de
impedimento e suspensão de licitar e contratar (artigo 87, III da Lei nº 8.666/93 e artigo 7º da Lei
nº 10.520/02), a medida repressiva se restringe à esfera de governo do órgão sancionador."
(https://www.tce.sp.gov.br/boletim-de-jurisprudencia/sumulas)

Usado pelo gerar_painel.py para marcar, em cada contrato assinado durante uma sanção (CEIS/CNEP ×
PNCP) ou um impedimento publicado pelo TCE-SP (× PNCP), se a pena alcança o órgão contratante pelo
entendimento do TCE-SP (`a51`), ao lado do critério padrão do painel (`apl`: abrangência registrada
no cadastro e alcance da lei citada). Sanções fundadas em outras leis (14.133/2021, 13.303/2016,
12.846/2013, 8.429/1992 etc.) não são tratadas pela súmula: para elas, `a51` repete `apl`.

Regras:
  - inidoneidade pela Lei 8.666/1993 (ou sem lei informada) -> todos os órgãos;
  - Lei 8.666/1993, art. 87, III, ou Lei 10.520/2002, art. 7º -> esfera de governo do sancionador:
      municipal: órgãos municipais do mesmo município; estadual de SP: órgãos estaduais de SP;
      federal: órgãos federais;
  - demais fundamentos -> critério padrão.
"""
import re, unicodedata

def _n(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()).strip()

def base_legal(texto):
    """Classifica a pena pela base legal (que prevalece sobre a categoria registrada):
    'sumula' = Lei 10.520/2002, art. 7º, ou Lei 8.666/1993, art. 87, III (impedimento/suspensão);
    'inid'   = inidoneidade da Lei 8.666/1993 (art. 87, IV), ou declaração de inidoneidade sem lei informada;
    None     = outra base legal (leis estaduais de outros estados, Lei 14.133/2021, 13.303/2016,
               12.846/2013 etc.), que segue o critério do registro e da lei."""
    t = _n(texto); d = re.sub(r'[.\s]', '', t)
    if '10520' in d:
        return 'sumula'
    if '8666' in d:
        if re.search(r'87\W*(INC(ISO)?\W*)?IV\b', t) or ('INIDONE' in t and not re.search(r'87\W*(INC(ISO)?\W*)?III\b', t)):
            return 'inid'
        if re.search(r'87\W*(INC(ISO)?\W*)?III\b', t) or re.search(r'SUSPENS|IMPEDIMENT', t):
            return 'sumula'
        return None
    if '14133' in d:
        return None   # a Lei 14.133/2021 define o próprio alcance (art. 156, §§ 4º e 5º): segue o registro e a lei
    if 'INIDONE' in t and not re.search(r'\bLEI\b|\bDECRETO\b', t):
        return 'inid'
    return None

def _esf(e):
    e = _n(e)
    return 'M' if e.startswith('MUNIC') else 'E' if e.startswith('ESTAD') else 'F' if e.startswith('FEDER') else ''

def s51_sancao(s, c, padrao):
    """s: linha de sancoes_empresas; c: linha de sancoes_contratos; padrao: c['aplicavel']."""
    b = base_legal((s.get('fundamentacao') or '') + ' ' + (s.get('categoria') or ''))
    if b == 'inid':
        return True
    if b != 'sumula':
        return bool(padrao)
    es, ec = _esf(s.get('esfera_orgao')), _esf(c.get('esfera'))
    if es != ec:
        return False
    if es == 'M':
        return (s.get('uf_orgao') == 'SP') and bool(c.get('municipio')) and _n(c.get('municipio')) in _n(s.get('orgao'))
    if es == 'E':
        return s.get('uf_orgao') == 'SP'
    return es == 'F'

def s51_impedimento(c, nivel_apenador, padrao):
    """c: linha de tce_impedimentos_contratos; nivel_apenador: 'Municipal' | 'Estadual' | 'Intermunicipal'."""
    b = base_legal(c.get('tipo') or '')
    if b == 'inid':
        return True
    if b != 'sumula':
        return bool(padrao)
    ec = _esf(c.get('esfera'))
    if nivel_apenador == 'Municipal':
        return ec == 'M' and _n(c.get('municipio')) == _n(c.get('municipio_apenador'))
    if nivel_apenador == 'Estadual':
        return ec == 'E'
    return False
