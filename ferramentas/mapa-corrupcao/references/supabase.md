# Base mestre no Supabase

Projeto: `pobqpofsieryoxzmaefb` (https://pobqpofsieryoxzmaefb.supabase.co). Use sempre esse `project_id` nas ferramentas do conector Supabase.

Segurança: todas as tabelas têm RLS ligado, com leitura pública (dados ostensivos) e nenhuma política de escrita. Só o conector (papel de serviço) grava. Nunca crie políticas de escrita para `anon` nem exponha chaves secretas no painel.

## Tabelas e correspondência com o painel (`DATA`)

### `registros` → `DATA.R` (um registro por agente e por evento)

| Coluna | Painel | Observação |
|---|---|---|
| id (PK) | id | `R` + número sequencial. Nunca reutilizar |
| municipio | mun | Casos estaduais: "São Paulo" |
| gi | gi | Índice do município no mapa. Copie de outro registro do mesmo município |
| nome, cargo | nome, cargo | |
| descricao | desc | Redação neutra e atribuída (SKILL.md, seção 5) |
| condenacao | cond | "Não", "Não (investigado)", "Não (réu)", "Sim (1ª instância)", "Sim (2ª instância – TRE)"… |
| afastamento | afast | "Sim" / "Não" |
| tipificacao | tip | Uma das 7 tipificações |
| crimes_apurados | crimes | |
| operacao, fase | op, fase | `fase` = operação, salvo desdobramento nomeado |
| orgao_investigativo | orgao | |
| ano, data_evento | ano, data | `data_evento` em dd/mm/aaaa; preencha também `data_evento_iso` (date) |
| medida | medida | Lista em `esquema-base.md` |
| situacao | situacao | Estado mais recente, com data |
| empresa, link, link2, fonte, credibilidade | empresa, link, link2, fonte, cred | `credibilidade` só aceita A1, B2, C2, C3 |
| qtd | qtd | 1 por agente |
| esfera, nivel, orgao_estadual | esfera, nivel, orgest | Estadual: municipio "Governo do Estado de SP", gi nulo, nivel "Estadual", esfera "Executivo estadual", orgao_estadual = órgão |
| setor_co, vinculo_co | co, co_vinc | Crime organizado: setor(es) separados por ";" e "direto"/"indireto" |
| status_validacao | val | "Pendente" (padrão da rotina) ou "Validado" |
| data_coleta, validado_em | coleta, validado | dd/mm/aaaa |
| historico | hist | JSON opcional |

### Camadas por nome e por empresa (desde 06/10/2026)

- `tjsp2_consultas` / `tjsp2_processos` → `DATA.TJ2` (`consultas` = nº de nomes consultados; `processos`: nome, tipo, registros, numero, link, area, classe, assunto, papel, parte, orgao, receb, orig, conf). Chave única: (nome_consultado, numero, codigo). `originaria` = ação que começou no TJ.
- `cnia_consultas` / `cnia_condenacoes` → `DATA.CNIA` (`itens`: nome, tipo, origem[], registros[], ncnia, numero, tribunal, grau, comarca, vara, julg, data, ress, cargo, susp, ineleg, proib, penas, link, conf). Chave única: (nome_consultado, seq_condenacao).
- `sancoes_empresas` (PK cadastro+codigo) e `sancoes_contratos` (único numero_controle+codigo_sancao) → `DATA.SANC` = {ref, outros, n_sancoes, emp[], con[]}; o gerador usa só a carga mais recente (`atualizado_em`) e só contratos com `aplicavel`. Nunca grave CPF de pessoa física.

- `tcu_listas` (único lista+nome+processo; `lista` = ci, el, in ou id; sem CPF) e `tcu_importacoes` → `DATA.TCU` = {meta: {importado, listas}, itens: [{l, nome, tipo, cnpj, mun, munr, gi, proc, lproc, ac, lac, dac, tj, fim, base}]}.

- `pessoas` (único `chave`) → `DATA.PES` (só nomes com apelido, chave alternativa ou possível homônimo: {n: nome, k: chave + chaves_alias, ap: apelidos, va: variantes, m: municipios, h: possivel_homonimo}). Colunas: chave, nome, apelidos[], chaves_alias[], variantes[] ("(a conferir)" = grafia achada no TJSP pela busca parcial), camadas[], municipios[], cargos[], registros[], possivel_homonimo, mesma_pessoa_que e observacao (manuais, nunca sobrescritos), atualizado_em. Gerada por `scripts/pessoas.py`.
- `DATA.META` (sem tabela própria): calculado pelo `gerar_painel.py` (`meta_qualidade`) com a data mais recente de cada camada, validação da base, situação dos links das notícias e pontos de atenção; alimenta a aba Metodologia.
- Arquivos separados do HTML (`separar_camadas`): `dados/tcu.json` (itens de `DATA.TCU`), `dados/sancoes.json` ({emp, con} de `DATA.SANC`) e `dados/pareceres_txt.json` ({processo: íntegra}). Publique-os junto com o painel (parâmetro `files`).

- `tce_impedimentos` (chave; lista contrato/repasse; sem CPF/RG) e `tce_impedimentos_contratos` (só `aplicavel` e não cancelados entram) → `DATA.IMP` = {ref, n, napl, lazy} + `dados/impedimentos.json` {itens: [{l, n, c, pf, o, m, gi, nv, i, t, tr, tp, al, mo, p}], con: [{c, n, oa, ma, i, t, tp, al, f, o, m, e, num, obj, ass, v, link}]}; o gerador usa a `referencia` mais recente.
- `qsa_empresas` (PK cnpj) e `qsa_socios` (chave cnpj|nome|qualificação; sem CPF) → `DATA.QSA` = {ref, n_emp, n_soc, rel, lazy} + `dados/qsa.json` {emp: {cnpj: [razão, situação, município, uf, abertura, cnae]}, soc: {cnpj: [[nome, qualificação, entrada, tipo]]}}.
- `relacoes_societarias` (chave cnpj|sócio|qualificação; `mesma_pessoa` e `observacao` manuais; `mesma_pessoa='nao'` sai do painel) → `DATA.QSA.rel` [{s, q, de, pk, pn, reg, mp, el, cf, c, e, se, me, ue, or, conf}].
- `tse_candidaturas` (chave ano|sq; eleitos de 2024, barradas por LC 64/90 em 2020/2024 e candidaturas ligadas ao cadastro; sem CPF nem título), `tse_doacoes` (sq|cnpj|doador) e `tse_fornecedores` (sq|cnpj) → `DATA.TSE` = {meta, lazy} + `dados/tse.json` {fl, cand, doa, forn}.

- `agenda` → `DATA.AGENDA` [{d (aaaa-mm-dd), p (dia/estimada), mun, gi, t, desc, esf, fonte, link, st, reg}]; eventos de "O que acompanhar".

### Demais tabelas

- `citados_sem_agente` → `DATA.CIT`: municipio, gi, operacao, ano, orgao, obs, link, setor_co, nivel, orgao_estadual, status_validacao, validado_em, ordem.
- `crime_organizado` → `DATA.CO`: gi, municipio, setores (text[]), origem ("Base curada (agente político)" ou "Operação/entidade (pesquisa)"), vinculo, operacao, descricao, link, ano, cargos (text[] ou null), medidas (text[] ou null), orgao, nivel, ordem.
- `operacoes` → `DATA.OPQ`: nome (PK), consulta (busca sugerida no card da operação).
- `operacao_fontes` → `DATA.OPLINKS`: operacao, ordem, tipo ("Oficial" ou "Imprensa"), fonte, titulo, url.
- `log_atualizacoes` → `DATA.LOG`: data (dd/mm/aaaa), registro_id, acao, campo, antes, depois, link.
- `noticias` → `DATA.NEWS` (só linhas com `link_status` nulo ou `ativo`); coluna `fora_do_escopo` (motivo da retirada; nulo = pertinente; o painel só exibe as nulas); colunas de verificação: `link_status` (ativo/inativo/indeterminado), `link_motivo`, `link_verificado_em`; `item` guarda o vetor de 15 posições; municipio, data, titulo, url, gi e ano são cópias para consulta. Posições de `item`: 0 `gi` do município; 1 ano; 2 índice do tema em `TEMAS`; 3 título; 4 URL; 5 resumo em 1–2 frases (redação própria); 6 operação ("" se não houver); 7 marcadores somados (1 operação, 4 cita agente político, 8 sinal de irregularidade, 16 sinal qualificado, 32 crime organizado); 8 cargos citados ("Prefeito; Vereador"); 9 medidas ("Prisão; Afastamento"); 10 data dd/mm/aaaa; 11 município; 12 famílias de sinal somadas (1 corrupção e desvio, 2 fraude em contratos, 4 investigação e operação, 8 controle externo, 16 responsabilização, 32 nepotismo); 13 quantidade de sinais; 14 órgão ("MPSP/Gaeco").

Inserção de notícia (ordem = maior + 1):
```sql
insert into noticias (ordem, gi, ano, municipio, data, titulo, url, item, link_status, link_verificado_em)
select coalesce(max(ordem),0)+1, 59, 2026, 'Bauru', '30/09/2026', 'Título…', 'https://…',
  jsonb_build_array(59, 2026, 2, 'Título…', 'https://…', 'Resumo…', 'Cavalo de Troia', 29, 'Prefeito', 'Investigação/busca', '30/09/2026', 'Bauru', 22, 7, 'MPSP/Gaeco'), 'ativo', current_date
from noticias
where not exists (select 1 from noticias where url = 'https://…');
```
- `SHOTS` (recortes de manchetes) ficam no próprio painel, não no Supabase: o `gerar_painel.py` preserva os do painel e acrescenta os de `--recortes`.
- `tjsp_consultas` e `tjsp_processos` → `DATA.TJSP` (seção "Processos no TJSP"): resumo por nome consultado no e-SAJ (1º grau) e processos de interesse público localizados, com link, classe, assunto, participação, foro, distribuição e confiança (`alta` ou `verificar homonímia`). Atualização mensal ou sob pedido; nunca incluir processos em que a pessoa é vítima/testemunha nem causas privadas (família, execuções fiscais, trabalhistas).
- `contas_irregulares_tce` → `DATA.TCE.itens` (seção "Contas irregulares (TCE-SP)" e camada do mapa): responsavel, papel, grupo, materia, processo_tc, origem, municipio, gi, nivel (Municipal/Estadual/Intermunicipal), exercicio, transito_julgado, transito_iso, lista_periodo, lista_atualizacao, fonte_xlsx. Tabela substituída por inteiro pela Edge Function `atualizar-contas-tce`; não edite linhas à mão.
- `tce_importacoes` → `DATA.TCE.meta`: histórico das execuções da função (importado / sem novidade / erro).
- `municipios`: gi, nome e nome normalizado dos municípios do mapa (usado pela função para localizar o órgão de origem).
- `pareceres_tce` → `DATA.PAR` (só os desfavoráveis; republicações do mesmo processo ficam uma vez): processo, processo_ref (reexame), municipio, gi, exercicio, prefeitos, relator, colegiado, data_sessao, data_publicacao, tipo (parecer/reexame), resultado (favorável/desfavorável), situacao (vigente / revertido em reexame), reexame_rev, ementa, decisao, texto (íntegra extraída, exibida no painel em "Ler a íntegra"), edicao_url, pagina, link_doe. O painel não usa o PDF direto (o visualizador de PDF do navegador é bloqueado dentro do Claude): abre a edição pelo visualizador do Google (`https://docs.google.com/viewer?url=` + URL do PDF) e mostra a íntegra em janela própria. Ato distinto de `contas_irregulares_tce` (julgamento).
- `boletins` → `DATA.BOL` (boletim mensal; referencia 'AAAA-MM', rotulo, publicado_em, conteudo JSON — ver SKILL.md, seção 6C).
- `referencias`: chave/valor JSON para CNM, ENT, FAMS, TEMAS, PORTAIS, COSET, NEWS_ADD e `DATA_BASE` (a cópia de SHOTS guardada ali é histórica).

## SQL de exemplo

Próximo ID:
```sql
select 'R' || (max(substring(id from 2)::int) + 1) as proximo from registros;
```

Deduplicação (mesmo agente, operação e medida):
```sql
select id, medida, data_evento, situacao from registros
where unaccent(lower(nome)) = unaccent(lower('Fulano de Tal')) and operacao = 'Exemplo';
```
(Se `unaccent` não estiver disponível, compare com `lower()`.)

Inclusão de registro pendente:
```sql
insert into registros (id, municipio, gi, nome, cargo, descricao, condenacao, afastamento, tipificacao,
  crimes_apurados, operacao, fase, orgao_investigativo, ano, data_evento, data_evento_iso, medida, situacao,
  empresa, link, link2, fonte, credibilidade, qtd, esfera, nivel, orgao_estadual, setor_co, vinculo_co,
  status_validacao, data_coleta)
values ('R194', 'Exemplo', 123, 'Fulano de Tal', 'Prefeito', '...', 'Não (investigado)', 'Sim',
  'Crime Comum', 'Fraude a licitação', 'Exemplo', 'Exemplo', 'MPSP (Gaeco)', 2026, '15/09/2026', '2026-09-15',
  'Busca e apreensão', 'Investigado', '', 'https://…', '', 'Metrópoles', 'B2', 1, 'Executivo', 'Municipal', '',
  null, null, 'Pendente', '28/09/2026');
insert into log_atualizacoes (data, registro_id, acao, campo, antes, depois, link)
values ('28/09/2026', 'R194', 'inclusão', '', '', 'Busca e apreensão – Exemplo', 'https://…');
```

Atualização com histórico:
```sql
with antigo as (select situacao from registros where id = 'R170')
insert into log_atualizacoes (data, registro_id, acao, campo, antes, depois, link)
select '28/09/2026', 'R170', 'atualização', 'Situação processual', antigo.situacao, 'Nova situação…', 'https://…' from antigo;
update registros set situacao = 'Nova situação…', atualizado_em = now() where id = 'R170';
```

Operação nova e suas fontes:
```sql
insert into operacoes (nome, consulta) values ('Exemplo', '"Operação Exemplo" município') on conflict (nome) do nothing;
insert into operacao_fontes (operacao, ordem, tipo, fonte, titulo, url)
values ('Exemplo', 1, 'Oficial', 'MPSP', 'Título da nota (15/09/2026)', 'https://…');
```

Data-base do painel:
```sql
update referencias set valor = '"28/09/2026"'::jsonb, atualizado_em = now() where chave = 'DATA_BASE';
```

Escape de aspas simples em SQL: duplique-as (`'d''Oeste'`).
