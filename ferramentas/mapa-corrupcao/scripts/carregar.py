#!/usr/bin/env python3
"""Carga em massa das camadas de impedimentos (TCE-SP), QSA e TSE pela função carga_observatorio.

Uso:  TOKEN_CARGA=<token> python3 carregar.py <tabela> <arquivo.json> [referencia aaaa-mm-dd]
Tabelas: tce_impedimentos, tce_impedimentos_contratos, qsa_empresas, qsa_socios, tse_candidaturas,
tse_doacoes, tse_fornecedores, relacoes_societarias.
O script calcula a coluna `chave` (identidade da linha), remove duplicatas e grava importado_em.
Campos manuais (relacoes_societarias.mesma_pessoa e observacao) nunca são enviados.
Ative e desative o token como descrito no SKILL.md ("Carga em massa").
"""
import datetime, json, os, sys, urllib.request

URL = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/rpc/carga_observatorio'
KEY = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
CHAVES = {
    'tce_impedimentos': lambda x: '|'.join(str(v or '') for v in (x['lista'], x.get('cnpj') or x['apenada'], x.get('codigo_orgao'), x.get('inicio'), x.get('processo'), (x.get('tipo') or '')[:40])),
    'tce_impedimentos_contratos': lambda x: '|'.join(str(v or '') for v in (x.get('numero_controle'), x.get('cnpj'), x.get('inicio'), (x.get('tipo') or '')[:40], x.get('orgao_apenador'))),
    'qsa_socios': lambda x: f"{x['cnpj']}|{x['nome_socio']}|{x.get('qualificacao')}",
    'tse_candidaturas': lambda x: f"{x['ano']}|{x['sq']}",
    'tse_doacoes': lambda x: f"{x['sq_candidato']}|{x['cnpj']}|{x['doador']}",
    'tse_fornecedores': lambda x: f"{x['sq_candidato']}|{x['cnpj']}",
    'relacoes_societarias': lambda x: f"{x['cnpj']}|{x['nome_socio']}|{x.get('qualificacao')}",
}

def enviar(tabela, linhas, lote=500):
    tok = os.environ['TOKEN_CARGA']; tot = 0
    for i in range(0, len(linhas), lote):
        body = json.dumps({'token': tok, 'tabela': tabela, 'linhas': linhas[i:i + lote]}, ensure_ascii=False).encode()
        r = urllib.request.Request(URL, data=body, headers={'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
        tot += json.load(urllib.request.urlopen(r, timeout=300))
    return tot

def main(tabela, arq, ref=None):
    L = json.load(open(arq, encoding='utf-8')); hoje = datetime.date.today().isoformat(); vis = {}
    for x in L:
        x = {k: v for k, v in x.items() if k not in ('mesma_pessoa', 'observacao')}
        if tabela in CHAVES: x['chave'] = CHAVES[tabela](x)[:500]
        if tabela in ('tce_impedimentos', 'tce_impedimentos_contratos'): x['referencia'] = ref or x.get('referencia') or hoje
        if tabela == 'qsa_empresas': x['consultado_em'] = x.get('consultado_em') or hoje
        elif tabela == 'qsa_socios': x['consultado_em'] = x.get('consultado_em') or hoje
        else: x['importado_em'] = hoje
        vis[x.get('chave') or x.get('cnpj')] = x
    print(tabela, enviar(tabela, list(vis.values())), 'linhas gravadas de', len(L))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
