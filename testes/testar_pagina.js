// Confere a lógica da página (logica.js) no Node, com o extrato fictício.
//   node testes/testar_pagina.js [outro_extrato.xls]   tem que terminar com "ok"
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const XLSX = require('../vendor/xlsx.full.min.js');
const P = require('../logica.js');

function ler(arq) {
  const livro = XLSX.read(fs.readFileSync(arq), { type: 'buffer', cellDates: true });
  return XLSX.utils.sheet_to_json(livro.Sheets[livro.SheetNames[0]], { header: 1, raw: true, defval: '', blankrows: false });
}

(async () => {
  const arq = process.argv[2] || path.join(__dirname, '..', 'exemplos', 'extrato_ficticio_padaria.xls');
  const lancs = P.lerLinhas(ler(arq));
  const ms = P.meses(lancs);
  if (process.argv[2]) {  // extrato real: só imprime os totais para comparar com o Python
    const ref = P.mesPadrao(lancs, new Date());
    const d = P.calcular(lancs, ref);
    console.log(JSON.stringify({ ref, entradas: d.entradas, saidas: d.saidas, cats: d.catDesp.length, alertas: d.alertas.length, lanc: lancs.length }));
    return;
  }
  assert.strictEqual(lancs.filter(x => x.transferencia).length, 24);
  assert.strictEqual(ms.length, 12);
  assert.strictEqual(P.mesPadrao(lancs, new Date(2026, 9, 20)), 202609);
  assert.strictEqual(P.mesPadrao(lancs, new Date(2026, 10, 3)), 202610);
  const d = P.calcular(lancs, 202610);
  assert.strictEqual(d.catDesp.reduce((a, b) => a + b[1], 0), d.saidas);
  assert.strictEqual(d.catRec.reduce((a, b) => a + b[1], 0), d.entradas);
  assert.strictEqual(d.resultado, d.entradas - d.saidas);
  assert.ok(d.alertas.some(a => a.includes('Energia elétrica')), d.alertas);
  assert.strictEqual(d.serie.length, 12);
  // o gráfico termina no mês do painel, sem repetir mês
  assert.deepStrictEqual(d.serie.map(x => x[0]), [202511, 202512, 202601, 202602, 202603, 202604, 202605, 202606, 202607, 202608, 202609, 202610]);
  assert.strictEqual(d.serie[11][1], d.entradas);

  const html = P.montar(d, { cliente: 'Padaria <Modelo>', nomeBpo: 'BPO Teste', corCliente: '#123456', corDestaque: 'javascript:x',
    logoCliente: 'data:image/png;base64,iVBORw0KGgo=', logoBpo: 'https://fora.com/x.png', comentario: 'Rever energia.' });
  ['Quanto entrou?', 'Quanto saiu?', 'Sobrou dinheiro?', 'O mês em 3 linhas', 'O que eu preciso olhar?', 'Estou melhor do que antes?',
    'Para onde foi o dinheiro?', 'De onde veio o dinheiro?', 'Quais foram os maiores pagamentos?', 'O que o seu BPO recomenda?']
    .forEach(p => assert.ok(html.includes(p), p));
  assert.ok(html.includes('Padaria &lt;Modelo&gt;') && !html.includes('Padaria <Modelo>'));
  assert.ok(html.includes('#123456') && html.includes('#2EA8E6') && !html.includes('javascript:x'));  // cor inválida vira a padrão
  assert.ok(html.includes('data:image/png;base64,iVBORw0KGgo=') && !html.includes('fora.com'));     // só logo embutida
  assert.ok(!/<script/i.test(html));

  // cadeado: o arquivo trancado não tem os números, e abre só com a senha certa
  const senha = P.novaSenha(globalThis.crypto);
  assert.ok(/^[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$/.test(senha));
  const fechado = await P.trancar(html, senha, { rodadas: 2000, titulo: 'Teste' }, globalThis.crypto);
  assert.ok(fechado.includes(P.MARCA_TRANCADO) && !fechado.includes('Quanto entrou?') && !fechado.includes(P.reais(d.entradas)));
  const pac = JSON.parse(/const P=(\{.*?\});/.exec(fechado)[1]);
  const abrir = async s => {
    const c = globalThis.crypto.subtle, b = x => Uint8Array.from(Buffer.from(x, 'base64'));
    const k0 = await c.importKey('raw', new TextEncoder().encode(s.trim().toUpperCase()), 'PBKDF2', false, ['deriveKey']);
    const k = await c.deriveKey({ name: 'PBKDF2', salt: b(pac.sal), iterations: pac.rodadas, hash: 'SHA-256' }, k0, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
    return new TextDecoder().decode(await c.decrypt({ name: 'AES-GCM', iv: b(pac.iv) }, k, b(pac.dados)));
  };
  assert.strictEqual(await abrir(senha.toLowerCase()), html);  // minúscula também abre
  await assert.rejects(abrir('AAAA-BBBB-CCCC'));

  // arquivo que não é o extrato: mensagem clara
  assert.throws(() => P.lerLinhas([['Data', 'Valor']]), /extrato financeiro do Conta Azul/);
  console.log('ok: leitura, transferências, conta do mês, alertas, 10 perguntas, marca, cadeado');
})().catch(e => { console.error(e); process.exit(1); });
