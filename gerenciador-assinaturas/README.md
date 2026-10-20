# Licenzy

Sistema de gestão de assinaturas do Instituto Recôncavo de Tecnologia.

O Licenzy usa uma SPA em React + TypeScript no navegador e uma API FastAPI que reaproveita
integralmente o núcleo Python existente. O Google Sheets continua como fonte de verdade:
quanto se gasta, quem usa cada ferramenta e o que vence nos próximos dias.

Durante a migração, a interface Streamlit permanece disponível em paralelo. `servicos/`,
o formato das seis abas, os cálculos e os relatórios não foram alterados.

Implementa os requisitos RF-01 a RF-30 do plano de desenvolvimento.

## Desenvolvimento local (sem Google)

O uso normal exige Google Sheets. Para desenvolvimento, o modo local precisa ser ativado
explicitamente; os dados ficam em `dados_locais/planilha_local.xlsx`.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
$env:GA_FORCAR_LOCAL="1"     # PowerShell
$env:LICENZY_SESSION_KEY="uma-chave-local"
uvicorn api.main:app --reload --port 8000
```

Em outro terminal:

```bash
cd web
npm install
npm run dev
```

Abra `http://localhost:5173`. Senha: `demo` quando não houver senha configurada nos
Secrets. Na primeira tela vazia, clique em **Carregar dados de exemplo** (20 assinaturas,
15 pessoas, histórico de 12 meses e algumas pendências de propósito).

Para abrir temporariamente a interface anterior: `streamlit run app.py`.

## Estrutura

```
web/                       React, TypeScript, Tailwind, TanStack, Recharts e componentes de UI
api/                       FastAPI, autenticação e adaptadores HTTP para o núcleo
app.py + paginas/          interface Streamlit mantida apenas durante a transição
servicos/planilha.py       ÚNICA camada que lê e grava (Google Sheets ou modo local)
servicos/cadastros.py      validação, vínculos nos 2 sentidos, histórico, edição simultânea
servicos/calculos.py       gasto mensal, alertas, custo por pessoa, evolução em 12 meses
servicos/pendencias.py     dados inconsistentes da planilha
servicos/relatorios.py     5 relatórios em PDF (fpdf2) e Excel (openpyxl)
servicos/graficos.py       4 gráficos Plotly
componentes/               login, janelas de cadastro, peças de interface
apps_script/historico.gs   gatilho que registra as edições feitas direto na planilha
scripts/                   criar a planilha modelo e preencher dados de exemplo
tests/                     pytest (regras e cadastros) + Playwright (navegador)
```

## Colocar em produção na Vercel

O build gera `web/dist` e o FastAPI declara esse diretório com `app.frontend()`. A Vercel
entrega o frontend pela CDN e executa `api/main.py` como uma função Python na região `gru1`.

No projeto da Vercel, use este diretório como **Root Directory** e configure:

| Variável | Conteúdo |
|---|---|
| `LICENZY_SECRETS_TOML` | Conteúdo completo do `.streamlit/secrets.toml` |
| `LICENZY_SESSION_KEY` | Chave longa e aleatória para assinar o cookie de sessão |
| `UPSTASH_REDIS_REST_URL` | Criada pela integração Upstash Redis |
| `UPSTASH_REDIS_REST_TOKEN` | Criada pela integração Upstash Redis |
| `VERCEL_SUPPORT_LARGE_FUNCTIONS` | `1` |

Instale a integração Upstash Redis no projeto. Ela preserva o bloqueio de cinco erros de
senha por cinco minutos mesmo quando a Vercel alterna entre instâncias da função.

Nunca defina `GA_FORCAR_LOCAL` na Vercel e nunca versione `.streamlit/secrets.toml`.

### Configurar o Google Sheets

#### 1. Conta de serviço do Google Cloud
1. Em <https://console.cloud.google.com>, com a conta da instituição, crie um projeto.
2. **APIs e serviços › Biblioteca**: ative **Google Sheets API** (e Google Drive API).
3. **IAM › Contas de serviço › Criar**. Depois, em **Chaves › Adicionar chave › JSON**.
   Guarde o arquivo baixado: ele é a senha do app para a planilha.

#### 2. Planilha
1. Crie uma planilha nova (ou use a existente) e **compartilhe como Editor** com o
   `client_email` da conta de serviço (`...@...iam.gserviceaccount.com`).
   Se o Workspace bloquear e-mails externos, a TI precisa liberar esse e-mail.
2. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e preencha a
   senha do app, o link da planilha e os campos do JSON da conta de serviço.
3. Rode `python scripts/criar_planilha_modelo.py`. Ele cria as 4 abas, as listas suspensas,
   validações (nome sem vírgula, valor > 0, data, e-mail), formatos e proteções
   (aba Histórico bloqueada; coluna ID com aviso).
