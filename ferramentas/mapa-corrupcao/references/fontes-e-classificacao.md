# Fontes e classificação

## Escala usada (convenção de relatórios de inteligência)

**Confiabilidade da fonte (letra)**

| Código | Significado | Aplicação nesta base |
|---|---|---|
| A | Completamente confiável | Fonte oficial primária: Agência SP (agenciasp.sp.gov.br, portal oficial do Governo do Estado), Controladoria Geral do Estado (CGE-SP), Corregedoria Geral da Administração, secretarias estaduais (SES-SP, SSP-SP, Seduc etc.), MPSP (inclui Gaeco), PF, Polícia Civil-SP, TJSP, TRF3, STJ, STF, TRE-SP, TSE, TCE-SP, CGU, Receita Federal, Ministério Público de Contas, Diário Oficial, atas e resoluções de Câmara Municipal |
| B | Geralmente confiável | Grande imprensa e agências: Estadão / Estadão Conteúdo, Folha / Folhapress, g1 e afiliadas Globo, CNN Brasil, UOL, Metrópoles, Poder360, Band, Record, SBT News, Agência Brasil, Veja, piauí, Gazeta do Povo |
| C | Razoavelmente confiável | Jornais e portais regionais com redação identificada (ex.: EPTV, TV TEM, jornais de cidade), agregadores e reproduções de outras fontes |
| D–F | Não usualmente confiável, não confiável ou não avaliável | NÃO usar na base |

**Credibilidade da informação (número)**

| Código | Significado | Quando usar |
|---|---|---|
| 1 | Confirmada | Nota oficial do próprio órgão que conduziu a medida, decisão judicial publicada ou confirmação independente |
| 2 | Provavelmente verdadeira | Coerente com outras fontes, sem contradição conhecida |
| 3 | Possivelmente verdadeira | Detalhamento parcial; requer confirmação nos autos |
| 4–6 | Duvidosa, improvável ou não avaliável | NÃO usar na base |

**Combinações permitidas:** A1, B2, C2, C3.
- C3 só entra quando o fato é plausível e específico (nome, órgão, data), e a descrição ganha a frase "informação a confirmar nos autos".
- Se um fato tiver apenas fonte C3 e envolver prisão ou condenação, procure outra fonte antes de incluir. Sem confirmação, mova para "Descartados" com o motivo "fonte insuficiente; reavaliar".

## Hierarquia na escolha do link principal (coluna O)

1. Nota oficial ou decisão do órgão (A1)
2. Grande imprensa (B2)
3. Imprensa regional (C2/C3)

As demais fontes vão para `Link complementar`. Quando surgir uma nota oficial para um fato antes só noticiado pela imprensa, promova a nota a link principal e ajuste a credibilidade, registrando no log.

## Descartar sempre

- Redes sociais, vídeos sem veículo identificado, blogs anônimos e grupos de mensagem.
- Conteúdo de campanha eleitoral, notas de partidos ou de adversários políticos, quando forem a única fonte.
- Páginas que só reproduzem título sem conteúdo (fazendas de conteúdo e sites de SEO).
- Reescritas automáticas de outros veículos (ex.: páginas marcadas "ia-auto" ou com "Fonte de referência: …" no rodapé). Abra e cite a matéria original.
- Notícias sobre municípios homônimos de outros estados. Confirme sempre a UF.
- Fatos sem vínculo com agente público ou com a administração municipal ou estadual paulista.

## Links

- Antes de gravar, abra o link e confirme que a página trata do fato. Não grave links montados ou deduzidos.
- HTTP 403 com página de desafio anti-robô (comum em MPSP, g1, Poder360) não é link quebrado. Grave o link e anote "acesso automatizado bloqueado; abre no navegador" no resumo.
- Link fora do ar: procure fonte equivalente. Sem substituto, mantenha o registro se houver outra fonte na base; se era a única fonte, sinalize nas pendências para decisão do usuário. Não apague o registro por conta própria.
