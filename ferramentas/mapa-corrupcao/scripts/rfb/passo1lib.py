import zipfile, io
def linhas(z):
    with zipfile.ZipFile(z) as zf:
        n=zf.namelist()[0]
        with zf.open(n) as f:
            for ln in io.TextIOWrapper(f,encoding='latin-1',newline=''):
                yield ln.rstrip('\r\n')[1:-1].split('";"')
