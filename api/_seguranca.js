// Proteções comuns das funções /api: só GET/HEAD, origem própria, limite de requisições por IP e validação do CNPJ.
// O limite é por instância (memória da função): barra rajadas de um mesmo IP; o cache da CDN (s-maxage) absorve o resto.
const JANELA = 60 * 1000, MAX = 30;           // até 30 consultas por minuto por IP em cada instância
const ORIGENS = /^https:\/\/(oisp\.vercel\.app|oisp-[a-z0-9-]+\.vercel\.app)$/;
const visto = new Map();

function ip(req) { return String(req.headers['x-real-ip'] || req.headers['x-forwarded-for'] || '').split(',')[0].trim() || 'sem-ip'; }

function limite(req) {
  const k = ip(req), agora = Date.now(); const v = (visto.get(k) || []).filter(t => agora - t < JANELA);
  v.push(agora); visto.set(k, v);
  if (visto.size > 5000) for (const [kk, vv] of visto) if (!vv.length || agora - vv[vv.length - 1] > JANELA) visto.delete(kk);
  return v.length <= MAX ? 0 : Math.ceil((JANELA - (agora - v[0])) / 1000);
}

// dígitos verificadores do CNPJ
function cnpjValido(c) {
  if (!/^\d{14}$/.test(c) || /^(\d)\1{13}$/.test(c)) return false;
  const dv = (s, p) => { let t = 0; for (let i = 0; i < p.length; i++) t += +s[i] * p[i]; const r = t % 11; return r < 2 ? 0 : 11 - r; };
  const p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], p2 = [6, ...p1];
  return dv(c, p1) === +c[12] && dv(c, p2) === +c[13];
}

// devolve true quando a requisição pode seguir; caso contrário já respondeu
function proteger(req, res) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'");
  const o = String(req.headers.origin || '');
  if (o && ORIGENS.test(o)) { res.setHeader('Access-Control-Allow-Origin', o); res.setHeader('Vary', 'Origin'); }
  if (req.method === 'OPTIONS') { res.setHeader('Access-Control-Allow-Methods', 'GET'); res.status(204).end(); return false; }
  if (req.method !== 'GET' && req.method !== 'HEAD') { res.setHeader('Allow', 'GET'); res.status(405).json({ erro: 'método não permitido' }); return false; }
  if (o && !ORIGENS.test(o)) { res.status(403).json({ erro: 'origem não permitida' }); return false; }
  const s = limite(req);
  if (s) { res.setHeader('Retry-After', String(s)); res.setHeader('Cache-Control', 'no-store'); res.status(429).json({ erro: 'muitas consultas seguidas; tente de novo em instantes' }); return false; }
  return true;
}

module.exports = { proteger, cnpjValido };
