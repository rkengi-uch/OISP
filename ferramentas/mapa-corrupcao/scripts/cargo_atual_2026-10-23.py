#!/usr/bin/env python3
"""Cargo atual dos agentes políticos da base (verificação de 23/10/2026).
Saída: cargo_atual.sql (UPDATE em registros: cargo_atual, cargo_atual_obs, cargo_atual_fonte, cargo_atual_verificado_em).
Regra: o campo `cargo` continua sendo o cargo À ÉPOCA do fato; `cargo_atual` diz o que a pessoa ocupa hoje,
no formato "Atual Prefeito · Ex-vereador" (cargo diferente), "Atual Vereador" (mesmo cargo) ou "Ex-prefeito"
(sem cargo atual localizado). Pessoas não identificadas pela fonte ficam sem cargo atual."""
import json

TSE = 'https://dadosabertos.tse.jus.br/dataset/candidatos-2024'
CNN94 = 'https://www.cnnbrasil.com.br/eleicoes/conheca-os-94-deputados-estaduais-eleitos-por-sao-paulo-em-2026/'
TRE70 = 'https://www.tre-sp.jus.br/comunicacao/noticias/2026/Outubro/eleicoes-2026-veja-as-deputadas-e-os-deputados-federais-eleitos-por-sao-paulo'
T24 = 'TSE: eleito(a) em 2024 para o mandato 2025–2028'
N24 = 'TSE: não eleito(a) para cargo municipal em 2024 (mandato 2025–2028); nenhum outro cargo público atual localizado nas fontes consultadas'
N24S = 'TSE: ficou como suplente em 2024 (mandato 2025–2028); nenhum outro cargo público atual localizado nas fontes consultadas'
SEC = 'cargo de livre nomeação; nenhuma fonte consultada confirma que permanece no cargo'
EXO = 'Exonerado(a) do cargo, segundo a base do painel'

