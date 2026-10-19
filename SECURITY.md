# Segurança

O Observatório da Integridade – SP publica apenas informações de fontes públicas. O site é estático e não tem login, formulários nem envio de arquivos.

Medidas em vigor:
- HTTPS obrigatório (HSTS) e cabeçalhos de segurança (CSP, X-Frame-Options, Permissions-Policy, nosniff, COOP).
- Bibliotecas externas com versão fixa e verificação de integridade (SRI).
- Funções /api somente leitura (GET), restritas à origem do site e a acessos do Brasil, com CNPJ validado e limite de requisições por IP.
- Banco de dados com RLS em todas as tabelas, leitura pública e escrita bloqueada para perfis públicos; nenhum CPF é armazenado.
- Nenhum segredo no repositório: a chave do Supabase presente nos scripts é a chave pública (publishable).

Para relatar uma vulnerabilidade, abra um aviso privado em "Security › Report a vulnerability" neste repositório, sem divulgar detalhes publicamente.
