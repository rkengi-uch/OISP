#!/usr/bin/env python3
"""Recorta a manchete (título) de notícias para a seção "Manchetes" do painel.

Uso:
  python3 recortar_manchete.py urls.txt recortes_novos.json [dd/mm/aaaa]

urls.txt: uma URL por linha (as notícias precisam estar também em `noticias`,
senão o painel não exibe o recorte). A data opcional vai no campo "cap"
(padrão: hoje).

Saída: lista JSON [{"u", "w", "h", "cap", "img"}], com a imagem JPEG em data URI,
no formato de DATA.SHOTS. URLs que não puderem ser recortadas são listadas na
saída de erro e ficam de fora (a notícia continua no rastreador).

O recorte reproduz só a manchete, para referência, e sempre leva à fonte.
"""
import base64, datetime, io, json, sys
from playwright.sync_api import sync_playwright
from PIL import Image

LARGURA_MAX = 720
ACEITAR = ['Aceitar', 'Aceito', 'Concordo', 'Entendi', 'OK', 'Aceitar todos', 'Aceitar e fechar', 'Continuar']

def recortar(pg, url):
    pg.goto(url, wait_until='domcontentloaded', timeout=45000)
    pg.wait_for_timeout(2500)
    for t in ACEITAR:                                  # banners de cookies
        try:
            b = pg.get_by_role('button', name=t, exact=True)
            if b.count() and b.first.is_visible():
                b.first.click(timeout=1500); pg.wait_for_timeout(500); break
        except Exception:
            pass
    alvo = None
    for sel in ['article h1', 'main h1', 'h1']:
        loc = pg.locator(sel)
        for i in range(min(loc.count(), 5)):
            el = loc.nth(i)
            try:
                if el.is_visible() and len((el.inner_text() or '').strip()) >= 15:
                    alvo = el; break
            except Exception:
                continue
        if alvo: break
    if not alvo:
        raise RuntimeError('manchete (h1) não encontrada')
    alvo.scroll_into_view_if_needed()
    pg.wait_for_timeout(400)
    bb = alvo.bounding_box()
    if not bb or bb['height'] < 20:
        raise RuntimeError('manchete sem área visível')
    pad = 14
    clip = {'x': max(bb['x'] - pad, 0), 'y': max(bb['y'] - pad, 0),
            'width': min(bb['width'] + 2 * pad, pg.viewport_size['width']), 'height': min(bb['height'] + 2 * pad, 420)}
    png = pg.screenshot(clip=clip)
    im = Image.open(io.BytesIO(png)).convert('RGB')
    if im.width > LARGURA_MAX:
        im = im.resize((LARGURA_MAX, round(im.height * LARGURA_MAX / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=72, optimize=True)
    return im.width, im.height, 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()

if __name__ == '__main__':
    urls = [l.strip() for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
    cap = sys.argv[3] if len(sys.argv) > 3 else datetime.date.today().strftime('%d/%m/%Y')
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 760, 'height': 1000}, device_scale_factor=1,
                        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
        for u in urls:
            try:
                w, h, img = recortar(pg, u)
                out.append({'h': h, 'u': u, 'w': w, 'cap': cap, 'img': img})
                print(f'ok: {u} ({w}x{h})', file=sys.stderr)
            except Exception as e:
                print(f'sem recorte: {u} — {str(e)[:120]}', file=sys.stderr)
        b.close()
    json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
