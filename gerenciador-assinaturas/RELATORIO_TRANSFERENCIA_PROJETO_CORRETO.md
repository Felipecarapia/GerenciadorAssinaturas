# Relatório de transferência — Gerenciador de Assinaturas

## Contexto importante

As implementações descritas neste documento foram feitas por engano na cópia localizada em:

`C:\Users\fcarapia\Desktop\GerenciadorAssinaturas`

A aplicação realmente utilizada, identificada pela interface exibida em captura de tela, está em:

`C:\Users\fcarapia\Downloads\gerenciador-assinaturas\gerenciador-assinaturas`

Não copiar arquivos inteiros da versão da Área de Trabalho para a versão correta. As arquiteturas são diferentes. O projeto correto possui, entre outros elementos, `componentes/ui.py`, `componentes/dialogos.py`, uma tabela selecionável e uma camada de dados acessada por `base()`. As funcionalidades abaixo devem ser adaptadas à arquitetura do projeto correto.

## Pedido original e decisões confirmadas

- O Google Sheets deve ser a única fonte oficial de dados.
- Não deve existir fallback silencioso para Excel ou outra base local durante o uso normal.
- O documento de requisitos é:
  `C:\Users\fcarapia\Downloads\Gerenciador de Assinaturas — Relatório Técnico (2).pdf`
- A aplicação deve seguir os requisitos RF-01 a RF-30 descritos nesse PDF.
- A funcionalidade mais recente solicitada é registrar o pagamento de uma assinatura e avançar automaticamente seu vencimento.

## Diagnóstico feito na primeira cópia

O projeto analisado inicialmente era Python com Streamlit, dividido em páginas e serviços, com:

- autenticação por senha;
- dashboard;
- assinaturas;
- colaboradores;
- histórico;
- pendências;
- relatórios PDF e Excel;
- integração com Google Sheets;
- Apps Script para auditoria de edições diretas.

Foram identificados os seguintes riscos ou lacunas na cópia analisada:

1. Existia fallback silencioso para um Excel local.
2. O salvamento limpava e regravava abas completas do Google Sheets.
3. A proteção de edição simultânea do RF-16 não estava efetivamente implementada.
4. O histórico podia ser sobrescrito por operações usando dados antigos.
5. Valor igual a zero era aceito, embora o requisito determine valor positivo.
6. O histórico não possuía filtro por período.
7. A busca de pessoas não incluía departamento.
8. O painel de pendências não oferecia correção direta.
9. Faltava o PDF do RF-30.
10. As dependências não estavam fixadas.
11. CORS/XSRF estavam desabilitados.
12. Existia senha padrão `admin` caso o segredo não estivesse configurado.

Esses itens devem ser novamente verificados no projeto correto antes de qualquer alteração, pois ele possui implementação diferente e alguns deles podem já estar resolvidos.

## Alterações realizadas na cópia errada

### Google Sheets como fonte única

- Remoção do fallback para Excel local.
- Erro amigável quando a planilha estiver indisponível.
- Bloqueio de gravações fora do Google Sheets.
- Remoção da geração automática de dados fictícios no fluxo normal.

### Persistência granular

- Alteração de somente uma linha por ID em vez de limpar e regravar abas completas.
- Inclusão por `append_row`/`append_rows`.
- Exclusão somente da linha correspondente.
- Histórico incluído por anexação, sem reescrever a aba.

### Concorrência — RF-16

- O formulário recebe uma fotografia dos dados originais.
- Antes de salvar ou excluir, a linha é relida diretamente do Sheets.
- Se os dados atuais forem diferentes dos dados que abriram o formulário, a operação é recusada.
- Mensagem usada: a assinatura ou o colaborador foi alterado por outra pessoa; atualizar a página antes de continuar.

### Histórico

- Centralização dos eventos da operação.
- Registro de criação, mudança de valor, plano, status, vínculo e desvínculo.
- Registro de vínculos alterados tanto pela tela de Assinaturas quanto pela tela de Pessoas.
- Filtro por período.
- Ordenação do evento mais recente para o mais antigo.
- Escape de valores apresentados em HTML para evitar injeção a partir da planilha.

### Validações e pendências

- Valor deve ser estritamente maior que zero.
- Data de vencimento obrigatória e válida.
- Categoria, plano e status obrigatórios.
- Departamento obrigatório.
- Nome da assinatura obrigatório, único e sem vírgula.
- E-mail obrigatório, válido, normalizado e único.
- Detecção de vínculos com assinaturas inexistentes.
- Filtro de pendências por aba.
- Botão de correção direta abrindo o formulário do item.

### Interface

- Inclusão de tabela ordenável de assinaturas na cópia errada.
- Busca de pessoas alterada para nome, e-mail ou departamento.
- Ações de edição e exclusão receberam rótulos mais visíveis.

Observação: a interface do projeto correto já possui uma tabela selecionável. Portanto, não recriar os cartões da cópia errada. O novo botão de pagamento deve seguir o padrão da interface correta.

### Relatórios

- Inclusão do PDF de colaboradores e gastos por departamento, completando o RF-30.
- Prévia do relatório de vencimentos.
- Sanitização e deduplicação dos nomes das abas geradas no Excel.

### Segurança e configuração

- Remoção da senha padrão `admin`.
- `app_password` passou a ser obrigatório nos Secrets.
- CORS e proteção XSRF foram habilitados.
- Versões das dependências foram fixadas de acordo com o ambiente testado.

## Funcionalidade prioritária: “Marcar como pago”

### Comportamento solicitado

Na página Assinaturas, o usuário seleciona uma linha e clica em **Marcar como pago**. A versão correta da tela possui atualmente os botões:

