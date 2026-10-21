#!/usr/bin/env python3
"""Aplica a janela móvel de 10 anos ao DATA de um painel já gerado (sem consultar o Supabase).

Uso: python3 janela10.py <index.html> [saida.html]

Use quando o DATA for editado diretamente (sem gerar_painel.py, que já aplica a janela).
Grava janela_retirados.json e janela_retirados.sql ao lado da saída; rode o .sql no Supabase
(tabela fatos_fora_janela; itens repetidos são ignorados).
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gerar_painel import janela10, janela_saida, substituir, meta_qualidade

entrada = sys.argv[1]; saida = sys.argv[2] if len(sys.argv) > 2 else entrada
html = open(entrada, encoding='utf-8').read()
k = html.find('<!DOCTYPE html>')
if k > 0: html = html[k:]
i = html.find('const DATA = ') + len('const DATA = ')
D, fim = json.JSONDecoder().raw_decode(html[i:])
corte, fora = janela10(D)
data_base = None
import re
m = re.search(r'DATA-BASE\s+([\d/]+)', html)
if m: data_base = m.group(1)
try: D['META'] = meta_qualidade(D)
except Exception as e: print('aviso: metadados de qualidade não recalculados:', e, file=sys.stderr)
try:
    html = substituir(html, D, data_base)          # troca o DATA e recalcula cabeçalho e legenda
except Exception as e:
    print('aviso: substituir() falhou (', e, '); só o DATA foi trocado', file=sys.stderr)
    html = html[:i] + json.dumps(D, ensure_ascii=False, separators=(',', ':')) + html[i + fim:]
open(saida, 'w', encoding='utf-8').write(html)
janela_saida(corte, fora, os.path.dirname(os.path.abspath(saida)), data_base)

