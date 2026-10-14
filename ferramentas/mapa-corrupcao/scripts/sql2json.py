"""Converte o SQL gerado pelos scripts (insert ... values (...) on conflict ...) em lotes JSON e
envia para a função de carga em massa carga_observatorio (ver SKILL.md, "Carga em massa").
Uso: TOKEN_CARGA=<token> python3 sql2json.py arquivo1.sql [arquivo2.sql ...]
"""
import re, json, sys, os, urllib.request
URL = 'https://pobqpofsieryoxzmaefb.supabase.co/rest/v1/rpc/carga_observatorio'
KEY = 'sb_publishable_gBUswVFIKZfF13iNt7UW5Q_zlXZeXoQ'
def enviar(tabela, linhas, lote=500):
    tok = os.environ['TOKEN_CARGA']; tot = 0
    for i in range(0, len(linhas), lote):
        body = json.dumps({'token': tok, 'tabela': tabela, 'linhas': linhas[i:i+lote]}, ensure_ascii=False).encode()
        r = urllib.request.Request(URL, data=body, headers={'apikey': KEY, 'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
        tot += json.load(urllib.request.urlopen(r, timeout=300))
    print(tabela, tot)
def valores(s):
    out=[]; i=0; n=len(s)
    while i<n:
        c=s[i]
        if c in ' ,': i+=1; continue
        if c=="'":
            j=i+1; buf=''
            while True:
                if s[j]=="'" and j+1<n and s[j+1]=="'": buf+="'"; j+=2; continue
                if s[j]=="'": break
                buf+=s[j]; j+=1
            i=j+1
            if s.startswith('::int',i): out.append(int(buf) if buf else None); i+=5; continue
            if s.startswith("::text[]",i): out.append([]); i+=8; continue   # '{}'::text[]
            out.append(buf); continue
        if s.startswith('array[',i):
            j=s.index(']::text[]',i); out.append(valores(s[i+6:j])); i=j+9; continue
        if s.startswith('current_date',i): out.append(None); i+=12; continue
        m=re.match(r'(null|true|false|-?\d+(?:\.\d+)?)(::int)?',s[i:])
        v=m.group(1); out.append(None if v=='null' else True if v=='true' else False if v=='false' else (float(v) if '.' in v else int(v))); i+=m.end(); continue
    return out
def parse(arquivos):
    T={}
    for f in arquivos:
        for l in open(f,encoding='utf-8'):
            m=re.match(r'insert into (\w+) \(([^)]*)\) values \((.*)\) on conflict',l.strip())
            if not m: continue
            cols=m.group(2).split(','); vals=valores(m.group(3))
            assert len(cols)==len(vals),(l[:200],len(cols),len(vals))
            T.setdefault(m.group(1),[]).append(dict(zip(cols,vals)))
    return T
if __name__=='__main__':
    T=parse(sys.argv[1:])
    for t,rows in T.items():
        if t.endswith('consultas'):  # última ocorrência vence
            d={}; [d.__setitem__((r['nome'],r['tipo']),r) for r in rows]; rows=list(d.values())
        print(t,len(rows)); enviar(t,rows,500)
