#!/bin/bash
B="https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/2026-09"
f=$1
for t in 1 2 3; do
  curl -s -m 7200 -u "gn672Ad4CF8N6TK:" -C - -o "$f" "$B/$f" && unzip -tq "$f" >/dev/null 2>&1 && { echo "ok $f"; exit 0; }
  sleep 5
done
echo "falhou $f"
