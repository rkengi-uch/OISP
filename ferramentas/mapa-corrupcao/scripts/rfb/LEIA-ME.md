# Base CNPJ da Receita (2 camadas), risco "empresas de envolvidos" e índice único de entidades

Pastas de trabalho esperadas: `/home/claude/rfb` (scripts e arquivos baixados) e `/home/claude/p2` (painel: `index.html` publicado sem o invólucro e `dados/`).
Copie esta pasta para `/home/claude/rfb` antes de começar (`cp -r <skill>/scripts/rfb/. /home/claude/rfb/`). `sal.txt` é o sal do identificador interno das pessoas: mantenha o mesmo arquivo para que os IDs não mudem e nunca o publique.

1. Baixar (mês mais recente em Dados/Cadastros/CNPJ/AAAA-MM; ajuste o mês em `baixar.sh`): Socios0-9, Empresas0-9, Estabelecimentos0-9, Municipios, Naturezas, Qualificacoes, Cnaes.
   `cd /home/claude/rfb/zip && cat ../lista.txt | xargs -P 8 -n 1 ../baixar.sh` (WebDAV público do SERPRO, usuário = token do compartilhamento). Arquivos grandes aceitam `curl -r` em partes paralelas.
2. `python3 sementes.py` → sementes.json (CNPJs e nomes citados no painel, com municípios).
3. `python3 passo1.py` (sócios das empresas-semente e linhas com nome igual às pessoas-semente), `python3 passo2.py` (2ª camada), `python3 passo3.py emp`, `python3 passo3.py est`.
4. `python3 receita.py` → rfb_full.json e envolvidos.json. Regras: pessoa do painel só é ligada a uma empresa se a empresa fica no município ligado à pessoa (`mun`) ou se o nome tem 4+ palavras significativas e é único entre sócios de empresas paulistas (`sp`, sempre "verificar homonímia"); nomes com 5+ cadastros no país ou 2+ aceitos também levam o alerta. Até 40 empresas por pessoa (SP primeiro) e 30 sócios por empresa.
5. `python3 rk_pncp.py` → pncp_cache.json (busca no PNCP em lotes de 40 CNPJs com OR; só empresas ativas, inaptas ou suspensas; matriz + até 9 filiais paulistas ativas).
6. `python3 rfb_painel.py` → dados/receita.json; `python3 entidades.py` → dados/entidades.json (índice único do autocompletar). Rode `entidades.py` sempre que entrarem nomes ou empresas novos no painel.
7. Publique `dados/receita.json` e `dados/entidades.json` junto com o painel (parâmetro files) e grave no Supabase: rfb_empresas, rfb_socios, rfb_vinculos, risco_empresas_envolvidos (carga em massa, coluna `chave`).
