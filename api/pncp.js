// Contratos de uma empresa com órgãos municipais e estaduais de SP, consultados na hora no
// Portal Nacional de Contratações Públicas (PNCP). Intermediário simples: o PNCP não aceita
// consulta direta de outro site pelo navegador. Não guarda nada; resposta em cache por 1 dia.
const ESF = { M: 'Municipal', E: 'Estadual' };

async function pagina(cnpj, pag) {
  const u = 'https://pncp.gov.br/api/search/?' + new URLSearchParams({
    q: '"' + cnpj + '"', tipos_documento: 'contrato', ufs: 'SP',
    pagina: String(pag), tam_pagina: '100', ordenacao: '-data'
  });
  const ac = new AbortController(); const t = setTimeout(() => ac.abort(), 9000);
  try {
    const r = await fetch(u, { signal: ac.signal, headers: { Accept: 'application/json', 'User-Agent': 'OISP/1.0 (oisp.vercel.app)' } });
    if (!r.ok) throw new Error('PNCP ' + r.status);
    return await r.json();
  } finally { clearTimeout(t); }
}

module.exports = async (req, res) => {
  const cnpj = String((req.query && req.query.cnpj) || '').replace(/\D/g, '');
  res.setHeader('Access-Control-Allow-Origin', '*');
  if (cnpj.length !== 14) { res.status(400).json({ erro: 'informe um CNPJ com 14 dígitos' }); return; }
  try {
    const G = new Map(); let total = 0, lidos = 0, pag = 1;
    for (; pag <= 5; pag++) {
      const d = await pagina(cnpj, pag); const its = d.items || [];
      if (pag === 1) total = d.total || 0;
      lidos += its.length;
      for (const x of its) {
        if ((x.fornecedor_ni || '') !== cnpj || x.cancelado || !ESF[x.esfera_id]) continue;
        const esf = ESF[x.esfera_id];
        const mun = esf === 'Estadual' ? 'Governo do Estado de SP' : (x.municipio_nome || '');
        const k = (x.orgao_nome || '') + '|' + mun + '|' + esf;
        const g = G.get(k) || { o: x.orgao_nome || '', m: mun, e: esf, n: 0, v: 0, d1: '', d2: '', l: '', obj: '', x: 0 };
        const dt = String(x.data_assinatura || '').slice(0, 10);
        let vv = Number(x.valor_global || 0);
        if (vv > 1e9) { g.x++; vv = 0; } // acima de R$ 1 bilhão num só contrato: provável erro de registro, fora da soma
        g.n++; g.v += vv;
        if (dt && (!g.d1 || dt < g.d1)) g.d1 = dt;
        if (dt && (!g.d2 || dt >= g.d2)) { g.d2 = dt; g.l = 'https://pncp.gov.br/app' + (x.item_url || ''); g.obj = String(x.description || '').slice(0, 200); }
        G.set(k, g);
      }
      if (its.length < 100) break;
    }
    const grupos = [...G.values()].map(g => Object.assign(g, { v: Math.round(g.v * 100) / 100 })).sort((a, b) => b.v - a.v || b.n - a.n);
    res.setHeader('Cache-Control', 'public, s-maxage=86400, stale-while-revalidate=604800');
    res.status(200).json({ cnpj, grupos, contratos: grupos.reduce((a, g) => a + g.n, 0), parcial: lidos < total, em: new Date().toISOString().slice(0, 10) });
  } catch (e) {
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).json({ erro: 'PNCP indisponível agora', motivo: String(e && (e.name === 'AbortError' ? 'tempo esgotado' : (e.message + (e.cause ? ' ' + (e.cause.code || e.cause.message || '') : ''))) || '').slice(0, 160) });
  }
};
