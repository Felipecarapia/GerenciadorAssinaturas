# Gerenciador de Assinaturas

Aplicação web em Python + Streamlit que centraliza as assinaturas de software da empresa
sobre uma planilha do Google Sheets: quanto se gasta, quem usa cada ferramenta e o que
vence nos próximos dias.

Implementa os requisitos RF-01 a RF-30 do plano de desenvolvimento.

## Desenvolvimento local (sem Google)

O uso normal exige Google Sheets. Para desenvolvimento, o modo local precisa ser ativado
explicitamente; os dados ficam em `dados_locais/planilha_local.xlsx`.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
$env:GA_FORCAR_LOCAL="1"     # PowerShell
streamlit run app.py
```

Senha: `demo`. Na primeira tela, clique em **Carregar dados de exemplo** (20 assinaturas,
15 pessoas, histórico de 12 meses e algumas pendências de propósito).

## Estrutura

```
app.py                     login + menu no topo (st.navigation)
paginas/                   Dashboard, Assinaturas, Pessoas, Projetos, Relatórios, Histórico, Pendências
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

## Colocar em produção (passo a passo)

### 1. Conta de serviço do Google Cloud
1. Em <https://console.cloud.google.com>, com a conta da instituição, crie um projeto.
2. **APIs e serviços › Biblioteca**: ative **Google Sheets API** (e Google Drive API).
3. **IAM › Contas de serviço › Criar**. Depois, em **Chaves › Adicionar chave › JSON**.
   Guarde o arquivo baixado: ele é a senha do app para a planilha.

### 2. Planilha
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

### 3. Histórico das edições feitas na planilha
Na planilha: **Extensões › Apps Script**, cole `apps_script/historico.gs`, salve, escolha a
função `instalarGatilho` e clique em **Executar** (com a conta dona da planilha).

### 4. Publicar no Streamlit Community Cloud
1. Envie o projeto para um **repositório privado** no GitHub (o `.gitignore` já impede
   que `secrets.toml` e arquivos `.json` subam).
2. Em <https://share.streamlit.io>: **Create app**, escolha o repositório, arquivo `app.py`,
   Python 3.13.
3. Em **Advanced settings › Secrets**, cole o conteúdo do seu `secrets.toml`.
4. Em **Share**, convide por e-mail quem administra as assinaturas. O acesso fica com duas
   camadas: o convite do Streamlit e a senha do app.

O `packages.txt` instala o Chromium no servidor para o Kaleido desenhar os gráficos dos
PDFs. Se ele não estiver disponível, os PDFs usam gráficos equivalentes em matplotlib.

## Guia rápido de uso

| Tarefa | Onde |
|---|---|
| Ver gasto, gráficos e o que vence | **Dashboard**. **Atualizar** busca na hora o que foi editado na planilha (o app relê sozinho a cada 60 s). |
| Cadastrar uma ferramenta | **Assinaturas › Nova assinatura**. Toda assinatura precisa de pelo menos 1 usuário, então cadastre as pessoas antes. |
| Editar, excluir, ver histórico | Clique na linha da tabela e use os botões acima dela. |
| Quem usa o quê / custo por pessoa | **Pessoas**: clique numa pessoa para ver as assinaturas e o custo mensal que ela representa (cada assinatura é dividida igualmente entre os usuários). |
| Onde cada assinatura é usada | **Projetos**: cadastre o projeto e vincule suas assinaturas. O custo é dividido igualmente entre os projetos ativos que usam cada assinatura. |
| Relatórios | **Relatórios**: prévia na tela e download em PDF ou Excel. |
| Dados com problema | **Pendências**: cada item mostra aba e linha, com botão para corrigir no app. |
| Tema claro/escuro | Menu **⋮ › Settings** (o Streamlit lembra a escolha no navegador). |

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
- **Login**: 5 senhas erradas bloqueiam aquele endereço IP por 5 minutos. Recarregar a página
  ou fechar a aba pede a senha de novo. "Quem" no Histórico é o e-mail do convidado do
  Streamlit Cloud, quando disponível; senão, "app".
- O CSS dos cards depende de nomes internos do Streamlit: a versão está fixa no
  `requirements.txt`. Ao atualizar, rode os testes e confira o dashboard.