- Nova assinatura;
- Editar;
- Excluir;
- Histórico.

O botão **Marcar como pago** deve ser incluído junto dessas ações e permanecer desabilitado enquanto nenhuma linha estiver selecionada.

### Regras do vencimento

- Plano mensal: avançar exatamente um mês a partir do vencimento armazenado.
  - `17/10/2026` → `17/11/2026`.
  - Novo pagamento: `17/11/2026` → `17/12/2026`.
- Plano anual: avançar exatamente um ano.
- Plano vitalício: não permitir registro de pagamento recorrente; ocultar ou desabilitar o botão.
- Preservar o dia sempre que possível.
- Quando o dia não existir no novo mês, usar o último dia disponível:
  - `31/01/2026` → `28/02/2026`.
  - `29/02/2024`, no plano anual → `28/02/2025`.
- O avanço deve partir do vencimento existente, não da data atual do computador.
- Se houver várias mensalidades atrasadas, cada confirmação avança somente um ciclo.

### Confirmação

Antes de gravar, abrir um diálogo informando:

- nome da assinatura;
- tipo de plano;
- vencimento atual;
- novo vencimento calculado.

O diálogo deve conter Cancelar e Confirmar pagamento.

### Gravação

- Reler a linha no Google Sheets antes de gravar.
- Comparar com os dados que estavam selecionados/abertos.
- Recusar a operação se outra pessoa tiver alterado a assinatura.
- Atualizar somente a célula/linha necessária.
- Limpar o cache após sucesso.
- Não alterar automaticamente outros campos sem requisito explícito. Em especial, não mudar o status silenciosamente.

### Histórico do pagamento

Adicionar evento:

- Evento: `Pagamento registrado`.
- Campo: `Vencimento`.
- Valor anterior: vencimento antes do pagamento.
- Valor novo: próximo vencimento.
- Origem: `App`.
- Responsável: usuário padrão adotado pelo projeto.
- Data e hora: momento da confirmação.

### Local correto na interface encontrada

Arquivo identificado:

`paginas/assinaturas.py`

A tabela usa `st.dataframe(..., on_select="rerun", selection_mode="single-row")`. O ID selecionado fica em `sel`. Os botões são construídos nas variáveis `b1`, `b2`, `b3` e `b4`. Incluir uma nova coluna/botão junto deles, preferencialmente após Histórico ou antes dele:

`Marcar como pago`, com ícone Material apropriado, por exemplo `:material/check_circle:` ou `:material/payments:`.

O botão deve ser habilitado somente quando:

- `sel` não for `None`;
- o plano selecionado for Mensal ou Anual;
- o vencimento for válido.

O diálogo deve ser implementado seguindo o padrão já existente em `componentes/dialogos.py`.

A operação de dados deve seguir a abstração real usada por `componentes.ui.base()` e pelos serviços do projeto correto. Não importar a classe criada na cópia errada sem antes mapear a camada correta.

## Testes implementados na cópia errada

A suíte passou de 5 para 13 testes e terminou com todos aprovados. Foram adicionados testes para:

- detecção de edição concorrente;
- ausência de falso conflito sem alteração;
- conversão de valores monetários;
- sanitização e deduplicação de nomes de abas Excel;
- geração do PDF de pessoas e departamentos;
- avanço mensal;
- virada de dezembro para janeiro;
- avanço anual;
- ajuste de 31 de janeiro para o último dia de fevereiro;
- ajuste de ano bissexto;
- rejeição de plano vitalício;
- simulação completa do pagamento atualizando a linha e anexando o histórico, sem acessar a planilha real.

No projeto correto, criar testes equivalentes usando os mocks, fixtures e abstrações que já existirem nele.

## Validação obrigatória no projeto correto

Antes de considerar concluído:

1. Ler integralmente o `README.md`, instruções do repositório e testes do projeto correto.
2. Mapear a camada retornada por `base()` e descobrir como ela atualiza uma assinatura.
3. Confirmar que nenhum teste toca a planilha real.
4. Executar a suíte existente antes das alterações.
5. Implementar a regra de avanço como função pura e testável.
6. Testar mensal, anual, vitalício, fim do mês, ano bissexto e conflito.
7. Executar todos os testes após as alterações.
8. Inicializar a interface e verificar que o botão aparece ao selecionar Claude ou ChatGPT na tabela.
9. Confirmar que o botão fica desabilitado sem seleção.
10. Confirmar que a data muda no Sheets e o evento aparece no Histórico somente após confirmação real do usuário.

## Arquivos alterados na cópia errada

- `app.py`
- `.streamlit/config.toml`
- `README.md`
- `requirements.txt`
- `servicos/planilha.py`
- `servicos/calculos.py`
- `servicos/relatorios.py`
- `paginas/assinaturas.py`
- `paginas/pessoas.py`
- `paginas/historico.py`
- `paginas/pendencias.py`
- `paginas/relatorios.py`
- `tests/test_calculos.py`
- `tests/test_planilha.py`
- `tests/test_relatorios.py`

## Prompt sugerido ao abrir o projeto correto

> Leia integralmente o arquivo `RELATORIO_TRANSFERENCIA_PROJETO_CORRETO.md` que estou anexando. Primeiro inspecione a arquitetura desta versão e compare cada recomendação com o código real; não copie arquivos inteiros da outra versão. Implemente prioritariamente a função “Marcar como pago” na tabela de Assinaturas, junto de Editar, Excluir e Histórico, com confirmação, avanço mensal/anual, tratamento de fim de mês, proteção contra conflito e registro no Histórico. Depois audite e adapte as demais correções do relatório que ainda forem necessárias neste projeto. Execute a suíte antes e depois e não escreva na planilha real durante os testes.