4. **Passo manual:** aba Funcionários › coluna Assinaturas › Dados › Validação de dados ›
   marque **Permitir seleções múltiplas**. (O Google não permite fazer isso pela API.)
5. Opcional, só numa planilha de testes: `python scripts/dados_exemplo.py`.

#### 3. Histórico das edições feitas na planilha
Na planilha: **Extensões › Apps Script**, cole `apps_script/historico.gs`, salve, escolha a
função `instalarGatilho` e clique em **Executar** (com a conta dona da planilha).

### Primeiro deploy

1. Envie o projeto para um repositório privado no GitHub.
2. Na Vercel, crie um projeto e selecione este diretório como raiz.
3. Instale o Upstash Redis e cadastre as variáveis acima em Production e Preview.
4. Faça o deploy, abra `/login` e confirme o bloqueio após cinco senhas erradas.
5. Baixe um PDF de cada relatório e teste a atualização após editar a planilha diretamente.

Na Vercel, os PDFs usam automaticamente o fallback Matplotlib quando o Chromium não está
disponível.

## Guia rápido de uso

| Tarefa | Onde |
|---|---|
| Ver gasto, gráficos e o que vence | **Dashboard**. **Atualizar** busca na hora o que foi editado na planilha (o app relê sozinho a cada 60 s). |
| Cadastrar uma ferramenta | **Assinaturas › Nova assinatura**. Toda assinatura precisa de pelo menos 1 usuário, então cadastre as pessoas antes. |
| Editar, excluir, ver histórico | Abra o menu de ações da linha. |
| Quem usa o quê / custo por pessoa | **Pessoas**: clique numa pessoa para ver as assinaturas e o custo mensal que ela representa (cada assinatura é dividida igualmente entre os usuários). |
| Onde cada assinatura é usada | **Projetos**: cadastre o projeto e vincule suas assinaturas. O custo é dividido igualmente entre os projetos ativos que usam cada assinatura. |
| Relatórios | **Relatórios**: prévia na tela e download em PDF ou Excel. |
| Dados com problema | **Pendências**: cada item mostra aba e linha, com botão para corrigir no app. |
| Tema claro/escuro | Botão no rodapé do menu lateral; a escolha fica salva no navegador. |

**Regras importantes**
- Renomeie assinaturas **pelo app**: ele troca o nome em todas as pessoas. Renomear direto na
  planilha deixa escolhas antigas inválidas (aparecem em Pendências).
- Nome de assinatura **sem vírgula** (a planilha separa as escolhas por vírgula).
- Gasto mensal: soma só as **ativas**; anual ÷ 12, semestral ÷ 6, trimestral ÷ 3;
  vitalício não entra. Gasto anual = mensal × 12.
- Alertas: 🔴 vencida ou até 7 dias · 🟡 8 a 30 dias · 🟢 acima de 30. Canceladas não alertam.
- Se alguém alterou a mesma assinatura na planilha enquanto você editava, o app avisa e
  **não sobrescreve**: clique em recarregar e refaça a edição.

## Testes

```bash
pip install -r requirements-dev.txt
playwright install chromium
pytest                     # regras, cadastros, motor do Sheets (simulado) e navegador
cd web
npm ci
npm run typecheck
npm run lint
npm run build
```

Os testes usam sempre uma planilha local temporária; nunca tocam no Google Sheets.
O teste de navegador sobe o app numa porta livre e percorre login, todas as páginas,
o cadastro pela janela (com validação) e a tela de celular.

## Decisões e limites

- **Gravação em modo RAW** no Sheets: datas vão como data de verdade e o texto nunca é
  "reinterpretado" pela localidade da planilha (ex.: `150.00` no Histórico continua texto).
- **ID** curto com prefixo (`A-7F3C2B`, `F-91D0AE`). Linhas digitadas à mão ganham ID na
  próxima leitura do app (ou pelo Apps Script).
- **Evolução em 12 meses** é reconstruída a partir do Histórico (desfaz valor, plano, status e
  nome mês a mês). Assinaturas excluídas não aparecem nos meses anteriores.
- **Apps Script**: exclusão de linhas direto na planilha não gera evento de edição no Google,
  então não entra no Histórico; ao colar várias células de uma vez, o Google não informa
  o valor anterior (fica "(não disponível)").
- **Login**: 5 senhas erradas bloqueiam aquele endereço IP por 5 minutos. A sessão usa cookie
  assinado, `HttpOnly`, `Secure` e `SameSite=Strict`; fechar o navegador encerra a sessão.
- A interface antiga ainda existe apenas para permitir comparação durante a migração. Ela
  será removida no corte final, depois da aprovação visual e funcional do novo frontend.