# (ids, cargo_atual, observação, fonte)
C = [
 (['R042'], 'Secretário municipal à época (afastado em jan/2026)', 'Afastado por 180 dias em 28/01/2026; ' + SEC, 'Base do painel'),
 (['R043'], 'Secretário municipal à época (afastado em jan/2026)', 'Afastado por 180 dias em 28/01/2026; ' + SEC, 'Base do painel'),
 (['R200'], 'Atual Vereador', T24 + ' (Taubaté)', TSE),
 (['R062'], 'Ex-vereadora', N24, TSE),
 (['R022'], 'Ex-secretário municipal', 'Gestão encerrada; ' + SEC, 'Base do painel'),
 (['R045'], 'Ex-vereador', N24, TSE),
 (['R190'], 'Prefeito afastado', T24 + ' (Ribeira); afastado por decisão judicial desde 16/09/2025, segundo a base', TSE),
 (['R013'], 'Ex-prefeito', N24, TSE),
 (['R003'], 'Atual Vereador (suplente em exercício)', 'TSE: suplente em 2024; voltou ao cargo de vereador em São Bernardo do Campo após 61 dias de afastamento (Diário do Grande ABC)', 'https://www.dgabc.com.br/Noticia/4263314/ary-de-oliveira-retorna-ao-cargo-de-vereador-depois-de-61-dias'),
 (['R010'], 'Atual Deputado estadual · Ex-prefeito', 'Deputado estadual (Alesp); reeleito em 04/10/2026 (lista da CNN Brasil a partir da totalização do TSE)', CNN94),
 (['R061'], 'Atual Vereador', T24 + ' (Osasco)', TSE),
 (['R052'], 'Atual Vice-prefeito', T24 + ' (Hortolândia); cassado em 1ª instância pela Justiça Eleitoral em jan/2025, permanece no cargo enquanto recorre (Revista Oeste)', 'https://revistaoeste.com/politica/justica-cassa-vice-prefeito-aliado-de-lula-em-hortolandia-sp/'),
 (['R096'], 'Ex-prefeito', 'Preso para cumprimento de pena (out/2025), segundo a base; ' + N24, TSE),
 (['R166'], 'Atual Vereador', T24 + ' (Itatiba)', TSE),
 (['R212'], 'Atual Vice-prefeito', T24 + ' (Jandira; registrado no TSE como Carlos Eduardo Pitteri)', TSE),
 (['R046'], 'Ex-vereador', N24, TSE),
 (['R150'], 'Ex-secretário municipal', 'Gestão municipal encerrada em 2024; ' + SEC, 'Base do painel'),
 (['R050'], 'Ex-vereador', N24S, TSE),
 (['R026'], 'Ex-secretário municipal', 'Gestão encerrada; ' + SEC, 'Base do painel'),
 (['R078', 'R238'], 'Ex-prefeito', N24, TSE),
 (['R172', 'R184', 'R221'], 'Ex-secretária municipal', EXO, 'Base do painel'),
 (['R014', 'R015', 'R016'], 'Ex-prefeito · Deputado federal eleito em 2026', 'Eleito deputado federal em 04/10/2026 (posse em fev/2027); registro de candidatura em julgamento no TSE (Correio da Manhã); ' + N24, TRE70),
 (['R132'], 'Ex-secretário estadual', 'Nenhum cargo público atual localizado nas fontes consultadas', 'Base do painel'),
 (['R086'], 'Vereador com mandato suspenso', T24 + ' (Rio Claro); mandato suspenso em 2025, segundo a base', TSE),
 (['R169'], 'Ex-prefeito (mandato cassado em 2026)', 'Cassação executada por ordem do TSE em 07/07/2026; eleição suplementar em 25/10/2026', 'Base do painel'),
 (['R002'], 'Atual Vereador (presidente da Câmara)', T24 + ' (São Bernardo do Campo); voltou à Câmara e à presidência após o afastamento (Diário do Grande ABC)', 'https://www.dgabc.com.br/Noticia/4267854/danilo-lima-volta-a-ocupar-presidencia-da-camara-de-sao-bernardo'),
 (['R020'], 'Ex-prefeita', N24, TSE),
 (['R142'], 'Ex-secretário estadual', 'Nenhum cargo público atual localizado nas fontes consultadas', 'Base do painel'),
 (['R241'], 'Atual Prefeito', T24 + ' (Cerqueira César)', TSE),
 (['R047'], 'Ex-vereador', N24S, TSE),
 (['R226'], 'Ex-prefeito', 'Candidato a prefeito de Paulínia em 2024, não eleito (TSE); nenhum cargo público atual localizado', TSE),
 (['R225'], 'Ex-prefeito', N24, TSE),
 (['R206'], 'Vereador com mandato suspenso', T24 + ' (Iguape); suspenso do mandato pela sentença de 08/06/2026, segundo a base', TSE),
 (['R163'], 'Atual Vereador', T24 + ' (Cotia)', TSE),
 (['R180'], 'Atual Prefeito', T24 + ' (Mococa)', TSE),
 (['R041'], 'Atual Vereador', T24 + ' (Ferraz de Vasconcelos); retorno ao mandato autorizado em 03/08/2026, segundo a base', TSE),
 (['R004'], 'Secretário municipal à época (afastado em 2025)', SEC, 'Base do painel'),
 (['R033'], 'Atual Vereador', T24 + ' (Jaú)', TSE),
 (['R183'], 'Secretário municipal à época (2025)', SEC, 'Base do painel'),
 (['R007'], 'Secretário municipal à época (2025)', SEC, 'Base do painel'),
 (['R149'], 'Ex-deputado estadual', 'Nenhum cargo público atual localizado nas fontes consultadas', 'Base do painel'),
 (['R034'], 'Atual Vereador', T24 + ' (Jaú)', TSE),
 (['R051'], 'Atual Prefeita', T24 + ' (Ubatuba)', TSE),
 (['R236'], 'Atual Vereador (preso temporariamente)', T24 + ' (Olímpia); preso temporariamente desde 15/10/2026, segundo a base', TSE),
 (['R037'], 'Ex-vereador', 'Renunciou ao mandato, segundo a base; ' + N24, TSE),
 (['R092'], 'Ex-prefeito', N24, TSE),
 (['R060'], 'Ex-vereador', N24S, TSE),
 (['R048'], 'Ex-vereador', N24, TSE),
 (['R054'], 'Vice-prefeito afastado', T24 + ' (Tupi Paulista); afastado, segundo a base', TSE),
 (['R214'], 'Atual Prefeito', T24 + ' (Taquaritinga)', TSE),
 (['R040'], 'Ex-vereador', N24S, TSE),
 (['R176'], 'Atual Prefeito', T24 + ' (Buri)', TSE),
 (['R108', 'R213'], 'Ex-prefeito', N24, TSE),
 (['R178'], 'Ex-prefeito', 'Preso desde 01/09/2026 para cumprimento de pena, segundo a base; ' + N24, TSE),
 (['R170', 'R171', 'R177', 'R204'], 'Ex-prefeito (mandato cassado em 2026) · Ex-vereador', 'Eleito prefeito de Ourinhos em 2024 (TSE) e vereador em 2020; mandato cassado pela Câmara em 03/09/2026 e em 16/09/2026; mandado de segurança em análise, segundo a base', TSE),
 (['R231'], 'Secretário municipal afastado', 'Afastado por decisão judicial desde 14/10/2026, segundo a base', 'Base do painel'),
 (['R232'], 'Secretário municipal afastado', 'Afastado por decisão judicial desde 14/10/2026, segundo a base', 'Base do painel'),
 (['R228'], 'Atual Prefeito', T24 + ' (São Roque)', TSE),
 (['R162', 'R195'], 'Atual Vereador (preso temporariamente)', T24 + ' (Sumaré); preso desde 09/09/2026 e licenciado da presidência da Câmara, segundo a base', TSE),
 (['R211'], 'Atual Prefeito', T24 + ' (Jandira)', TSE),
 (['R017'], 'Atual Prefeito · Ex-vereador', T24 + ': eleito prefeito de Embu das Artes em 2024', TSE),
 (['R115'], 'Ex-prefeito', N24, TSE),
 (['R049'], 'Ex-vereador', N24, TSE),
 (['R011'], 'Ex-secretário municipal', SEC, 'Base do painel'),
 (['R025'], 'Atual Deputado federal · Ex-prefeito', 'Deputado federal; reeleito em 04/10/2026 (TRE-SP)', TRE70),
 (['R053'], 'Ex-secretário municipal', 'A própria fonte o qualifica como ex-secretário', 'Base do painel'),
 (['R028'], 'Ex-vereador', N24S, TSE),
 (['R091'], 'Ex-prefeito', N24, TSE),
 (['R118'], 'Ex-vereador', N24, TSE),
 (['R224'], 'Ex-prefeito', N24, TSE),
 (['R189'], 'Ex-vice-prefeita (falecida)', 'Eleita vice-prefeita de Ribeira em 2024 (TSE); faleceu em 26/09/2026, segundo a base', TSE),
 (['R104'], 'Ex-prefeito', N24, TSE),
 (['R117'], 'Atual Vereador', T24 + ' (Guarujá)', TSE),
 (['R139'], 'Ex-secretário estadual', 'Nenhum cargo público atual localizado nas fontes consultadas', 'Base do painel'),
 (['R023'], 'Ex-secretário municipal', SEC, 'Base do painel'),
 (['R210'], 'Ex-secretário municipal', 'A própria fonte o qualifica como ex-secretário', 'Base do painel'),
 (['R218'], 'Secretário municipal à época (2026)', SEC, 'Base do painel'),
 (['R039'], 'Ex-vereador', N24, TSE),
 (['R029'], 'Ex-vereador', N24, TSE),
 (['R215'], 'Secretário municipal à época (2026)', SEC, 'Base do painel'),
 (['R031'], 'Ex-vereador', N24, TSE),
 (['R001'], 'Atual Prefeito · Ex-vice-prefeito', T24 + ' (São Bernardo do Campo; vice-prefeito eleito em 2020); reassumiu o cargo após o afastamento, segundo a base', TSE),
 (['R009'], 'Ex-secretário municipal', 'Gestão encerrada em 2024; ' + SEC, 'Base do painel'),
 (['R227'], 'Ex-prefeita', N24, TSE),
 (['R181'], 'Ex-prefeito', N24, TSE),
 (['R152'], 'Ex-governador · Ex-ministro', 'Deixou o Ministério do Empreendedorismo em abril de 2026 (Folha de Pernambuco); nenhum cargo público atual localizado', 'https://www.folhape.com.br/politica/marcio-franca-deixa-o-ministerio-do-empreendedorismo-para-se/478228/'),
 (['R080'], 'Ex-vice-prefeito', N24, TSE),
 (['R121'], 'Ex-secretário municipal', 'Gestão encerrada em 2024; ' + SEC, 'Base do painel'),
 (['R021'], 'Ex-secretário municipal', 'Gestão encerrada; ' + SEC + ' (há homônimo eleito vereador em Piraju em 2024, que não é a mesma pessoa)', 'Base do painel'),
 (['R098'], 'Ex-prefeito', N24, TSE),
 (['R168'], 'Ex-vice-prefeito (mandato cassado em 2026)', 'Mandato cassado pelo TRE-SP em 19/03/2026; eleição suplementar em 25/10/2026, segundo a base', 'Base do painel'),
 (['R194', 'R229'], 'Ex-secretário municipal', 'Pediu exoneração em 25/08/2026, segundo a base', 'Base do painel'),
 (['R063'], 'Ex-prefeito', N24, TSE),
 (['R120'], 'Atual Vereador', T24 + ' (Guarujá)', TSE),
 (['R151'], 'Atual Vereador (preso em 2026)', T24 + ' (Catanduva); preso na Operação Rei do Pix, segundo a base; situação do mandato não confirmada', TSE),
 (['R030'], 'Atual Vereador', T24 + ' (Jaú)', TSE),
 (['R044'], 'Atual Vereador', T24 + ' (Mogi das Cruzes; reeleito)', TSE),
 (['R114'], 'Ex-prefeito', N24, TSE),
 (['R209'], 'Ex-vereador', 'Não concorreu em 2024 (TSE); preso desde 18/09/2026, segundo a base', TSE),
 (['R064'], 'Ex-secretária municipal', EXO, 'Base do painel'),
 (['R005'], 'Ex-prefeito · Ex-secretário municipal (São Paulo)', 'Deixou a Secretaria Municipal de Segurança Urbana de São Paulo em 2026 para disputar vaga de deputado federal; não aparece entre os eleitos (TRE-SP)', 'https://www.dgabc.com.br/Noticia/4350624/carla-e-orlando-morando-encerram-campanha-em-sao-bernardo'),
 (['R161'], 'Ex-prefeito (mandato cassado em 2026) · Ex-vice-prefeito', 'Eleito prefeito de Pratânia em 2024 (TSE) e vice em 2020; mandato cassado pela Câmara em 19/09/2026, segundo a base', TSE),
 (['R058'], 'Atual Deputado federal · Ex-prefeito', 'Deputado federal; reeleito em 04/10/2026 (TRE-SP; Diário do Litoral)', TRE70),
 (['R035'], 'Ex-prefeito', N24, TSE),
 (['R237'], 'Ex-secretário municipal', EXO, 'Base do painel'),
 (['R038'], 'Ex-vereador', 'Renunciou ao mandato em jul/2024, segundo a base; ' + N24, TSE),
 (['R187'], 'Ex-prefeito', N24, TSE),
 (['R006', 'R205'], 'Atual Prefeito', T24 + ' (Sorocaba); reconduzido ao cargo por decisão do STF em mar/2026 e no exercício do cargo em set/2026 (Correio da Manhã)', 'https://www.correiodamanha.com.br/nacional/sao-paulo/campinas/interior-de-sao-paulo/2026/09/321981-rodrigo-manga-surpreende-e-exonera-dois-a-10-dias-da-eleicao.html'),
 (['R093'], 'Vereador afastado (ago/2025)', T24 + ' (Caiabu); afastado em ago/2025, segundo a base; situação atual do mandato não confirmada', TSE),
 (['R018'], 'Ex-prefeito · Ex-vereador · Deputado estadual eleito em 2026', 'Prefeito de Osasco eleito em 2016 e 2020 (TSE); eleito deputado estadual em 04/10/2026 (posse em mar/2027); nenhum cargo público atual localizado', CNN94),
 (['R119'], 'Atual Vereador', T24 + ' (Guarujá)', TSE),
 (['R174', 'R186', 'R223'], 'Ex-secretária municipal', EXO, 'Base do painel'),
 (['R207', 'R208'], 'Atual Vereador', T24 + ' (São Paulo)', TSE),
 (['R164'], 'Atual Vereador', T24 + ' (Cotia)', TSE),
 (['R024'], 'Ex-secretário municipal', EXO, 'Base do painel'),
 (['R199'], 'Ex-secretária municipal', 'A própria fonte a qualifica como ex-secretária', 'Base do painel'),
 (['R188', 'R197', 'R198'], 'Atual Prefeita', T24 + ' (Bauru)', TSE),
 (['R105'], 'Ex-vice-prefeito', N24, TSE),
 (['R032'], 'Atual Vereador', T24 + ' (Jaú)', TSE),
 (['R036'], 'Ex-vice-prefeito', N24, TSE),
 (['R167'], 'Ex-prefeito (mandato cassado em 2026) · Ex-vice-prefeito', 'Eleito prefeito de Martinópolis em 2024 e vice em 2020 (TSE); mandato cassado pelo TRE-SP em 19/03/2026, segundo a base', TSE),
 (['R008', 'R116'], 'Ex-prefeito', N24, TSE),
 (['R057'], 'Ex-prefeito', N24, TSE),
 (['R179'], 'Ex-vereador (mandato cassado em 2026)', 'Mandato cassado pela Câmara de Campinas em 09/09/2026, segundo a base', 'Base do painel'),
 (['R173', 'R185', 'R222'], 'Ex-secretário municipal', EXO, 'Base do painel'),
 (['R165'], 'Atual Vereador', T24 + ' (Cotia)', TSE),
 (['R175'], 'Atual Prefeito', T24 + ' (Caçapava)', TSE),
 # pessoas não identificadas pela fonte, mas com perda do cargo documentada
 (['R112'], 'Ex-prefeito (mandato cassado)', 'Cassação mantida pelo TRE-SP em mar/2026, segundo a base', 'Base do painel'),
 (['R113'], 'Ex-vice-prefeita (mandato cassado)', 'Cassação mantida pelo TRE-SP em mar/2026, segundo a base', 'Base do painel'),
]

if __name__ == '__main__':
    R = {r['id']: r for r in json.load(open('registros.json'))}
    vistos = set()
    out = []
    q = lambda s: "'" + s.replace("'", "''") + "'"
    for ids, cat, obs, fonte in C:
        for i in ids:
            assert i in R, i
            assert i not in vistos, i
            vistos.add(i)
            out.append(f"update registros set cargo_atual={q(cat)}, cargo_atual_obs={q(obs)}, cargo_atual_fonte={q(fonte)}, cargo_atual_verificado_em='2026-10-23' where id={q(i)};")
    open('cargo_atual.sql', 'w').write('\n'.join(out) + '\n')
    pol = [r for r in R.values() if not __import__('re').search(r'servidor|dirigente|estagi', r['cargo'] or '', 2)]
    falta = [(r['id'], r['nome']) for r in pol if r['id'] not in vistos]
    print('atualizados', len(vistos), 'de', len(pol), 'agentes políticos; sem cargo atual (não identificados):', len(falta))
    for f in falta: print('  ', *f)
