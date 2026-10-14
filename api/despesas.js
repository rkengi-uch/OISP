// Despesas municipais pagas a um fornecedor (CNPJ), no Portal da Transparência Municipal do TCE-SP
// (https://transparencia.tce.sp.gov.br/despesas-fornecedor). Consulta a exportação CSV do portal, um exercício por vez,
// só o evento "Pagamento" (ou "Liquidação", com ev=liq), e devolve os totais por município e órgão. O município de São Paulo (capital) não está na
// jurisdição do TCE-SP e não aparece. Intermediário simples (o portal não aceita consulta direta de outro site pelo
// navegador); não guarda nada; resposta em cache por 1 dia.
// Observação: na exportação CSV, o código do exercício está deslocado em relação ao formulário (1 = 2025, 2 = 2024…);
// por isso o ano é sempre lido da própria linha. O exercício corrente pode não sair na exportação: a resposta avisa.
const BASE = 'https://transparencia.tce.sp.gov.br/despesas-fornecedor';
const LIM = 10000; // a exportação devolve no máximo 10 mil linhas por consulta

function csvLinhas(txt) { // CSV com ";" e campos entre aspas que podem ter quebra de linha
  const out = []; let row = [], f = '', q = false;
  for (let i = 0; i < txt.length; i++) {
    const c = txt[i];
    if (q) { if (c === '"') { if (txt[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; continue; }
    if (c === '"') q = true; else if (c === ';') { row.push(f); f = ''; }
    else if (c === '\n') { row.push(f); out.push(row); row = []; f = ''; } else if (c !== '\r') f += c;
  }
  if (f || row.length) { row.push(f); out.push(row); }
  return out;
}
const num = v => Number(String(v || '0').replace(/\./g, '').replace(',', '.')) || 0;

async function exercicio(cnpj, id, ev) {
  const u = BASE + '/csv?' + new URLSearchParams({ nr_identificador_despesa: cnpj, exercicio: String(id), mes: 'All', evento: ev, municipio: 'All', _format: 'csv' });
  let erro;
  for (let t = 0; t < 3; t++) {
    const ac = new AbortController(); const tm = setTimeout(() => ac.abort(), 20000);
    try {
      const r = await fetch(u, { signal: ac.signal, headers: { 'User-Agent': 'OISP/1.0 (oisp.vercel.app)', Accept: 'text/csv' } });
      if (!r.ok) throw new Error('TCE-SP ' + r.status);
      const L = csvLinhas((await r.text()).replace(/^﻿/, ''));
      return L.slice(1).filter(x => x.length >= 10);
    } catch (e) { erro = e; await new Promise(r => setTimeout(r, 400 * (t + 1))); } finally { clearTimeout(tm); }
  }
  throw erro;
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const cnpj = String((req.query && req.query.cnpj) || '').replace(/\D/g, '');
  const liq = String((req.query && req.query.ev) || '') === 'liq'; // liquidado (evento 4) ou pago (evento 5, padrão)
  const EV = liq ? '4' : '5', RX = liq ? /liquid/i : /pago/i;
  if (cnpj.length !== 14) { res.status(400).json({ erro: 'informe um CNPJ com 14 dígitos' }); return; }
  try {
    const ids = Array.from({ length: 13 }, (_, i) => i + 1);
    const falhas = []; let parcial = false;
    const lotes = await Promise.all(ids.map(id => exercicio(cnpj, id, EV).then(L => { if (L.length >= LIM) parcial = true; return L; }).catch(() => { falhas.push(id); return []; })));
    const G = new Map(), A = {}; let total = 0, n = 0, nome = '';
    lotes.flat().forEach(x => {
      const [mun, ano, org, , ev, emp, doc, forn, dt, val, fun] = x;
      if (!RX.test(ev || '')) return;
      if (doc && !String(doc).replace(/\D/g, '').endsWith(cnpj)) return;
      const v = num(val); nome = nome || forn || '';
      const k = mun + '|' + org; const g = G.get(k) || { m: mun, o: org, v: 0, n: 0, a1: ano, a2: ano, f: {} };
      g.v += v; g.n++; if (ano < g.a1) g.a1 = ano; if (ano > g.a2) g.a2 = ano; if (fun) g.f[fun] = (g.f[fun] || 0) + v; G.set(k, g);
      A[ano] = (A[ano] || 0) + v; total += v; n++;
    });
    const grupos = [...G.values()].map(g => ({ m: g.m, o: g.o, v: Math.round(g.v * 100) / 100, n: g.n, a1: g.a1, a2: g.a2, f: Object.entries(g.f).sort((a, b) => b[1] - a[1]).slice(0, 2).map(x => x[0]) })).sort((a, b) => b.v - a.v);
    const anos = Object.keys(A).sort();
    res.setHeader('Cache-Control', falhas.length ? 'no-store' : 'public, s-maxage=86400, stale-while-revalidate=604800');
    res.status(200).json({ cnpj, ev: liq ? 'liq' : 'pag', nome, total: Math.round(total * 100) / 100, pagamentos: n, municipios: new Set(grupos.map(g => g.m)).size, grupos, anos: anos.map(a => [a, Math.round(A[a] * 100) / 100]), parcial, falhas: falhas.length, em: new Date().toISOString().slice(0, 10) });
  } catch (e) {
    res.setHeader('Cache-Control', 'no-store');
    res.status(502).json({ erro: 'Portal do TCE-SP indisponível agora', motivo: String(e && e.message || '').slice(0, 160) });
  }
};
