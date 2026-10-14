# Esquema da BASE MESTRE

## Abas

| Aba | Conteúdo | A tarefa diária altera? |
|---|---|---|
| Leia-me | Escopo, estrutura, ressalva de presunção de inocência, data-base | Só a data-base |
| Base_Registros | Um registro por agente e por evento | Sim (inclui e atualiza) |
| Municipios | Os 645 municípios do modelo LISTA, com contagens por fórmula | Não (as fórmulas recalculam sozinhas) |
| Tipificação | As 7 categorias, com contagens por fórmula | Não |
| Operacoes | Síntese por operação | Sim (acrescenta operações novas) |
| Crime_Organizado | Evidências de facção no setor público: município, setor, origem, vínculo, link | Sim, quando houver |
| Citados_sem_agente | Municípios citados em operações sem agente político identificado | Sim, quando houver |
| Fontes | Legenda A–F / 1–6 e contagens por combinação | Não |
| Verificacao_links | Teste de links | Não (é tarefa de revisão periódica) |
| CNM_2012_SP / CNM_2012_Brasil | Série histórica de afastamentos | Não |
| Log_Atualizacoes | Histórico de cada alteração automática | Sim (sempre) |

Se `Log_Atualizacoes` não existir, crie-a com as colunas: `Data da execução | ID | Ação (inclusão/atualização/descarte) | Campo | Valor anterior | Valor novo | Link da fonte`.

## Colunas de Base_Registros

As colunas A–O seguem exatamente o modelo LISTA.xlsx. Não renomeie nem reordene.

| Col. | Nome | Preenchimento |
|---|---|---|
| A | Código IBGE | 7 dígitos, conforme a aba Municipios. Obrigatório. |
| B | Código Sefaz-SP | Conforme a aba Municipios |
| C | Município | Grafia da aba Municipios. Casos estaduais: "São Paulo" |
| D | Nome | Nome do agente, como consta na fonte. Vazio se não identificado |
| E | Cargo | Prefeito, Vice-Prefeito, Ex-Prefeito, Secretário Municipal, Vereador, Presidente da Câmara, Servidor/Agente estadual |
| F | Descrição | 2 a 5 frases: fato, órgão, data, valores e situação. Redação neutra e atribuída |
| G | Condenacao | "Não"; "Sim (1ª instância)"; "Sim (2ª instância)"; "Sim (trânsito em julgado)" |
| H | Afastamento | "Sim" ou "Não" |
| I | Crime | Uma das 7 tipificações (ver SKILL.md, seção 3) |
| J | Operacao | Nome da operação, sem a palavra "Operação". Sem nome: "[Órgão] – [tema] [ano]" |
| K | Orgao Investigativo | Ex.: MPSP/Gaeco; PF; Polícia Civil; CGU; TCE-SP; TRE-SP; Câmara Municipal |
| L | Ano | Ano do evento (AAAA) |
| M | Empresa | Razão social citada pela fonte; vazio se não houver |
| N | CNPJ | Só se a fonte informar. Nunca inferir |
| O | link | Fonte principal (a de melhor credibilidade) |
| P | ID | Sequencial, continuando o maior ID existente |
| Q | Esfera | "Municipal" ou "Estadual" |
| R | Data do evento | dd/mm/aaaa (data da medida, não da notícia) |
| S | Medida | Ver lista abaixo |
| T | Crimes apurados | Ex.: "Peculato; fraude a licitação; associação criminosa" |
| U | Situação processual | Estado mais recente conhecido, com data. Ex.: "Réu desde 12/03/2026; ação em curso na 2ª Vara de X" |
| V | Qtd agentes | 1 por agente; >1 só em registro coletivo (ex.: "13 vereadores"); 0 se não houver agente identificado |
| W | Fonte (veículo) | Ex.: "MPSP (nota oficial)"; "g1"; "Estadão" |
| X | Credibilidade | A1, B2, C2 ou C3 |
| Y | Link complementar | Outras fontes, separadas por " ; " |
| Z | Setor | Setores do crime organizado (quando aplicável), separados por ";" |
| AA | Vínculo | "direto" / "indireto" (quando houver Setor) |
| AB | Status de validação | "Pendente" (padrão da tarefa) ou "Validado" (só o usuário marca) |
| AC | Data da coleta | dd/mm/aaaa da execução que incluiu ou atualizou |

Se as colunas Z–AC ainda não existirem, crie-as nessa ordem, sem mover as anteriores. Os registros antigos recebem `Status de validação = Validado`, porque já foram revisados nas edições anteriores do estudo.

## Valores de "Medida"

Busca e apreensão; Prisão temporária; Prisão preventiva; Afastamento cautelar; Indisponibilidade de bens; Instauração de inquérito/PIC; Ação de improbidade ajuizada; Denúncia oferecida; Denúncia recebida (réu); Cassação (Câmara); Cassação (Justiça Eleitoral); Condenação 1ª instância; Condenação 2ª instância; Trânsito em julgado; Absolvição; Arquivamento; Trancamento/anulação por tribunal; Retorno ao cargo.

## Exemplo de registro (fictício, só para formato)

```
A 3599999 | C Município Exemplo | D Fulano de Tal | E Prefeito
F Prefeito foi afastado do cargo por 180 dias por decisão do TJSP, a pedido do MPSP/Gaeco, na Operação Exemplo, que apura fraude em contratos de coleta de lixo estimados em R$ 12 milhões (2021–2024), segundo nota do MPSP. Cabe recurso.
G Não | H Sim | I Organização Criminosa | J Exemplo | K MPSP/Gaeco | L 2026
O [link da nota do MPSP] | P [próximo ID] | Q Municipal | R 15/09/2026 | S Afastamento cautelar
T Fraude a licitação; organização criminosa | U Afastado desde 15/09/2026; investigação em curso
V 1 | W MPSP (nota oficial) | X A1 | Y [link g1] | Z Coleta de lixo e limpeza urbana | AA direto
AB Pendente | AC 16/09/2026
```
