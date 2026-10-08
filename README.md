# Observatório da Integridade – SP (OISP) — front-end estático

Site estático: `index.html` + camadas em `dados/*.json`. Sem build.

## Publicar no Vercel (link público)
Opção 1 — terminal (Node instalado):
    cd oisp-vercel
    npx vercel login
    npx vercel deploy --prod
Na primeira vez, aceite as perguntas padrão (framework: "Other", sem build, diretório de saída ".").

Opção 2 — GitHub: suba esta pasta para um repositório e, em vercel.com/new, importe o repositório (Framework Preset: Other; Build Command vazio; Output Directory: .).

## Atualizar
Substitua `index.html` e `dados/*.json` pelos arquivos novos e rode `npx vercel deploy --prod` (ou faça push no GitHub).

Fora do claude.ai, a seção de validação (acesso restrito) não aparece e os relatórios/planilhas são baixados direto pelo navegador.
