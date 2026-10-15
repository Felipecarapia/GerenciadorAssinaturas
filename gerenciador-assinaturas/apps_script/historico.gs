/**
 * Gerenciador de Assinaturas — registro no Histórico das edições feitas
 * DIRETO na planilha (RF-22 e RF-23). O app registra as próprias alterações.
 *
 * COMO INSTALAR (uma vez só, com a conta dona da planilha):
 *   1. Na planilha: Extensões > Apps Script.
 *   2. Apague o conteúdo de Código.gs e cole este arquivo inteiro. Salve.
 *   3. No seletor de funções, escolha "instalarGatilho" e clique em Executar.
 *      Autorize o acesso quando o Google pedir.
 *
 * Por que um gatilho "instalável" e não o onEdit simples?
 *   O gatilho instalável roda com a permissão de quem o instalou. Assim ele
 *   consegue gravar na aba Histórico mesmo com ela protegida contra edição
 *   pelos outros editores.
 *
 * Limites do Google: exclusão de linhas não dispara edição (não é registrada);
 * ao colar várias células de uma vez o Google não informa o valor anterior.
 */

const ABA_ASSINATURAS = 'Assinaturas';
const ABA_FUNCIONARIOS = 'Funcionários';
const ABA_HISTORICO = 'Histórico';

const EVENTO_POR_COLUNA = {
  'Nome': 'Assinatura renomeada',
  'Plano': 'Plano alterado',
  'Valor (R$)': 'Valor alterado',
  'Status': 'Status alterado',
};

/** Rode uma vez para ligar o registro automático. */
function instalarGatilho() {
  const planilha = SpreadsheetApp.getActive();
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'registrarEdicao')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('registrarEdicao').forSpreadsheet(planilha).onEdit().create();
  SpreadsheetApp.getUi().alert('Pronto! As edições feitas na planilha serão registradas no Histórico.');
}

/** Chamado pelo Google a cada edição feita por uma pessoa na planilha. */
function registrarEdicao(e) {
  try {
    registrar_(e);
  } catch (erro) {
    console.error('Histórico: ' + erro);
  }
}

function registrar_(e) {
  if (!e || !e.range) return;
  const aba = e.range.getSheet();
  const nomeAba = aba.getName();
  if (nomeAba !== ABA_ASSINATURAS && nomeAba !== ABA_FUNCIONARIOS) return;
  if (e.range.getLastRow() < 2) return;

  const cabecalho = aba.getRange(1, 1, 1, aba.getLastColumn()).getValues()[0].map(String);
  const col = nome => cabecalho.indexOf(nome); // base 0
  const quem = emailDoUsuario_();
  const agora = new Date();
  const umaCelula = e.range.getNumRows() === 1 && e.range.getNumColumns() === 1;
  const registros = [];

  const primeiraLinha = Math.max(2, e.range.getRow());
  const ultimaLinha = e.range.getLastRow();
  const linhas = aba.getRange(primeiraLinha, 1, ultimaLinha - primeiraLinha + 1, cabecalho.length).getValues();

  linhas.forEach((linha, i) => {
    const numeroLinha = primeiraLinha + i;
    const linhaNova = garantirId_(aba, nomeAba, numeroLinha, linha, col);

    for (let c = e.range.getColumn(); c <= e.range.getLastColumn(); c++) {
      const nomeColuna = cabecalho[c - 1];
      const novo = linha[c - 1];
      const anterior = umaCelula ? (e.oldValue === undefined ? '' : e.oldValue) : '(não disponível)';

      if (nomeAba === ABA_ASSINATURAS && EVENTO_POR_COLUNA[nomeColuna]) {
        const nomeAssinatura = String(linha[col('Nome')] || '').trim();
        if (nomeColuna === 'Nome' && (anterior === '' || linhaNova) && nomeAssinatura) {
          const resumo = [linha[col('Plano')], formatarValor_(linha[col('Valor (R$)')]), linha[col('Status')]]
            .filter(v => String(v).trim() !== '').join(' · ');
          registros.push([agora, 'planilha', quem, nomeAssinatura, 'Assinatura criada', '', '', resumo]);
          continue;
        }
        if (!nomeAssinatura && nomeColuna !== 'Nome') continue; // linha ainda sem nome
        const ant = nomeColuna === 'Valor (R$)' ? formatarValor_(anterior) : String(anterior);
        const nov = nomeColuna === 'Valor (R$)' ? formatarValor_(novo) : String(novo);
        if (ant === nov) continue;
        registros.push([agora, 'planilha', quem, nomeAssinatura || ant, EVENTO_POR_COLUNA[nomeColuna],
                        nomeColuna, ant, nov]);
      }

      if (nomeAba === ABA_FUNCIONARIOS && nomeColuna === 'Assinaturas') {
        const pessoa = String(linha[col('Nome completo')] || '').trim() || ('linha ' + numeroLinha);
        const antes = umaCelula ? separar_(anterior) : [];
        const depois = separar_(novo);
        depois.filter(n => antes.indexOf(n) < 0).forEach(n =>
          registros.push([agora, 'planilha', quem, n, 'Usuário vinculado', 'Usuários', '', pessoa]));
        antes.filter(n => depois.indexOf(n) < 0).forEach(n =>
          registros.push([agora, 'planilha', quem, n, 'Usuário desvinculado', 'Usuários', pessoa, '']));
      }
    }
  });

  if (registros.length) {
    const hist = SpreadsheetApp.getActive().getSheetByName(ABA_HISTORICO);
    hist.getRange(hist.getLastRow() + 1, 1, registros.length, registros[0].length).setValues(registros);
  }
}

/** Linha incluída à mão: gera o ID (o app também gera, se este falhar).
 *  Retorna true quando a linha é nova (acabou de ganhar um ID). */
function garantirId_(aba, nomeAba, numeroLinha, linha, col) {
  const iId = col('ID');
  const iNome = col(nomeAba === ABA_ASSINATURAS ? 'Nome' : 'Nome completo');
  if (iId < 0 || iNome < 0) return false;
  if (String(linha[iId]).trim() === '' && String(linha[iNome]).trim() !== '') {
    const prefixo = nomeAba === ABA_ASSINATURAS ? 'A-' : 'F-';
    const id = prefixo + Utilities.getUuid().replace(/-/g, '').slice(0, 6).toUpperCase();
    try {
      aba.getRange(numeroLinha, iId + 1).setValue(id);
      linha[iId] = id;
    } catch (erro) {
      console.warn('Sem permissão para gravar o ID: ' + erro);
    }
    return true;
  }
  return false;
}

function separar_(texto) {
  return String(texto || '').split(',').map(s => s.trim()).filter(s => s !== '');
}

function formatarValor_(v) {
  if (v === '' || v === undefined || v === null) return '';
  if (typeof v === 'number') return v.toFixed(2);
  let s = String(v).replace('R$', '').replace(/\s/g, '');
  if (s.indexOf(',') >= 0) s = s.replace(/\./g, '').replace(',', '.');
  const n = Number(s);
  return isNaN(n) ? String(v) : n.toFixed(2);
}

function emailDoUsuario_() {
  try {
    return Session.getActiveUser().getEmail() || 'planilha';
  } catch (erro) {
    return 'planilha';
  }
}
